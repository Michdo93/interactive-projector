# Interactive Projector (`interactive-projector`)

An open-source computer vision system that transforms any flat surface (table or wall) into an interactive touch screen using a **Projector**, a **Microsoft Kinect v2 or Kinect v1**, and **Python**.

By mounting a Kinect directly onto or next to a projector, this software monitors distance differentials relative to the baseline surface. When an object (such as a finger or hand) enters a tight depth zone above the surface, it calculates the coordinate, converts it to display coordinates via 2D Homography, and triggers native OS mouse events.

---

## 📐 System Architecture, Hardware Setup & Setup Scenarios

```
   [ Projector + Kinect Mounted Together ]
                       |
                       |  (Projection & Depth Sensing Area)
                       v
   ==========================================
              [ Surface / Table ]
```

### Scenario 1: Windows (All-in-One)
* Projector and Kinect are connected directly to the same Windows PC.
* Kinect v2: Microsoft Kinect SDK v2.0 (`pykinect2`). Kinect v1: Kinect SDK 1.8 runtime + OpenNI2 (`openni`).
* Native PyAutoGUI input simulation.

### Scenario 2: Ubuntu Linux (All-in-One)
* Projector and Kinect are connected directly to the same Ubuntu system.
* Kinect v2: `libfreenect2` (`pylibfreenect2`). Kinect v1: `libfreenect` (`python3-freenect`).
* X11/PyAutoGUI for input control (Wayland is not supported by PyAutoGUI – use an X11 session).

### Scenario 3: Headless Server (e.g. Raspberry Pi 4/5) + Remote Client (e.g. Laptop) -- Recommended for Ceiling Mounts
* **Ceiling Setup:** Raspberry Pi (with Kinect v2 or v1) is mounted near the projector on the ceiling.
* **Display Output:** Laptop streams display content wirelessly to the projector (e.g., Wireless HDMI Transmitter or Miracast/Chromecast).
* **Network Pipeline:** The Pi processes raw depth frames locally, detects touch coordinates and gestures (tap, drag/slide, long press), and broadcasts lightweight UDP network packets to the laptop.
* **Laptop Client:** Receives touch events over Wi-Fi/Ethernet and controls local mouse movements and clicks.

```
[ Raspberry Pi 4 / 5 ]  ---- (USB) ---->  [ Kinect v2 / v1 ]
            │
            │ (Processes depth image locally)
            │ (Sends touch events via UDP over Wi-Fi/Ethernet)
            ▼
       [ Laptop ]  <======= (Wireless HDMI) =======>  [ Projector ]
 (Receives coordinates &
controls the mouse cursor)
```

---

## 🏗️ How it works

In short: **The Kinect measures in millimeters/meters**, your **screen uses pixels**—and calibration creates the “translation dictionary” between the two worlds.

### 1. Why do I have to touch 4 targets? (Homography)

The Kinect sees the surface from its own angle, the projector casts its image from another. Calibration measures how the projected rectangle appears in the depth image.

The projector shows a target at a known projector pixel, e.g. **(100, 100)**. You touch it with your fingertip, and the touch detector measures where that fingertip is in the depth image, e.g. camera pixel **(142, 89)**:

> *"If a finger is later detected at camera pixel (142, 89), the user means projector pixel (100, 100)."*

From four such pairs the **homography matrix** is computed. It absorbs rotation, scaling, keystone distortion and even mirroring – it doesn't matter how far away or how crooked the devices are mounted.

> **Why touch instead of clicking into a preview?** The projected light is invisible in the Kinect's depth image, so the target cannot be located there by eye. The fingertip, however, is exactly what the depth image measures – and it is measured the same way it is later used for interaction, so systematic offsets cancel out.

The result is stored (`CALIBRATION_FILE`) and reused on the next start as long as projector resolution and sensor stay the same. Use `--calibrate` to force a new calibration.

### 2. What about the resolutions? (Client 1920px vs. Pi/Kinect 1200px / 640px)

The Kinect couldn't care less about that!

1. **The Kinect has its own sensor:** A standard Kinect v1, for example, provides a depth image of **$640 \times 480$ pixels**. For each point in this image, there is a distance value in **millimeters**.
2. **The client has its own display resolution:** For example, **$1920 \times 1080$ pixels**.
3. **The math handles the conversion:** If, according to Kinect, your hand is at 50% of the projected width, the system sends the event to pixel `960` on the client. The system converts the Kinect area **proportionally** to the client's resolution. The resolution of the server or the Pi is irrelevant in this context.

