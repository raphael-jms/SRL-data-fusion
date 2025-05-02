import cv2
import numpy as np
import yaml

from src.util import DataStreamer, VideoStreamer

from examples.example_animation import Animator

class DataFusion:
    def __init__(self, video_streamer, data_streamer, config_path):
        background = video_streamer.get_background()
        self.background_gray = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)

        config = yaml.safe_load(open(config_path, "r"))
        self.THRESH = config["FUSION_PARAMS"].get("THRESHOLD", 60)
        self.ASSIGN_VALUE = 255

        ## Prepare intermediate animation layer
        self.ani = Animator(dpi=100)

        # Find mapping from animation to video
        # Get the corner positions in the arena video
        try:
            pts_video = np.array([
                config["CORNER_POS"]["VIDEO"]["TOP_LEFT"],
                config["CORNER_POS"]["VIDEO"]["TOP_RIGHT"],
                config["CORNER_POS"]["VIDEO"]["BOTTOM_LEFT"],
                config["CORNER_POS"]["VIDEO"]["BOTTOM_RIGHT"]])
        except KeyError as e:
            raise KeyError(f"Missing corner position in config file: Please check the config file.") from e
            
        # Get corner positions (dimensions) of the animation video 
        pts_ani = np.array(
            [[0, 0],                         # upper left
            [self.ani.width_px, 0],              # upper right
            [0, self.ani.height_px],             # lower left
            [self.ani.width_px, self.ani.height_px]]) # lower right

        # Calculate the transfrom from the animation to arena plane in the video
        ani_transform, _ = cv2.findHomography(pts_ani, pts_video, cv2.RANSAC, 5.0)
        bg_height, bg_width = self.background_gray.shape

        self.ani_transform = ani_transform
        self.bg_width, self.bg_height = bg_width, bg_height

        # Create a mask for inserting the animation
        ani_img = self.ani.get_plot()
        white_img_like_ani = np.ones_like(ani_img[:,:,0], dtype=np.uint8) * 255
        self.ani_mask = cv2.warpPerspective(white_img_like_ani, ani_transform, (bg_width, bg_height)
                                    #, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
                                    )

        self.ani_mask_active = np.where(self.ani_mask > 0)
        self.ani_mask_inactive = np.where(self.ani_mask == 0)
        
        ## Prepare video stream
        self.video = video_streamer
        self.data_stream = data_streamer

        ## Check if there is a logo to be added
        if "LOGO" in config.keys() and "FILE" in config["LOGO"].keys() and \
                config["LOGO"]["FILE"] != "" and config["LOGO"]["FILE"] is not None:
            self.add_logo = True
            # Read and resize the logo
            logo = cv2.imread(config["LOGO"]["FILE"])
            logo_height, logo_width = config["LOGO"].get("SIZE", [100, 100])
            logo_offset_height, logo_offset_width = config["LOGO"].get("OFFSET", [10, 10])

            # Resize the logo to fit the background and save positions
            logo = cv2.resize(logo, (logo_width, logo_height))
            self.logo_start = [
                int(bg_width - logo_width - logo_offset_width),
                int(logo_offset_height)
            ]
            self.logo_end = [
                self.logo_start[0] + logo_width,
                self.logo_start[1] + logo_height
            ]
            self.logo = logo
            self.logo_width, self.logo_height = logo_width, logo_height
        else:
            self.add_logo = False

        # Save the video stream
        fourcc = cv2.VideoWriter_fourcc(*"MP4V")
        self.video_writer = cv2.VideoWriter("output.mp4", fourcc, self.video.fps, (bg_width, bg_height))

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

        self.video_writer.release()
    
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

        ani_warped = cv2.warpPerspective(ani_plot, self.ani_transform, (self.bg_width, self.bg_height),
                            # flags = cv2.INTER_NEAREST,
                            # flags = cv2.INTER_LINEAR,
                            flags = cv2.INTER_CUBIC,
                            # flags = cv2.INTER_AREA,
                            # flags = cv2.INTER_LANCZOS4,
                            # flags = cv2.INTER_LINEAR_EXACT,
                            # flags = cv2.INTER_NEAREST_EXACT,
                            # flags = cv2.INTER_MAX,
                            # flags = cv2.WARP_FILL_OUTLIERS,
                            # flags = cv2.WARP_INVERSE_MAP, 
                            # borderMode=cv2.BORDER_TRANSPARENT,
                            )

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

        # Add the logo if specified
        if self.add_logo:
            result[self.logo_start[1]:self.logo_end[1], self.logo_start[0]:self.logo_end[0], :] = self.logo

        # # Add text to the frame
        # cv2.putText(result, f"Time video: {self.video.get_time()}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # cv2.putText(result, f"Time data:  {self.data_stream.get_time()}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # cv2.putText(result, f"Time diff:  {(self.video.get_time() - self.data_stream.get_time())*1e-9} s", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # cv2.putText(result, f"FPS: {self.video.measured_fps()} == {self.video.fps}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        self.video_writer.write(result)

        return result

if __name__ == "__main__":
    orig_video = "./test_data/IMG_3965.MOV"
    rosbag_file = "./test_data/rosbag2_2025_02_10-18_17_04"
    config_path ="config.yaml"

    data_fusion = DataFusion(orig_video, rosbag_file, config_path)
    data_fusion.fuse_data()
