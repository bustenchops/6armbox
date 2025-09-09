
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from datetime import datetime
import time
import csv
import os

# GPIO pin assignments
POWER_LED_PIN    = 14
INPUT_PIN        = 15
RECORD_LED_PIN   = 18

# State variables
recording = False
on_time   = None

# Prepare CSV log
log_filename = f"log_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv"
file_exists = os.path.exists(log_filename)
with open(log_filename, "a", newline='') as log_file:
    writer = csv.writer(log_file)
    if not file_exists:
        writer.writerow(["LED State", "Timestamp"])

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(POWER_LED_PIN,  GPIO.OUT)
GPIO.setup(RECORD_LED_PIN, GPIO.OUT)
GPIO.setup(INPUT_PIN,      GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Turn on the “power” LED, ensure recording LED is off
GPIO.output(POWER_LED_PIN,  GPIO.HIGH)
GPIO.output(RECORD_LED_PIN, GPIO.LOW)

# Initialize camera
camera = Picamera2()
video_config = camera.create_video_configuration(
    main={'size': (1920, 1080), 'format': 'YUV420'}
)
camera.configure(video_config)
camera.framerate = 24
encoder = H264Encoder(bitrate=10000000)  # 10 Mbps

def log_event(state: str, timestamp: datetime):
    """Append an ON/OFF event to the CSV log."""
    with open(log_filename, "a", newline='') as log_file:
        csv.writer(log_file).writerow([state, timestamp.strftime('%Y-%m-%d %H:%M:%S')])

def start_record(timestamp: datetime):
    """Start recording."""
    global recording, on_time
    on_time = timestamp
    GPIO.output(RECORD_LED_PIN, GPIO.HIGH)
    filename = f"video_{on_time:%Y-%m-%d_%H-%M-%S}.mp4"
    try:
        camera.start_recording(encoder, output=filename)
        log_event("ON", on_time)
        recording = True
        print(f"Recording started: {filename}")
    except Exception as e:
        print(f"Error starting recording: {e}")

def stop_record(timestamp: datetime):
    """Stop recording."""
    global recording
    try:
        camera.stop_recording()
        GPIO.output(RECORD_LED_PIN, GPIO.LOW)
        log_event("OFF", timestamp)
        recording = False
        print(f"Recording stopped at {timestamp:%Y-%m-%d %H:%M:%S}")
    except Exception as e:
        print(f"Error stopping recording: {e}")

def handle_input_change(channel):
    """Unified callback for both rising and falling edges."""
    timestamp = datetime.now()
    if GPIO.input(INPUT_PIN):  # HIGH = Rising edge
        if not recording:
            start_record(timestamp)
    else:  # LOW = Falling edge
        if recording:
            stop_record(timestamp)

# Attach unified edge callback
GPIO.add_event_detect(INPUT_PIN, GPIO.BOTH, callback=handle_input_change, bouncetime=100)

try:
    print("Ready. Waiting for button presses to start/stop recording.")
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nInterrupted by user; exiting.")

finally:
    camera.stop_recording()
    camera.close()
    GPIO.cleanup()
