#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Imu
from geometry_msgs.msg import Vector3, Quaternion

import math

# MPU6050 driver (external package)
try:
    from mpu6050 import mpu6050
except ImportError as e:
    raise RuntimeError(
        "MPU6050 driver not found.\n"
        "Install with:\n"
        "  sudo apt install -y python3-smbus i2c-tools\n"
        "  pip3 install mpu6050-raspberrypi"
    ) from e


G_TO_MS2 = 9.80665


class ImuPublisher(Node):

    def __init__(self):
        super().__init__('imu_publisher')

        # ---------------- Parameters ----------------
        self.declare_parameter('i2c_address', 0x68)
        self.declare_parameter('frame_id', 'imu')
        self.declare_parameter('publish_hz', 30.0)  # decrease to <20 Hz
        self.declare_parameter('topic_name', '/imu')

        self.declare_parameter('accel_offsets', [0.0, 0.0, 0.0])
        self.declare_parameter('gyro_offsets', [0.0, 0.0, 0.0])

        # Reading 1:
        # Gyroscope Offsets: 
        # gyro_x_offset --> -2.79618
        # gyro_y_offset --> -2.73005
        # gyro_z_offset --> 1.66064

        # Accelerometer Offsets: 
        # accel_x_offset --> 0.212989
        # accel_y_offset --> 0.132406
        # accel_z_offset --> 10.4905

        # Reading 2: 
        # Gyroscope Offsets: 
        # gyro_x_offset --> -2.80351
        # gyro_y_offset --> -2.69489
        # gyro_z_offset --> 1.65768

        # Accelerometer Offsets: 
        # accel_x_offset --> 0.041544
        # accel_y_offset --> 0.515226
        # accel_z_offset --> 10.4795


        i2c_address = self.get_parameter('i2c_address').value
        self.frame_id = self.get_parameter('frame_id').value
        publish_hz = self.get_parameter('publish_hz').value
        topic_name = self.get_parameter('topic_name').value

        self.accel_offsets = self.get_parameter('accel_offsets').value
        self.gyro_offsets = self.get_parameter('gyro_offsets').value

        # ---------------- Publisher ----------------
        self.publisher_ = self.create_publisher(Imu, topic_name, 10)

        period = 1.0 / publish_hz
        self.timer = self.create_timer(period, self.publish_imu_data)

        # ---------------- Sensor ----------------
        self.get_logger().info(
            f"Initializing MPU6050 at I2C address 0x{i2c_address:02x}"
        )
        self.sensor = mpu6050(i2c_address)

        self.get_logger().info(
            f"IMU publisher started | topic: {topic_name} | rate: {publish_hz} Hz | frame: {self.frame_id}"
        )

    # -------------------------------------------------

    def publish_imu_data(self):
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        try:
            accel = self.sensor.get_accel_data()
            gyro = self.sensor.get_gyro_data()
        except Exception as e:
            self.get_logger().warn(f"MPU6050 read failed: {e}")
            return

        # ---------- Linear acceleration (m/s^2) ----------
        ax = accel['x'] - self.accel_offsets[0]
        ay = accel['y'] - self.accel_offsets[1]
        az = accel['z'] - self.accel_offsets[2]

        msg.linear_acceleration = Vector3(
            x=ax * G_TO_MS2,
            y=ay * G_TO_MS2,
            z=az * G_TO_MS2
        )
        msg.linear_acceleration_covariance = [-1.0] * 9

        # ---------- Angular velocity (rad/s) ----------
        gx = gyro['x'] - self.gyro_offsets[0]
        gy = gyro['y'] - self.gyro_offsets[1]
        gz = gyro['z'] - self.gyro_offsets[2]

        msg.angular_velocity = Vector3(
            x=math.radians(gx),
            y=math.radians(gy),
            z=math.radians(gz)
        )
        msg.angular_velocity_covariance = [-1.0] * 9

        # ---------- Orientation (not provided) ----------
        msg.orientation = Quaternion(x=0.0, y=0.0, z=0.0, w=0.0)
        msg.orientation_covariance = [-1.0] * 9

        self.publisher_.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ImuPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()




# #!/usr/bin/env python3
# import rclpy
# from rclpy.node import Node
# from sensor_msgs.msg import Imu
# from std_msgs.msg import Header
# from geometry_msgs.msg import Vector3, Quaternion
# import math
# import time

# # Try to import MPU6050 driver
# try:
#     # from tortoisebot.tbot_imu.scripts.mpu6050_node import mpu6050
#     from mpu6050 import mpu6050
# except Exception as e:
#     raise RuntimeError("mpu6050 driver not found. Install with: sudo apt update && sudo apt install -y python3-smbus && pip3 install mpu6050-raspberrypi") from e

