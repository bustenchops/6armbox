from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
import time

# Initialize the camera
picam2 = Picamera2()

# Configure the camera for video recording
print('configure cam')
video_config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(video_config)

# Set up the H.264 encoder
print('encoder defined')
encoder = H264Encoder()

# Start the camera preview (optional)
print('preview start')
picam2.start_preview(Preview.QTGL)  # Use Preview.NULL if no preview is needed

# Start the camera
print('start camera')
picam2.start()

# Start recording to a file
print('start recording to file')
output_file = "video_output.h264"
picam2.start_encoder(encoder, output_file)

print("Recording started. Press Ctrl+C to stop.")
try:
    # Record for a specific duration or until interrupted
    time.sleep(10)  # Replace with desired recording duration in seconds
except KeyboardInterrupt:
    print("Recording stopped by user.")

# Stop recording and clean up
picam2.stop_encoder()
picam2.stop()
picam2.close()

print(f"Video saved as {output_file}")