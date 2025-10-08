from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from datetime import datetime
import csv
import os
import time

# State variables
recording = False
on_time = None
lens_pos = 6

# Prepare CSV log
log_filename = f"log_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
file_exists = os.path.exists(log_filename)
with open(log_filename, "a", newline='') as log_file:
    writer = csv.writer(log_file)
    if not file_exists:
        writer.writerow(["LED State", "Timestamp"])

# Initialize camera
camera = Picamera2()
video_config = camera.create_video_configuration(main={'size': (1920, 1080)})
camera.configure(video_config)
camera.framerate = 25
camera.set_controls({
    "AfMode": 0,
    "LensPosition": lens_pos
})
encoder = H264Encoder(bitrate=10000000)

def log_event(state: str, timestamp: datetime):
    with open(log_filename, "a", newline='') as log_file:
        csv.writer(log_file).writerow([state, timestamp.strftime('%Y-%m-%d %H_%M_%S.%f')])

def start_record(timestamp: datetime):
    global recording, on_time
    on_time = timestamp
    filename = f"video_{on_time:%Y-%m-%d_%H-%M-%S.%f}.h264"
    try:
        camera.start_recording(encoder, output=filename)
        log_event("ON", on_time)
        recording = True
        print(f"Recording started: {filename}")
    except Exception as e:
        print(f"Error starting recording: {e}")

def stop_record(timestamp: datetime):
    global recording
    try:
        camera.stop_recording()
        log_event("OFF", timestamp)
        recording = False
        print(f"Recording stopped at {timestamp:%Y-%m-%d %H:%M:%S.%f}")
    except Exception as e:
        print(f"Error stopping recording: {e}")

# Start recording immediately
print("Starting recording automatically...")
camera.start()
start_record(datetime.now())

try:
    while True:
        time.sleep(0.1)  # Keep the program alive

except KeyboardInterrupt:
    print("Interrupted by user.")

finally:
    if recording:
        stop_record(datetime.now())
    camera.close()
    print("Program exited.")
