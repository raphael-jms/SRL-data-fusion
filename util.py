import ffmpeg
import os
import cv2
# import datetime
from datetime import datetime, timedelta
import time

from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
import rosbag2_py
from micro_orbiting_msgs.msg import ControllerValues

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
    def __init__(self, video_path, start_time=None, start_playback_t=0, end_playback_t=None):

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

        # time.ctime(1739207828001926291*1e-9)
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
        return self.video.isOpened()

    def get_data(self, time=None):
        # Logic to get the newest frame from the video
        self.frame_count += 1

        if self.frame_count > self.video.get(cv2.CAP_PROP_FRAME_COUNT) or \
                self.frame_count > self.end_playback_frame:
            self.video.release()
            print("Video stream ended.")
            return None

        return self.video.read()

    def get_time(self):
        # Convert to nanoseconds
        return  int((self.frame_count / self.video.get(cv2.CAP_PROP_FPS) + self.start_time) * 1e9)
    
    def measured_fps(self):
        return (self.frame_count - self.start_playback_frame) / (time.time() - self.start_t)

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
        self.last_timestamp = None

        self.buffer = []

    def get_data(self, time):
        # Read ahead until we have data points beyond the requested time
        # if self.buffer:
        #     print(self.buffer[-1]['t'])
        #     print(time)
        #     print(f"Time difference seconds: {(self.buffer[-1]['t'] - time) * 1e-9}")
        #     print("need correct conversion between time and t; check what ROS2 actually uses")
        

        while (not self.buffer or self.buffer[-1]['t'] <= time) and self.reader.has_next():
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
        self.last_timestamp = self.buffer[closest_idx]['t']
        
        # Remove data points that are no longer needed
        # (everything before the closest point, except the closest point itself)
        self.buffer = self.buffer[closest_idx:]
        
        return result

    def is_running(self):
        return self.reader.has_next()
    
    def get_time(self):
        if self.last_timestamp is None:
            raise ValueError("No data has been read yet.")
        
        return self.last_timestamp
