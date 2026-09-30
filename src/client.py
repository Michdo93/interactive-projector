"""Client (projector machine): receives touch events via UDP and drives the OS mouse.

Also renders the calibration targets requested by the server. Works for both the
Kinect v2 server (server.py) and the Kinect v1 server (server_v1.py).
"""

import json
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import build_arg_parser, load_config  # noqa: E402
from mouse_output import MouseController  # noqa: E402


def main():
    args = build_arg_parser("Interactive Projector - touch client", "config_network.json",
                            mode="client").parse_args()
    config = load_config(args.config)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((config["CLIENT_BIND_IP"], int(config["UDP_PORT"])))
    sock.settimeout(0.02)

    mouse = MouseController(config["PROJECTOR_OFFSET_X"], config["PROJECTOR_OFFSET_Y"])
    calib_window = None

    print("=== CLIENT ACTIVE ===")
    print(f"Listening for touch events on {config['CLIENT_BIND_IP']}:{config['UDP_PORT']} ...")

    try:
        while True:
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                if calib_window is not None:
                    calib_window.poll()   # keep the OpenCV window responsive
                continue

            try:
                packet = json.loads(data.decode("utf-8"))
                event = packet.get("event")

                if event == "calib":
                    if calib_window is None:
                        from projector_display import ProjectorWindow
                        calib_window = ProjectorWindow(
                            config["PROJECTOR_WIDTH"], config["PROJECTOR_HEIGHT"],
                            config["PROJECTOR_OFFSET_X"], config["PROJECTOR_OFFSET_Y"])
                        print("[Calibration] Server requested calibration.")
                    calib_window.show(packet["index"], packet["total"], packet["x"], packet["y"],
                                      packet.get("progress", 0.0), packet.get("state", "touch"))
                    calib_window.poll()
                elif event == "calib_done":
                    if calib_window is not None:
                        calib_window.close()
                        calib_window = None
                        print("[Calibration] Finished.")
                elif event in ("move", "down", "up", "click", "right_click"):
                    mouse.handle(event, packet.get("x", 0), packet.get("y", 0))
            except (ValueError, KeyError, TypeError) as e:
                print(f"Invalid packet ignored: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        mouse.release()
        if calib_window is not None:
            calib_window.close()
        sock.close()


if __name__ == "__main__":
    main()
