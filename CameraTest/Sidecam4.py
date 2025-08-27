
import time
import csv
from datetime import datetime
import cv2
import RPi.GPIO as GPIO
from picamera2 import Picamera2

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)

# Initialize camera
camera = Picamera2()
camera_config = camera.create_video_configuration(main={'size': (1920, 1080), 'format': 'XRGB8888'})
camera.configure(camera_config)

recording = False
frame_number = 0
out = None
log_file = None
log_writer = None

camera.start()
print("Camera initialized. Press 't' to toggle recording. Press 'q' to quit.")

try:
    while True:
        key = cv2.waitKey(1) & 0xFF

        if key == ord('t'):
            if not recording:
                # Start recording
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_camera_1.mp4"
                log_filename = f"{timestamp}_camera_1_log.csv"
                fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 encoding
                out = cv2.VideoWriter(filename, fourcc, 24.0, (1920, 1080))
                GPIO.output(18, GPIO.HIGH)
                print("LED ON")
                recording = True
                frame_number = 0
                log_file = open(log_filename, mode='w', newline='')
                log_writer = csv.writer(log_file)
                log_writer.writerow(["Frame Number", "Timestamp"])
                print(f"Recording started: {filename}")
            else:
                # Stop recording
                out.release()
                GPIO.output(18, GPIO.LOW)
                print("LED OFF")
                recording = False
                log_file.close()
                print("Recording stopped")

        elif key == ord('q'):
            break

        if recording:
            frame = camera.capture_array()
            capture_time = datetime.now().isoformat(timespec='microseconds')
            out.write(frame)
            frame_number += 1
            log_writer.writerow([frame_number, capture_time])
            time.sleep(1 / 24)

except KeyboardInterrupt:
    pass
finally:
    if recording:
        out.release()
        GPIO.output(18, GPIO.LOW)
        log_file.close()
    camera.stop()
    GPIO.cleanup()
    print("Program terminated")
