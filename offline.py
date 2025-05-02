import argparse

from src.util import VideoStreamer, DataStreamer
from src.data_fusion import DataFusion

parser = argparse.ArgumentParser()
parser.add_argument("--video", type=str, default="./test_data/IMG_3965.MOV", help="Path to the video file")
parser.add_argument("--rosbag", type=str, default="./test_data/rosbag2_2025_02_10-18_17_04", help="Path to the rosbag file")
parser.add_argument("--ros_topic", type=str, default="/px4_mpc/controller_values", help="ROS topic to read data from")
parser.add_argument("--config", type=str, default="config.yaml", help="Path to the configuration file")
parser.add_argument("--start_playback", type=float, default=0.0, help="Start time of the video in seconds")
parser.add_argument("--end_playback", type=float, default=None, help="End time of the video in seconds. None: play until end")
parser.add_argument("--time_sync", type=float, default=None, help="Start time of video as POSIX timestamp. None: will try to synchronize automatically")
args = parser.parse_args()

video = VideoStreamer(args.video, 
                      start_time=args.time_sync,
                      start_playback_t=args.start_playback, 
                      end_playback_t=args.end_playback)

data = DataStreamer(args.rosbag, args.ros_topic)

data_fusion = DataFusion(video, data, args.config)
data_fusion.fuse_data()

# Save data