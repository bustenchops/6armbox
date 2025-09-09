import RPi.GPIO as GPIO
from picamera2 import Picamera2
from datetime import datetime
import time
import csv

# GPIO pin assignments
POWER_LED_PIN    = 14
INPUT_PIN        = 15
RECORD_LED_PIN   = 18

# State variables
recording = False
on_time   = None

# Prepare CSV log
log_filename = f"log_{datetime.now():%Y-%m-%d}.csv"
with open(log_filename, "w", newline='') as log_file:
    csv.writer(log_file).writerow(["LED State", "Timestamp"])

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

def start_record(channel):
    """Callback on rising edge: begin recording if not already."""
    global recording, on_time
    if not recording:
        on_time = datetime.now()
        GPIO.output(RECORD_LED_PIN, GPIO.HIGH)
        filename = f"video_{on_time:%Y-%m-%d_%H-%M-%S}.mp4"
        camera.start_recording(output=filename)
        log_event("ON", on_time)
        recording = True
        print(f"Recording started: {filename}")

def stop_record(channel):
    """Callback on falling edge: stop recording if active."""
    global recording
    if recording:
        off_time = datetime.now()
        camera.stop_recording()
        GPIO.output(RECORD_LED_PIN, GPIO.LOW)
        log_event("OFF", off_time)
        recording = False
        print(f"Recording stopped at {off_time:%Y-%m-%d %H:%M:%S}")

# Attach edge callbacks with debounce
GPIO.add_event_detect(INPUT_PIN, GPIO.RISING,  callback=start_record, bouncetime=100)
GPIO.add_event_detect(INPUT_PIN, GPIO.FALLING, callback=stop_record,  bouncetime=100)

try:
    print("Ready. Waiting for button presses to start/stop recording.")
    # Idle loop; callbacks handle everything
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nInterrupted by user; exiting.")

finally:
    camera.close()
    GPIO.cleanup()
