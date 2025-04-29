#!/usr/bin/env python3

import sys
import numpy as np
from rclpy.serialization import deserialize_message
import rosbag2_py
from rosidl_runtime_py.utilities import get_message as original_get_message

# Create message classes that match the ROS2 message structure

class DummyTime:
    def __init__(self):
        self.sec = 0
        self.nanosec = 0

class DummyHeader:
    def __init__(self):
        self.stamp = DummyTime()
        self.frame_id = ""

class ControllerValues:
    """
    Custom class that matches the micro_orbiting_msgs/msg/ControllerValues structure
    """
    def __init__(self):
        # NOTE: This must match exactly the memory layout of the original message
        self.header = DummyHeader()
        
        # State variables (x)
        self.x1 = 0.0
        self.y1 = 0.0
        self.alpha = 0.0
        self.x2 = 0.0
        self.y2 = 0.0
        self.omega = 0.0
        
        # Error terms (e)
        self.e1 = 0.0
        self.e2 = 0.0
        self.e_alpha = 0.0
        self.e3 = 0.0
        self.e5 = 0.0
        self.e_omega = 0.0
        
        # Control inputs (u)
        self.u = []
        self.u_nom = []
        self.u_control = []
        
        # Full control inputs (u8)
        self.u_full = [0.0] * 8
        
        # Planned state trajectory
        self.plan_x1 = []
        self.plan_y1 = []
        self.plan_alpha = []
        self.plan_x2 = []
        self.plan_y2 = []
        self.plan_omega = []
        
        # Performance metrics
        self.control_cost = 0.0
        self.solver_time = 0.0
        self.solver_state = 0
        
        # Center position (only used for orbiting)
        self.center_state_x = 0.0
        self.center_state_y = 0.0
        self.center_state_omega = 0.0
        self.center_state_alpha = 0.0
        self.center_state_vx = 0.0
        self.center_state_vy = 0.0
        
        self.center_error_x = 0.0
        self.center_error_y = 0.0
        self.center_error_omega = 0.0
        self.center_error_vx = 0.0
        self.center_error_vy = 0.0
        
        # Desired position
        self.desired_state = []

def custom_get_message(message_type):
    """
    Custom function to handle missing message types
    """
    try:
        # First try the normal way
        return original_get_message(message_type)
    except ModuleNotFoundError:
        # Handle specific known types
        if message_type == 'micro_orbiting_msgs/msg/ControllerValues':
            return ControllerValues
        else:
            # Generic handler for any other unknown message
            class DummyMessage:
                def __init__(self):
                    pass
            return DummyMessage

class DataStreamer:
    """
    Read data from a ROS bag file with support for custom message types
    """
    def __init__(self, data_file, topic_name='/px4_mpc/controller_values'):
        # Initialize storage reader
        storage_options = rosbag2_py.StorageOptions(
            uri=str(data_file),
            storage_id='sqlite3'
        )
        converter_options = rosbag2_py.ConverterOptions(
            input_serialization_format='cdr',
            output_serialization_format='cdr'
        )
        self.reader = rosbag2_py.SequentialReader()
        self.reader.open(storage_options, converter_options)

        # Get topic types
        topic_types = self.reader.get_all_topics_and_types()
        self.type_map = {topic.name: topic.type for topic in topic_types}

        # Override the get_message function
        import rosidl_runtime_py.utilities
        rosidl_runtime_py.utilities.get_message = custom_get_message
        
        self.topic_name = topic_name
        self.buffer = []
        
        # Print some info about the bag
        print(f"Found {len(topic_types)} topics in the bag file:")
        for topic in topic_types:
            print(f"  {topic.name}: {topic.type}")
        
        if topic_name not in self.type_map:
            print(f"WARNING: Requested topic '{topic_name}' not found in bag file!")
            print(f"Available topics: {list(self.type_map.keys())}")

    def get_data(self, time):
        """
        Get the closest data point to the requested time
        """
        # Read ahead until we have data points beyond the requested time
        while (not self.buffer or self.buffer[-1]['t'] <= time) and self.reader.has_next():
            topic_name, data, t = self.reader.read_next()
            
            if topic_name == self.topic_name:
                try:
                    # Get the correct message type and deserialize
                    msg_type = custom_get_message(self.type_map[topic_name])
                    msg = deserialize_message(data, msg_type)
                    
                    self.buffer.append({
                        't': t,
                        'data': msg
                    })
                except Exception as e:
                    print(f"Error deserializing message: {e}")
        
        if not self.buffer:
            raise ValueError("No data found in Rosbag for topic: " + self.topic_name)
        
        # Find the closest data point
        closest_idx = 0
        closest_diff = abs(self.buffer[0]['t'] - time)
        
        for i, data_point in enumerate(self.buffer):
            diff = abs(data_point['t'] - time)
            if diff < closest_diff:
                closest_diff = diff
                closest_idx = i
        
        # Get result
        result = self.buffer[closest_idx]['data']
        
        # Remove data points that are no longer needed
        # (everything before the closest point, except the closest point itself)
        self.buffer = self.buffer[closest_idx:]
        
        return result

    def is_running(self):
        return self.reader.has_next()
    
    def get_all_data(self):
        """
        Get all data points for the topic
        """
        all_data = []
        
        # Read all messages from the bag
        while self.reader.has_next():
            topic_name, data, t = self.reader.read_next()
            
            if topic_name == self.topic_name:
                try:
                    # Get the correct message type and deserialize
                    msg_type = custom_get_message(self.type_map[topic_name])
                    msg = deserialize_message(data, msg_type)
                    
                    all_data.append({
                        'timestamp': t,
                        'data': msg
                    })
                except Exception as e:
                    print(f"Error deserializing message at time {t}: {e}")
        
        return all_data

def test_reader(bag_path, topic='/px4_mpc/controller_values'):
    """
    Test the DataStreamer class by reading all data from a bag file
    """
    streamer = DataStreamer(bag_path, topic)
    
    try:
        # Read all data
        data = streamer.get_all_data()
        
        if not data:
            print(f"No data found for topic: {topic}")
            return
            
        print(f"Read {len(data)} messages from topic: {topic}")
        
        # Print details of the first message
        first_msg = data[0]['data']
        print("\nFirst message details:")
        
        # Print state variables
        print("State variables:")
        print(f"  x1: {first_msg.x1}")
        print(f"  y1: {first_msg.y1}")
        print(f"  alpha: {first_msg.alpha}")
        print(f"  x2: {first_msg.x2}")
        print(f"  y2: {first_msg.y2}")
        print(f"  omega: {first_msg.omega}")
        
        # Print control inputs if available
        if hasattr(first_msg, 'u') and first_msg.u:
            print("\nControl inputs (u):")
            print(f"  u: {first_msg.u}")
            print(f"  u_full: {first_msg.u_full}")
        
        # Print arrays and their sizes
        print("\nArray sizes:")
        for field in ['u', 'u_nom', 'u_control', 'plan_x1', 'plan_y1', 'plan_alpha', 
                     'plan_x2', 'plan_y2', 'plan_omega', 'desired_state']:
            value = getattr(first_msg, field)
            if isinstance(value, list):
                print(f"  {field}: {len(value)} elements")
                
        # Print timestamp
        timestamp = data[0]['timestamp']
        print(f"\nTimestamp: {timestamp}")
        
    except Exception as e:
        print(f"Error reading bag file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_bag_directory> [topic_name]")
        sys.exit(1)
    
    bag_path = sys.argv[1]
    topic = sys.argv[2] if len(sys.argv) > 2 else '/px4_mpc/controller_values'
    
    test_reader(bag_path, topic)