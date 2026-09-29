# Interactive Projector (`interactive-projector`)

An open-source computer vision system that transforms any flat surface (table or wall) into an interactive touch screen using a **Projector**, a **Microsoft Kinect v2**, and **Python**.

By mounting a Kinect v2 directly onto or next to a projector, this software monitors distance differentials relative to the baseline surface. When an object (such as a finger or hand) enters a tight depth zone above the surface, it calculates the coordinate, converts it to display coordinates via 2D Homography, and triggers native OS mouse events.

---

## 📐 System Architecture, Hardware Setup & Setup Scenarios

```
   [ Projector + Kinect v2 Mounted Together ]
                       |
                       |  (Projection & Depth Sensing Area)
                       v
   ==========================================
              [ Surface / Table ]
```

### Scenario 1: Windows (All-in-One)
* Projector and Kinect v2 are connected directly to the same Windows PC.
* Uses Microsoft Kinect SDK v2.0 and native PyAutoGUI input simulation.

### Scenario 2: Ubuntu Linux (All-in-One)
* Projector and Kinect v2 are connected directly to the same Ubuntu system.
* Uses `libfreenect2` for depth acquisition and X11/PyAutoGUI for input control.

### Scenario 3: Headless Server (e.g. Raspberry Pi 4/5) + Remote Client (e.g. Laptop) -- Recommended for Ceiling Mounts
* **Ceiling Setup:** Raspberry Pi (with Kinect v2) is mounted near the projector on the ceiling.
* **Display Output:** Laptop streams display content wirelessly to the projector (e.g., Wireless HDMI Transmitter or Miracast/Chromecast).
* **Network Pipeline:** The Pi processes raw depth frames locally, detects touch coordinates and gestures (tap, drag/slide, long press), and broadcasts lightweight UDP network packets to the laptop.
* **Laptop Client:** Receives touch events over Wi-Fi/Ethernet and controls local mouse movements and clicks.

```
[ Raspberry Pi 4 / 5 ]  ---- (USB 3.0) ---->  [ Kinect v2 ]
            │
            │ (Processes depth image locally)
            │ (Sends touch coordinates via UDP/TUIO over Wi-Fi)
            ▼
       [ Laptop ]  <======= (Wireless HDMI) =======>  [ Projector ]
 (Receives coordinates &
controls the mouse cursor)
```

---

## 🛠️ Hardware Requirements

* **Projector:** Short-Throw or Ultra-Short-Throw projector recommended (>= 2500 ANSI Lumens, 1080p).
* **Depth Camera:** Microsoft Kinect for Windows v2 with USB 3.0 Adapter (mounted directly on or adjacent to the projector lens facing the same direction).
* **Mounting:** Attach the Kinect v2 directly onto or right next to the projector housing facing the exact same direction.
* **Processing Unit:**
  * Single PC (Windows 10/11 or Ubuntu 22.04/24.04), OR
  * Raspberry Pi 4 (4GB+) / Raspberry Pi 5 running 64-bit OS + Remote Laptop.
---

## 💻 Pre-Installation

