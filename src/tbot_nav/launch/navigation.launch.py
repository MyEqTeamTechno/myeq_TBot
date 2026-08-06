import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    nav2_launch_dir = os.path.join(get_package_share_directory('nav2_bringup'), 'launch')

    default_map = os.path.join(
        get_package_share_directory('tbot_bringup'),
        'maps',
        'my_play_map.yaml')

    default_params = os.path.join(
        get_package_share_directory('tbot_nav'),
        'config',
        'nav2_params_robot.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Full path to map yaml file'),

        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock'),

        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Full path to nav2 params yaml file'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([nav2_launch_dir, '/bringup_launch.py']),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'params_file': LaunchConfiguration('params_file'),
                'use_collision_monitor': 'False',
            }.items(),
        ),

        Node(
            package='topic_tools',
            executable='relay',
            name='cmd_vel_relay',
            arguments=['/cmd_vel_smoothed', '/cmd_vel'],
            output='screen',
        ),
    ])
