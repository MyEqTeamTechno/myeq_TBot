from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        # 1. Camera — publishes /image_raw
        # USB UVC webcam (e.g. Zebronics Sharp Pro) — plug and play, no drivers needed
        # Verify device: ls /dev/video* after plugging in
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='camera_node',
            parameters=[{
                'video_device':    '/dev/video0',
                'image_size':      [640, 480],
                'camera_frame_id': 'camera_link',
                'output_encoding': 'bgr8',
                'time_per_frame':  [1, 15],   # 15 fps (numerator/denominator)
            }],
            output='screen',
        ),

        # 2. HSV object tracker — /image_raw → /tracked_object + /tracker_debug
        Node(
            package='tbot_vision',
            executable='tracker_node.py',
            name='tracker_node',
            parameters=[{
                'hue_low':  35,    # tune with: ros2 param set /tracker_node hue_low <val>
                'hue_high': 85,
                'sat_low':  60,
                'min_area': 500,
                'debug':    True,          # draws circle around detected object
                'process_every_n': 1,      # process every frame at camera fps
            }],
            output='screen',
        ),

        # 3. Drive controller — merges gesture + tracking → /cmd_vel
        Node(
            package='tbot_vision',
            executable='drive_controller.py',
            name='drive_controller',
            parameters=[{
                'linear_speed':     0.25,
                'angular_gain':     1.5,
                'dead_zone':        0.07,
                'gesture_timeout':  2.0,
                'min_track_radius': 20.0,
                'approach_radius':  80.0,
            }],
            output='screen',
        ),

        # 4. Motor firmware — /cmd_vel → wheels
        Node(
            package='tbot_firmware',
            executable='four_wheeled_diff.py',
            name='differential_drive_publisher',
            output='screen',
        ),
    ])
