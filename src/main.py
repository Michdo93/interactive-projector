import json
import os
import cv2
import numpy as np
import pyautogui
from src.calibration import Calibrator
from src.kinect_driver import KinectDepthSensor

# Configure PyAutoGUI performance settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(config_path, "r") as f:
        return json.load(f)


def capture_baseline(sensor) -> np.ndarray:
    """Captures baseline surface depth map by calculating the median over multiple frames."""
    print("\n=== BASELINE SURFACE CAPTURE ===")
    print("Please clear all hands and objects from the surface.")
    print("Capturing baseline in 3 seconds...")
    cv2.waitKey(3000)

    frames = []
    for _ in range(30):
        f = None
        while f is None:
            f = sensor.get_depth_frame()
        frames.append(f)

    baseline = np.median(frames, axis=0)
    print("Baseline surface successfully captured!\n")
    return baseline


def main():
    config = load_config()
    sensor = KinectDepthSensor()

    # 1. Homography Calibration
    calibrator = Calibrator(config["PROJECTOR_WIDTH"], config["PROJECTOR_HEIGHT"])
    homography_matrix = calibrator.run_calibration(sensor)

    # 2. Surface Baseline Capture
    baseline_plane = capture_baseline(sensor)

    # 3. Processing Loop
    print("=== SYSTEM ACTIVE ===")
    print("Touch the projected area to interact. Press 'q' in preview to quit.\n")

    touch_frame_counter = 0

    while True:
        depth_frame = sensor.get_depth_frame()
        if depth_frame is None:
            continue

        # Differential depth processing (baseline - current = height above surface)
        diff = baseline_plane - depth_frame

        # Filter depth offsets within touch interaction threshold
        touch_mask = (diff >= config["TOUCH_MIN_MM"]) & (diff <= config["TOUCH_MAX_MM"])
        touch_mask = touch_mask.astype(np.uint8) * 255

        # Morphological noise removal
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        touch_mask = cv2.morphologyEx(touch_mask, cv2.MORPH_OPEN, kernel)

        # Detect contours of touched areas
        contours, _ = cv2.findContours(touch_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid_touch = False

        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)

            if config["MIN_CONTOUR_AREA"] <= area <= config["MAX_CONTOUR_AREA"]:
                M = cv2.moments(largest)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    # Perspective transformation from Kinect space to Projector space
                    cam_pt = np.array([[[cx, cy]]], dtype=np.float32)
                    proj_pt = cv2.perspectiveTransform(cam_pt, homography_matrix)

                    px, py = proj_pt[0][0]
                    px = np.clip(px, 0, config["PROJECTOR_WIDTH"] - 1)
                    py = np.clip(py, 0, config["PROJECTOR_HEIGHT"] - 1)

                    # Update mouse position
                    pyautogui.moveTo(int(px), int(py))
                    valid_touch = True

                    touch_frame_counter += 1
                    if touch_frame_counter == config["CLICK_HOLD_FRAMES"]:
                        pyautogui.click()

        if not valid_touch:
            touch_frame_counter = 0

        # Preview Window
        cv2.imshow("Interactive Projector Pipeline", touch_mask)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()