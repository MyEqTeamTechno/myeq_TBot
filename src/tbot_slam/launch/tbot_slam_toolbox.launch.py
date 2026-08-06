import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Get package directories
    pkg_slam_toolbox = get_package_share_directory('tbot_slam')
    pkg_gazebo = get_package_share_directory('tbot_gazebo')

    # Default path to the slam toolbox configuration file
    default_config_path = os.path.join(pkg_slam_toolbox, 'config', 'mapper_params_online_async_.yaml')

    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')
    world = LaunchConfiguration('world')

    # Default world file path
    default_world_path = os.path.join(
        pkg_gazebo, 'worlds', 'campus_indoor.world'
    )

    # Declare launch arguments
    declare_use_sim_time_argument = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation/Gazebo clock if true'
    )

    declare_params_file_argument = DeclareLaunchArgument(
        'params_file',
        default_value=default_config_path,
        description='Full path to the ROS2 parameters file to use for the slam_toolbox node'
    )

    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=default_world_path,
        description='Full path to Gazebo world file to load'
    )

    # Include the Gazebo simulation launch file
    launch_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo, 'launch', 'launch_sim.launch.py')
        ),
        launch_arguments={'world': world}.items()
    )

    # Run the slam_toolbox node
    start_slam_toolbox_node = Node(
        parameters=[
            params_file,
            {'use_sim_time': use_sim_time}
        ],
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen'
    )

    return LaunchDescription([
        declare_use_sim_time_argument,
        declare_params_file_argument,
        declare_world_cmd,
        launch_sim,
        start_slam_toolbox_node
    ])
