#!/usr/bin/env python3
import rclpy
from rclpy.serialization import deserialize_message
import rosbag2_py
from rosidl_runtime_py.utilities import get_message


storage_options = rosbag2_py.StorageOptions(
    uri="./rosbag2_2025_02_10-18_17_04",
    storage_id='sqlite3'
)
converter_options = rosbag2_py.ConverterOptions('', '')
reader = rosbag2_py.SequentialReader()
reader.open(storage_options, converter_options)

# Get topic types
topic_types = reader.get_all_topics_and_types()
type_map = {topic.name: topic.type for topic in topic_types}

# Process messages
while reader.has_next():
    topic_name, data, t = reader.read_next()
    
    msg_type = get_message(type_map[topic_name])
    msg = deserialize_message(data, msg_type)

    print(msg.desired_state)
    print(msg)
    if len(msg.desired_state) == 0:
        breakpoint()