
import RPi.GPIO as GPIO
from picamera2 import Picamera2
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
log_filename = f"log_{datetime.now():%Y-%m-%d}.csv"
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
    main={'size': (1920, 1080), 'format': 'XRGB8888'}
)
camera.configure(video_config)
camera.framerate = 24

def log_event(state: str, timestamp: datetime):
    """Append an ON/OFF event to the CSV log."""
    with open(log_filename, "a", newline='') as log_file:
        csv.writer(log_file).writerow([state, timestamp.strftime('%Y-%m-%d %H:%M:%S')])

def start_record(timestamp: datetime):
    """Start recording."""
    global
