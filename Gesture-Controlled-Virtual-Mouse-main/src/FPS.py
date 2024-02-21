import time
import numpy as np
from PIL import ImageGrab

def calculate_screen_fps(duration=30):
    # Start time
    start_time = time.time()
    frame_count = 0

    # Process frames for the specified duration
    while (time.time() - start_time) < duration:
        # Capture a screenshot of the entire screen
        screenshot = ImageGrab.grab()

        # Convert the screenshot to a numpy array
        frame = np.array(screenshot)

        # Increment frame count
        frame_count += 1

    # End time
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time

    # Calculate frames per second (FPS)
    fps = frame_count / elapsed_time

    return fps

if __name__ == "__main__":
    # Specify the duration for calculating FPS (in seconds)
    duration = 30

    # Calculate screen FPS
    fps = calculate_screen_fps(duration)

    # Print FPS
    print("Screen Frames per Second (FPS):", fps)
