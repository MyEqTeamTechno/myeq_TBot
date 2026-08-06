cmake_minimum_required(VERSION 3.8)
project(tbot_firmware)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)

find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)

  ament_lint_auto_find_test_dependencies()
endif()

# Install Python modules
ament_python_install_package(${PROJECT_NAME})

# Install Python executables
install(PROGRAMS
  scripts/four_wheeled_diff.py # for servo motors
  DESTINATION lib/${PROJECT_NAME}
)
#Required for dependencies and other folder
install(
  DIRECTORY tbot_firmware/scservo_sdk
  DESTINATION share/${PROJECT_NAME}
)
  
ament_package()
