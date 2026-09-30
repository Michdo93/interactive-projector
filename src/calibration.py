"""Touch-based homography calibration between depth sensor and projector.

The projected targets are invisible in the depth image, so instead of clicking into a
depth preview the user touches each projected target with a finger. The touch detector
(which already knows the empty surface) measures where the fingertip is in camera
pixels. Any mirroring, rotation or keystone distortion is absorbed by the homography.
"""

import time

import cv2
import numpy as np


class CalibrationAborted(Exception):
    pass


class Calibrator:
    def __init__(self, config: dict):
        self.proj_w = int(config["PROJECTOR_WIDTH"])
        self.proj_h = int(config["PROJECTOR_HEIGHT"])
        self.margin = int(config["CALIBRATION_MARGIN_PX"])
        self.n_points = 9 if int(config["CALIBRATION_POINTS"]) >= 9 else 4
        self.hold_sec = float(config["CALIBRATION_HOLD_SEC"])
        self.max_jitter = float(config["CALIBRATION_MAX_JITTER_PX"])
        self.release_sec = 0.4
        self.proj_points = self._target_points()

    def _target_points(self) -> np.ndarray:
        m, w, h = self.margin, self.proj_w, self.proj_h
        if self.n_points == 4:
            pts = [[m, m], [w - m, m], [w - m, h - m], [m, h - m]]
        else:
            xs, ys = [m, w // 2, w - m], [m, h // 2, h - m]
            pts = [[x, y] for y in ys for x in xs]
        return np.float32(pts)

    def run(self, sensor, detector, display, log=print) -> np.ndarray:
        """Runs the calibration. `display` must provide show(), poll() and close().

        Returns the 3x3 homography (camera -> projector).
        Raises CalibrationAborted if the user presses q/ESC.
        """
        log("\n=== CALIBRATION ===")
        log("Touch each projected target with ONE fingertip and hold it until the ring is full.")
        cam_points = []
        total = len(self.proj_points)
        try:
            for idx, target in enumerate(self.proj_points):
                tx, ty = int(target[0]), int(target[1])
                cam_pt = self._capture_point(sensor, detector, display, idx, total, tx, ty)
                cam_points.append(cam_pt)
                log(f"[Calibration] Target {idx + 1}/{total}: projector ({tx}, {ty}) "
                    f"<- camera ({cam_pt[0]:.1f}, {cam_pt[1]:.1f})")
        finally:
            display.close()

        src = np.array(cam_points, dtype=np.float32)
        homography, _ = cv2.findHomography(src, self.proj_points, 0)
        if homography is None:
            raise RuntimeError("Homography could not be computed (degenerate target positions).")

        # Reprojection error as quality indicator
        mapped = cv2.perspectiveTransform(src.reshape(-1, 1, 2), homography).reshape(-1, 2)
        err = np.linalg.norm(mapped - self.proj_points, axis=1)
        log(f"[Calibration] Homography computed. Mean reprojection error: {err.mean():.1f} px\n")
        return homography

    def _capture_point(self, sensor, detector, display, idx, total, tx, ty):
        samples = []
        hold_start = None
        progress = 0.0

        # Phase 1: wait for a stable touch held for hold_sec
        while True:
            self._check_abort(display)
            frame = sensor.get_depth_frame()
            if frame is None:
                display.show(idx, total, tx, ty, progress, "touch" if progress == 0 else "hold")
                time.sleep(0.005)
                continue
            point, _ = detector.detect(frame)
            now = time.monotonic()
            if point is None:
                samples, hold_start, progress = [], None, 0.0
            else:
                samples.append(point)
                if hold_start is None:
                    hold_start = now
                arr = np.array(samples)
                if np.max(np.linalg.norm(arr - np.median(arr, axis=0), axis=1)) > self.max_jitter:
                    samples, hold_start = [point], now   # finger moved -> restart
                progress = min(1.0, (now - hold_start) / self.hold_sec) if self.hold_sec > 0 else 1.0
                if progress >= 1.0:
                    result = tuple(np.median(np.array(samples), axis=0))
                    break
            display.show(idx, total, tx, ty, progress, "touch" if progress == 0 else "hold")

        # Phase 2: wait until the finger is lifted (avoid reusing the same touch)
        released_since = None
        while True:
            self._check_abort(display)
            display.show(idx, total, tx, ty, 1.0, "release")
            frame = sensor.get_depth_frame()
            if frame is None:
                time.sleep(0.005)
                continue
            point, _ = detector.detect(frame)
            now = time.monotonic()
            if point is None:
                released_since = released_since or now
                if now - released_since >= self.release_sec:
                    return result
            else:
                released_since = None

    @staticmethod
    def _check_abort(display):
        key = display.poll()
        if key in (ord("q"), 27):
            raise CalibrationAborted()
