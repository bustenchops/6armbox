
import time
import csv
from datetime import datetime
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(15, GPIO.IN)
GPIO.setup(18, GPIO.OUT)

# Initialize camera
camera = Picamera2()
camera.configure(camera.create_video_configuration(
    main={'size': (1920, 1080), 'format': 'XRGB8888'},
    controls={'FrameRate': 24}
))
encoder = H264Encoder()
camera.encoder = encoder

recording = False
frame_number = 0

try:
    while True:
        if GPIO.input(15) and not recording:
            # Start recording
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_camera_1.h264"
            log_filename = f"{timestamp}_camera_1_log.csv"
            output = FileOutput(filename)
            encoder.output = output
            camera.start()
            GPIO.output(18, GPIO.HIGH)
            recording = True
            frame_number = 0
            log_file = open(log_filename, mode='w', newline='')
            log_writer = csv.writer(log_file)
            log_writer.writerow(["Frame Number", "Timestamp"])
            print(f"Recording started: {filename}")

        elif not GPIO.input(15) and recording:
            # Stop recording
            camera.stop()
            GPIO.output(18, GPIO.LOW)
            recording = False
            log_file.close()
            print("Recording stopped")

        if recording:
            frame_number += 1
            log_writer.writerow([frame_number, datetime.now().isoformat()])
            time.sleep(1 / 24)  # simulate frame rate

        time.sleep(0.1)

except KeyboardInterrupt:
    if recording:
        camera.stop()
        GPIO.output(18, GPIO.LOW)
        log_file.close()
    GPIO.cleanup()
    print("Program terminated")
