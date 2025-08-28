
#!/usr/bin/env python3

import cv2
import numpy as np
import time
import datetime
import csv
import threading
import RPi.GPIO as GPIO
from picamera2 import Picamera2

# Constants
WIDTH, HEIGHT = 640, 480
FPS = 24
HEX_RADIUS = 225
CENTER_RADIUS = 100
STATIONARY_THRESHOLD = 3.0
MIN_AREA = 500
NO_TRACKING_MARGIN = 80
LED_PIN = 2

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

# LED flashing thread control
led_thread = None
led_thread_running = False

def led_flashing():
    global led_thread_running
    while led_thread_running:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(2)

def start_led_thread():
    global led_thread, led_thread_running
    led_thread_running = True
    led_thread = threading.Thread(target=led_flashing)
    led_thread.start()

def stop_led_thread():
    global led_thread_running
    led_thread_running = False
    GPIO.output(LED_PIN, GPIO.LOW)
    if led_thread:
        led_thread.join()

def initialize_camera():
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(main={"format": "BGR888", "size": (WIDTH, HEIGHT)})
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)
    return picam2

# ... [Other functions remain unchanged: draw_zones, determine_piezone, in_center, etc.]

def main():
    base_time = datetime.datetime.now()
    sample_number = input("Enter sample number: ")
    session_number = 1

    picam2 = initialize_camera()
    print("Press spacebar to start tracking...")
    while True:
        frame = picam2.capture_array()
        cv2.putText(frame, "Press SPACE to start", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow("Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord(' '):
            break

    previous_frame = picam2.capture_array()
    tracker = None
    tracking = False
    paused = False
    last_position = None
    stationary_start = None

    video_filename = generate_filename(base_time, sample_number, session_number, "video.mp4")
    log_filename = generate_filename(base_time, sample_number, session_number, "log.csv")
    video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))
    log_file = open(log_filename, mode='w', newline='')
    log_writer = csv.writer(log_file)
    log_writer.writerow(["Frame", "Timestamp", "Piezone", "InCenter", "FPS"])
    start_led_thread()

    frame_count = 0
    prev_time = time.time()
    fps = 0.0

    while True:
        frame = picam2.capture_array()
        draw_zones(frame)
        timestamp = datetime.datetime.now()
        frame_count += 1
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time
        fps = 0.9 * fps + 0.1 * (1.0 / dt)

        if not paused:
            # [Tracking logic remains unchanged]

            if video_writer:
                video_writer.write(frame)

        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow("Tracking", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        elif key == ord('m'):
            paused = True
            print("Paused tracking and recording.")

            if video_writer:
                video_writer.release()
                video_writer = None
                print("Video file saved.")

            if log_file:
                log_file.close()
                log_file = None
                print("Log file saved.")

            stop_led_thread()

        elif key == ord('c') and paused:
            paused = False
            session_number += 1
            tracking = False
            tracker = None
            print("Resumed tracking and recording.")

            video_filename = generate_filename(base_time, sample_number, session_number, "video.mp4")
            video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))
            print(f"Started new video file: {video_filename}")

            log_filename = generate_filename(base_time, sample_number, session_number, "log.csv")
            log_file = open(log_filename, mode='w', newline='')
            log_writer = csv.writer(log_file)
            log_writer.writerow(["Frame", "Timestamp", "Piezone", "InCenter", "FPS"])
            print(f"Started new log file: {log_filename}")

            start_led_thread()

        previous_frame = frame.copy()

    if video_writer:
        video_writer.release()
    if log_file:
        log_file.close()
    stop_led_thread()
    GPIO.cleanup()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
