#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import os

class ImagePublisher(Node):
    def __init__(self):
        super().__init__('image_publisher')
        self.publisher = self.create_publisher(Image, '/flir_camera/image_raw', 10)
        self.timer = self.create_timer(1.0, self.publish_image)  # Publish at 1 Hz
        self.bridge = CvBridge()
        
        # Load image from file - replace with your image path
        self.image_path = "/home/sml-laptop-1/Pictures/vlcsnap-2025-05-02-13h41m45s218.png"
        # self.image_path = "/home/sml-laptop-1/Pictures/Screenshot from 2025-04-30 14-05-01.png"

        if not os.path.exists(self.image_path):
            self.get_logger().error(f"Image file {self.image_path} does not exist.")
            rclpy.shutdown()
            return
        
    def publish_image(self):
        try:
            # Load image from file
            cv_image = cv2.imread(self.image_path)
            
            if cv_image is None:
                self.get_logger().error(f"Failed to load image from {self.image_path}")
                return
                
            # Convert OpenCV image to ROS Image message
            ros_image = self.bridge.cv2_to_imgmsg(cv_image, encoding="bgr8")
            
            # Set header information
            ros_image.header.stamp = self.get_clock().now().to_msg()
            ros_image.header.frame_id = "camera_frame"
            
            # Publish the image
            self.publisher.publish(ros_image)
            self.get_logger().info("Published image to /flir_camera/image_raw")
            
        except Exception as e:
            self.get_logger().error(f"Error publishing image: {str(e)}")

def main(args=None):
    rclpy.init(args=args)
    image_publisher = ImagePublisher()
    
    try:
        rclpy.spin(image_publisher)
    except KeyboardInterrupt:
        pass
    
    image_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()