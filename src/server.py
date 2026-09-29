import json
import os
import socket
import time
import cv2
import numpy as np
from calibration import Calibrator
from kinect_driver import KinectDepthSensor


def load_network_config():
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config_network.json"
    )
    with open(config_path, "r") as f:
        return json.load(f)


def capture_baseline(sensor) -> np.ndarray:
    print("\n=== BACKGROUND BASELINE CAPTURE ===")
    print("Ensure the projection plane is empty. Capturing in 3 seconds...")
    time.sleep(3)

    frames = []
    for _ in range(30):
        f = None
        while f is None:
            f = sensor.get_depth_frame()
        frames.append(f)

    baseline = np.median(frames, axis=0)
    print("Baseline plane captured successfully!\n")
    return baseline


def main():
    config = load_network_config()
    sensor = KinectDepthSensor()

    calibrator = Calibrator(
        config["PROJECTOR_WIDTH"], config["PROJECTOR_HEIGHT"]
    )
    homography_matrix = calibrator.run_calibration(sensor)
    baseline_plane = capture_baseline(sensor)

    # UDP Socket Initialization
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target_address = (config["CLIENT_IP"], config["UDP_PORT"])

    print(f"=== PI TOUCH SERVER ACTIVE ===")
    print(f"Broadcasting touch packets to {config['CLIENT_IP']}:{config['UDP_PORT']}")

    is_touching = False
    touch_start_time = 0

    while True:
        depth_frame = sensor.get_depth_frame()
        if depth_frame is None:
            continue

        diff = baseline_plane - depth_frame
        touch_mask = (diff >= config["TOUCH_MIN_MM"]) & (
            diff <= config["TOUCH_MAX_MM"]
        )
        touch_mask = touch_mask.astype(np.uint8) * 255

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        touch_mask = cv2.morphologyEx(touch_mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(
            touch_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        current_touch = False

        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)

            if config["MIN_CONTOUR_AREA"] <= area <= config["MAX_CONTOUR_AREA"]:
                M = cv2.moments(largest)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    cam_pt = np.array([[[cx, cy]]], dtype=np.float32)
                    proj_pt = cv2.perspectiveTransform(
                        cam_pt, homography_matrix
                    )

                    px, py = proj_pt[0][0]
                    px = float(np.clip(px, 0, config["PROJECTOR_WIDTH"] - 1))
                    py = float(np.clip(py, 0, config["PROJECTOR_HEIGHT"] - 1))

                    if not is_touching:
                        event_type = "down"
                        touch_start_time = time.time()
                        is_touching = True
                    else:
                        duration = time.time() - touch_start_time
                        if duration >= config["HOLD_RIGHT_CLICK_SEC"]:
                            event_type = "right_click"
                            touch_start_time = time.time() + 999  # prevent duplicate right click
                        else:
                            event_type = "move"

                    payload = {
                        "event": event_type,
                        "x": px,
                        "y": py,
                        "timestamp": time.time(),
                    }
                    sock.sendto(
                        json.dumps(payload).encode("utf-8"), target_address
                    )
                    current_touch = True

        if not current_touch and is_touching:
            payload = {"event": "up", "x": 0, "y": 0, "timestamp": time.time()}
            sock.sendto(json.dumps(payload).encode("utf-8"), target_address)
            is_touching = False

        time.sleep(0.01)


if __name__ == "__main__":
    main()