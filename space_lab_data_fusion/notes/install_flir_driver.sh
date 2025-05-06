# Install the driver
# First attempt will not work
sudo apt install ros-${ROS_DISTRO}-spinnaker-camera-driver
# update and upgrade, then try again
sudo apt update
sudo apt upgrade
sudo apt install ros-${ROS_DISTRO}-spinnaker-camera-driver

# setup the camera
ros2 run spinnaker_camera_driver linux_setup_flir

# restart.
echo "restart your computer"

# Start the driver
ros2 launch spinnaker_camera_driver driver_node.launch.py camera_type:=blackfly_s serial:="'19516894'"

# display with
ros2 run rqt_image_view rqt_image_view


# try this only in case of problems
#  493  sudo apt install ros-$ROS_DISTRO-camera-info-manager ros-$ROS_DISTRO-diagnostic-updater ros-$ROS_DISTRO-dynamic-reconfigure ros-$ROS_DISTRO-image-exposure-msgs ros-$ROS_DISTRO-image-transport ros-$ROS_DISTRO-nodelet ros-$ROS_DISTRO-roscpp ros-$ROS_DISTRO-sensor-msgs ros-$ROS_DISTRO-wfov-camera-msgs


# Operate: Starting up the camera will always use the default values, but can be changed afterwards.
ros2 param set /flir_camera frame_rate 30.0