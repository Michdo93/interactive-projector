"""Sensor-independent touch detection: baseline capture, touch detector, gesture tracker."""

import collections
import math
import time
import warnings

import cv2
import numpy as np


# --------------------------------------------------------------------------- #
# Baseline
# --------------------------------------------------------------------------- #
def capture_baseline(sensor, n_frames: int = 30, delay_sec: float = 3.0, log=print):
    """Captures the empty surface.

    Returns (baseline_mm, noise_mm). Pixels that are invalid (0) in most frames are
    marked invalid (baseline 0) and are never considered for touches.
    """
    log("\n=== BASELINE SURFACE CAPTURE ===")
    log("Please clear all hands and objects from the surface.")
    remaining = float(delay_sec)
    while remaining > 0:
        log(f"  capturing in {remaining:.0f} s ...")
        step = min(1.0, remaining)
        time.sleep(step)
        remaining -= step

    frames = []
    deadline = time.monotonic() + max(10.0, n_frames * 0.5)
    while len(frames) < n_frames:
        frame = sensor.get_depth_frame()
        if frame is None:
            if time.monotonic() > deadline:
                raise RuntimeError("Depth sensor delivers no frames (baseline capture timed out).")
            time.sleep(0.002)
            continue
        frames.append(np.asarray(frame, dtype=np.float32).copy())

    stack = np.stack(frames)
    stack[stack <= 0] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        baseline = np.nanmedian(stack, axis=0)
        noise = np.nanstd(stack, axis=0)
    valid_ratio = np.mean(~np.isnan(stack), axis=0)

    invalid = np.isnan(baseline) | (valid_ratio < 0.5)
    baseline[invalid] = 0.0
    noise[invalid | np.isnan(noise)] = 0.0

    coverage = 100.0 * (1.0 - invalid.mean())
    valid_noise = noise[~invalid]
    median_noise = float(np.median(valid_noise)) if valid_noise.size else 0.0
    log(f"Baseline captured: {coverage:.1f}% valid pixels, median noise {median_noise:.2f} mm\n")
    return baseline.astype(np.float32), noise.astype(np.float32)


# --------------------------------------------------------------------------- #
# Touch detector
# --------------------------------------------------------------------------- #
class TouchDetector:
    """Finds the touching fingertip as a blob in a thin depth band above the surface."""

    def __init__(self, config: dict, baseline: np.ndarray, noise: np.ndarray):
        self.baseline = baseline
        self.valid_base = baseline > 0
        self.min_diff = np.maximum(
            float(config["TOUCH_MIN_MM"]), float(config["NOISE_SIGMA_FACTOR"]) * noise
        ).astype(np.float32)
        self.max_mm = float(config["TOUCH_MAX_MM"])
        self.min_area = float(config["MIN_CONTOUR_AREA"])
        self.max_area = float(config["MAX_CONTOUR_AREA"])

        ksize = int(config["MORPH_KERNEL"])
        self.kernel = (cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
                       if ksize > 1 else None)
        self.history = collections.deque(maxlen=max(1, int(config["TEMPORAL_FILTER_FRAMES"])))
        self.roi = None
        self.roi_polygon = None

    def set_roi(self, homography, proj_w: int, proj_h: int) -> None:
        """Restricts detection to the projected area (inverse-mapped into camera space)."""
        if homography is None:
            self.roi, self.roi_polygon = None, None
            return
        inv = np.linalg.inv(homography)
        corners = np.float32([[0, 0], [proj_w - 1, 0], [proj_w - 1, proj_h - 1],
                              [0, proj_h - 1]]).reshape(-1, 1, 2)
        cam = cv2.perspectiveTransform(corners, inv).reshape(-1, 2)
        polygon = np.round(cam).astype(np.int32)
        roi = np.zeros(self.baseline.shape, dtype=np.uint8)
        cv2.fillPoly(roi, [polygon], 255)
        self.roi = roi > 0
        self.roi_polygon = polygon

    def _filtered(self, frame: np.ndarray) -> np.ndarray:
        """Temporal median over the last N frames (invalid zeros ignored).

        A median (unlike a mean) keeps the full height of a finger that is present in
        most of the frames, so moving fingers are not smeared below the touch threshold.
        """
        if self.history.maxlen == 1:
            return frame
        self.history.append(frame)
        if len(self.history) == 1:
            return frame
        # Invalid pixels (0) are treated as +inf so they sort to the end;
        # the (lower) median is taken over the valid samples only.
        frames = [np.where(f > 0, f, np.inf) for f in self.history]
        valid_count = sum((f > 0).astype(np.uint8) for f in self.history)

        if len(frames) == 3:
            # Sorting network for 3 values - much faster than np.sort
            a, b, c = frames
            lo_ab, hi_ab = np.minimum(a, b), np.maximum(a, b)
            smallest = np.minimum(lo_ab, c)
            middle = np.maximum(lo_ab, np.minimum(hi_ab, c))
            depth = np.where(valid_count == 3, middle, smallest)
        else:
            stack = np.sort(np.stack(frames, axis=-1), axis=-1)   # contiguous axis
            mid = np.maximum(valid_count.astype(np.intp) - 1, 0) // 2
            depth = np.take_along_axis(stack, mid[..., None], axis=-1)[..., 0]

        depth[valid_count == 0] = 0.0
        return depth.astype(np.float32, copy=False)

    def detect(self, frame: np.ndarray):
        """Returns ((cx, cy) in camera pixels or None, binary touch mask)."""
        depth = self._filtered(np.asarray(frame, dtype=np.float32))
        diff = self.baseline - depth
        mask = self.valid_base & (depth > 0) & (diff >= self.min_diff) & (diff <= self.max_mm)
        if self.roi is not None:
            mask &= self.roi
        mask = mask.astype(np.uint8) * 255
        if self.kernel is not None:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, mask

        # Largest blob must be in range -> huge blobs (arm lying on the table) reject the frame.
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if not (self.min_area <= area <= self.max_area):
            return None, mask
        m = cv2.moments(largest)
        if m["m00"] == 0:
            return None, mask
        return (m["m10"] / m["m00"], m["m01"] / m["m00"]), mask


