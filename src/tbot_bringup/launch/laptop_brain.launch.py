import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

"""
This launch file is used for 'MAPPING' and will run on laptop (remote machine).
Launches:
    1. SLAM via Cartographer (from tbot_slam)
    2. RViz2 for visualisation
"""


def generate_launch_description():

    pkg_slam = get_package_share_directory('tbot_slam')
    pkg_desc = get_package_share_directory('tbot_description')

    rviz_config = os.path.join(pkg_desc, 'rviz', 'myeq_office.rviz')

    return LaunchDescription([

        # ── Launch arguments ──────────────────────────────────────────────────
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            description='Use simulation clock if True'
        ),

        DeclareLaunchArgument(
            'exploration',
            default_value='True',
            description='Enable autonomous exploration mode'
        ),

        # ── 1. SLAM (Cartographer) ────────────────────────────────────────────
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_slam, 'launch', 'cartographer.launch.py')
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'exploration':  LaunchConfiguration('exploration'),
            }.items()
        ),


    ])


# import os
# from launch import LaunchDescription
# from launch_ros.actions import Node
# from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
# from launch.substitutions import LaunchConfiguration
# from launch.launch_description_sources import PythonLaunchDescriptionSource
# from ament_index_python.packages import get_package_share_directory
# """

# This launch file used for 'MAPPING' and will run on laptop (remote machine)

# """
# def generate_launch_description():
#     pkg_nav = get_package_share_directory('tbot_nav')
#     pkg_slam = get_package_share_directory('tbot_slam')
#     pkg_desc = get_package_share_directory('tbot_description')

#     # rviz_config = os.path.join(pkg_desc, 'rviz/tortoisebot_sensor_display.rviz')
#     rviz_config = os.path.join(pkg_desc, 'rviz/myeq_office.rviz')

#     nav_params = os.path.join(pkg_nav, 'config', 'nav2_params_robot.yaml')

#     return LaunchDescription([
#         DeclareLaunchArgument('exploration', default_value='True'),

#         # 1. SLAM (Cartographer) - 
#         IncludeLaunchDescription(
#             PythonLaunchDescriptionSource(os.path.join(pkg_slam, 'launch', 'cartographer.launch.py')),
#             launch_arguments={'use_sim_time': 'False', 'exploration': LaunchConfiguration('exploration')}.items()
#         ),

#         # 2. Navigation2 Stack
#         IncludeLaunchDescription(
#             PythonLaunchDescriptionSource(os.path.join(pkg_nav, 'launch', 'navigation.launch.py')),
#             launch_arguments={
#                 'params_file': nav_params, 
#                 'use_sim_time': 'False', 
#                 # 'slam': 'True',   
#                 }.items()
#         ),

#         # 3. RViz2 
#         Node(
##             package='rviz2',
##             executable='rviz2',
##             arguments=['-d', rviz_config],
##             parameters=[{'use_sim_time': False}]
##         ),
#        
##     ])  