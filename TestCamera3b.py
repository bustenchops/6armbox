from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
import time
import keyboard

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
filenumber = 1
output_file = f"video_output_{filenumber}.h264"
doingitsthing = 1
picam2.start_encoder(encoder, output_file)
print("Recording started. Press Ctrl+C to stop.")

try:
    while True:
        if keyboard.is_pressed('t'):  # Start recording when 't' is pressed
            if doingitsthing == 0:
                print("Recording started...")
                picam2.start_encoder(encoder, output_file)
                doingitsthing = 1
                while keyboard.is_pressed('t'):
                    print("Recording started. Press P to stop.")  # Wait for key release
                    time.sleep(0.1)

        if keyboard.is_pressed('p'):  # Stop recording when 'p' is pressed
            if doingitsthing == 1:
                print("Recording stopped.")
                picam2.stop_encoder()
                filenumber += 1
                output_file = f"video_output_{filenumber}.h264"
                doingitsthing = 0
                while keyboard.is_pressed('p'):
                    print('stopped')# Wait for key release
                    time.sleep(0.1)

except KeyboardInterrupt:
    print("Recording stopped by user.")

# Stop recording and clean up
picam2.stop_encoder()
picam2.stop()
picam2.close()

print(f"Video saved as {output_file}")