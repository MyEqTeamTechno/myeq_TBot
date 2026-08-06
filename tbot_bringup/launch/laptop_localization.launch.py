import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_nav = get_package_share_directory('tbot_nav')
    pkg_desc = get_package_share_directory('tbot_description')
    pkg_bringup = get_package_share_directory('tbot_bringup')

    # Paths to your saved files

    # map_file_path = os.path.join(pkg_bringup, 'maps', 'mye_office_cdr.yaml')
    map_file_path = os.path.join(pkg_bringup, 'maps', 'my_play_map.yaml')


    nav_params = os.path.join(pkg_nav, 'config', 'nav2_params_robot.yaml')
    # nav_params = os.path.join(pkg_nav, 'config', 'playground.yaml')

    rviz_config = os.path.join(pkg_desc, 'rviz', 'localisation_config.rviz')
    # rviz_config = os.path.join(pkg_desc, 'rviz', 'myeq_office.rviz')
    # rviz_config = os.path.join(pkg_desc, 'rviz', 'mapping_rviz_config_2.rviz')


    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=map_file_path),

        # # 1. Map Server: Loads the map
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            parameters=[{'yaml_filename': LaunchConfiguration('map')},    # map:= run time argument name 
                        {'use_sim_time': False}]
        ),

        # # 2. AMCL: Localization 
        # Node(
        #     package='nav2_amcl',
        #     executable='amcl',
        #     name='amcl',
        #     parameters=[nav_params, {'use_sim_time': False}]
        # ),

        # 3. Nav2 Stack: Path Planning and Control
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(pkg_nav, 'launch', 'navigation.launch.py')),
            launch_arguments={'params_file': nav_params, 
                              'use_sim_time': 'False'
                              }.items()
        ),

        # Lifecycle is fully managed by nav2_bringup's internal lifecycle managers:
        #   - lifecycle_manager_localization  (map_server, amcl)
        #   - lifecycle_manager_navigation    (bt_navigator, waypoint_follower, planner, controller, ...)
        # Do NOT add a second lifecycle_manager_navigation here — same node name would conflict.

        # # 5. IMU Filter (Madgwick)    - only for mpu6050 as there is built-in co-processor for data fusion.
        # # This turns your raw /imu into /imu/data with orientation
        # Node(
        #     package='imu_filter_madgwick',
        #     executable='imu_filter_madgwick_node',
        #     name='imu_filter',
        #     parameters=[{
        #         'use_mag': False,
        #         'publish_tf': False,  # EKF will handle TF
        #         'fixed_frame': 'odom'
        #     }],
        #     remappings=[('/imu/data_raw', '/imu')]
        # ),


    ])
