#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point
from std_msgs.msg import String


class DriveController(Node):
    def __init__(self):
        super().__init__('drive_controller')

        self.declare_parameter('linear_speed',    0.25)
        self.declare_parameter('angular_gain',    1.5)
        self.declare_parameter('dead_zone',       0.07)
        self.declare_parameter('gesture_timeout', 2.0)   # seconds
        # Minimum radius (px) before the robot starts reacting
        self.declare_parameter('min_track_radius', 20.0)
        # Robot approaches until radius reaches this value
        self.declare_parameter('approach_radius',  80.0)

        self._last_gesture      = 'NONE'
        self._last_gesture_time = 0.0
        self._tracked           = Point()

        self.create_subscription(Point,  '/tracked_object', self._track_cb,   10)
        self.create_subscription(String, '/gesture_cmd',    self._gesture_cb, 10)
        self._cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.create_timer(0.05, self._loop)   # 20 Hz control loop
        self.get_logger().info('drive_controller ready')

    # ------------------------------------------------------------------
    def _gesture_cb(self, msg: String):
        if msg.data not in ('NONE', ''):
            self._last_gesture      = msg.data
            self._last_gesture_time = self.get_clock().now().nanoseconds * 1e-9

    def _track_cb(self, msg: Point):
        self._tracked = msg

    # ------------------------------------------------------------------
    def _loop(self):
        lin    = self.get_parameter('linear_speed').value
        gain   = self.get_parameter('angular_gain').value
        dz     = self.get_parameter('dead_zone').value
        t_out  = self.get_parameter('gesture_timeout').value
        min_r  = self.get_parameter('min_track_radius').value
        app_r  = self.get_parameter('approach_radius').value

        now     = self.get_clock().now().nanoseconds * 1e-9
        gesture_active = (now - self._last_gesture_time) < t_out

        cmd = Twist()

        if gesture_active:
            g = self._last_gesture
            if   g == 'FORWARD':  cmd.linear.x  =  lin
            elif g == 'BACKWARD': cmd.linear.x  = -lin
            elif g == 'LEFT':     cmd.angular.z =  lin
            elif g == 'RIGHT':    cmd.angular.z = -lin
            # STOP → cmd is zero by default
        else:
            # Tracking mode — steer toward the detected object
            err = self._tracked.x   # -0.5 … +0.5
            r   = self._tracked.z   # radius in px

            if r > min_r:
                if abs(err) > dz:
                    cmd.angular.z = -gain * err
                if r < app_r:
                    cmd.linear.x = lin * 0.5

        self._cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(DriveController())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