# G_TO_MS2 = 9.80665

# class ImuPublisher(Node):
#     def __init__(self,
#                  i2c_address=0x68,
#                  frame_id='imu',
#                  publish_hz=30.0,
#                  accel_offsets=(0.0, 0.0, 0.0),     #
#                  gyro_offsets=(0.0, 0.0, 0.0),      #   
#                  topic_name='/imu'):
#         super().__init__('imu_publisher')

#         self.frame_id = frame_id
#         self.topic_name = topic_name

#         q_size = 10
#         self.publisher_ = self.create_publisher(Imu, self.topic_name, q_size)

#         self.period = 1.0 / float(publish_hz)
#         self.timer = self.create_timer(self.period, self.publish_imu_data)

#         # Initialize sensor
#         self.get_logger().info(f"Initializing MPU6050 at I2C address 0x{i2c_address:02x}")
#         self.sensor = mpu6050(i2c_address)
#         # Simple offsets you can tune after calibration
#         self.accel_offsets = accel_offsets
#         self.gyro_offsets = gyro_offsets

#         self.get_logger().info(f"IMU publisher started: topic={self.topic_name}, rate={publish_hz} Hz, frame_id={self.frame_id}")

#     def publish_imu_data(self):
#         msg = Imu()
#         msg.header = Header()
#         msg.header.stamp = self.get_clock().now().to_msg()
#         msg.header.frame_id = self.frame_id

#         # MPU6050 Python libraries typically expose:
#         #   accel_data = {'x':..., 'y':..., 'z':...}  (units: g in many libs)
#         #   gyro_data  = {'x':..., 'y':..., 'z':...}  (units: deg/s in many libs)
#         # Convert accel -> m/s^2, gyro -> rad/s.
#         try:
#             accel = self.sensor.get_accel_data()   # dict with x,y,z
#             gyro = self.sensor.get_gyro_data()     # dict with x,y,z
#         except Exception as e:
#             self.get_logger().warn(f"Failed to read MPU6050: {e}")
#             return

#         # Linear acceleration (m/s^2)
#         try:
#             ax = float(accel['x']) - float(self.accel_offsets[0])
#             ay = float(accel['y']) - float(self.accel_offsets[1])
#             az = float(accel['z']) - float(self.accel_offsets[2])
#             # assume accel is in g -> convert to m/s^2
#             msg.linear_acceleration = Vector3(
#                 x=ax * G_TO_MS2,
#                 y=ay * G_TO_MS2,
#                 z=az * G_TO_MS2
#             )
#             msg.linear_acceleration_covariance = [-1.0] * 9
#         except Exception as e:
#             self.get_logger().warn(f"Accel type/format issue: {e}")

#         # Angular velocity (rad/s)
#         try:
#             gx = float(gyro['x']) - float(self.gyro_offsets[0])
#             gy = float(gyro['y']) - float(self.gyro_offsets[1])
#             gz = float(gyro['z']) - float(self.gyro_offsets[2])
#             # assume gyro is in degrees/sec -> convert to rad/s
#             msg.angular_velocity = Vector3(
#                 x=math.radians(gx),
#                 y=math.radians(gy),
#                 z=math.radians(gz)
#             )
#             msg.angular_velocity_covariance = [-1.0] * 9
#         except Exception as e:
#             self.get_logger().warn(f"Gyro type/format issue: {e}")

#         # Orientation: MPU6050 Python driver typically doesn't provide fused quaternion.
#         # Leave orientation invalid and tell consumers by setting covariance to -1.
#         msg.orientation = Quaternion(x=0.0, y=0.0, z=0.0, w=0.0)
#         msg.orientation_covariance = [-1.0] * 9

#         self.publisher_.publish(msg)
#         # debug-level logging only
#         self.get_logger().debug("Published IMU message")

# def main(args=None):
#     rclpy.init(args=args)
#     node = ImuPublisher(
#         i2c_address=0x68,
#         frame_id='imu',
#         publish_hz=30.0,
#         accel_offsets=(0.0, 0.0, 0.0),
#         gyro_offsets=(0.0, 0.0, 0.0),
#         topic_name='/imu'
#     )

#     try:
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         node.get_logger().info("IMU publisher stopped cleanly")
#     except Exception as e:
#         node.get_logger().error(f"IMU publisher exception: {e}")
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()

# if __name__ == '__main__':
#     main()
