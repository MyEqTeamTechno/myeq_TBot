import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from launch_ros.descriptions import ParameterValue

"""

This launch file will only run on TortoiseBot robot

"""

def generate_launch_description():
    pkg_description = get_package_share_directory('tbot_description')
    pkg_ydlidar = get_package_share_directory('ydlidar_ros2_driver')
    pkg_slam = get_package_share_directory('tbot_slam')

    model_path = os.path.join(pkg_description, 'models/urdf/tortoisebot_simple.xacro')
    ekf_config_path = os.path.join(pkg_slam, 'config', 'ekf.yaml')
    # pkg_mpu_driver = get_package_share_directory('mpu6050driver')

    return LaunchDescription([
        SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1'),

        # 1. Robot State Publisher 
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': ParameterValue(Command(['xacro ', model_path]), value_type=str)}]
        ),

        # 2. Differential Drive 
        Node(
            package='tbot_firmware',
            executable='four_wheeled_diff.py',
            # executable='close_loop_st.py', # In tb_2 
            # executable='servo_differential',  # For servo motors
            # executable='differential.py',    
            name='differential_drive_publisher',
        ),

        # bno055 IMU node
        Node(
            package='tbot_imu',
            executable='imu_node.py',   # or create an ROS2 executable entry point
            name='imu_publisher',
            output='screen',
            parameters=[{'use_sim_time': False}],
            remappings=[('/imu/data', '/imu')]
        ),

        # # mpu6050 IMU node - 
        # Node(
        #     package='tbot_imu',
        #     executable='mpu6050_node.py',   # or create an ROS2 executable entry point
        #     name='imu_publisher',
        #     namespace='',
        #     output='screen',
        #     parameters=[{'i2c_address': 0x68, 'frame_id': 'imu', 'publish_hz': 20.0}],
        #     # condition=IfCondition(PythonExpression(['not ', use_sim_time]))
        # ),


        # 3. YDLiDAR Driver
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(pkg_ydlidar, 'launch', 'ydlidar_launch.py')),
            launch_arguments={'use_sim_time': 'False'}.items()
        ),

        # 4. Robot Localization / EKF 
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[ekf_config_path, {'use_sim_time': False}]
        ),
 
        # # 5. mpu6050 driver launch file  
        # IncludeLaunchDescription(
        #     PythonLaunchDescriptionSource(
        #         os.path.join(pkg_mpu_driver, 'launch', 'mpu6050driver_launch.py')
        #     )
        # ),

        ##### Need to remove static_tf
        # 6. Fixed Static TF (Connects base_link to the laser)
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='statictf_baselink_to_laser',
            arguments=['0', '0', '0.02', '0', '0', '0', '1', 'base_link', 'laser_frame'],
        ),

        # 7. Fixed Static TF (Connects base_link to the laser)
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='statictf_baselink_to_laser1',
            arguments=['0', '0', '0.02', '0', '0', '0', '1', 'base_link', 'lidar_1'],
        ),

        # 8. Joint State Publisher (to mimic encoders)
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            parameters=[{'use_sim_time': False}]
        ),

    ])