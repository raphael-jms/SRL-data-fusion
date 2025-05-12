import rclpy # Python library for ROS 2
from rclpy.node import Node # Handles the creation of nodes
from sensor_msgs.msg import Image # Image is the message type
import cv2

from space_lab_data_fusion.src.data_fusion import DataFusion
from space_lab_data_fusion.src.util_live import VideoStreamerLive, DataStreamerLive


class OnlineDataFusion(Node):
    def __init__(self):
        super().__init__('data_fusion_node')
        self.get_logger().info("Initializing data fusion node...")

        self.video = VideoStreamerLive(self, "/flir_camera/image_raw")
        self.data = DataStreamerLive(self, "/px4_mpc/controller_values")

        self.declare_parameter('config_path', "")
        self.config_path = self.get_parameter('config_path').value
        if self.config_path == "":
            raise ValueError("No config file provided. Please provide a config file.")
        self.get_logger().info(f"Config file: {self.config_path}")

        self.data_fusion = DataFusion(self.video, self.data, self.config_path)

        self.get_logger().info("Creating timer...")
        self.wait_for_message_timer = self.create_timer(
            0.3, 
            self.wait_for_message_callback)
   
    def timer_callback(self):
        # implement data fusion
        self.get_logger().info("Fusing frame...")
        res = self.data_fusion.fuse_frame()

        if res is not None:
            cv2.imshow('Current Frame', res)
            cv2.waitKey(1)
    
    def wait_for_message_callback(self):
        self.get_logger().info("Waiting for messages...")
        if self.data_fusion.video.has_started() and self.data_fusion.data_stream.has_started():
            self.get_logger().info("Message transmission started. Starting data fusion...")
            # Stop the current timer
            self.wait_for_message_timer.cancel()

            # Create new timer for data fusion
            self.timer_period = 0.1  # seconds
            self.timer = self.create_timer(
                self.timer_period, 
                self.timer_callback)
    
    def destroy_node(self):
        self.data_fusion.video_writer.release()
        super().destroy_node()
 
def main(args=None):
    # Initialize the rclpy library
    rclpy.init(args=args)

    # Create the node
    data_animator = OnlineDataFusion()

    # Spin the node so the callback function is called.
    rclpy.spin(data_animator)

    # Shutdown the ROS client library for Python
    data_animator.destroy_node()
    rclpy.shutdown()
   
if __name__ == '__main__':
    main()
