#!/usr/bin/env python3
"""
differential_drive_2motor.py

ROS2 node to control a 4-wheeled chassis where only 2 diagonal wheels are powered
(ST3215 style):
    - Front-Left  wheel: powered (acts as the "left" wheel)
    - Rear-Right  wheel: powered (acts as the "right" wheel)
    - Front-Right & Rear-Left: passive (ball-bearing mounts)

Because only one wheel drives each side, this behaves as a standard differential
drive with a single left motor and a single right motor. No per-side averaging is
needed anymore.

- Sends the left command to the front-left motor, the right command to the rear-right motor.
- Reads each motor's reported position for odometry (one wheel per side).
- Publishes /odom and broadcasts odom -> base_link TF (needed for Nav2).
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Quaternion, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
from math import pi, sin, cos
import sys
import os

# Ensure the SDK is in your path (adjust if package layout differs)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tbot_firmware.scservo_sdk import *   # Provides sms_sts, PortHandler, COMM_SUCCESS, etc.


class DifferentialClosedLoop2M(Node):
    def __init__(self):
        super().__init__('differential_closed_loop_2m')

        # --- Robot Physical Params ---
        self.wheel_diameter = 0.065      # meters

        # wheel_separation - meters (lateral distance between the LEFT and RIGHT
        # driven wheel centers, i.e. the track width). Even though the two driven
        # wheels are diagonal, differential-drive kinematics only depend on this
        # lateral separation.
        self.wheel_separation = 0.23
        # self.wheel_separation = 0.17 (def value)
        self.wheel_radius = self.wheel_diameter / 2.0

        # --- ST3215 Servo Setup (update IDs to match your hardware) ---
        # Only the two diagonally-opposed driven wheels remain.
        self.LEFT_ID = 2      # Front-Left wheel (powered)
        self.RIGHT_ID = 1    # Rear-Right wheel (powered)

        self.BAUDRATE = 1000000
        self.DEVICENAME = '/dev/ttyACM0'
        self.SCS_MOVING_ACC = 50
        self.MAX_SCS_SPEED = 2400        # integer units used by servo
        self.motor_rpm = 60.0            # RPM corresponding to MAX_SCS_SPEED (measured)
        self.max_speed_ms = ((2 * pi * self.wheel_radius) * self.motor_rpm) / 60.0

        # If True, the sign/direction mapping used when writing <-> reading is inverted.
        # Tune this if your motors run reversed in one side.
        self.invert_motors = True

        # --- Initialize Serial Port and Packet Handler ---
        self.portHandler = PortHandler(self.DEVICENAME)
        self.packetHandler = sms_sts(self.portHandler)

        if self.portHandler.openPort():
            self.get_logger().info("Succeeded to open the port")
        else:
            self.get_logger().error("Failed to open the port")
            sys.exit(1)

        if self.portHandler.setBaudRate(self.BAUDRATE):
            self.get_logger().info("Succeeded to change the baudrate")
        else:
            self.get_logger().error("Failed to change the baudrate")
            sys.exit(1)

        # Put each driven servo into wheel (continuous) mode
        for scs_id in (self.LEFT_ID, self.RIGHT_ID):
            self.setup_wheel_mode(scs_id)

        # --- Odometry State Variables ---
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        self.last_time = self.get_clock().now()
        self.last_positions = {
            self.LEFT_ID: None,
            self.RIGHT_ID: None
        }

        # --- ROS 2 Subscriptions & Publishers ---
        self.vel_subscription = self.create_subscription(Twist, "cmd_vel", self.cmd_vel_callback, 10)
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Timer to read encoders and publish odometry at 20Hz
        self.timer = self.create_timer(0.05, self.update_odometry)

        self.get_logger().info("ST3215 2-motor (diagonal) Closed-Loop Drive & Odom Ready for Nav2.")

    def setup_wheel_mode(self, scs_id):
        """Sets the specified ST3215 servo into wheel (continuous) mode."""
        scs_comm_result, scs_error = self.packetHandler.WheelMode(scs_id)
        if scs_comm_result != COMM_SUCCESS:
            self.get_logger().error(f"ID {scs_id}: {self.packetHandler.getTxRxResult(scs_comm_result)}")
        elif scs_error != 0:
            self.get_logger().error(f"ID {scs_id}: {self.packetHandler.getRxPacketError(scs_error)}")

    def speed_to_scs_units(self, speed_ms, is_left=True):
        """Converts linear speed (m/s) to ST3215 integer speed units for writing."""
        if abs(speed_ms) < 0.01:
            return 0

        # Normalize between -1.0 and 1.0
        normalized = speed_ms / self.max_speed_ms
        normalized = max(min(normalized, 1.0), -1.0)

        # Handle motor physical orientation mirroring
        if self.invert_motors:
            direction_multiplier = -1 if is_left else 1
        else:
            direction_multiplier = 1 if is_left else -1

        return int(normalized * self.MAX_SCS_SPEED * direction_multiplier)

    def decode_scs_speed_to_ms(self, raw_speed, is_left=True):
        """Decodes raw 15-bit + sign speed from servo to real m/s."""
        # ST3215 uses bit 15 (0x8000) as the sign bit
        magnitude = raw_speed & 0x7FFF
        sign = -1 if (raw_speed & 0x8000) else 1
        scs_speed = magnitude * sign

        # Reverse the inversion multiplier applied during writing
        if self.invert_motors:
            direction_multiplier = -1 if is_left else 1
        else:
            direction_multiplier = 1 if is_left else -1

        real_scs_speed = scs_speed * direction_multiplier

        # Convert back to m/s
        rpm = (real_scs_speed / self.MAX_SCS_SPEED) * self.motor_rpm
        speed_ms = (rpm * 2 * pi * self.wheel_radius) / 60.0
        return speed_ms

    def cmd_vel_callback(self, data):
        """Calculates IK and sends target speeds to the two driven servos."""
        v = data.linear.x
        w = data.angular.z

        # Differential Kinematics
        left_vel = v - (w * self.wheel_separation / 2.0)
        right_vel = v + (w * self.wheel_separation / 2.0)

        left_scs_speed = self.speed_to_scs_units(left_vel, is_left=True)
        right_scs_speed = self.speed_to_scs_units(right_vel, is_left=False)

        # One motor per side
        self.packetHandler.WriteSpec(self.LEFT_ID, left_scs_speed, self.SCS_MOVING_ACC)
        self.packetHandler.WriteSpec(self.RIGHT_ID, right_scs_speed, self.SCS_MOVING_ACC)

    def get_position_delta_m(self, raw_pos, scs_id, is_left, comm_success):
        if comm_success != COMM_SUCCESS:
            return 0.0

        current_pos = raw_pos & 0x0FFF
        last_pos = self.last_positions[scs_id]
        self.last_positions[scs_id] = current_pos

        if last_pos is None:
            return 0.0

        diff = current_pos - last_pos
        if diff > 2048:
            diff -= 4096
        elif diff < -2048:
            diff += 4096

        distance_m = (diff / 4096.0) * (2 * pi * self.wheel_radius)

        if self.invert_motors:
            direction_multiplier = -1 if is_left else 1
        else:
            direction_multiplier = 1 if is_left else -1

        return distance_m * direction_multiplier

    def update_odometry(self):
        """Reads position feedback, computes FK, integrates pose, and publishes Odom/TF."""
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        if dt <= 0.0:
            return

        l_pos, _, l_comm, _ = self.packetHandler.ReadPosSpeed(self.LEFT_ID)
        r_pos, _, r_comm, _ = self.packetHandler.ReadPosSpeed(self.RIGHT_ID)

        # One wheel per side, so no averaging needed.
        dist_left = self.get_position_delta_m(l_pos, self.LEFT_ID, True, l_comm)
        dist_right = self.get_position_delta_m(r_pos, self.RIGHT_ID, False, r_comm)

        # Forward Kinematics (Actual Robot displacement)
        actual_distance = (dist_right + dist_left) / 2.0
        delta_th = (dist_right - dist_left) / self.wheel_separation

        actual_v = actual_distance / dt
        actual_w = delta_th / dt

        delta_x = actual_distance * cos(self.th + delta_th / 2.0)
        delta_y = actual_distance * sin(self.th + delta_th / 2.0)

        self.x += delta_x
        self.y += delta_y
        self.th += delta_th

        # Populate Odometry Message
        odom_quat = self.yaw_to_quaternion(self.th)

        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation = odom_quat

        odom.twist.twist.linear.x = actual_v
        odom.twist.twist.angular.z = actual_w

        # Basic covariance tuning (optional)
        odom.pose.covariance[0] = 0.001
        odom.pose.covariance[7] = 0.001
        odom.pose.covariance[35] = 0.01

        # Publish TF Transform
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = "odom"
        t.child_frame_id = "base_link"
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = odom_quat

        # Publish
        self.odom_pub.publish(odom)
        self.tf_broadcaster.sendTransform(t)

        self.last_time = current_time

    def yaw_to_quaternion(self, yaw):
        q = Quaternion()
        q.z = sin(yaw / 2.0)
        q.w = cos(yaw / 2.0)
        return q

    def stop_robot(self):
        self.get_logger().info("Stopping robot and closing port...")
        # Stop both driven motors
        for scs_id in (self.LEFT_ID, self.RIGHT_ID):
            self.packetHandler.WriteSpec(scs_id, 0, self.SCS_MOVING_ACC)
        if self.portHandler.is_open:
            self.portHandler.closePort()


def main(args=None):
    rclpy.init(args=args)
    node = DifferentialClosedLoop2M()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
