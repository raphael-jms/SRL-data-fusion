import ffmpeg
import os
import cv2
# import datetime
from datetime import datetime, timedelta
import time
from collections import deque
from numbers import Number
import warnings

from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
import rosbag2_py
from micro_orbiting_msgs.msg import ControllerValues

from space_lab_data_fusion.src.setup_configuration import extract_background

class Streamer:
    def __init__(self, data_source):
        pass

    def get_data(self, time=None):
        """ Get the desired data. If time is None, return the most recent data. """
        pass

    def is_running(self):
        """ Check that there is still data to be read. """
        return True

class VideoStreamerRecorded(Streamer):
    def __init__(self, video_path, start_time=None, start_playback_t=0, end_playback_t=None, background_path=None):

        """
        Args:
            video_path (str): Path to the video file.
            start_time (float): Start time as POSIX timestamp, i.e. seconds since 00:00:00 1-Jan-1970 UTC.
                                If None, will try to automatically synchronize using creation time of video.
            start_playback_t (float): Start time of playback in seconds after video start
            end_playback_t (float): End time of playback in seconds after video start; if None, play until end of video.
        """
        super().__init__(video_path)

        # Convert to mp4 if necessary, adjust fps, and trim the video
        self.video_path = video_path
        self.background_path = background_path
        if not os.path.exists(self.video_path):
            raise ValueError(f"Video file {self.video_path} does not exist.")

        self.video = cv2.VideoCapture(self.video_path)
        self.fps = self.video.get(cv2.CAP_PROP_FPS)

        self.frame_count = 0

        # Jump to the start of the playback
        self.start_playback_frame = int(start_playback_t * self.fps)
        self.video.set(cv2.CAP_PROP_POS_FRAMES, self.start_playback_frame)
        self.frame_count += self.start_playback_frame

        self.end_playback_frame = end_playback_t * self.fps if end_playback_t is not None else \
            self.video.get(cv2.CAP_PROP_FRAME_COUNT)

        try:
            if start_time is None:
                streams = ffmpeg.probe(self.video_path)["streams"]
                video_stream = [s for s in streams if s["codec_type"]=="video"][0]
                duration = timedelta(seconds=float(video_stream["duration"]))
                creation_time = video_stream["tags"]["creation_time"]
                creation_time  = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))

                # Creation time is when video was saved (i.e. the end), get start time instead
                # self.start_time = datetime.timestamp(creation_time - duration)
                self.start_time = datetime.timestamp(creation_time)
            else:
                self.start_time = start_time
        except Exception as e:
            raise ValueError("Error getting video stream information. Try again with setting --start_time "
                             +  "to manually set start time as POSIX timestamp. \n\n" +
                             + f"Error message: {repr(e)}") from e
        
        self.start_t = time.time()

    def is_running(self):
        """ Check if the video stream is still running. """
        return self.video.isOpened()

    def get_data(self, time=None):
        """ Get the newest frame from the video stream. """
        # Logic to get the newest frame from the video
        self.frame_count += 1

        if self.frame_count > self.video.get(cv2.CAP_PROP_FRAME_COUNT) or \
                self.frame_count > self.end_playback_frame:
            self.video.release()
            print("Video stream ended.")
            return None, None

        return self.video.read()

    def get_time(self):
        # Convert to nanoseconds
        return  int((self.frame_count / self.video.get(cv2.CAP_PROP_FPS) + self.start_time) * 1e9)
    
    def measured_fps(self):
        return (self.frame_count - self.start_playback_frame) / (time.time() - self.start_t)
    
    def get_background(self):
        """
        Get the constant background image from the video stream.
        """
        if self.background_path is None:
            video_name = self.video_path.split(".")[-2].split("/")[-1]
            self.background_path = "./test_data/background_" + video_name + ".png"

        if not os.path.exists(self.background_path):
            warnings.warn(f"Background file {self.background_path} does not exist. Extracting background from video. Please wait...")
            # Extract background from video
            extract_background(self.video_path, self.background_path, num_frames=25)

        print(f"Video file: {self.video_path} \nBackground file: {self.background_path}")

        background = cv2.imread(self.background_path)
        return background

class DataStreamerRosbag(Streamer):
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
        self.last_timestamp = None

        self.buffer = deque(maxlen=2)

    def get_data(self, time):
        """
        Read the data from the ROS bag file at the specified time. 
        Interpolate the two closest messages if possible.
        """
        # Read the closes data points to the requested time
        while (not self.buffer or self.buffer[0]['t'] >= time or self.buffer[-1]['t'] <= time) and self.reader.has_next():
            topic_name, data, t = self.reader.read_next()
            
            if topic_name == self.topic_name:
                msg_type = get_message(self.type_map[topic_name])
                msg = deserialize_message(data, msg_type)
                self.buffer.append({
                    't': t,
                    'data': msg
                })
        
        if not self.buffer:
            raise ValueError("No data found in Rosbag.")

        # interpolate
        if len(self.buffer) == 1:
            self.last_timestamp = self.buffer[0]['t']
            return self.buffer[0]['data']
        elif len(self.buffer) == 2:
            t1 = self.buffer[0]['t']
            t2 = self.buffer[1]['t']
            data1 = self.buffer[0]['data']
            data2 = self.buffer[1]['data']

            # Interpolate all numeric fields
            alpha = (time - t1) / (t2 - t1)
            interpolated_data = ControllerValues()
            for field in dir(data1):
                if field in dir(data2) and isinstance(getattr(data1, field), Number):
                    setattr(interpolated_data, field, getattr(data1, field) * (1 - alpha) + getattr(data2, field) * alpha)
            
            self.last_timestamp = time
            return interpolated_data

    def is_running(self):
        return self.reader.has_next()
    
    def get_time(self):
        if self.last_timestamp is None:
            raise ValueError("No data has been read yet.")
        
        return self.last_timestamp
