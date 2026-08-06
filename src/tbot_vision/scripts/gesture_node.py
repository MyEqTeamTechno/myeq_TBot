"""
This file will run on remote pc
"""
#!/usr/bin/env python3
import os
import time
import cv2
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe import Image as MpImage, ImageFormat

TIPS = [8, 12, 16, 20]
PIPS = [6, 10, 14, 18]

GESTURE_MAP = {
    0: 'STOP',
    1: 'FORWARD',
    2: 'LEFT',
    3: 'RIGHT',
    4: 'BACKWARD',
}

_DEFAULT_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'hand_landmarker.task')
"""
wget -O /home/gjrdhrl/tortoisebot_ws/src/tortoisebot/tbot_vision/scripts/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
"""

class GestureNode(Node):
    def __init__(self):
        super().__init__('gesture_node')

        self.declare_parameter('camera_index', 0)
        self.declare_parameter('show_window',  True)
        self.declare_parameter('model_path',   _DEFAULT_MODEL)

        model_path = self.get_parameter('model_path').value
        if not os.path.exists(model_path):
            self.get_logger().error(
                f'Hand landmark model not found: {model_path}\n'
                'Download it with:\n'
                '  wget -O hand_landmarker.task https://storage.googleapis.com/'
                'mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
            )
            raise FileNotFoundError(model_path)

        options = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.75,
            min_hand_presence_confidence=0.65,
            min_tracking_confidence=0.65,
        )
        self._detector = mp_vision.HandLandmarker.create_from_options(options)
        self._start_ms = int(time.time() * 1000)

        cam_idx = self.get_parameter('camera_index').value
        self._cap = cv2.VideoCapture(cam_idx)
        if not self._cap.isOpened():
            self.get_logger().error(f'Cannot open webcam index {cam_idx}')

        self._pub = self.create_publisher(String, '/gesture_cmd', 10)
        self.create_timer(0.05, self._loop)   # 20 Hz

        self.get_logger().info('gesture_node ready')

    # ------------------------------------------------------------------
    def _count_fingers(self, landmarks, handedness: str) -> int:
        fingers_up = sum(landmarks[t].y < landmarks[p].y
                         for t, p in zip(TIPS, PIPS))
        if handedness == 'Right':
            thumb_up = 1 if landmarks[4].x < landmarks[3].x else 0
        else:
            thumb_up = 1 if landmarks[4].x > landmarks[3].x else 0
        return fingers_up + thumb_up

    # ------------------------------------------------------------------
    def _loop(self):
        show = self.get_parameter('show_window').value

        ok, frame = self._cap.read()
        if not ok:
            return

        frame    = cv2.flip(frame, 1)
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ts_ms    = int(time.time() * 1000) - self._start_ms
        mp_img   = MpImage(image_format=ImageFormat.SRGB, data=rgb)
        result   = self._detector.detect_for_video(mp_img, ts_ms)

        gesture = 'NONE'

        if result.hand_landmarks and result.handedness:
            landmarks  = result.hand_landmarks[0]
            handedness = result.handedness[0][0].display_name
            count      = self._count_fingers(landmarks, handedness)
            gesture    = GESTURE_MAP.get(count, 'NONE')

            if show:
                h, w = frame.shape[:2]
                for lm in landmarks:
                    cv2.circle(frame,
                               (int(lm.x * w), int(lm.y * h)),
                               4, (0, 255, 0), -1)

        if show:
            colour = (0, 200, 0) if gesture != 'NONE' else (100, 100, 100)
            cv2.putText(frame, gesture, (20, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.6, colour, 3)
            cv2.imshow('Gesture Control', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self._cap.release()
                cv2.destroyAllWindows()
                rclpy.shutdown()

        msg      = String()
        msg.data = gesture
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(GestureNode())
    rclpy.shutdown()


if __name__ == '__main__':
    main()
