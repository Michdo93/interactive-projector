import cv2
import numpy as np


class Calibrator:
    """Calculates 2D Perspective Homography Matrix between Kinect and Projector."""

    def __init__(self, proj_w: int, proj_h: int):
        self.proj_w = proj_w
        self.proj_h = proj_h

        # Define 4 target points on projected space with a safety margin
        margin = 100
        self.proj_points = np.float32([
            [margin, margin],
            [self.proj_w - margin, margin],
            [self.proj_w - margin, self.proj_h - margin],
            [margin, self.proj_h - margin]
        ])
        self.cam_points = []

    def run_calibration(self, sensor) -> np.ndarray:
        """Displays target points on projector and captures user clicks in camera frame."""
        cv2.namedWindow("Projector Calibration", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Projector Calibration", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.namedWindow("Kinect Depth Preview")

        def mouse_click(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(self.cam_points) < 4:
                self.cam_points.append([x, y])
                print(f"[Calibration] Target {len(self.cam_points)} selected at camera coords: ({x}, {y})")

        cv2.setMouseCallback("Kinect Depth Preview", mouse_click)

        print("\n=== CALIBRATION INSTRUCTIONS ===")
        print("Click on the corresponding projected red circle in the 'Kinect Depth Preview' window.\n")

        while len(self.cam_points) < 4:
            depth_frame = None
            while depth_frame is None:
                depth_frame = sensor.get_depth_frame()

            # Visualize depth map
            depth_vis = cv2.normalize(depth_frame, None, 0, 255, cv2.NORM_MINMAX)
            depth_vis = cv2.applyColorMap(depth_vis.astype(np.uint8), cv2.COLORMAP_JET)

            # Draw current projection target
            proj_img = np.zeros((self.proj_h, self.proj_w, 3), dtype=np.uint8)
            idx = len(self.cam_points)
            target = tuple(self.proj_points[idx].astype(int))

            cv2.circle(proj_img, target, 25, (0, 0, 255), -1)
            cv2.putText(
                proj_img,
                f"Click Target {idx + 1}",
                (target[0] - 80, target[1] - 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 255, 255),
                2
            )

            cv2.imshow("Projector Calibration", proj_img)
            cv2.imshow("Kinect Depth Preview", depth_vis)
            cv2.waitKey(1)

        cv2.destroyWindow("Projector Calibration")

        # Compute Perspective Homography Matrix
        src = np.array(self.cam_points, dtype=np.float32)
        dst = self.proj_points
        homography_matrix, _ = cv2.findHomography(src, dst)
        print("[Calibration] Homography Matrix computed successfully!\n")
        return homography_matrix