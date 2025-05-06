import rclpy # Python library for ROS 2
from rclpy.node import Node # Handles the creation of nodes
from sensor_msgs.msg import Image # Image is the message type

from space_lab_data_fusion.src.data_fusion import DataFusion
from space_lab_data_fusion.src.util_live import VideoStreamerLive, DataStreamerLive

"""

Also: Need to restructure everything as a ROS package
"""

class OnlineDataFusion(Node):
    def __init__(self):
        super().__init__('data_fusion_node')

        self.video = VideoStreamerLive(self, "/flir_camera/image_raw")
        self.data = DataStreamerLive(self, "/px4_mpc/controller_values")

        self.data_fusion = DataFusion(self.video, self.data, "config.yaml")

        self.timer_period = 0.1  # seconds
        self.timer = self.create_timer(
            self.timer_period, 
            self.timer_callback,
            callback_group=self.timer_callback_group)
    
    def timer_callback(self):
        # implement data fusion
        res = self.data_fusion.fuse_frame()

        # Todo: Is that really what I want to do here?
        if res is not None:
            self.data_fusion.video_writer.release()

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
