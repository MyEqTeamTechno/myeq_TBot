<div align="center">

# 🤖 TBot — ROS 2 Jazzy Differential-Drive Robot

**A 4-wheeled (2 driven / 2 caster) differential-drive robot — SLAM, Nav2 navigation, IMU fusion, and lidar — running entirely on a Raspberry Pi 4B.**

![ROS2](https://img.shields.io/badge/ROS_2-Jazzy-1E88E5?style=for-the-badge&logo=ros&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04_LTS-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![RaspberryPi](https://img.shields.io/badge/Raspberry_Pi-4B-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white)

</div>

---

## 📑 Table of contents

- [Overview](#-overview)
- [Robot hardware](#-robot-hardware)
- [Package guide](#-package-guide)
- [1. Flash the OS](#1️⃣-flash-the-os-raspberry-pi-4b)
- [2. First boot & system setup](#2️⃣-first-boot--system-setup)
- [3. Install ROS 2 Jazzy](#3️⃣-install-ros-2-jazzy)
- [4. Clone & build the workspace](#4️⃣-clone--build-the-workspace)
- [5. Hardware wiring & permissions](#5️⃣-hardware-wiring--permissions)
- [6. Running on the real robot](#6️⃣-running-on-the-real-robot)
- [7. Remote RViz visualization](#7️⃣-remote-rviz-visualization-view-it-from-your-laptop)
- [8. Configuration reference](#8️⃣-configuration-reference)
- [Troubleshooting](#-troubleshooting)

---

## 🧭 Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Raspberry Pi 4B (TBot)                         │
│                                                                       │
│   Terminal 1 — "robot" role         Terminal 2 — "brain" role         │
│   robot_hardware.launch.py          laptop_brain.launch.py            │
│   ├─ tbot_firmware  (servos)        └─ tbot_slam (Cartographer)       │
│   ├─ tbot_imu       (BNO055)            — mapping mode                │
│   ├─ ydlidar_ros2_driver                                              │
│   ├─ robot_localization EKF         Terminal 2 — "localization" role  │
│   └─ robot_state_publisher          laptop_localization.launch.py     │
│                                          └─ tbot_nav (Nav2)           │
│                                          — navigation mode            │
│									│
└───────────────────────────────────────────────────────────────────────┘
              ▲                                        ▲
              └── you SSH in / attach a display ───────┘
              (optional: view RViz remotely via VNC or X11 forwarding)
```

Since everything is co-located on one Pi, just open multiple terminals/SSH sessions to run the pieces described in [Section 6](#6️⃣-running-on-the-real-robot).

## 🔧 Robot hardware

- 🖥️ **SBC** — Raspberry Pi 4B, Ubuntu 24.04 Server, ROS 2 Jazzy — runs the **entire stack**
- ⚙️ **Drive** — 4 wheels, only **2 motorized** (front-left + rear-right, diagonal drive) using **Waveshare ST3215** smart servos over serial `/dev/ttyACM0` @ 1,000,000 baud; front-right/rear-left are passive casters
- 📡 **Lidar** — YDLidar (X2 by default) on `/dev/ttyUSB0` @ 115200 baud
- 🧭 **IMU** — Bosch BNO055 (default, I²C); MPU6050 supported as an alternative

## 📦 Package guide

- 🚀 `tbot_bringup` — orchestration — top-level launch files for hardware, SLAM, Nav2, plus saved maps
- 🦴 `tbot_description` — URDF/meshes — robot model, RViz configs, state-publisher launch helpers
- 🛞 `tbot_firmware` — motor driver — talks to ST3215 servos over serial, publishes `/odom`, subscribes `/cmd_vel`
- 🌐 `tbot_gazebo` — simulation — placeholder package, not currently implemented
- 🧭 `tbot_imu` — sensor driver — BNO055 / MPU6050 IMU nodes, publish `sensor_msgs/Imu`
- 🗺️ `tbot_nav` — navigation — Nav2 parameters + launch wrapper around `nav2_bringup`
- 🧩 `tbot_slam` — mapping/localization — Cartographer config, EKF sensor fusion, slam_toolbox config
- 📟 `ydlidar_ros2_driver` — 3rd-party — YDLidar ROS 2 driver + udev-rule installer script
- 🧮 `YDLidar_SDK_jazzy` — 3rd-party — C++ SDK dependency required to build `ydlidar_ros2_driver`

### 🚀 tbot_bringup — top-level launch orchestration

- **`launch/robot_hardware.launch.py`** — starts the hardware stack:
    - `robot_state_publisher` (from `tbot_description` xacro)
    - `tbot_firmware` motor node (`four_wheeled_diff.py`)
    - `tbot_imu` node (`imu_node.py`, remapped to `/imu`)
    - `ydlidar_ros2_driver/launch/ydlidar_launch.py`
    - `robot_localization` EKF node (`tbot_slam/config/ekf.yaml`)
    - static TF (`base_link`→`laser_frame`)
    - `joint_state_publisher`
- **`launch/laptop_brain.launch.py`** — **mapping** role, wraps `tbot_slam/launch/cartographer.launch.py`
- **`launch/laptop_localization.launch.py`** — **navigation** role, loads a saved map + `tbot_nav/launch/navigation.launch.py`
- **`maps/`** — saved maps:
    - `home_sir`
    - `mye_office_cdr`
    - `myeq_office`
    - `my_map`
    - `my_play_map` (default)
    - `test_map`

### 🛞 tbot_firmware — motor driver (Waveshare ST3215 servos)

- Node: `scripts/four_wheeled_diff.py` → node name `differential_closed_loop_2m`
- Serial:
    - port: `/dev/ttyACM0`
    - baud: 1,000,000
- Servo IDs:
    - `LEFT_ID = 2` (front-left)
    - `RIGHT_ID = 1` (rear-right)
- Geometry:
    - wheel diameter: 0.065 m
    - wheel separation: 0.23 m
    - wheel radius: 0.0325 m
- Subscribes `/cmd_vel`
- Publishes `/odom` + `odom→base_link` TF at 20 Hz
- Vendors `scservo_sdk` (Feetech STS/SCS binary protocol over serial)

### 🧭 tbot_imu — IMU driver

- **`imu_node.py`** (default) — Bosch BNO055 over I²C
    - requires `adafruit-blinka` + `adafruit-circuitpython-bno055`
    - publishes `/imu/data` at 20 Hz
    - `frame_id: imu`
    - ships fixed calibration offsets labeled "myeq_office specific" — **recalibrate for your environment** using `bno055_calibrator.py` (present but not wired into the build — run it manually with `python3`)
- **`mpu6050_node.py`** (alternate) — MPU6050 over I²C
    - requires `python3-smbus` + `mpu6050`
    - params: `i2c_address` (default `0x68`), `frame_id`

### 🧩 tbot_slam — SLAM & sensor fusion config

- **`config/mapping.lua`** — Cartographer config:
    - frames: `map_frame`, `odom_frame`, `base_link`
    - pure-lidar mapping (`use_odometry=false`, `use_imu_data=false`)
    - `min_range=0.05`, `max_range=8.0`
- **`config/ekf.yaml`** — `robot_localization` EKF:
    - fuses `/odom` (yaw-rate only)
    - fuses `/imu` (yaw, roll/pitch rates)
    - runs at 20 Hz
- **`launch/cartographer.launch.py`** — mapping-mode launch (used by `laptop_brain.launch.py`)
- **`launch/tbot_slam_toolbox.launch.py`** — alternate slam_toolbox-based launch path

### 🗺️ tbot_nav — Nav2 navigation stack

- **`config/nav2_params_robot.yaml`**:
    - controller: DWB, `max_vel_x=0.15`, `max_vel_theta=3.0`
    - localization: AMCL
    - costmaps: `robot_radius=0.1`
- **`launch/navigation.launch.py`** — wraps `nav2_bringup/launch/bringup_launch.py`, default map `tbot_bringup/maps/my_play_map.yaml`

### 📟 ydlidar_ros2_driver — lidar driver (3rd-party)

- **`launch/ydlidar_launch.py`** loads `params/X2.yaml` by default:
    - port: `/dev/ttyUSB0`
    - baud: 115200
- Other model configs available in `params/`: G1, G2, G6, GS2, TEA, TG, TminiPro, X4, X4-Pro — pass `params_file:=` to override
- **`startup/initenv.sh`** — installs udev rules for common USB-serial chips (CP2102, STM32 CDC, PL2303) → symlinks to `/dev/ydlidar`. **Run once as root on the robot.**

---

## 1️⃣ Flash the OS (Raspberry Pi 4B)

Pick one of two paths.

### Path A — Flash the pre-built TBot image (fastest)

This image already has Ubuntu 24.04, ROS 2 Jazzy, the built workspace, all dependencies, and udev rules set up — you just flash it and boot, no setup steps required.

> [!NOTE]
> Image link placeholder — replace with your own pre-built TBot image:
> **`<TBOT_PREBUILT_IMAGE_URL_HERE>`**

1. Flash the image to a microSD card (or SSD/USB) using [Raspberry Pi Imager](https://www.raspberrypi.com/software/) or `dd`.
2. Insert the flashed media into the Pi 4B and power it on.
3. SSH in (see [Section 2](#2️⃣-first-boot--system-setup) for the credentials) and, optionally, pull/rebuild the latest workspace changes:
   ```bash
   cd ~/tbot_2M_ws
   colcon build --symlink-install
   source install/setup.bash
   ```
4. Skip straight to [Section 6 — Running on the real robot](#6️⃣-running-on-the-real-robot).

### Path B — Build from scratch

Start from a vanilla Ubuntu image and do the full ROS 2 + workspace setup yourself. Continue with Sections 2–5 below.

> [!NOTE]
> Image link placeholder — replace with a vanilla Ubuntu 24.04 (Noble) arm64 Raspberry Pi image:
> **`<VANILLA_UBUNTU_24.04_RPI4B_IMAGE_URL_HERE>`**

1. Open [Raspberry Pi Imager](https://www.raspberrypi.com/software/) and select the vanilla Ubuntu 24.04 (Noble) arm64 image above as the OS.
2. Before writing, click the ⚙️ gear icon ("Edit Settings") and configure:
    - **Hostname** — e.g. `tbot`
    - **Username / password** — e.g. `ubuntu` / `pi` (or your own credentials — just make sure they match what you use to SSH in later)
    - **Wi-Fi SSID / password** (or plan to use Ethernet instead)
    - **Enable SSH** — toggle on, using password authentication
    - **Locale/timezone/keyboard** as needed
3. Write the image to a microSD card (or SSD/USB).
4. Insert the media into the Pi 4B and power it on.
5. Continue with [Section 2](#2️⃣-first-boot--system-setup).

## 2️⃣ First boot & system setup

```bash
# SSH into the robot
ssh ubuntu@<robot-ip>
# password: pi

# Update system
sudo apt update && sudo apt upgrade -y

# Enable I2C for the IMU (BNO055 / MPU6050)
sudo apt install -y i2c-tools python3-smbus
sudo raspi-config   # Interface Options -> I2C -> Enable
sudo reboot
```

Verify I2C after reboot:

```bash
i2cdetect -y 1
```

## 3️⃣ Install ROS 2 Jazzy

Follow the official instructions: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository universe

sudo apt update && sudo apt install -y curl
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
sudo apt install -y /tmp/ros2-apt-source.deb

sudo apt update && sudo apt upgrade -y
sudo apt install -y ros-jazzy-ros-base ros-dev-tools
```

Install the packages this workspace depends on (Nav2, Cartographer, robot_localization, etc.):

```bash
sudo apt install -y \
  ros-jazzy-nav2-bringup ros-jazzy-nav2-common \
  ros-jazzy-cartographer ros-jazzy-cartographer-ros \
  ros-jazzy-slam-toolbox \
  ros-jazzy-robot-localization \
  ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher \
  ros-jazzy-xacro \
  ros-jazzy-tf2-tools \
  python3-colcon-common-extensions python3-rosdep
```

Source ROS in your shell profile:

```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## 4️⃣ Clone & build the workspace

```bash
mkdir -p ~/tbot_2M_ws/src
cd ~/tbot_2M_ws
git clone <your-repo-url> src_tmp && shopt -s dotglob && mv src_tmp/* src/ && rm -rf src_tmp
# (or, if this repo already contains the src/ layout at its root:)
# git clone <your-repo-url> .

cd ~/tbot_2M_ws

# Install Python dependencies not covered by apt/rosdep
pip install --break-system-packages \
  adafruit-blinka adafruit-circuitpython-bno055

# Resolve remaining ROS dependencies
rosdep update
rosdep install --from-paths src --ignore-src -r -y

# Build
colcon build --symlink-install

# Source the workspace (add to ~/.bashrc for persistence)
echo "source ~/tbot_2M_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

> [!TIP]
> This is all done **once, on the Pi** — there's no separate laptop build step in this setup.

## 5️⃣ Hardware wiring & permissions

```bash
# Serial/dialout permissions (servo controller + lidar)
sudo usermod -aG dialout $USER
# log out/in (or reboot) for group change to take effect

# Lidar udev rules (creates /dev/ydlidar symlink, mode 0666, group dialout)
cd ~/tbot_2M_ws/src/ydlidar_ros2_driver/startup
sudo chmod +x initenv.sh
sudo ./initenv.sh
```

Confirm devices are present before launching:

```bash
ls -l /dev/ttyACM0     # Waveshare ST3215 servo bus (motor driver)
ls -l /dev/ttyUSB0      # YDLidar (or /dev/ydlidar after the udev rule)
i2cdetect -y 1          # BNO055 (0x28/0x29) or MPU6050 (0x68)
```

> [!TIP]
> If your servo bus or lidar enumerates on a different `/dev/tty*` path, edit `DEVICENAME` in
> `src/tbot_firmware/tbot_firmware/scripts/four_wheeled_diff.py` (or the params in
> `src/ydlidar_ros2_driver/params/X2.yaml`) accordingly, then rebuild with `colcon build --symlink-install`.

## 6️⃣ Running on the real robot

All commands below run **on the Pi**, each in its own terminal or SSH session — "robot"/"brain"/"localization" refer to the *role* each terminal plays, not a different physical machine.

### 🗺️ Mapping (build a new map)


#### Terminal 1 — hardware role
```bash
ros2 launch tbot_bringup robot_hardware.launch.py
```

#### Terminal 2 — mapping role
```bash
ros2 launch tbot_bringup laptop_brain.launch.py
```

#### Terminal 3 — once mapping is done, save it straight into the workspace's maps folder
```bash
ros2 run nav2_map_server map_saver_cli -f ~/tbot_2M_ws/src/tbot_bringup/maps/map
# .yaml is appended automatically — this produces:
#   ~/tbot_2M_ws/src/tbot_bringup/maps/map.pgm
#   ~/tbot_2M_ws/src/tbot_bringup/maps/map.yaml
```

#### Terminal 4 — Drive the robot around the space until the map looks complete
```bash
ros2 launch teleop_twist_keyboard teleop_twist_keyboard
```

### 🧭 Navigation (localize + move autonomously on a saved map)

#### Terminal 1 — hardware role
```bash
ros2 launch tbot_bringup robot_hardware.launch.py
```

#### Terminal 2 — navigation role, pointing at the map saved above
```
ros2 launch tbot_bringup laptop_localization.launch.py map:=/home/ubuntu/tbot_2M_ws/src/tbot_bringup/maps/map.yaml

# Use RViz "2D Pose Estimate" to set the initial pose, then "Nav2 Goal" to send goals
```

### 🌳 Save the TF tree (debugging)

```bash
ros2 run tf2_tools view_frames
```

## 7️⃣ Remote RViz visualization (view it from your laptop)

The Pi does all the heavy lifting (SLAM/Nav2/drivers), but RViz is a GPU-hungry GUI you don't want to run on the Pi itself — run it on your laptop instead. ROS 2 nodes discover each other automatically over the network (DDS), so RViz on your laptop can subscribe directly to the topics/TFs published by the Pi with **no SSH or X11 forwarding needed**.

### One-time laptop setup

1. Install Ubuntu 24.04 on your laptop (matching the Pi's ROS distro avoids message/DDS compatibility issues).
2. Install ROS 2 Jazzy with RViz included:
   ```bash
   sudo apt install ros-jazzy-desktop
   ```
   (`ros-jazzy-desktop` includes `rviz2`; you don't need to build the TBot workspace on the laptop since this repo only uses standard message types.)
3. Source ROS in your shell profile:
   ```bash
   echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
   source ~/.bashrc
   ```

### Match the ROS network

1. Connect the laptop to the **same network** as the Pi (same Wi-Fi AP or switch — avoid "guest"/client-isolated Wi-Fi networks, they block the multicast traffic ROS 2 discovery needs).
2. Set the same `ROS_DOMAIN_ID` on **both** the Pi and the laptop:
   ```bash
   echo "export ROS_DOMAIN_ID=42" >> ~/.bashrc   # pick any number 0-232, same on both machines
   source ~/.bashrc
   ```
3. Quick check from the laptop — with the stack running on the Pi (Section 6), confirm you can already see its topics:
   ```bash
   ros2 topic list
   ```
   If nothing shows up, double-check both machines are on the same subnet/`ROS_DOMAIN_ID`, and that no firewall is blocking UDP multicast.

### Launch RViz on the laptop

Grab the matching `.rviz` config from `tbot_description/rviz/` (copy it over with `scp`, or just clone the repo on the laptop too) and point RViz at it:

```bash
# Mapping session (matches laptop_brain.launch.py)
rviz2 -d ~/tbot_2M_ws/src/tbot_description/rviz/myeq_office.rviz

# Navigation/localization session (matches laptop_localization.launch.py)
rviz2 -d ~/tbot_2M_ws/src/tbot_description/rviz/localisation_config.rviz
```

You should see the live laser scan, TF tree, and map/costmaps streaming in from the Pi in real time. Set **Fixed Frame** to `map` (or `odom` if no map is loaded yet) if it isn't already selected.

> [!TIP]
> Simpler but slower fallback: `ssh -X ubuntu@<robot-ip>` then run `rviz2` directly on the Pi — X11 forwards the GUI to your laptop's display without any network/domain-ID setup. Fine for a quick look, but noticeably laggier than native DDS discovery, especially over Wi-Fi.

## 8️⃣ Configuration reference

| Setting | Location | Value |
|---|---|---|
| Servo serial port / baud | `tbot_firmware/scripts/four_wheeled_diff.py` | `/dev/ttyACM0` @ 1,000,000 |
| Wheel separation / radius | `tbot_firmware/scripts/four_wheeled_diff.py` | 0.23 m / 0.0325 m |
| Lidar port / baud | `ydlidar_ros2_driver/params/X2.yaml` | `/dev/ttyUSB0` @ 115200 |
| IMU (default) | `tbot_imu/src/imu_node.py` | BNO055 over I²C, `/imu/data` @ 20 Hz |
| EKF fusion config | `tbot_slam/config/ekf.yaml` | fuses `/odom` + `/imu` → `/odometry/filtered` |
| Cartographer config | `tbot_slam/config/mapping.lua` | lidar-only mapping |
| Nav2 params | `tbot_nav/config/nav2_params_robot.yaml` | `max_vel_x=0.15`, `robot_radius=0.1` |
| Map (saved above) | `tbot_bringup/maps/map.yaml` | pass via `map:=` |

## 🩺 Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Failed to load map yaml file: map.yaml` | You launched without passing `map:=` an explicit path to a saved map |
| `collision_monitor` process dies immediately | `observation_sources` isn't configured for the collision monitor in `nav2_params_robot.yaml`; safe to ignore or configure it if you need collision monitoring |
| Robot doesn't move / serial port won't open | Check `/dev/ttyACM0` exists and your user is in `dialout` (Section 5); confirm servo IDs `1`/`2` are set correctly on the ST3215 units |
| Topics missing between terminals | Confirm all sessions source `install/setup.bash` |
| IMU readings drifting/wrong | Recalibrate the BNO055 with `tbot_imu/src/bno055_calibrator.py` and update the offsets in `imu_node.py` for your environment |
