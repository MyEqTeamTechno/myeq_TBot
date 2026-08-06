"""
TortoiseBot Cartographer Launch File 

Purpose:
--------
This launch file is responsible for bringing up Cartographer SLAM for TortoiseBot.
It supports two operational modes:
1. Exploration Mode   -> Active SLAM (mapping)
2. Localization Mode  -> Localization against an existing map (conceptually)

The mode is selected using the `exploration` launch argument.

Why this file exists:
---------------------
Cartographer requires:
- A Lua configuration file
- Runtime parameters (resolution, publish period)
- Proper ROS time handling (sim vs real robot)

This launch file centralizes those concerns so SLAM behavior
can be changed without touching source code.

"""

import os
import launch
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration,PythonExpression
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch_ros.actions import Node
from launch.conditions import IfCondition

def generate_launch_description():
  """
    Generate the ROS 2 launch description for Cartographer SLAM.

    Purpose:
    --------
    - Locate configuration files inside the tbot_slam package
    - Declare all runtime-tunable parameters as launch arguments
    - Conditionally start Cartographer in exploration or localization mode
    - Optionally publish an occupancy grid when mapping

    Arguments (via LaunchConfiguration):
    -----------------------------------
    use_sim_time (bool):
        True = To use simulated clock (Gazebo) 
        False = When real robot is used  

    exploration (bool):
        True = Controls whether SLAM is running in exploration (mapping) mode.
        False = the intention is localization-only (though same node is used).

    resolution (float):
        Resolution of the occupancy grid in meters/cell.

    publish_period_sec (float):
        How often the occupancy grid is published (in seconds).

    Returns:
    --------
    LaunchDescription:
        A complete launch description that ROS 2 can execute.
  """

  # Get absolute path to the tbot_slam package.
  prefix_address = get_package_share_directory('tbot_slam') 

  # Configuration directory containing Cartographer Lua files.
  config_directory = os.path.join(prefix_address, 'config')

  # Lua file defines Cartographer behavior.
  # Use diff lua file for diff behavior - exporation and locatization
  mapping_config = 'mapping.lua'
  # localization_config = 'localization.lua'

  # Runtime-tunable parameters exposed as launch arguments.
  res = LaunchConfiguration('resolution', default='0.05')
  publish_period = LaunchConfiguration('publish_period_sec', default='1.0')
  use_sim_time=LaunchConfiguration('use_sim_time')
  exploration=LaunchConfiguration('exploration')  # slam in exploration = mapping MODE


  return LaunchDescription([

    # Ensures logs are flushed immediately. Critical for debugging crashes or startup failures.
    SetEnvironmentVariable(
      'RCUTILS_LOGGING_BUFFERED_STREAM', '1'
    ),

    # Declare simulation toggle argument (if TRUE -> /clock topic is used)
    launch.actions.DeclareLaunchArgument(
      name='use_sim_time', 
      default_value='False',
      description='Flag to enable use_sim_time'
    ),

    # Controls SLAM mode.
    # True  -> exploration (mapping)
    # False -> localization (conceptually, requires diff lua file)
    launch.actions.DeclareLaunchArgument(
      name='exploration', 
      default_value='True',
      description='Enable exploration (SLAM mapping) mode'
    ),

    # Grid resolution directly affects map quality and CPU usage.
    # Smaller value = better detail, higher computation cost.
    DeclareLaunchArgument(
      'resolution',
      default_value=res,
      description='configure the Occupancy grid resolution (meters per cell)'
    ),

    # Publishing too frequently wastes bandwidth.
    # Publishing too slowly causes stale maps.
    DeclareLaunchArgument(
      'publish_period_sec',
      default_value=publish_period,
      description='Occupancy grid publish period in seconds'
    ),

    # Directory containing Cartographer Lua configs.
    DeclareLaunchArgument(
      'configuration_directory',
      default_value=config_directory,
      description='Path to Cartographer configuration directory'
    ),

    # Lua config file name for mapping.
    DeclareLaunchArgument(
      'mapping_configuration_basename',
      default_value=mapping_config, 
      description='Cartographer mapping configuration file'
    ),

    # # Lua config file name for localization.
    # DeclareLaunchArgument(
    #   'localization_configuration_basename',
    #   default_value=localization_config, 
    #   description='Cartographer localization configuration file'
    # ),

    # ---------------- CARTOGRAPHER NODE (EXPLORATION MODE) ----------------
    Node(
      package='cartographer_ros',
      executable='cartographer_node',
      name='as21_cartographer_node',

      # Node runs ONLY if exploration == True
      condition= IfCondition(exploration),

      # Arguments passed directly to Cartographer.
      # These define which Lua file is loaded at runtime.
      arguments=[
        '-configuration_directory', config_directory,
        '-configuration_basename', mapping_config
      ],
      parameters= [{'use_sim_time':use_sim_time}],
      output='screen'
    ),

    # ---------------- CARTOGRAPHER NODE (NON-EXPLORATION MODE) ----------------
    # Node(
    #   package='cartographer_ros',
    #   executable='cartographer_node',
    #   name='as21_cartographer_node',

        # Runs when exploration == False
    #   condition=IfCondition(PythonExpression(['not ', exploration])
    #   ),
    #   arguments=[
    #     '-configuration_directory', config_directory,
    #     '-configuration_basename', localization_config
    #   ],
    #   parameters= [{'use_sim_time':use_sim_time}],
    #   output='screen'
    # ),

    #---------------- OCCUPANCY GRID NODE ----------------
    # This node converts Cartographer submaps into a 2D occupancy grid.
    Node(
      package='cartographer_ros',
      condition= IfCondition(exploration),
      executable='cartographer_occupancy_grid_node',
      name='cartographer_occupancy_grid_node',
      arguments=[
        '-resolution', res,
        '-publish_period_sec', publish_period
      ]
    ),   
])
