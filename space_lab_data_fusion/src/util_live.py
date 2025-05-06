import rclpy # Python library for ROS 2
from rclpy.node import Node # Handles the creation of nodes
from sensor_msgs.msg import Image # Image is the message type
from cv_bridge import CvBridge # Package to convert between ROS and OpenCV Images
import os
import warnings
import cv2

from space_lab_data_fusion.src.util import Streamer

class VideoStreamerLive(Streamer):
    def __init__(self, ros_node, topic_name):
        super().__init__()

        self.image = None
        self.timestamp = None

        # To convert between ROS and OpenCV images
        self.bridge = CvBridge()

        # Where the background image is stored
        self.background_path = None

        self.ros_node = ros_node
        # TODO: Check if the topic name is valid
        self.ros_node.declare_parameter('frame_rate', 30)
        self.subscriber = self.ros_node.create_subscription(
            Image,
            topic_name,
            self.callback,
            2
        )

        self.fps = self.get_parameter('frame_rate').get_parameter_value().float_value
        
    def callback(self, msg):
        """
        Callback function to receive the image from the ROS topic
        """
        self.image = self.bridge.imgmsg_to_cv2(msg)
        self.timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

    def is_running(self):
        """ Check if the video stream is still running. """
        return self.ros_node.get_clock().now() - self.timestamp > rclpy.time.Duration(seconds=10.0*self.fps)

    def get_data(self, time=None):
        """ Get the newest frame from the video stream. """
        return True, self.image

    def get_time(self):
        if self.timestamp is None:
            raise ValueError("No data has been read yet.")

        return  self.timestamp
    
    def get_background(self):
        """
        Get the constant background image from the video stream.
        """
        if not os.path.exists(self.background_path):
            raise FileNotFoundError(f"Background file {self.background_path} does not exist. Please provide a valid path.")

        background = cv2.imread(self.background_path)
        return background

class DataStreamerLive(Streamer):
    """
    Read data from a ROS topic
    """
    def __init__(self, ros_node, topic_name='/px4_mpc/controller_values'):
        super().__init__()

        self.data = None
        self.timestamp = None

        self.ros_node = ros_node
        self.topic_name = topic_name

        # create a subscriber to the topic
        self.subscriber = self.ros_node.create_subscription(
            Image,
            topic_name,
            self.callback,
            10
        )
    
    def callback(self, msg):
        """
        Callback function to receive the data from the ROS topic
        """
        self.data = msg.data
        self.timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

    def get_data(self, time=None):
        return self.data

    def is_running(self):
        """ Check if the data stream is still running. """
        return self.ros_node.get_clock().now() - self.timestamp > rclpy.time.Duration(seconds=10.0*self.fps)

    def get_time(self):
        if self.timestamp is None:
            raise ValueError("No data has been read yet.")
        
        return self.timestamp
