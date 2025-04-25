import ffmpeg
import os
import cv2

import rclpy
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
import rosbag2_py

class Streamer:
    def __init__(self, data_source):
        pass

    def get_data(self, time=None):
        """ Get the desired data. If time is None, return the most recent data. """
        pass

    def is_running(self):
        """ Check that there is still data to be read. """
        return True

class VideoStreamer(Streamer):
    def __init__(self, video_path, start_time=0, end_time=None, fps=30):

        """
        Could maybe rewrite this all and completely remove the ffmpeg dependency?
        In that case just start reading the video at the given start time
        """
        super().__init__(video_path)
        self.start_time = start_time
        self.end_time = end_time
        self.fps = fps

        # Convert to mp4 if necessary, adjust fps, and trim the video
        video_name = video_path.split(".")[-2]
        processed_video_name = "." + video_name + "_temp" + '.mp4'

        if not os.path.exists(processed_video_name):
            (
                ffmpeg
                .input(video_path)
                .filter('fps', fps=self.fps, round='up')
                .output(processed_video_name, ss=self.start_time, to=self.end_time)
                .run()
            )
        else:
            print(f"File {processed_video_name} already exists. Skipping conversion.")

        self.video_path = processed_video_name
        self.original_video_path = video_path

        self.video = cv2.VideoCapture(self.video_path)

    def is_running(self):
        return self.video.isOpened()

    def get_data(self, time=None):
        # Logic to get the newest frame from the video
        return self.video.read()

    def get_time(self):
        return  cv2.CAP_PROP_POS_MSEC

class DataStreamer(Streamer):
    """
    Read data from a ROS bag file
    """
    def __init__(self, data_file, topic_name='/px4_mpc/controller_values'):
        # Initialize storage reader
        storage_options = rosbag2_py.StorageOptions(
            uri=str(data_file),
            storage_id='sqlite3'
        )
        converter_options = rosbag2_py.ConverterOptions('', '')
        self.reader = rosbag2_py.SequentialReader()
        self.reader.open(storage_options, converter_options)

        # Get topic types
        topic_types = self.reader.get_all_topics_and_types()
        self.type_map = {topic.name: topic.type for topic in topic_types}

        self.topic_name = topic_name

        self.last_data = None

    def get_data(self, time):
        # Get the next data point of the topic that interests us (if existing)
        current_data = None
        while current_data is None and self.reader.has_next():
            topic_name, data, t = self.reader.read_next()
            msg_type = get_message(self.type_map[topic_name])
            msg = deserialize_message(data, msg_type)
            
            if topic_name == self.topic_name:
                current_data = {
                    't': t,
                    'data': msg
                }

        if current_data is not None and self.last_data is not None:
            # both last and current data exist, choose the one closest to the current time
            if abs(current_data['t'] - time) < abs(self.last_data['t'] - time):
                self.last_data = current_data
                return current_data['msg']
            else:
                return self.last_data['msg']
        elif current_data is not None and self.last_data is None:
            # first read
            self.last_data = current_data
            return current_data['msg']
        elif current_data is None and self.last_data is not None:
            # probably the last data point in the bag
            return self.last_data['msg']
        else:
            raise ValueError("No data found in Rosbag.")

    def is_running(self):
        return self.reader.has_next()
