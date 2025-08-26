
import time
import csv
from datetime import datetime
import cv2
import threading
import RPi.GPIO as GPIO
from picamera2 import Picamera2

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(15, GPIO.IN)
GPIO.setup(18, GPIO.OUT)

# Simulated GPIO state
simulated_gpio_15 = False

def toggle_gpio_simulation():
    global simulated_gpio_15
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord('t'):
            simulated_gpio_15 = not simulated_gpio_15
            print(f"Simulated GPIO 15 toggled to: {'HIGH' if simulated_gpio_15 else 'LOW'}")
        elif key == ord('q'):
            break
        time.sleep(0.1)

# Start simulation thread
simulation_thread = threading.Thread(target=toggle_gpio_simulation, daemon=True)
simulation_thread.start()

# Initialize camera
camera = Picamera2()
camera_config = camera.create_video_configuration(main={'size': (1920, 1080), 'format': 'XRGB8888'})
camera.configure(camera_config)

recording = False
frame_number = 0

try:
    while True:
        gpio_15_state = simulated_gpio_15 or GPIO.input(15)

        if gpio_15_state and not recording:
            # Start recording
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_camera_1.mp4"
            log_filename = f"{timestamp}_camera_1_log.csv"
            fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 encoding
            out = cv2.VideoWriter(filename, fourcc, 24.0, (1920, 1080))
            camera.start()
            GPIO.output(18, GPIO.HIGH)
            recording = True
            frame_number = 0
            log_file = open(log_filename, mode='w', newline='')
            log_writer = csv.writer(log_file)
            log_writer.writerow(["Frame Number", "Timestamp"])
            print(f"Recording started: {filename}")

        elif not gpio_15_state and recording:
            # Stop recording
            camera.stop()
            out.release()
            GPIO.output(18, GPIO.LOW)
            recording = False
            log_file.close()
            print("Recording stopped")

        if recording:
            frame = camera.capture_array()
            capture_time = datetime.now().isoformat(timespec='microseconds')
            out.write(frame)
            frame_number += 1
            log_writer.writerow([frame_number, capture_time])

        time.sleep(0.01)

except KeyboardInterrupt:
    if recording:
        camera.stop()
        out.release()
        GPIO.output(18, GPIO.LOW)
        log_file.close()
    GPIO.cleanup()
    print("Program terminated")
