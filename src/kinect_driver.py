"""Depth driver for the Microsoft Kinect v2 (Xbox One / Kinect for Windows v2).

Backends:
  pykinect2      Windows, Kinect for Windows SDK 2.0
  libfreenect2   Linux / Raspberry Pi, via the pylibfreenect2 bindings

Interface (shared with kinect_driver_v1.KinectV1DepthSensor):
  get_depth_frame() -> float32 array (424 x 512) in millimetres, 0 = invalid,
                       or None if no new frame is available
  close()
"""

import sys
import time

import numpy as np


class KinectDepthSensor:
    WIDTH = 512
    HEIGHT = 424

    def __init__(self, config: dict = None):
        config = config or {}
        backend = str(config.get("KINECT_BACKEND", "auto")).lower()
        self.depth_width, self.depth_height = self.WIDTH, self.HEIGHT
        self._backend = None

        if backend == "auto":
            order = ["pykinect2", "libfreenect2"] if sys.platform.startswith("win") \
                else ["libfreenect2", "pykinect2"]
        else:
            order = [backend]

        errors = []
        for name in order:
            try:
                if name == "pykinect2":
                    self._init_pykinect2()
                elif name == "libfreenect2":
                    self._init_libfreenect2(config.get("KINECT_V2_PIPELINE", "auto"))
                else:
                    raise ValueError(f"unknown backend '{name}'")
                self._backend = name
                break
            except Exception as e:  # noqa: BLE001 - report all backend failures together
                errors.append(f"{name}: {e}")
        if self._backend is None:
            raise RuntimeError("No Kinect v2 backend available:\n  " + "\n  ".join(errors))
        print(f"[Kinect v2] Using backend '{self._backend}'")

    # ------------------------------------------------------------------ pykinect2
    def _init_pykinect2(self):
        # PyKinectRuntime still calls time.clock(), which was removed in Python 3.8.
        if not hasattr(time, "clock"):
            time.clock = time.perf_counter
        from pykinect2 import PyKinectRuntime, PyKinectV2

        self._kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameType_Depth)

    def _read_pykinect2(self):
        if not self._kinect.has_new_depth_frame():
            return None
        frame = self._kinect.get_last_depth_frame()
        return frame.reshape((self.HEIGHT, self.WIDTH)).astype(np.float32)

    # --------------------------------------------------------------- libfreenect2
    def _init_libfreenect2(self, pipeline_name: str):
        import pylibfreenect2 as fn2

        self._fn2 = fn2
        pipeline = self._create_pipeline(fn2, str(pipeline_name).lower())
        self._freenect = fn2.Freenect2()
        if self._freenect.enumerateDevices() == 0:
            raise RuntimeError("no Kinect v2 device found")
        serial = self._freenect.getDeviceSerialNumber(0)
        self._device = self._freenect.openDevice(serial, pipeline=pipeline)
        self._listener = fn2.SyncMultiFrameListener(fn2.FrameType.Depth)
        self._device.setIrAndDepthFrameListener(self._listener)
        self._device.startStreams(rgb=False, depth=True)

    @staticmethod
    def _create_pipeline(fn2, name: str):
        candidates = {
            "cuda": "CudaPacketPipeline",
            "opencl": "OpenCLPacketPipeline",
            "opengl": "OpenGLPacketPipeline",
            "cpu": "CpuPacketPipeline",
        }
        order = [name] if name in candidates else ["cuda", "opencl", "opengl", "cpu"]
        for key in order:
            cls = getattr(fn2, candidates[key], None)
            if cls is None:
                continue
            try:
                pipeline = cls()
                print(f"[Kinect v2] libfreenect2 pipeline: {key}")
                return pipeline
            except Exception:  # noqa: BLE001 - pipeline not usable on this machine
                continue
        raise RuntimeError("no usable libfreenect2 packet pipeline")

    def _read_libfreenect2(self):
        if not self._listener.hasNewFrame():
            return None
        frames = self._listener.waitForNewFrame()
        try:
            # asarray() is a view on libfreenect2's buffer -> copy before release
            return np.array(frames["depth"].asarray(np.float32), dtype=np.float32, copy=True)
        finally:
            self._listener.release(frames)

    # -------------------------------------------------------------------- public
    def get_depth_frame(self):
        """Latest depth frame in millimetres (float32), or None if no new frame is ready."""
        if self._backend == "pykinect2":
            return self._read_pykinect2()
        return self._read_libfreenect2()

    def close(self):
        try:
            if self._backend == "pykinect2":
                self._kinect.close()
            elif self._backend == "libfreenect2":
                self._device.stop()
                self._device.close()
        except Exception:  # noqa: BLE001 - best effort on shutdown
            pass
