import json
import os
import socket
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001


def load_network_config():
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config_network.json"
    )
    with open(config_path, "r") as f:
        return json.load(f)


def main():
    config = load_network_config()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((config["SERVER_BIND_IP"], config["UDP_PORT"]))

    print(f"=== LAPTOP CLIENT ACTIVE ===")
    print(f"Listening for touch events on port {config['UDP_PORT']}...")

    is_mouse_down = False

    while True:
        data, addr = sock.recvfrom(1024)
        try:
            packet = json.loads(data.decode("utf-8"))
            event = packet.get("event")
            x = int(packet.get("x", 0))
            y = int(packet.get("y", 0))

            if event == "down":
                pyautogui.moveTo(x, y)
                pyautogui.mouseDown(button="left")
                is_mouse_down = True
            elif event == "move":
                pyautogui.moveTo(x, y)
            elif event == "right_click":
                if is_mouse_down:
                    pyautogui.mouseUp(button="left")
                    is_mouse_down = False
                pyautogui.rightClick(x, y)
            elif event == "up":
                if is_mouse_down:
                    pyautogui.mouseUp(button="left")
                    is_mouse_down = False

        except Exception as e:
            print(f"Error processing packet: {e}")


if __name__ == "__main__":
    main()