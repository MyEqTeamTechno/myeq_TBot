# Minimum CMake version and project definition
cmake_minimum_required(VERSION 3.5)
if(POLICY CMP0048)
  cmake_policy(SET CMP0048 NEW)
endif()
project(ydlidar_sdk VERSION 1.4.7 LANGUAGES C CXX)
#add_definitions(-std=c++11) # Use C++11
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
include_directories(include)
include_directories(src)

IF (WIN32)
FILE(GLOB SDK_SRC 
  "src/*.cpp"
  "src/*.c"
  "src/*.h"
  "src/impl/windows/*.cpp"
  "src/impl/windows/*.h"
)
  
ELSE()
FILE(GLOB SDK_SRC 
  "src/*.cpp"
  "src/*.c"
  "src/*.h"
  "src/impl/unix/*.cpp"
  "src/impl/unix/*.h"
)

  
ENDIF()

add_subdirectory(samples)

add_library(ydlidar_driver STATIC ${SDK_SRC})
IF (WIN32)
target_link_libraries(ydlidar_driver setupapi Winmm)
ELSE()
target_link_libraries(ydlidar_driver rt pthread)
ENDIF()                    

# Install rules for SDK
install(TARGETS ydlidar_driver EXPORT ydlidar_sdkTargets
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
        RUNTIME DESTINATION bin)
install(DIRECTORY include/ DESTINATION include)

# Export targets for downstream usage
install(EXPORT ydlidar_sdkTargets
        FILE ydlidar_sdkTargets.cmake
        NAMESPACE ydlidar_sdk::
        DESTINATION lib/cmake/ydlidar_sdk)

# Generate and install a basic Config file for find_package
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
  "${CMAKE_CURRENT_BINARY_DIR}/ydlidar_sdkConfigVersion.cmake"
  VERSION ${PROJECT_VERSION}
  COMPATIBILITY AnyNewerVersion
)
configure_package_config_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/cmake/ydlidar_sdkConfig.cmake.in"
  "${CMAKE_CURRENT_BINARY_DIR}/ydlidar_sdkConfig.cmake"
  INSTALL_DESTINATION lib/cmake/ydlidar_sdk
)
install(FILES
  "${CMAKE_CURRENT_BINARY_DIR}/ydlidar_sdkConfig.cmake"
  "${CMAKE_CURRENT_BINARY_DIR}/ydlidar_sdkConfigVersion.cmake"
  DESTINATION lib/cmake/ydlidar_sdk
)
