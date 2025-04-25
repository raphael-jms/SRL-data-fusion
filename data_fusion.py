import ffmpeg
import cv2
import numpy as np

from example_animation import Animator

orig_video = "./test_data/IMG_3965.MOV"
video_name = orig_video.split(".")[-2].split("/")[-1]

video_file = "./test_data/" + video_name + "_temp.mp4"
video_file = orig_video
background_file = "./test_data/background_" + video_name + ".png"
print(f"Video file: {video_file} \nBackground file: {background_file}")

background = cv2.imread(background_file)
background_gray = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)

MAX_FRAMES = 1000
THRESH = 60
ASSIGN_VALUE = 255

## Prepare intermediate animation layer
ani = Animator()

pts_video = np.array(
    [[550, 115],  # upper left
     [1480, 135], # upper right
     [390, 928],  # lower left
     [1685, 907]])# lower right
    
pts_ani = np.array(
    [[0, 0], # upper left
     [1000, 0], # upper right
     [0, 1000], # lower left
     [1000, 1000]])# lower right

ani_transform, _ = cv2.findHomography(pts_ani, pts_video, cv2.RANSAC, 5.0)
bg_height, bg_width = background_gray.shape

# Create a mask for inserting the animation
ani_img = ani.get_plot()
white_img_like_ani = np.ones_like(ani_img[:,:,0], dtype=np.uint8) * 255
# print(background_gray.shape)
ani_mask = cv2.warpPerspective(white_img_like_ani, ani_transform, (bg_width, bg_height)
                               #, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
                               )
# ani_mask = cv2.cvtColor(ani_mask, cv2.COLOR_GRAY2RGB)

# cv2.imshow('ani_img', ani_img)
# cv2.waitKey(0)  
# cv2.imshow('white_img_like_ani', white_img_like_ani)
# cv2.waitKey(0)  
# print(background_gray.shape)
# print(ani_mask.shape)
# cv2.imshow('bg', background_gray)
# cv2.waitKey(0)  
# cv2.imshow('ani_mask', ani_mask)
# cv2.waitKey(0)  
# exit()

## Prepare video stream
video = cv2.VideoCapture(video_file)


## Process video stream
while video.isOpened():
    # Capture frame-by-frame
    ret, frame = video.read()
    if not ret:
        break

    # Convert frame to grayscale
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)      

    # Background subtraction and Mask thresholding
    diff = cv2.absdiff(background_gray, frame_gray)
    ret, motion_mask = cv2.threshold(diff, THRESH, ASSIGN_VALUE, cv2.THRESH_BINARY)

    # Improve the mask
    # Open: remove noise & Close: fill holes
    motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

    # add the animation to the background
    ani.update()
    ani_plot = ani.get_plot()

    ani_warped = cv2.warpPerspective(ani_plot, ani_transform, (bg_width, bg_height)
                        # , dst=ani_plot, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
                        )
    # remove all black pixels
    transparent_overlay = cv2.addWeighted(frame, 0.5, ani_warped, 0.5, 0) # add the animation
    background = cv2.add(
        cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(ani_mask)), # cut out the 
        cv2.bitwise_and(
            transparent_overlay, transparent_overlay, mask=ani_mask
        )
    )
            # cv2.addWeighted(frame, 0.5, ani_warped, 0.5, 0), # add the animation

    # Overlay the foreground (robot) with the background using the motion_mask
    result = cv2.add(
        cv2.bitwise_and(frame, frame, mask=motion_mask), # cut out the 
        # cv2.cvtColor( cv2.bitwise_and(frame, frame, mask=cv2.bitwise_not(motion_mask)), cv2.COLOR_GRAY2RGB)
        cv2.bitwise_and(background, background, mask=cv2.bitwise_not(motion_mask))
    )

    # Display the current frame
    # cv2.imshow('Current Frame', motion_mask)

    # masked_original = cv2.bitwise_and(frame, frame, mask=motion_mask)
    # cv2.imshow('Current Frame', masked_original)

    cv2.imshow('Current Frame', result)
    # Wait for 1 ms and check for 'q' key to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
