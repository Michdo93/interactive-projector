"""Shared helpers: configuration loading, paths, calibration persistence, CLI."""

import argparse
import json
import os
import time

import numpy as np

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SRC_DIR, ".."))

# Every key has a sane default, so older/minimal config files keep working.
DEFAULTS = {
    # Projector / display
    "PROJECTOR_WIDTH": 1920,
    "PROJECTOR_HEIGHT": 1080,
    "PROJECTOR_OFFSET_X": 0,          # position of the projector in the virtual desktop
    "PROJECTOR_OFFSET_Y": 0,
    # Touch detection (depth sensor space)
    "TOUCH_MIN_MM": 5.0,
    "TOUCH_MAX_MM": 25.0,
    "NOISE_SIGMA_FACTOR": 3.0,        # per-pixel threshold = max(TOUCH_MIN_MM, factor * noise)
    "MIN_CONTOUR_AREA": 20,
    "MAX_CONTOUR_AREA": 8000,
    "MORPH_KERNEL": 5,
    "TEMPORAL_FILTER_FRAMES": 1,      # >1 averages depth frames (useful for Kinect v1)
    # Gestures
    "CLICK_HOLD_FRAMES": 2,           # frames needed to confirm a touch (debounce)
    "RELEASE_FRAMES": 3,              # frames without touch needed to confirm release
    "DRAG_THRESHOLD_PX": 25,          # projector pixels before a touch becomes a drag
    "HOLD_RIGHT_CLICK_SEC": 1.2,      # stationary hold -> right click (0 disables)
    "SMOOTHING_ALPHA": 0.5,           # EMA factor for cursor position (1.0 = no smoothing)
    # Baseline
    "BASELINE_FRAMES": 30,
    "BASELINE_DELAY_SEC": 3.0,
    # Calibration
    "CALIBRATION_POINTS": 4,          # 4 (corners) or 9 (3x3 grid)
    "CALIBRATION_MARGIN_PX": 100,
    "CALIBRATION_HOLD_SEC": 1.0,
    "CALIBRATION_MAX_JITTER_PX": 4.0,
    "CALIBRATION_FILE": "calibration.json",
    # Network
    "CLIENT_BIND_IP": "0.0.0.0",
    "CLIENT_IP": "192.168.1.100",
    "UDP_PORT": 5005,
    # Sensor backend ("auto" or a specific backend, see the driver modules)
    "KINECT_BACKEND": "auto",
}


def resolve_path(path: str) -> str:
    """Resolves a path relative to the repository root (absolute paths stay unchanged)."""
    if os.path.isabs(path):
        return path
    return os.path.join(REPO_ROOT, path)


def load_config(path: str) -> dict:
    """Loads a JSON config and merges it over the defaults."""
    candidate = path if os.path.exists(path) else resolve_path(path)
    with open(candidate, "r", encoding="utf-8") as f:
        user_cfg = json.load(f)

    # Backwards compatibility: the client used SERVER_BIND_IP for its own bind address.
    if "CLIENT_BIND_IP" not in user_cfg and "SERVER_BIND_IP" in user_cfg:
        user_cfg["CLIENT_BIND_IP"] = user_cfg["SERVER_BIND_IP"]

    config = dict(DEFAULTS)
    config.update(user_cfg)
    return config


def save_calibration(path: str, homography: np.ndarray, config: dict, cam_shape) -> None:
    data = {
        "homography": np.asarray(homography, dtype=float).tolist(),
        "projector_width": int(config["PROJECTOR_WIDTH"]),
        "projector_height": int(config["PROJECTOR_HEIGHT"]),
        "camera_height": int(cam_shape[0]),
        "camera_width": int(cam_shape[1]),
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[Calibration] Saved to {path}")


def load_calibration(path: str, config: dict, cam_shape):
    """Returns the stored homography, or None if missing/incompatible."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if (data["projector_width"] != int(config["PROJECTOR_WIDTH"])
                or data["projector_height"] != int(config["PROJECTOR_HEIGHT"])
                or data["camera_height"] != int(cam_shape[0])
                or data["camera_width"] != int(cam_shape[1])):
            print("[Calibration] Stored calibration does not match current setup -> recalibrating.")
            return None
        homography = np.array(data["homography"], dtype=np.float64)
        if homography.shape != (3, 3):
            return None
        print(f"[Calibration] Loaded from {path} (created {data.get('created', '?')})")
        return homography
    except (OSError, KeyError, ValueError, TypeError) as e:
        print(f"[Calibration] Could not read {path}: {e}")
        return None


def build_arg_parser(description: str, default_config: str, mode: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=default_config,
                        help=f"Path to the config file (default: {default_config})")
    if mode in ("standalone", "server"):
        parser.add_argument("--calibrate", action="store_true",
                            help="Force a new calibration even if a stored one exists")
    if mode == "standalone":
        parser.add_argument("--no-preview", action="store_true",
                            help="Do not show the touch-mask preview window")
    if mode == "server":
        parser.add_argument("--preview", action="store_true",
                            help="Show the touch-mask preview window (requires a display)")
    return parser