### 3. What is the maximum detectable range of the Kinect?

That depends on two factors: the **field of view** and the **camera's range**.

#### Maximum Distance & Measurement Range:

**Kinect v1 (Xbox 360 / Model 1414/1473):**
* **Recommended distance:** approx. **0.8 m to 3.5 m** (it can't detect anything below 0.8 m, and becomes extremely inaccurate above 3.5 m).
* **For touch detection:** keep it at **0.9 m – 1.6 m**. The depth resolution of the structured-light sensor degrades roughly quadratically (≈3 mm at 1 m, ≈7 mm at 1.5 m, ≈12 mm at 2 m); beyond ~1.8 m a finger on the table can hardly be separated from the surface.


**Kinect v2 (Xbox One / Model 1520):**
* **Recommended distance:** approx. **0.5 m to 4.5 m**.


**Azure Kinect (DK):**
* **Recommended distance:** approx. **0.25 m to 3.8 m** (depending on the depth mode).

#### Maximum area on the table/wall:

The Kinect has a fixed field of view (Kinect v1: approx. 57° horizontally, 43° vertically). This means: **The farther away the Kinect is mounted, the larger the area it can see.**

* If the Kinect v1 is suspended **1.5 meters** above the table, it covers an area of approximately **$1.60 \text{ m} \times 1.20 \text{ m}$**.
* If it is suspended **2.5 meters** away, it covers an area of just under **$2.70 \text{ m} \times 2.00 \text{ m}$**.

> **The projector is usually the bottleneck:** The projector determines how large your touch area actually is. The Kinect simply needs to be mounted high enough or far enough away so that the entire projected image is within the Kinect's field of view.

---

## 🛠️ Hardware Requirements

* **Projector:** Short-Throw or Ultra-Short-Throw projector recommended (>= 2500 ANSI Lumens, 1080p).
* **Depth Camera** (mounted on or right next to the projector, facing the same direction):
  * **Kinect v2** (Xbox One / Kinect for Windows v2) with the USB 3.0 adapter, **or**
  * **Kinect v1** (Xbox 360 model 1414/1473 or Kinect for Windows) with its USB/power adapter (USB 2.0 is sufficient).
* **Processing Unit:**
  * Single PC (Windows 10/11 or Ubuntu 22.04/24.04), OR
  * Raspberry Pi 4 (4GB+) / Raspberry Pi 5 running 64-bit OS + Remote Laptop.

### Which scripts belong to which sensor?

| Purpose | Kinect v2 | Kinect v1 |
|---|---|---|
| Standalone (sensor + projector on one PC) | `src/main.py` + `config.json` | `src/main_v1.py` + `config_v1.json` |
| Server (sensor machine, e.g. Pi) | `src/server.py` + `config_network.json` | `src/server_v1.py` + `config_network_v1.json` |
| Client (projector machine) | `src/client.py` + `config_network.json` | `src/client.py` + `config_network_v1.json` (`--config`) |
| Depth driver | `src/kinect_driver.py` | `src/kinect_driver_v1.py` |

Touch detection, gestures, calibration and networking are shared (`touch_detection.py`, `calibration.py`, `runner.py`, `projector_display.py`, `mouse_output.py`). The client is sensor-independent.

---

## 💻 Pre-Installation

### Kinect v2

**Windows**
1. Install the **[Kinect for Windows SDK v2.0](https://www.microsoft.com/en-us/download/details.aspx?id=44561)**.
2. Install Python 3.8 – 3.10 (64-bit).
3. The PyPI release of `pykinect2` is outdated. Recommended: `pip install git+https://github.com/Kinect/PyKinect2.git`. If the import fails with `assert sizeof(tagSTATSTG) == 72`, remove that assertion line in `PyKinectV2.py` (known issue on 64-bit Python). The `time.clock()` incompatibility with Python ≥ 3.8 is handled by the driver.

**Ubuntu / Raspberry Pi** – build `libfreenect2`, then the Python bindings:
```bash
sudo apt update
sudo apt install -y build-essential cmake pkg-config libusb-1.0-0-dev libturbojpeg0-dev libglfw3-dev python3-pip python3-dev
git clone https://github.com/OpenKinect/libfreenect2.git
cd libfreenect2 && mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/freenect2 && make -j4 && make install
sudo cp ../platform/linux/udev/90-kinect2.rules /etc/udev/rules.d/   # access without root
export LIBFREENECT2_INSTALL_PREFIX=$HOME/freenect2
export LD_LIBRARY_PATH=$HOME/freenect2/lib:$LD_LIBRARY_PATH
pip install cython && pip install pylibfreenect2
```
The processing pipeline (CUDA / OpenCL / OpenGL / CPU) is selected automatically; force one with `"KINECT_V2_PIPELINE": "cpu"` in the config. On a Raspberry Pi only the CPU pipeline is usually available.

### Kinect v1

**Ubuntu / Raspberry Pi** (libfreenect):
```bash
sudo apt update
sudo apt install -y freenect python3-freenect
# The kernel's webcam driver grabs the Kinect camera -> blacklist it
echo "blacklist gspca_kinect" | sudo tee /etc/modprobe.d/blacklist-kinect.conf
sudo modprobe -r gspca_kinect
# Allow access without root
sudo cp /usr/share/doc/freenect/examples/51-kinect.rules /etc/udev/rules.d/ 2>/dev/null || \
  echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="045e", MODE="0666"' | sudo tee /etc/udev/rules.d/51-kinect.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```
`python3-freenect` is a system package → create the virtual environment with `--system-site-packages` (see below). Test with `freenect-glview`.

**Windows** (OpenNI2):
1. Install the **Kinect for Windows SDK 1.8** (or runtime 1.8) – works with Xbox 360 Kinects as well.
2. Install **OpenNI 2.2 (x64)**; it ships the Kinect bridge driver (`Kinect.dll`) in `Redist\OpenNI2\Drivers`.
3. `pip install openni`
4. If OpenNI2 is not found automatically, set `"OPENNI2_REDIST"` in `config_v1.json` (or the environment variable `OPENNI2_REDIST`) to the `Redist` folder, e.g. `C:\\Program Files\\OpenNI2\\Redist`.

Backend selection is automatic (`"KINECT_BACKEND": "auto"`); force it with `"freenect"` or `"openni2"`. With libfreenect you can set the tilt motor via `"KINECT_V1_TILT_DEG"`.

---

## ⚡ Installation Guide

### 1. Clone Repository
```bash
git clone https://github.com/Michdo93/interactive-projector.git
cd interactive-projector
```

### 2. Set Up Virtual Environment

#### Linux / Raspberry Pi
```bash
python3 -m venv .                          # Kinect v2
python3 -m venv --system-site-packages .   # Kinect v1 (uses the apt package python3-freenect)
source bin/activate
```

#### Windows
```powershell
python -m venv .
.\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
Then install the sensor bindings as described in *Pre-Installation* (`pylibfreenect2`, `openni`, ...). On a headless server `pyautogui` is not needed.

---

## 🚀 Running the System

All scripts are run from the repository root. Common options:

* `--config <file>` – use another config file
* `--calibrate` – ignore the stored calibration and calibrate again

### Option A: Standalone (Single PC)

1. **Display Setup:**
   * Connect your projector as a second display and set the OS display mode to **Extend**.
   * Set `PROJECTOR_WIDTH` / `PROJECTOR_HEIGHT` to the projector resolution.
   * Set `PROJECTOR_OFFSET_X` / `PROJECTOR_OFFSET_Y` to the projector's position in the virtual desktop (e.g. `1920` / `0` if the projector is placed right of a 1920 px wide main monitor). Touch coordinates and the calibration window use this offset.

2. **Launch:**
   ```bash
   python src/main.py        # Kinect v2
   python src/main_v1.py     # Kinect v1
   ```

3. **Baseline capture** (automatic): keep the surface empty for the countdown (`BASELINE_DELAY_SEC`, default 3 s). The empty surface and the per-pixel sensor noise are measured.

4. **Calibration** (only if no stored calibration exists or `--calibrate` is given):
   * Red targets appear on the projector one after another.
   * Touch each target with **one fingertip** and hold still until the ring is full (yellow), then lift the finger (green).
   * `q` / `ESC` aborts.

5. **Touch interaction:** see *Gestures* below.
   Preview window keys: `q` quit, `b` recapture baseline (e.g. after moving objects on the table), `c` recalibrate. Disable the preview with `--no-preview`.

### Option B: Networked (Server & Client)

1. **Configure both machines** (`config_network.json` for Kinect v2, `config_network_v1.json` for Kinect v1):
   * `CLIENT_IP` (server side): IP of the client/laptop the events are sent to.
   * `CLIENT_BIND_IP` (client side): address the client listens on (`0.0.0.0` = all interfaces).
   * `UDP_PORT`: identical on both sides (allow it in the client's firewall).
   * `PROJECTOR_WIDTH` / `PROJECTOR_HEIGHT` identical on both sides; `PROJECTOR_OFFSET_*` on the client.

2. **Start the client** on the projector machine:
   ```bash
   python src/client.py                                   # Kinect v2 setup
   python src/client.py --config config_network_v1.json   # Kinect v1 setup
   ```

3. **Start the server** on the sensor machine (runs headless, no display needed):
   ```bash
   python src/server.py      # Kinect v2
   python src/server_v1.py   # Kinect v1
   ```
   Optional `--preview` shows the touch mask if the server has a display.

4. **Workflow:** the server captures the baseline, then – if no stored calibration exists – sends calibration targets to the client, which shows them fullscreen on the projector. Touch them as described above; the result is stored on the server. Afterwards touch events are streamed to the client, which drives the OS pointer.

### Gestures

| Gesture | Result |
|---|---|
| Short tap | Left click at the touch position |
| Touch and move (> `DRAG_THRESHOLD_PX`) | Left button down → drag → button up when lifted (sliders, scrolling, drawing) |
| Hold still for `HOLD_RIGHT_CLICK_SEC` | Right click (set to `0` to disable) |
| Finger on the surface | Cursor follows the finger |

Only one touch point (the largest blob) is tracked.

### Network protocol (UDP, JSON)

Server → client, one datagram per event:
```json
{"event": "move", "x": 812.4, "y": 377.0, "timestamp": 1759212345.1}
```
`event` is one of `move`, `down`, `up`, `click`, `right_click` (coordinates in projector pixels, without offset), or `calib` / `calib_done` during calibration.

---

## ⚙️ Configuration

All keys are optional – missing keys fall back to the defaults in `src/common.py`.

| Key | Default v2 / v1 | Meaning |
|---|---|---|
| `PROJECTOR_WIDTH` / `PROJECTOR_HEIGHT` | 1920 / 1080 | Projector resolution in pixels |
| `PROJECTOR_OFFSET_X` / `PROJECTOR_OFFSET_Y` | 0 / 0 | Position of the projector in the virtual desktop (standalone, client) |
| `TOUCH_MIN_MM` / `TOUCH_MAX_MM` | 5–25 / 10–40 | Height band above the surface that counts as touch |
| `NOISE_SIGMA_FACTOR` | 3.0 / 2.5 | Per-pixel minimum height = max(`TOUCH_MIN_MM`, factor × measured noise) |
| `MIN_CONTOUR_AREA` / `MAX_CONTOUR_AREA` | 20–8000 / 30–12000 | Blob size in sensor pixels (noise / arms are rejected) |
| `MORPH_KERNEL` | 5 / 7 | Size of the morphological noise filter |
| `TEMPORAL_FILTER_FRAMES` | 1 / 3 | Temporal median over N depth frames (reduces Kinect v1 noise, +1 frame latency) |
| `CLICK_HOLD_FRAMES` | 2 / 3 | Frames needed to confirm a touch |
| `RELEASE_FRAMES` | 3 / 4 | Frames without touch needed to confirm lifting the finger |
| `DRAG_THRESHOLD_PX` | 25 / 35 | Movement in projector pixels before a touch becomes a drag |
| `HOLD_RIGHT_CLICK_SEC` | 1.2 | Stationary hold time for a right click (`0` = off) |
| `SMOOTHING_ALPHA` | 0.5 / 0.4 | Cursor smoothing (1.0 = none) |
| `BASELINE_FRAMES` / `BASELINE_DELAY_SEC` | 30 / 3 | Baseline capture |
| `CALIBRATION_POINTS` | 4 | `4` corners or `9` (3×3 grid, more robust against lens distortion) |
| `CALIBRATION_MARGIN_PX` | 100 | Distance of the targets from the projector edge |
| `CALIBRATION_HOLD_SEC` / `CALIBRATION_MAX_JITTER_PX` | 1.0 / 4 (v1: 6) | How long / how steady a target must be touched |
| `CALIBRATION_FILE` | `calibration*.json` | Where the calibration is stored (relative to the repo root) |
| `CLIENT_IP` / `CLIENT_BIND_IP` / `UDP_PORT` | – | Networking (see above); `SERVER_BIND_IP` from older configs is still accepted |
| `KINECT_BACKEND` | `auto` | v2: `pykinect2`, `libfreenect2` – v1: `freenect`, `openni2` |
| `KINECT_V2_PIPELINE` | `auto` | libfreenect2 pipeline: `cuda`, `opencl`, `opengl`, `cpu` |
| `KINECT_DEVICE_INDEX`, `KINECT_V1_TILT_DEG`, `OPENNI2_REDIST` | – | Kinect v1 specific |

**Tuning tips:** false touches while hovering → lower `TOUCH_MAX_MM`; touches not recognised → lower `TOUCH_MIN_MM` or `NOISE_SIGMA_FACTOR`; jittery cursor → lower `SMOOTHING_ALPHA` (Kinect v1: raise `TEMPORAL_FILTER_FRAMES` to 5).

---

## 🔄 Autostart / Background Services

Service files and installer scripts are located in the `services/` directory. Adjust `User=` and the paths to your installation (and the Python path to your venv, e.g. `/home/pi/interactive-projector/bin/python`).

| File | Purpose |
|---|---|
| `interactive-projector-standalone.service` | Standalone, Kinect v2 (`main.py`) |
| `interactive-projector-standalone-v1.service` | Standalone, Kinect v1 (`main_v1.py`) |
| `interactive-projector-server.service` | Server, Kinect v2 (`server.py`) |
| `interactive-projector-server-v1.service` | Server, Kinect v1 (`server_v1.py`) |
| `interactive-projector-client.service` | Client (`client.py`) |

Calibrate once interactively before enabling a service; the service then reuses the stored calibration. The surface must be empty while the service starts (baseline capture).

### On Ubuntu / Raspberry Pi (systemd)

```bash
# Example: Kinect v1 server
sudo cp services/interactive-projector-server-v1.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now interactive-projector-server-v1.service
journalctl -u interactive-projector-server-v1.service -f   # logs
```
The same pattern applies to the other service files.

### On Windows (PowerShell, as Administrator)

```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
.\services\install-windows-service.ps1 -Mode standalone      # Kinect v2
.\services\install-windows-service.ps1 -Mode standalone_v1   # Kinect v1
.\services\install-windows-service.ps1 -Mode client
# optional: -PythonPath "C:\path\to\interactive-projector\Scripts\python.exe"
```
The task runs at logon in the interactive user session (required for mouse control and the calibration window).

---

## ❓ Common Questions

### 1. Does USB/IP work with the Kinect?

**Kinect v2: No.** It transmits an uncompressed USB 3.0 isochronous stream with very high bandwidth (≈ 2–3 Gbit/s); over USB/IP it drops out or causes extreme latency.
**Kinect v1:** also isochronous (USB 2.0) and not reliable over USB/IP either. Run the server directly on the machine the Kinect is plugged into.

### 2. How do client and server communicate?

The server processes the depth data locally with OpenCV and only sends small JSON datagrams (a few bytes per event) via **UDP** to the client (see *Network protocol*). During calibration the server also sends the target positions, which the client displays.

### 3. Can dragging motions (dragging/slider) be detected?

**Yes.** A touch that moves further than `DRAG_THRESHOLD_PX` becomes `down` → continuous `move` → `up` when the finger is lifted.

### 4. Can we distinguish between left-click and right-click?

A short tap is a **left click**; holding the finger still for `HOLD_RIGHT_CLICK_SEC` (default 1.2 s) triggers a **right click**. Multi-finger gestures are not implemented.

### 5. Kinect v1 or v2?

The **v2** (time of flight) is more precise and less noisy; it is the better choice for small touch targets. The **v1** (structured light) works well for buttons and larger UI elements if it is mounted at 0.9–1.6 m; its advantages are USB 2.0 (runs easily on a Raspberry Pi) and low price. Fingers cast an IR shadow on the v1 – this is handled (invalid pixels are ignored), but it is the reason for the higher default thresholds in `config_v1.json`.
