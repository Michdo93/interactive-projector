import numpy as np
from pykinect2 import PyKinectRuntime, PyKinectV2


class KinectDepthSensor:
    """Handles communication with Microsoft Kinect v2 Depth Camera."""

    def __init__(self):
        self.kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameType_Depth)
        self.depth_width = 512
        self.depth_height = 424

    def get_depth_frame(self) -> np.ndarray:
        """Fetches the latest raw depth frame in millimeters.

        Returns None if no frame is ready.
        """
        if self.kinect.has_new_depth_frame():
            frame = self.kinect.get_last_depth_frame()
            frame = frame.reshape((self.depth_height, self.depth_width)).astype(np.float32)
            return frame
        return None