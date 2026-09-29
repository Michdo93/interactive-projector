# Interactive Projector (`interactive-projector`)

An open-source computer vision and depth-sensing system that transforms any flat surface (table top or vertical wall) into an interactive touch screen using a **Projector**, a **Microsoft Kinect v2**, and **Python**.

By mounting a Kinect v2 directly onto or next to a projector, this software monitors distance differentials relative to the baseline surface. When an object (such as a finger or hand) enters a tight depth zone above the surface, it calculates the coordinate, converts it to display coordinates via 2D Homography, and triggers native OS mouse events.

---

## 📐 System Architecture & Hardware Setup

```
   [ Projector + Kinect v2 Mounted Together ]
                       |
                       |  (Projection & Depth Sensing Area)
                       v
   ==========================================
              [ Surface / Table ]
```

### Hardware Requirements
1. **Projector:** Short-throw or Ultra-Short-Throw projector recommended (Full HD 1080p, $\ge 2500$ ANSI Lumens).
2. **Kinect v2:** Microsoft Kinect for Windows v2 with the official (or compatible third-party) PC USB 3.0 & Power Adapter.
3. **Mounting:** Attach the Kinect v2 directly onto or right next to the projector housing facing the exact same direction.
4. **Surface:** Matte white or light-colored flat table or wall.
5. **PC:** Windows 10/11 (64-bit) with a dedicated USB 3.0 controller host.

---

## 💻 Software Prerequisites

1. **Kinect for Windows SDK 2.0:** Download and install from Microsoft's official driver site.
2. **Python 3.8 to 3.10 (64-bit)** (Python 3.11+ might require compiling `pykinect2` C-bindings manually).

---

## ⚡ Installation Guide

### 1. Clone or Extract Repository
```bash
git clone https://github.com/Michdo93/interactive-projector.git
cd interactive-projector
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Execution & Usage Tutorial

### Step 1: Display Configuration
1. Connect the projector as a second display.
2. In Windows Display Settings, set display mode to **Extend** (do not duplicate).
3. Ensure the display resolution matches `PROJECTOR_WIDTH` and `PROJECTOR_HEIGHT` in `config.json` (e.g., 1920x1080).

### Step 2: Run the Main Script
```bash
python src/main.py
```

### Step 3: Homography Calibration
1. A fullscreen window will open on your projector showing red target circles one by one in 4 corners.
2. Look at the `Kinect Depth Preview` window on your primary monitor.
3. Left-click with your physical PC mouse on the center of the target dot as seen through the Kinect camera view.
4. Repeat for all 4 corner points. The homography matrix will be computed automatically.

### Step 4: Baseline Plane Capture
1. When prompted by the console, remove all objects, hands, and obstructions from the surface area.
2. The system will sample baseline surface depth for 3 seconds.

### Step 5: Touch Interaction Mode
1. Tap your finger on the projected display area on your table or wall.
2. The mouse cursor will move directly to your finger's location. Holding a tap for consecutive frames triggers a left click.
3. Press `q` in the preview window to exit at any time.

---

## ⚙️ Configuration Parameters (`config.json`)

* `PROJECTOR_WIDTH` / `PROJECTOR_HEIGHT`: Pixel dimensions of your projector display.
* `TOUCH_MIN_MM`: Minimum elevation from surface to register touch (default: `5.0` mm).
* `TOUCH_MAX_MM`: Maximum elevation threshold for touch detection (default: `25.0` mm).
* `MIN_CONTOUR_AREA`: Minimum contour pixel area to ignore noise (default: `20`).
* `MAX_CONTOUR_AREA`: Maximum contour pixel area to reject massive obstructions like arms or leaning bodies (default: `8000`).
* `CLICK_HOLD_FRAMES`: Number of stable touch frames required to issue a mouse click event.
