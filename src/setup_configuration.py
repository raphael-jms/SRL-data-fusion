import yaml
import ffmpeg
import os
import argparse

def extract_background(input_file, output_file=None, num_frames=25):
    """
    Extract the background from a video with a steady camera by sampling frames
    across the entire video duration and applying temporal median filtering.
    
    Args:
        input_file (str): Path to input video file
        output_file (str): Path to output background image
        num_frames (int): Number of frames to use for median calculation
    """
    video_name = input_file.split(".")[-2].split("/")[-1]
    if output_file is None:
        output_file = "./test_data/background_" + video_name +".png"
    try:
        # Get video duration and total frames using ffprobe
        probe = ffmpeg.probe(input_file)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        duration = float(probe['format']['duration'])
        total_frames = int(video_info.get('nb_frames', 0))
        
        # If nb_frames is not available, estimate it
        if total_frames == 0:
            fps = eval(video_info['avg_frame_rate'])
            total_frames = int(duration * fps)
        
        # Calculate frame interval to get evenly distributed frames
        frame_interval = max(1, total_frames // num_frames)
        
        print(f"Video duration: {duration:.2f}s")
        print(f"Total frames: {total_frames}")
        print(f"Using {num_frames} frames with interval {frame_interval} for background extraction")
        
        # Build the ffmpeg command using tmedian filter
        (
            ffmpeg
            .input(input_file)
            .filter('select', f'not(mod(n,{frame_interval}))')
            .filter('setpts', 'N/TB')
            .filter('tmedian', radius=num_frames//2)  # tmedian uses radius which is half the window size
            .output(output_file, frames=1)
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
        
        print(f"Background successfully extracted to {output_file}")
        return True
        
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--get_background', action='store_true', help='Extract background from video')
    parser.add_argument('--file', type=str, default="./test_data/IMG_3965.MOV", help='Path to the input video file')

    args = parser.parse_args()

    if args.get_background:
        # Extract the background from the video specified in the configuration
        input_file = args.file
        num_frames = 25  # Default to 25 frames if not specified
        extract_background(input_file, num_frames=num_frames)