def map_to_projector(point, homography, proj_w: int, proj_h: int):
    """Maps a camera pixel to projector pixels (clipped to the projector area)."""
    pt = np.array([[point]], dtype=np.float32)
    px, py = cv2.perspectiveTransform(pt, homography)[0][0]
    return float(np.clip(px, 0, proj_w - 1)), float(np.clip(py, 0, proj_h - 1))


# --------------------------------------------------------------------------- #
# Gesture tracker
# --------------------------------------------------------------------------- #
class GestureTracker:
    """Turns a stream of touch positions into mouse events.

    Events (tuples of (event, x, y)):
      move        cursor follows finger (no button, or drag while button is down)
      click       short tap
      down / up   drag start / end (finger moved more than DRAG_THRESHOLD_PX)
      right_click finger held stationary for HOLD_RIGHT_CLICK_SEC
    """

    IDLE, PENDING, TOUCH, DRAG, HELD = range(5)

    def __init__(self, config: dict):
        self.confirm_frames = max(1, int(config["CLICK_HOLD_FRAMES"]))
        self.release_frames = max(1, int(config["RELEASE_FRAMES"]))
        self.drag_threshold = float(config["DRAG_THRESHOLD_PX"])
        self.hold_sec = float(config["HOLD_RIGHT_CLICK_SEC"])
        self.alpha = min(1.0, max(0.01, float(config["SMOOTHING_ALPHA"])))
        self.reset()

    def reset(self) -> None:
        self.state = self.IDLE
        self.count = 0
        self.miss = 0
        self.pos = None
        self.origin = None
        self.start = 0.0

    @property
    def button_down(self) -> bool:
        return self.state == self.DRAG

    def update(self, point, now: float = None):
        now = time.monotonic() if now is None else now
        events = []

        if point is None:
            if self.state == self.PENDING:
                self.reset()
            elif self.state in (self.TOUCH, self.DRAG, self.HELD):
                self.miss += 1
                if self.miss >= self.release_frames:
                    if self.state == self.TOUCH:
                        events.append(("click", *self.origin))
                    elif self.state == self.DRAG:
                        events.append(("up", *self.pos))
                    self.reset()
            return events

        self.miss = 0
        if self.state == self.IDLE:
            self.state, self.count, self.pos = self.PENDING, 1, point
            if self.count >= self.confirm_frames:
                self._begin_touch(point, now, events)
            return events

        if self.state == self.PENDING:
            self.count += 1
            self.pos = point
            if self.count >= self.confirm_frames:
                self._begin_touch(point, now, events)
            return events

        # Exponential smoothing against jitter
        self.pos = (self.alpha * point[0] + (1 - self.alpha) * self.pos[0],
                    self.alpha * point[1] + (1 - self.alpha) * self.pos[1])

        if self.state == self.TOUCH:
            dist = math.hypot(self.pos[0] - self.origin[0], self.pos[1] - self.origin[1])
            if dist > self.drag_threshold:
                events.append(("down", *self.origin))
                events.append(("move", *self.pos))
                self.state = self.DRAG
            elif self.hold_sec > 0 and now - self.start >= self.hold_sec:
                events.append(("right_click", *self.origin))
                self.state = self.HELD
            else:
                events.append(("move", *self.pos))
        elif self.state == self.DRAG:
            events.append(("move", *self.pos))
        # HELD: ignore until the finger is lifted
        return events

    def _begin_touch(self, point, now, events):
        self.state = self.TOUCH
        self.origin = point
        self.pos = point
        self.start = now
        events.append(("move", *point))
