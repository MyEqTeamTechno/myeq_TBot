# #!/usr/bin/env python3
# import rclpy
# import cv2
# import numpy as np
# from rclpy.node import Node
# from cv_bridge import CvBridge
# from sensor_msgs.msg import Image
# from geometry_msgs.msg import Point


# class TrackerNode(Node):
#     def __init__(self):
#         super().__init__('tracker_node')
#         self.bridge = CvBridge()

#         self.declare_parameter('hue_low',  35)
#         self.declare_parameter('hue_high', 85)
#         self.declare_parameter('sat_low',  60)
#         self.declare_parameter('min_area', 500)
#         self.declare_parameter('debug',    True)

#         self.sub = self.create_subscription(
#             Image, '/image_raw', self.cb, 10)
#         self.pub = self.create_publisher(Point, '/tracked_object', 10)
#         self.dbg = self.create_publisher(Image, '/tracker_debug', 10)

#         self._frame_count = 0
#         self.declare_parameter('debug_every_n',   6)  # publish debug at ~5fps (30/6)
#         self.declare_parameter('process_every_n', 3)  # process every 3rd frame → ~10fps tracking
#         self._last_pt = Point()
#         self.get_logger().info('tracker_node ready — waiting for /image_raw')

#     def cb(self, msg):
#         self._frame_count += 1

#         # Skip frames for tracking — reduces CPU by ~60%
#         if self._frame_count % self.get_parameter('process_every_n').value != 0:
#             self.pub.publish(self._last_pt)
#             return

#         frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
#         h, w  = frame.shape[:2]

#         hl  = self.get_parameter('hue_low').value
#         hh  = self.get_parameter('hue_high').value
#         sl  = self.get_parameter('sat_low').value
#         min_area = self.get_parameter('min_area').value
#         debug    = self.get_parameter('debug').value

#         hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
#         mask = cv2.inRange(
#             hsv,
#             np.array([hl, sl,  50], dtype=np.uint8),
#             np.array([hh, 255, 255], dtype=np.uint8),
#         )
#         mask = cv2.erode(mask,  None, iterations=2)
#         mask = cv2.dilate(mask, None, iterations=2)

#         cnts, _ = cv2.findContours(
#             mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

#         pt = Point()   # x=0, y=0, z=0 → "nothing detected"
#         if cnts:
#             c = max(cnts, key=cv2.contourArea)
#             if cv2.contourArea(c) > min_area:
#                 (cx, cy), r = cv2.minEnclosingCircle(c)
#                 pt.x = cx / w - 0.5   # -0.5 (far left) … +0.5 (far right)
#                 pt.y = cy / h - 0.5
#                 pt.z = r               # radius in px — proxy for distance
#                 if debug:
#                     cv2.circle(frame, (int(cx), int(cy)), int(r),
#                                (0, 255, 0), 2)
#                     cv2.circle(frame, (int(cx), int(cy)), 4,
#                                (0, 0, 255), -1)

#         self._last_pt = pt
#         self.pub.publish(pt)

#         n = self.get_parameter('debug_every_n').value
#         if debug and (self._frame_count % n == 0):
#             cv2.putText(
#                 frame,
#                 f'x:{pt.x:.2f}  r:{pt.z:.0f}',
#                 (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
#             )
#             self.dbg.publish(self.bridge.cv2_to_imgmsg(frame, 'bgr8'))


# def main(args=None):
#     rclpy.init(args=args)
#     rclpy.spin(TrackerNode())
#     rclpy.shutdown()


# if __name__ == '__main__':
#     main()


#!/usr/bin/env python3
import rclpy, cv2, numpy as np
from rclpy.node import Node
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
import threading


