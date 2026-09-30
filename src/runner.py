"""Sensor-independent run loops for standalone and server mode.

The entry scripts (main.py, main_v1.py, server.py, server_v1.py) only choose the
depth sensor and the config file and then call run_standalone() / run_server().
"""

import json
import signal
import socket
import sys
import time

import cv2

from calibration import CalibrationAborted, Calibrator
from common import load_calibration, resolve_path, save_calibration
from touch_detection import GestureTracker, TouchDetector, capture_baseline, map_to_projector

PREVIEW_WINDOW = "Interactive Projector Pipeline"


def _install_sigterm_handler():
    # systemd stops services with SIGTERM -> turn it into a clean exit (finally-blocks run)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))


def _setup_detector(sensor, config):
    baseline, noise = capture_baseline(
        sensor, int(config["BASELINE_FRAMES"]), float(config["BASELINE_DELAY_SEC"])
    )
    return TouchDetector(config, baseline, noise)


def _get_homography(sensor, config, detector, display, force: bool):
    path = resolve_path(config["CALIBRATION_FILE"])
    cam_shape = detector.baseline.shape
    homography = None if force else load_calibration(path, config, cam_shape)
    if homography is None:
        homography = Calibrator(config).run(sensor, detector, display)
        save_calibration(path, homography, config, cam_shape)
    return homography


def _render_preview(mask, detector, point):
    vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    if detector.roi_polygon is not None:
        cv2.polylines(vis, [detector.roi_polygon], True, (0, 255, 0), 1)
    if point is not None:
        cv2.circle(vis, (int(point[0]), int(point[1])), 6, (0, 0, 255), 2)
    cv2.putText(vis, "q=quit  b=baseline  c=calibrate", (5, vis.shape[0] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.imshow(PREVIEW_WINDOW, vis)
    return cv2.waitKey(1) & 0xFF


# --------------------------------------------------------------------------- #
# Standalone: sensor + projector + mouse on the same machine
# --------------------------------------------------------------------------- #
def run_standalone(sensor, config: dict, args) -> None:
    from mouse_output import MouseController
    from projector_display import ProjectorWindow

    _install_sigterm_handler()
    w, h = int(config["PROJECTOR_WIDTH"]), int(config["PROJECTOR_HEIGHT"])
    display = ProjectorWindow(w, h, config["PROJECTOR_OFFSET_X"], config["PROJECTOR_OFFSET_Y"])
    preview = not args.no_preview

    detector = _setup_detector(sensor, config)
    try:
        homography = _get_homography(sensor, config, detector, display, args.calibrate)
    except CalibrationAborted:
        print("Calibration aborted.")
        return
    detector.set_roi(homography, w, h)

    tracker = GestureTracker(config)
    mouse = MouseController(config["PROJECTOR_OFFSET_X"], config["PROJECTOR_OFFSET_Y"])

    print("=== SYSTEM ACTIVE ===")
    print("Touch the projected area to interact.")
    if preview:
        print("Preview keys: q = quit, b = recapture baseline, c = recalibrate\n")

    try:
        while True:
            frame = sensor.get_depth_frame()
            if frame is None:
                if preview:
                    cv2.waitKey(1)
                time.sleep(0.002)
                continue

            cam_pt, mask = detector.detect(frame)
            proj_pt = map_to_projector(cam_pt, homography, w, h) if cam_pt else None
            for event, x, y in tracker.update(proj_pt):
                mouse.handle(event, x, y)

            if not preview:
                continue
            key = _render_preview(mask, detector, cam_pt)
            if key == ord("q"):
                break
            if key in (ord("b"), ord("c")):
                mouse.release()
                tracker.reset()
                detector = _setup_detector(sensor, config)
                if key == ord("c"):
                    try:
                        homography = _get_homography(sensor, config, detector, display, True)
                    except CalibrationAborted:
                        print("Recalibration aborted - keeping previous calibration.")
                detector.set_roi(homography, w, h)
    except KeyboardInterrupt:
        pass
    finally:
        mouse.release()
        cv2.destroyAllWindows()


# --------------------------------------------------------------------------- #
# Server: sensor on a (headless) machine, events via UDP to the client
# --------------------------------------------------------------------------- #
class RemoteDisplay:
    """Shows calibration targets on the client's projector via UDP.

    Packets are resent periodically because UDP is lossy and the client might start later.
    """

    def __init__(self, sock, address, resend_sec: float = 0.25):
        self.sock, self.address, self.resend_sec = sock, address, resend_sec
        self._last_key, self._last_time = None, 0.0

    def show(self, index, total, x, y, progress=0.0, state="touch"):
        key = (index, state, round(progress, 1))
        now = time.monotonic()
        if key == self._last_key and now - self._last_time < self.resend_sec:
            return
        _send(self.sock, self.address, {
            "event": "calib", "index": int(index), "total": int(total),
            "x": int(x), "y": int(y), "progress": round(float(progress), 2), "state": state,
        })
        self._last_key, self._last_time = key, now

    def poll(self):
        return 255

    def close(self):
        for _ in range(3):
            _send(self.sock, self.address, {"event": "calib_done"})
            time.sleep(0.02)
        self._last_key = None


def _send(sock, address, payload: dict) -> None:
    payload["timestamp"] = time.time()
    try:
        sock.sendto(json.dumps(payload).encode("utf-8"), address)
    except OSError as e:  # e.g. network temporarily unreachable
        print(f"[Network] send failed: {e}")


def run_server(sensor, config: dict, args) -> None:
    _install_sigterm_handler()
    w, h = int(config["PROJECTOR_WIDTH"]), int(config["PROJECTOR_HEIGHT"])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    address = (config["CLIENT_IP"], int(config["UDP_PORT"]))
    display = RemoteDisplay(sock, address)

    detector = _setup_detector(sensor, config)
    print(f"Calibration targets (if needed) are shown by the client at {address[0]}:{address[1]}")
    homography = _get_homography(sensor, config, detector, display, args.calibrate)
    detector.set_roi(homography, w, h)
    tracker = GestureTracker(config)

    print("=== TOUCH SERVER ACTIVE ===")
    print(f"Sending touch events to {address[0]}:{address[1]} (Ctrl+C to stop)")

    last_pos = (0.0, 0.0)
    try:
        while True:
            frame = sensor.get_depth_frame()
            if frame is None:
                if args.preview:
                    cv2.waitKey(1)
                time.sleep(0.002)
                continue

            cam_pt, mask = detector.detect(frame)
            proj_pt = map_to_projector(cam_pt, homography, w, h) if cam_pt else None
            for event, x, y in tracker.update(proj_pt):
                last_pos = (x, y)
                _send(sock, address, {"event": event, "x": round(x, 1), "y": round(y, 1)})

            if args.preview and _render_preview(mask, detector, cam_pt) == ord("q"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        if tracker.button_down:
            _send(sock, address, {"event": "up", "x": last_pos[0], "y": last_pos[1]})
        sock.close()
        if args.preview:
            cv2.destroyAllWindows()
