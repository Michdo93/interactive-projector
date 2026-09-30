"""Depth driver for the Microsoft Kinect v1 (Xbox 360 model 1414/1473, Kinect for Windows).

Backends:
  freenect   Linux / Raspberry Pi, libfreenect (OpenKinect) Python bindings
  openni2    Windows (Kinect SDK 1.8 runtime + OpenNI2 Kinect driver) or Linux,
             via the `openni` Python package

Interface is identical to kinect_driver.KinectDepthSensor:
  get_depth_frame() -> float32 array (480 x 640) in millimetres, 0 = invalid,
                       or None if no new frame is available
  close()

Notes on the Kinect v1 compared to the v2:
  * structured light instead of time of flight -> minimum distance ~0.8 m,
    depth noise/quantisation grows roughly quadratically with distance
    (~3 mm at 1 m, ~7 mm at 1.5 m, ~12 mm at 2 m)
  * a finger casts an IR shadow; shadowed pixels are 0 (invalid) and are ignored
  -> use config_v1.json (larger thresholds, temporal filtering)
"""

import os
import sys

import numpy as np


class KinectV1DepthSensor:
    WIDTH = 640
    HEIGHT = 480

    def __init__(self, config: dict = None):
        config = config or {}
        backend = str(config.get("KINECT_BACKEND", "auto")).lower()
        self.device_index = int(config.get("KINECT_DEVICE_INDEX", 0))
        self.depth_width, self.depth_height = self.WIDTH, self.HEIGHT
        self._backend = None

        if backend == "auto":
            order = ["openni2", "freenect"] if sys.platform.startswith("win") \
                else ["freenect", "openni2"]
        else:
            order = [backend]

        errors = []
        for name in order:
            try:
                if name == "freenect":
                    self._init_freenect(config)
                elif name == "openni2":
                    self._init_openni2(config)
                else:
                    raise ValueError(f"unknown backend '{name}'")
                self._backend = name
                break
            except Exception as e:  # noqa: BLE001 - report all backend failures together
                errors.append(f"{name}: {e}")
        if self._backend is None:
            raise RuntimeError("No Kinect v1 backend available:\n  " + "\n  ".join(errors))
        print(f"[Kinect v1] Using backend '{self._backend}'")

    # ------------------------------------------------------------------ freenect
    def _init_freenect(self, config):
        import freenect

        self._freenect = freenect
        # DEPTH_MM (libfreenect >= 0.2) delivers millimetres directly.
        self._fn_mm = hasattr(freenect, "DEPTH_MM")
        self._fn_format = freenect.DEPTH_MM if self._fn_mm else freenect.DEPTH_11BIT
        self._fn_last_ts = None

        # Tilt must be set BEFORE the sync API claims the device.
        tilt = config.get("KINECT_V1_TILT_DEG")
        if tilt is not None:
            self._set_tilt_freenect(float(tilt))

        result = freenect.sync_get_depth(self.device_index, self._fn_format)
        if result is None:
            raise RuntimeError("no Kinect v1 device found (or device busy / missing permissions)")

    def _set_tilt_freenect(self, degrees: float):
        fn = self._freenect
        try:
            ctx = fn.init()
            dev = fn.open_device(ctx, self.device_index)
            fn.set_tilt_degs(dev, max(-27.0, min(27.0, degrees)))
            fn.close_device(dev)
            fn.shutdown(ctx)
            print(f"[Kinect v1] Tilt set to {degrees:.1f} deg")
        except Exception as e:  # noqa: BLE001 - tilt is optional
            print(f"[Kinect v1] Could not set tilt: {e}")

    @staticmethod
    def _raw11_to_mm(raw: np.ndarray) -> np.ndarray:
        """Converts 11-bit disparity to millimetres (approximation by S. Magnenat)."""
        raw = raw.astype(np.float32)
        mm = 1000.0 * 0.1236 * np.tan(raw / 2842.5 + 1.1863)
        mm[(raw >= 2047) | (mm <= 0)] = 0.0
        return mm

    def _read_freenect(self):
        result = self._freenect.sync_get_depth(self.device_index, self._fn_format)
        if result is None:
            return None
        depth, timestamp = result
        if timestamp == self._fn_last_ts:
            return None
        self._fn_last_ts = timestamp
        if self._fn_mm:
            return depth.astype(np.float32)
        return self._raw11_to_mm(depth)

    # ------------------------------------------------------------------- openni2
    def _init_openni2(self, config):
        from openni import openni2
        from openni import _openni2 as c_api

        self._openni2 = openni2
        redist = config.get("OPENNI2_REDIST") or os.environ.get("OPENNI2_REDIST")
        if redist:
            openni2.initialize(redist)
        else:
            openni2.initialize()

        self._ni_device = openni2.Device.open_any()
        self._ni_stream = self._ni_device.create_depth_stream()
        try:
            self._ni_stream.set_video_mode(c_api.OniVideoMode(
                pixelFormat=c_api.OniPixelFormat.ONI_PIXEL_FORMAT_DEPTH_1_MM,
                resolutionX=self.WIDTH, resolutionY=self.HEIGHT, fps=30))
        except Exception as e:  # noqa: BLE001 - keep the driver's default mode
            print(f"[Kinect v1] Could not set 640x480@30 1mm mode, using default: {e}")
        try:
            self._ni_stream.set_mirroring_enabled(False)
        except Exception:  # noqa: BLE001 - not supported by every driver
            pass
        self._ni_stream.start()

    def _read_openni2(self):
        try:
            ready = self._openni2.wait_for_any_stream([self._ni_stream], timeout=0.05)
        except Exception:  # noqa: BLE001 - timeout is reported as error by some versions
            return None
        if ready is None:
            return None
        frame = self._ni_stream.read_frame()
        buf = frame.get_buffer_as_uint16()
        depth = np.ctypeslib.as_array(buf).reshape(frame.height, frame.width)
        depth = depth.astype(np.float32)   # copies out of the OpenNI buffer
        if depth.shape != (self.HEIGHT, self.WIDTH):
            self.depth_height, self.depth_width = depth.shape
        return depth

    # -------------------------------------------------------------------- public
    def get_depth_frame(self):
        """Latest depth frame in millimetres (float32), or None if no new frame is ready."""
        if self._backend == "freenect":
            return self._read_freenect()
        return self._read_openni2()

    def close(self):
        try:
            if self._backend == "freenect":
                self._freenect.sync_stop()
            elif self._backend == "openni2":
                self._ni_stream.stop()
                self._ni_device.close()
                self._openni2.unload()
        except Exception:  # noqa: BLE001 - best effort on shutdown
            pass
