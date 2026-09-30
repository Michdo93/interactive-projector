"""Interactive Projector - touch server (Kinect v2), sends events to client.py via UDP.

Run from the repository root:  python src/server.py [--config config_network.json] [--calibrate] [--preview]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import build_arg_parser, load_config  # noqa: E402
from kinect_driver import KinectDepthSensor  # noqa: E402
from runner import run_server  # noqa: E402


def main():
    args = build_arg_parser("Interactive Projector - touch server (Kinect v2), sends events to client.py via UDP.", "config_network.json", mode="server").parse_args()
    config = load_config(args.config)
    sensor = KinectDepthSensor(config)
    try:
        run_server(sensor, config, args)
    finally:
        sensor.close()


if __name__ == "__main__":
    main()
