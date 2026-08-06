/*
 *  YDLIDAR SYSTEM
 *  YDLIDAR ROS 2 Node
 *
 *  Copyright 2017 - 2020 EAI TEAM
 *  http://www.eaibot.com
 *
 */

#ifdef _MSC_VER
#ifndef _USE_MATH_DEFINES
#define _USE_MATH_DEFINES
#endif
#endif

#include "CYdLidar.h"
#include <math.h>
#include <chrono>
#include <iostream>
#include <memory>

#include "rclcpp/clock.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp/time_source.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "std_srvs/srv/empty.hpp"
#include <vector>
#include <iostream>
#include <string>
#include <signal.h>

#define ROS2Verision "1.0.1"


int main(int argc, char *argv[]) {
  rclcpp::init(argc, argv);

  auto node = rclcpp::Node::make_shared("ydlidar_ros2_driver_node");

  RCLCPP_INFO(node->get_logger(), "[YDLIDAR INFO] Current ROS Driver Version: %s\n", ((std::string)ROS2Verision).c_str());

  CYdLidar laser;
  std::string port = node->declare_parameter<std::string>("port", "/dev/ydlidar");
  laser.setSerialPort(port);

  std::string ignore_array_str = node->declare_parameter<std::string>("ignore_array", "");
  std::vector<float> ignore_array;
  // Parse comma-separated ignore_array_str to vector<float>
  if (!ignore_array_str.empty()) {
    size_t start = 0, end = 0;
    while ((end = ignore_array_str.find(',', start)) != std::string::npos) {
      ignore_array.push_back(std::stof(ignore_array_str.substr(start, end - start)));
      start = end + 1;
    }
    ignore_array.push_back(std::stof(ignore_array_str.substr(start)));
  }
  laser.setIgnoreArray(ignore_array);

  std::string frame_id = node->declare_parameter<std::string>("frame_id", "laser_frame");

  //////////////////////int property/////////////////
  /// lidar baudrate
  int baudrate = node->declare_parameter<int>("baudrate", 230400);
  laser.setSerialBaudrate(baudrate);
  /// tof lidar
  int lidar_type = node->declare_parameter<int>("lidar_type", TYPE_TRIANGLE);
  laser.setLidarType(lidar_type);
  /// device type
  // int device_type = node->declare_parameter<int>("device_type", YDLIDAR_TYPE_SERIAL);
  // laser.setDeviceType(device_type); // Not in SDK
  /// sample rate
  int sample_rate = node->declare_parameter<int>("sample_rate", 9);
  laser.setSampleRate(sample_rate);
  /// abnormal count
  int abnormal_check_count = node->declare_parameter<int>("abnormal_check_count", 4);
  laser.setAbnormalCheckCount(abnormal_check_count);

  /// Intenstiy bit count
  // Intensity bit not supported in SDK, skip
     
  //////////////////////bool property/////////////////
  /// fixed angle resolution
  bool fixed_resolution = node->declare_parameter<bool>("fixed_resolution", false);
  laser.setFixedResolution(fixed_resolution);
  /// rotate 180
  bool reversion = node->declare_parameter<bool>("reversion", true);
  laser.setReversion(reversion);
  /// Counterclockwise
  bool inverted = node->declare_parameter<bool>("inverted", true);
  laser.setInverted(inverted);
  bool auto_reconnect = node->declare_parameter<bool>("auto_reconnect", true);
  laser.setAutoReconnect(auto_reconnect);
  /// one-way communication
  bool is_single_channel = node->declare_parameter<bool>("isSingleChannel", false);
  laser.setSingleChannel(is_single_channel);
  /// intensity
  // bool intensity = node->declare_parameter<bool>("intensity", false);
  // laser.setIntensity(intensity); // Not in SDK
  /// Motor DTR
  // bool support_motor_dtr = node->declare_parameter<bool>("support_motor_dtr", false);
  // laser.setSupportMotorDtrCtrl(support_motor_dtr); // Not in SDK
  // bool debug = node->declare_parameter<bool>("debug", false);
  // laser.setEnableDebug(debug); // Not in SDK

  //////////////////////float property/////////////////
  /// unit: °
  float angle_max = node->declare_parameter<double>("angle_max", 180.0);
  laser.setMaxAngle(angle_max);
  float angle_min = node->declare_parameter<double>("angle_min", -180.0);
  laser.setMinAngle(angle_min);
  float range_max = node->declare_parameter<double>("range_max", 64.0);
  laser.setMaxRange(range_max);
  float range_min = node->declare_parameter<double>("range_min", 0.1);
  laser.setMinRange(range_min);
  float frequency = node->declare_parameter<double>("frequency", 10.0);
  laser.setScanFrequency(frequency);

  bool invalid_range_is_inf = node->declare_parameter<bool>("invalid_range_is_inf", false);

  //初始化
  bool ret = laser.initialize();
  if (ret) 
  {
    //设置GS工作模式（非GS雷达请无视该代码）
    // WorkMode not available in SDK, skip
    //启动扫描
    ret = laser.turnOn();
  } 
  else 
  {
    RCLCPP_ERROR(node->get_logger(), "Failed to initialize YDLIDAR");
  }
  
  auto laser_pub = node->create_publisher<sensor_msgs::msg::LaserScan>("scan", rclcpp::SensorDataQoS());

  auto stop_scan_service =
    [&laser](const std::shared_ptr<rmw_request_id_t> request_header,
  const std::shared_ptr<std_srvs::srv::Empty::Request> req,
  std::shared_ptr<std_srvs::srv::Empty::Response> response) -> bool
  {
    return laser.turnOff();
  };

  auto stop_service = node->create_service<std_srvs::srv::Empty>("stop_scan",stop_scan_service);

  auto start_scan_service =
    [&laser](const std::shared_ptr<rmw_request_id_t> request_header,
  const std::shared_ptr<std_srvs::srv::Empty::Request> req,
  std::shared_ptr<std_srvs::srv::Empty::Response> response) -> bool
  {
    return laser.turnOn();
  };

  auto start_service = node->create_service<std_srvs::srv::Empty>("start_scan",start_scan_service);

  rclcpp::WallRate loop_rate(20);

  //std::ofstream file("pointcloud_data.txt"); // 打开文件流
  while (ret && rclcpp::ok()) 
  {
    LaserScan scan;
    bool hardwareError = false;
    if (laser.doProcessSimple(scan, hardwareError)) {
      auto scan_msg = std::make_shared<sensor_msgs::msg::LaserScan>();
      scan_msg->header.stamp.sec = RCL_NS_TO_S(scan.stamp);
      scan_msg->header.stamp.nanosec =  scan.stamp - RCL_S_TO_NS(scan_msg->header.stamp.sec);
      scan_msg->header.frame_id = frame_id;
      scan_msg->angle_min = scan.config.min_angle;
      scan_msg->angle_max = scan.config.max_angle;
      scan_msg->angle_increment = scan.config.angle_increment;
      scan_msg->scan_time = scan.config.scan_time;
      scan_msg->time_increment = scan.config.time_increment;
      scan_msg->range_min = scan.config.min_range;
      scan_msg->range_max = scan.config.max_range;
      int size = (scan.config.max_angle - scan.config.min_angle)/ scan.config.angle_increment + 1;
      scan_msg->ranges.resize(size);
      scan_msg->intensities.resize(size);
      for (size_t i=0; i < scan.points.size(); i++) {
        const auto& p = scan.points.at(i);
        int index = std::ceil((scan.points[i].angle - scan.config.min_angle)/scan.config.angle_increment);
        if(index >=0 && index < size) {
          scan_msg->ranges[index] = scan.points[i].range;
          scan_msg->intensities[index] = scan.points[i].intensity;
        }
      }
      laser_pub->publish(*scan_msg);
    } else {
      RCLCPP_ERROR(node->get_logger(), "Failed to get scan");
    }
    if(!rclcpp::ok()) 
    {
      break;
    }
    rclcpp::spin_some(node);
    loop_rate.sleep();
  }

  RCLCPP_INFO(node->get_logger(), "[YDLIDAR INFO] Now YDLIDAR is stopping .......");
  laser.turnOff();
  laser.disconnecting();
  rclcpp::shutdown();

  return 0;
}
