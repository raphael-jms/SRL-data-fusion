import ffmpeg
import os
import cv2

class Streamer:
    def __init__(self, data):
        self.data = None
        self.index = 0

    def get_newest(self):
        pass

    def is_running(self):
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

    def get_newest(self):
        # Logic to get the newest frame from the video
        return self.video.read()

    def get_time(self):
        return  cv2.CAP_PROP_POS_MSEC

class DataStreamer(Streamer):
    def __init__(self, data):
        super().__init__(data)
        self.data = data
        self.index = 0

    def get_data(sellf, time):
        return None

    def get_newest(self):
        # Logic to get the newest data
        return self.data[self.index], True