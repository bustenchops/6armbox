from picamera2 import Picamera2
import time

# Initialize the camera
picam2 = Picamera2()

# Configure the camera for video recording
video_config = picam2.create_video_configuration()
picam2.configure(video_config)

# Start the camera
picam2.start()

# File to save the recording
output_file = "test_video.h264"

print("Recording started...")
picam2.start_recording(output_file)

# Record for 10 seconds
time.sleep(10)

# Stop recording
picam2.stop_recording()
print(f"Recording saved to {output_file}")

# Stop the camera
picam2.stop()
