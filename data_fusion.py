import ffmpeg
import cv2
import numpy as np
import yaml

from util import DataStreamer, VideoStreamer

from example_animation import Animator

class DataFusion:
    def __init__(self, orig_video, data_file, config_path):
        video_name = orig_video.split(".")[-2].split("/")[-1]

        video_file = "./test_data/" + video_name + "_temp.mp4"
        video_file = orig_video
        background_file = "./test_data/background_" + video_name + ".png"
        print(f"Video file: {video_file} \nBackground file: {background_file}")

        config = yaml.safe_load(open(config_path, "r"))

        background = cv2.imread(background_file)
        self.background_gray = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)

        self.THRESH = 60
        self.ASSIGN_VALUE = 255

        ## Prepare intermediate animation layer
        self.ani = Animator(dpi=100)

        # Find mapping from animation to video
        pts_video = np.array([
            config["CORNER_POS"]["TOP_LEFT"]["px"],
            config["CORNER_POS"]["TOP_RIGHT"]["px"],
            config["CORNER_POS"]["BOTTOM_LEFT"]["px"],
            config["CORNER_POS"]["BOTTOM_RIGHT"]["px"]])
            
        pts_ani = np.array(
            [[0, 0],                         # upper left
            [self.ani.width_px, 0],              # upper right
            [0, self.ani.height_px],             # lower left
            [self.ani.width_px, self.ani.height_px]]) # lower right

        ani_transform, _ = cv2.findHomography(pts_ani, pts_video, cv2.RANSAC, 5.0)
        bg_height, bg_width = self.background_gray.shape

        self.ani_transform = ani_transform
        self.bg_width, self.bg_height = bg_width, bg_height

        # Create a mask for inserting the animation
        ani_img = self.ani.get_plot()
        white_img_like_ani = np.ones_like(ani_img[:,:,0], dtype=np.uint8) * 255
        # print(background_gray.shape)
        self.ani_mask = cv2.warpPerspective(white_img_like_ani, ani_transform, (bg_width, bg_height)
                                    #, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
                                    )
        
        ## Prepare video stream
        # self.video = VideoStreamer(video_file, start_playback_t=10)
        self.video = VideoStreamer(video_file, start_playback_t=10)
        self.data_stream = DataStreamer(data_file)

    def fuse_data(self):
        """
        Fuse the data from the video stream and the animation.
        """
        while self.video.is_running():
            result = self.fuse_frame()

            if result is None:
                break

            cv2.imshow('Current Frame', result)
            # Wait for 1 ms and check for 'q' key to exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    def fuse_frame(self):
        """
        Fuse the current frame from the video stream with the animation.
        """
        ret, frame = self.video.get_data()
        if not ret:
            return None

        # Convert frame to grayscale
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)      

        # Background subtraction and Mask thresholding
        diff = cv2.absdiff(self.background_gray, frame_gray)
        ret, motion_mask = cv2.threshold(diff, self.THRESH, self.ASSIGN_VALUE, cv2.THRESH_BINARY)

        # Improve the mask
        # Open: remove noise & Close: fill holes
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

        # add the animation to the background
        cur_time_msec = self.video.get_time()
        self.ani.update(self.data_stream.get_data(cur_time_msec))
        ani_plot = self.ani.get_plot()

        ani_warped = cv2.warpPerspective(ani_plot, self.ani_transform, (self.bg_width, self.bg_height)
                            # , dst=ani_plot, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
                            )
        # remove all black pixels
        transparent_overlay = cv2.addWeighted(frame, 0.5, ani_warped, 0.5, 0) # add the animation
        background = cv2.add(
            cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(self.ani_mask)), # cut out the 
            cv2.bitwise_and(
                transparent_overlay, transparent_overlay, mask=self.ani_mask
            )
        )

        # Overlay the foreground (robot) with the background using the motion_mask
        result = cv2.add(
            cv2.bitwise_and(frame, frame, mask=motion_mask), # cut out the 
            # cv2.cvtColor( cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(motion_mask)), cv2.COLOR_GRAY2RGB)
            cv2.bitwise_and(background, background, mask=cv2.bitwise_not(motion_mask))
        )

        # Add text to the frame
        cv2.putText(result, f"Time video: {self.video.get_time()}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(result, f"Time data:  {self.data_stream.get_time()}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(result, f"Time diff:  {(self.video.get_time() - self.data_stream.get_time())*1e-9} s", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(result, f"FPS: {self.video.measured_fps()} == {self.video.fps}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        return result

if __name__ == "__main__":
    orig_video = "./test_data/IMG_3965.MOV"
    rosbag_file = "./test_data/rosbag2_2025_02_10-18_17_04"
    config_path ="config.yaml"

    data_fusion = DataFusion(orig_video, rosbag_file, config_path)
    data_fusion.fuse_data()
