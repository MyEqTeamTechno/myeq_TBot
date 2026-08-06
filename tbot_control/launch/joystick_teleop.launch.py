"""
Joystick Teleop Launch File for TortoiseBot
============================================
Launches two nodes:
  1. joy_node        — reads the USB joystick and publishes sensor_msgs/Joy
  2. teleop_node     — converts Joy messages to geometry_msgs/Twist on /cmd_vel

Usage (standalone, without full bringup):
  ros2 launch tortoisebot_control joystick_teleop.launch.py

Usage (alongside autobringup on another terminal):
  ros2 launch tortoisebot_control joystick_teleop.launch.py
  ros2 run tbot_firmware four_wheeled_diff.py


Launch Arguments:
  joy_dev    — joystick device path (default: /dev/input/js0)
  config     — path to teleop_twist_joy YAML config
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    config_file = os.path.join(
        get_package_share_directory('tortoisebot_control'),
        'config',
        'joystick_controller.yaml'
    )

    joy_dev = LaunchConfiguration('joy_dev')
    config   = LaunchConfiguration('config')

    return LaunchDescription([

        DeclareLaunchArgument(
            'joy_dev',
            default_value='/dev/input/js0',
            description='Joystick device path'
        ),

        DeclareLaunchArgument(
            'config',
            default_value=config_file,
            description='Path to teleop_twist_joy YAML config'
        ),

        # joy_node: reads raw joystick input
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{
                'device_name': '',        # use device_id + dev below
                'dev': joy_dev,
                'deadzone': 0.05,         # ignore small stick drift
                'autorepeat_rate': 20.0,  # Hz — republish even if no change
            }],
            output='screen',
        ),

        # teleop_node: converts Joy → Twist on /cmd_vel
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_twist_joy_node',
            parameters=[config],
            remappings=[
                ('cmd_vel', '/cmd_vel'),   # matches TortoiseBot firmware topic
            ],
            output='screen',
        ),
    ])
