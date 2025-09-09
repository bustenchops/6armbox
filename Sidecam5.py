
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from datetime import datetime
import time
import csv

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(14, GPIO.OUT)  # LED always on
GPIO.setup(15, GPIO.IN)   # Input pin
GPIO.setup(18, GPIO.OUT)  # Running LED

# Turn on LED on GPIO 14
GPIO.output(14, GPIO.HIGH)

# Ensure runningLED is initially off
GPIO.output(18, GPIO.LOW)

# Initialize camera
camera = Picamera2()
camera_config = camera.create_video_configuration(main={'size': (1920, 1080), 'format': 'XRGB8888'})
camera.configure(camera_config)
camera.framerate = 24
encoder = H264Encoder(bitrate=10000000)  # 10 Mbps

# Create log file with current date
log_filename = f"log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
with open(log_filename, "w", newline='') as log_file:
    log_writer = csv.writer(log_file)
    log_writer.writerow(["LED State", "Timestamp"])

# Variables to track state
recording = False
on_time = None

try:
    while True:
        input_state = GPIO.input(15)

        if input_state == GPIO.HIGH and not recording:
            on_time = datetime.now()
            GPIO.output(18, GPIO.HIGH)
            video_filename = f"video_{on_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
            camera.start_recording(encoder, output=video_filename)
            with open(log_filename, "a", newline='') as log_file:
                log_writer = csv.writer(log_file)
                log_writer.writerow(["ON", on_time.strftime('%Y-%m-%d %H:%M:%S')])
            recording = True

        elif input_state == GPIO.LOW and recording:
            off_time = datetime.now()
            camera.stop_recording()
            GPIO.output(18, GPIO.LOW)
            with open(log_filename, "a", newline='') as log_file:
                log_writer = csv.writer(log_file)
                log_writer.writerow(["OFF", off_time.strftime('%Y-%m-%d %H:%M:%S')])
            recording = False

        time.sleep(0.03)

except KeyboardInterrupt:
    print("Exiting program")

finally:
    camera.close()
    GPIO.cleanup()
