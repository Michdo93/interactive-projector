"""Interactive Projector - standalone mode (Kinect v1).

Run from the repository root:  python src/main_v1.py [--config config_v1.json] [--calibrate] [--no-preview]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import build_arg_parser, load_config  # noqa: E402
from kinect_driver_v1 import KinectV1DepthSensor  # noqa: E402
from runner import run_standalone  # noqa: E402


def main():
    args = build_arg_parser("Interactive Projector - standalone mode (Kinect v1).", "config_v1.json", mode="standalone").parse_args()
    config = load_config(args.config)
    sensor = KinectV1DepthSensor(config)
    try:
        run_standalone(sensor, config, args)
    finally:
        sensor.close()


if __name__ == "__main__":
    main()