class TrackerNode(Node):
    def __init__(self):
        super().__init__('tracker_node')
        self.bridge = CvBridge()

        self.declare_parameter('hue_low',        35)
        self.declare_parameter('hue_high',        85)
        self.declare_parameter('sat_low',         60)
        self.declare_parameter('min_area',       500)
        self.declare_parameter('debug',         True)
        self.declare_parameter('debug_every_n',    6)
        self.declare_parameter('process_every_n',  3)
        self.declare_parameter('scale',          0.5)  # ← NEW: resize factor

        # Cache params — avoids ROS2 lookup overhead on every frame
        self._p = {}
        self._cache_params()

        self.sub = self.create_subscription(
            Image, '/image_raw', self.cb, 10)
        self.pub = self.create_publisher(Point, '/tracked_object', 10)
        self.dbg = self.create_publisher(Image, '/tracker_debug', 10)

        # Param re-cache timer (every 2s) — cheap vs per-frame lookup
        self.create_timer(2.0, self._cache_params)

        self._frame_count = 0
        self._last_pt = Point()

        # Offload debug publishing to a background thread
        self._debug_queue = None
        self._debug_lock  = threading.Lock()
        self._debug_thread = threading.Thread(
            target=self._debug_worker, daemon=True)
        self._debug_thread.start()

        self.get_logger().info('tracker_node ready')

    def _cache_params(self):
        self._p = {
            'hl':       self.get_parameter('hue_low').value,
            'hh':       self.get_parameter('hue_high').value,
            'sl':       self.get_parameter('sat_low').value,
            'min_area': self.get_parameter('min_area').value,
            'debug':    self.get_parameter('debug').value,
            'dbg_n':    self.get_parameter('debug_every_n').value,
            'proc_n':   self.get_parameter('process_every_n').value,
            'scale':    self.get_parameter('scale').value,
        }

    def _debug_worker(self):
        """Publishes debug frames off the main callback thread."""
        while True:
            with self._debug_lock:
                item = self._debug_queue
                self._debug_queue = None
            if item is not None:
                frame, pt = item
                cv2.putText(frame, f'x:{pt.x:.2f}  r:{pt.z:.0f}',
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 255, 0), 2)
                self.dbg.publish(
                    self.bridge.cv2_to_imgmsg(frame, 'bgr8'))
            else:
                # ~30fps budget for debug thread
                import time; time.sleep(0.033)

    def cb(self, msg):
        self._frame_count += 1
        p = self._p  # local ref, avoids repeated dict lookups

        if self._frame_count % p['proc_n'] != 0:
            self.pub.publish(self._last_pt)
            return

        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        h, w  = frame.shape[:2]

        # ── Resize early — all heavy ops run on the smaller image ──
        s = p['scale']
        small = cv2.resize(frame, (0, 0), fx=s, fy=s,
                           interpolation=cv2.INTER_LINEAR)
        sh, sw = small.shape[:2]

        hsv  = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array([p['hl'], p['sl'],  50], dtype=np.uint8),
            np.array([p['hh'],      255, 255], dtype=np.uint8),
        )

        # Smaller kernel on downscaled mask — same effect, less work
        k    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)  # erode+dilate in one call
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        cnts, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        pt = Point()
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            area = cv2.contourArea(c)
            if area > p['min_area'] * s * s:   # scale area threshold too
                (cx, cy), r = cv2.minEnclosingCircle(c)
                # Map back to original-resolution coordinates
                pt.x = (cx / sw) - 0.5
                pt.y = (cy / sh) - 0.5
                pt.z = r / s             # radius in original-px units

                if p['debug']:
                    cv2.circle(small, (int(cx), int(cy)), int(r),
                               (0, 255, 0), 2)
                    cv2.circle(small, (int(cx), int(cy)), 4,
                               (0, 0, 255), -1)

        self._last_pt = pt
        self.pub.publish(pt)

        # Queue debug frame — never blocks the tracking path
        if p['debug'] and (self._frame_count % p['dbg_n'] == 0):
            with self._debug_lock:
                self._debug_queue = (small.copy(), pt)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(TrackerNode())
    rclpy.shutdown()


if __name__ == '__main__':
    main()