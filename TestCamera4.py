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
encoder = H264Encoder(bitrate=3000000)

# Start the camera preview (optional)
print('preview start')
picam2.start_preview(Preview.NULL)  # Use Preview.NULL if no preview is needed

# Start the camera
print('start camera')
picam2.start()

# Start recording to a file
print('start recording to file')
filenumber = 5
output_file = f"video_output_{x}.h264"

try:
    for x in range(filenumber):
        print(f"file_{x}")
        picam2.start_encoder(encoder, output_file)
        print("Recording started...")

        time.sleep(5)

        picam2.stop_encoder()
        print("Recording stopped.")
        output_file = f"video_output_{x}.h264"
        time.sleep(1)


except KeyboardInterrupt:
    print("Recording stopped by user.")

# Stop recording and clean up
picam2.stop_encoder()
picam2.stop()
picam2.close()