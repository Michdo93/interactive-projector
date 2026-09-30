"""Fullscreen calibration target window on the projector (used by standalone and client)."""

import cv2
import numpy as np

_MESSAGES = {
    "touch": "Touch and hold target {i}/{n}",
    "hold": "Hold still ...",
    "release": "OK - lift your finger",
}
_COLORS = {
    "touch": (0, 0, 255),
    "hold": (0, 215, 255),
    "release": (0, 200, 0),
}


class ProjectorWindow:
    WINDOW = "Interactive Projector - Calibration"

    def __init__(self, width: int, height: int, offset_x: int = 0, offset_y: int = 0):
        self.w, self.h = int(width), int(height)
        self.ox, self.oy = int(offset_x), int(offset_y)
        self._open = False

    def _ensure_open(self):
        if self._open:
            return
        cv2.namedWindow(self.WINDOW, cv2.WINDOW_NORMAL)
        # Move onto the projector BEFORE switching to fullscreen, otherwise the window
        # goes fullscreen on the primary monitor.
        cv2.moveWindow(self.WINDOW, self.ox, self.oy)
        cv2.resizeWindow(self.WINDOW, self.w, self.h)
        cv2.setWindowProperty(self.WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        self._open = True

    def show(self, index: int, total: int, x: int, y: int, progress: float = 0.0,
             state: str = "touch") -> None:
        self._ensure_open()
        x, y = int(x), int(y)
        img = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        color = _COLORS.get(state, (0, 0, 255))
        radius = 32

        cv2.line(img, (x - 50, y), (x + 50, y), (255, 255, 255), 1)
        cv2.line(img, (x, y - 50), (x, y + 50), (255, 255, 255), 1)
        cv2.circle(img, (x, y), radius, color, 3)
        if progress > 0:
            cv2.ellipse(img, (x, y), (radius - 6, radius - 6), -90, 0,
                        int(360 * min(1.0, progress)), color, -1)

        text = _MESSAGES.get(state, "").format(i=index + 1, n=total)
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
        tx = int(min(max(x - tw // 2, 10), self.w - tw - 10))
        ty = y + radius + 50 if y < self.h // 2 else y - radius - 30
        cv2.putText(img, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(img, "q / ESC = abort", (20, self.h - 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (120, 120, 120), 1)
        cv2.imshow(self.WINDOW, img)

    def poll(self) -> int:
        return cv2.waitKey(1) & 0xFF if self._open else 255

    def close(self) -> None:
        if self._open:
            cv2.destroyWindow(self.WINDOW)
            cv2.waitKey(1)
            self._open = False
