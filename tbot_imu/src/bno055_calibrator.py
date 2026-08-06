#!/usr/bin/env python3
"""
bno055_calibrator.py

Interactive calibrator for Adafruit / Bosch BNO055 using CircuitPython driver.

Usage:
  python3 bno055_calibrator.py        # enter interactive calibration -> save offsets
  python3 bno055_calibrator.py --load # load offsets from bno055_calib.json onto the device
"""
import time
import json
import argparse
import board
import adafruit_bno055

CALIB_FILE = "bno055_calib.json"
POLL_HZ = 5.0

def read_cal_status(sensor):
    # returns tuple (sys, gyro, accel, mag)
    try:
        return sensor.calibration_status
    except Exception:
        return (0,0,0,0)

def read_offsets(sensor):
    # library exposes offsets as properties (may be None if not available)
    offsets = {}
    for name in ("offsets_accelerometer", "offsets_gyroscope", "offsets_magnetometer"):
        try:
            val = getattr(sensor, name)
            if val is None:
                offsets[name] = None
            else:
                offsets[name] = [int(v) for v in val]
        except Exception:
            offsets[name] = None
    # mag radius / accel radius may exist -> include if present
    try:
        offsets["mag_radius"] = int(sensor.magnetometer_radius) if hasattr(sensor, "magnetometer_radius") and sensor.magnetometer_radius is not None else None
    except Exception:
        # some library builds call it mag_radius
        try:
            offsets["mag_radius"] = int(sensor.mag_radius)
        except Exception:
            offsets["mag_radius"] = None
    return offsets

def save_offsets_to_file(offsets, filename=CALIB_FILE):
    with open(filename, "w") as f:
        json.dump(offsets, f, indent=2)
    print(f"Saved offsets to {filename}")

def load_offsets_from_file(filename=CALIB_FILE):
    with open(filename, "r") as f:
        return json.load(f)

def apply_offsets_to_sensor(sensor, offsets):
    # To write offsets we switch to CONFIG_MODE, write offsets, then return to NDOF_MODE
    try:
        sensor.mode = adafruit_bno055.CONFIG_MODE
    except Exception:
        pass
    # set offsets if present
    if offsets.get("offsets_accelerometer"):
        try:
            sensor.offsets_accelerometer = tuple(offsets["offsets_accelerometer"])
            print("Applied accelerometer offsets")
        except Exception as e:
            print("Failed to apply accel offsets:", e)
    if offsets.get("offsets_gyroscope"):
        try:
            sensor.offsets_gyroscope = tuple(offsets["offsets_gyroscope"])
            print("Applied gyroscope offsets")
        except Exception as e:
            print("Failed to apply gyro offsets:", e)
    if offsets.get("offsets_magnetometer"):
        try:
            sensor.offsets_magnetometer = tuple(offsets["offsets_magnetometer"])
            print("Applied magnetometer offsets")
        except Exception as e:
            print("Failed to apply mag offsets:", e)
    if offsets.get("mag_radius") is not None:
        try:
            # some builds use sensor.magnetometer_radius or sensor.mag_radius
            if hasattr(sensor, "magnetometer_radius"):
                sensor.magnetometer_radius = int(offsets["mag_radius"])
            elif hasattr(sensor, "mag_radius"):
                sensor.mag_radius = int(offsets["mag_radius"])
            print("Applied magnetometer radius")
        except Exception as e:
            print("Failed to apply mag radius:", e)
    # go back to fusion mode for normal operation
    try:
        sensor.mode = adafruit_bno055.NDOF_MODE
    except Exception:
        pass

def interactive_calibrate(sensor):
    print("Starting interactive calibration.")
    print("Guidance:")
    print(" - Gyro: keep the board perfectly still for a few seconds.")
    print(" - Accelerometer: orient the board on each face (x+/-, y+/-, z+/-) and hold ~1-2s each.")
    print(" - Magnetometer: wave the board slowly in a figure-8 motion in 3D until Mag reaches 3.")
    print()
    print("Press Ctrl-C to abort at any time.")
    print()

    try:
        while True:
            sys, gyro, accel, mag = read_cal_status(sensor)
            print(f"Calibration status: SYS={sys}  GYRO={gyro}  ACCEL={accel}  MAG={mag}", end="\r")
            if sys == 3 and gyro == 3 and accel == 3 and mag == 3:
                print("\n*** Device fully calibrated (3/3/3/3). Reading offsets... ***")
                offsets = read_offsets(sensor)
                print("Offsets read from sensor:")
                print(json.dumps(offsets, indent=2))
                save_offsets_to_file(offsets)
                print("Done. You can now copy the JSON file to your robot/software and load it at startup.")
                return
            time.sleep(1.0 / POLL_HZ)
    except KeyboardInterrupt:
        print("\nCalibration aborted by user.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--load", action="store_true", help="Load offsets from file onto the BNO055 and exit")
    args = parser.parse_args()

    i2c = board.I2C()
    sensor = adafruit_bno055.BNO055_I2C(i2c)
    print("BNO055 initialized. Current mode:", getattr(sensor, "mode", "unknown"))
    time.sleep(0.5)

    if args.load:
        try:
            offsets = load_offsets_from_file()
            apply_offsets_to_sensor(sensor, offsets)
            print("Offsets loaded from file and applied.")
        except FileNotFoundError:
            print(f"No offset file found ({CALIB_FILE}). Run without --load to create one.")
        return

    # Interactive calibration flow
    interactive_calibrate(sensor)

if __name__ == "__main__":
    main()