### Option A: Windows (Standalone or Remote Laptop Client)
1. Install **[Kinect for Windows SDK v2.0](https://www.microsoft.com/en-us/download/details.aspx?id=44561)**.
2. Install Python 3.8 – 3.10 (64-bit).

### Option B: Ubuntu Linux (Standalone or Remote Laptop Client)

Install system dependencies and `libfreenect2`:
```bash
sudo apt update
sudo apt install -y build-essential cmake pkg-config libusb-1.0-0-dev libturbojpeg0-dev libglfw3-dev python3-pip
```

### Option C: Headless Server (e.g. Raspberry Pi)

1. Flash **Raspberry Pi OS (64-bit)**.
2. Install `libfreenect2` drivers and Python dependencies:
```bash
sudo apt update
sudo apt install -y libusb-1.0-0-dev libturbojpeg0-dev python3-pip
```

---

## ⚡ Installation Guide

### 1. Clone or Extract Repository
```bash
git clone https://github.com/Michdo93/interactive-projector.git
cd interactive-projector
```

### 2. Set Up Virtual Environment

#### Linux

```bash
python -m venv .
.\Scripts\activate
```

#### Windows

```bash
python -m venv .
.\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Running the System

### Option A: Running Standalone (Single PC)

Use this mode if your camera and projector are connected to the same computer.

1. **Display Setup:**
   * Connect your projector as a second display.
   * Set your OS display settings to **Extend** (do not duplicate).
   * Ensure the display resolution matches `PROJECTOR_WIDTH` and `PROJECTOR_HEIGHT` in `config.json` (e.g., `1920x1080`).

2. **Launch System:**
   ```bash
   python src/main.py
   ```

3. **Homography Calibration:**
* A fullscreen window will open on your projector showing red target circles in the corners sequentially.
* Look at the camera depth preview window on your main monitor.
* Click with your physical mouse on the center of each target dot within the camera view to match all 4 points.

4. **Baseline Plane Capture:**
* Clear all hands, objects, and obstructions from the projection area.
* Press `Space` (or confirm via console prompt) to capture the empty baseline surface (samples depth for ~3 seconds).

5. **Touch Interaction Mode:**
* Tap your finger on the projected display surface.
* The mouse cursor will map to your finger's location and issue left clicks upon steady pressure.
* Press `q` in the preview window to exit.

---

### Option B: Running Networked (Server & Client)

Use this mode if the depth camera is connected to a remote board (e.g., Raspberry Pi as Server) and the projector/display runs on a main computer (e.g., Laptop as Client).

#### Step 1: Start the Server (Camera Machine)

Run on the device connected to the depth camera:

```bash
python src/server.py
```

* **Camera Initialization:** The server starts streaming depth data and listens for client connections on the port specified in `config_network.json`.

#### Step 2: Start the Client (Projector Machine)

Run on the device connected to the projector:

```bash
python src/client.py
```

* **Display Output:** Opens the projection interface and handles OS cursor/click events locally.

#### Step 3: Network Calibration & Capture Workflow

1. **Homography Alignment:**
* The calibration targets will render on the **Client's** projector screen.
* The remote depth preview stream will render on the **Client** display (or server console window).
* Click the 4 target points to send the calibration matrix back to the server.

2. **Baseline Surface Capture:**
* Ensure the interaction area is completely clear.
* Trigger baseline sampling via the Client terminal.

3. **Active Session:**
* Touch detection is computed on the Server and streamed as touch coordinates to the Client to control the OS pointer.
* Press `q` on either terminal to stop the network session.

---

## ⚙️ Configuration

### config.json

Edit the `config.json` for standalone setups

* `PROJECTOR_WIDTH` / `PROJECTOR_HEIGHT`: Pixel dimensions of your projector display.
* `TOUCH_MIN_MM`: Minimum elevation from surface to register touch (default: `5.0` mm).
* `TOUCH_MAX_MM`: Maximum elevation threshold for touch detection (default: `25.0` mm).
* `MIN_CONTOUR_AREA`: Minimum contour pixel area to ignore noise (default: `20`).
* `MAX_CONTOUR_AREA`: Maximum contour pixel area to reject massive obstructions like arms or leaning bodies (default: `8000`).
* `CLICK_HOLD_FRAMES`: Number of stable touch frames required to issue a mouse click event.

### config_network.json

Edit the `config_network.json` for networked server/client setups.

* `ROLE`: Mode of the current node (`"server"` or `"client"`).
* `SERVER_IP`: IP address of the server (used by the client to connect).
* `PORT`: Network port for Communication/UDP/TCP streaming (default: `5000`).
* `CAMERA_INDEX`: Hardware index of the depth camera connected to the server (default: `0`).
* `PROJECTOR_WIDTH` / `PROJECTOR_HEIGHT`: Pixel dimensions of the projector display attached to the client.
* `TOUCH_MIN_MM` / `TOUCH_MAX_MM`: Elevation thresholds in mm for touch detection (processed on the server).
* `MIN_CONTOUR_AREA` / `MAX_CONTOUR_AREA`: Area thresholds for filtering noise and large obstructions.
* `CLICK_HOLD_FRAMES`: Stable frame threshold to trigger click events.

#### On which device does the file need to be configured?

The file must be configured on **both devices (server and client)**, but with different settings:

* **On the server:**
* `"ROLE"` is set to `"server"`.
* This is where the camera and processing settings (`CAMERA_INDEX`, `TOUCH_MIN_MM`, `TOUCH_MAX_MM`, `MIN_CONTOUR_AREA`, etc.) are located, since the server processes the camera image.


* **On the client:**
* `"ROLE"` is set to `"client"`.
* `"SERVER_IP"` must be the server’s IP address so that the client can connect.
* This is where the display settings (`PROJECTOR_WIDTH`, `PROJECTOR_HEIGHT`) are located, since the client outputs the image to the projector and processes touch clicks on its own system.

---

## 🔄 Autostart / Background Services

Service files and installer scripts are located in the `services/` directory:

* **Ubuntu / Raspberry Pi:** Refer to `services/interactive-projector-server.service` and `services/interactive-projector-client.service`. Or if you need the standalone configuration you have to use the `services/interactive-projector-client.service` file.
* **Windows:** Run `services/install-windows-service.ps1` via PowerShell as Administrator to create a background task or startup shortcut.

### Instructions to Enable the Services

#### On Ubuntu / Raspberry Pi (systemd)

##### Standalone

1. Copy the service file to systemd:
```bash
sudo cp services/interactive-projector-standalone.service /etc/systemd/system/
```

2. Reload daemon and enable autostart on boot:
```bash
sudo systemctl daemon-reload
sudo systemctl enable interactive-projector-standalone.service
sudo systemctl start interactive-projector-standalone.service
```

##### Server

1. Copy the service file to systemd:
```bash
sudo cp services/interactive-projector-server.service /etc/systemd/system/
```

2. Reload daemon and enable autostart on boot:
```bash
sudo systemctl daemon-reload
sudo systemctl enable interactive-projector-server.service
sudo systemctl start interactive-projector-server.service
```

##### Client

1. Copy the service file to systemd:
```bash
sudo cp services/interactive-projector-client.service /etc/systemd/system/
```

2. Reload daemon and enable autostart on boot:
```bash
sudo systemctl daemon-reload
sudo systemctl enable interactive-projector-client.service
sudo systemctl start interactive-projector-client.service
```

#### On Windows (PowerShell)

##### Standalone

1. Open PowerShell as **Administrator**.
2. Run the installation script:
```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
.\services\install-windows-service.ps1 -Mode standalone
```

##### Client

1. Open PowerShell as **Administrator**.
2. Run the installation script:
```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
.\services\install-windows-service.ps1 -Mode client
```
