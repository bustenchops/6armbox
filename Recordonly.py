
#!/usr/bin/env python3

import cv2
import numpy as np
import time
import datetime
import csv
import threading
import RPi.GPIO as GPIO
from picamera2 import Picamera2, Preview

# Constants
WIDTH, HEIGHT = 640, 480
FPS = 24
HEX_RADIUS = 225
CENTER_RADIUS = 30
LED_PIN = 2
FLASHDURATION = 2
cam1 = 14
cam2 = 15
cam3 = 18
cam4 = 23
cam5 = 24
cam6 = 25
lens_pos = 0

zone = 99
center = 66

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(cam1, GPIO.OUT)
GPIO.setup(cam2, GPIO.OUT)
GPIO.setup(cam3, GPIO.OUT)
GPIO.setup(cam4, GPIO.OUT)
GPIO.setup(cam5, GPIO.OUT)
GPIO.setup(cam6, GPIO.OUT)

GPIO.output(cam1, GPIO.LOW)
GPIO.output(cam2, GPIO.LOW)
GPIO.output(cam3, GPIO.LOW)
GPIO.output(cam4, GPIO.LOW)
GPIO.output(cam5, GPIO.LOW)
GPIO.output(cam6, GPIO.LOW)

# LED flashing thread control
led_thread = None
led_thread_running = False

def led_flashing():
    global led_thread_running
    while led_thread_running:
        zone = 1
        log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), zone, center, round(fps, 2), cameratriggered])
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(FLASHDURATION)
        zone = 0
        log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), zone, center, round(fps, 2), cameratriggered])
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(FLASHDURATION)

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
    picam2.start_preview(Preview.NULL)
    cfg = picam2.create_preview_configuration(main={"format": "BGR888", "size": (WIDTH, HEIGHT)})
    picam2.configure(cfg)
    picam2.set_controls({
        "AfMode": 0,
        "LensPosition": lens_pos
    })
    picam2.start()
    time.sleep(2)
    return picam2

def generate_filename(base_time, sample_number, session_number, suffix):
    timestamp = base_time.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_Sample{sample_number}_Session{session_number}_{suffix}"

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


    paused = False

    video_filename = generate_filename(base_time, sample_number, session_number, "video.mp4")
    log_filename = generate_filename(base_time, sample_number, session_number, "log.csv")
    video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))
    log_file = open(log_filename, mode='w', newline='')
    log_writer = csv.writer(log_file)
    log_writer.writerow(["Frame", "Timestamp", "LED state", "InCenter", "FPS", "Camera"])
    start_led_thread()
    timestamp = datetime.datetime.now()
    cameratriggered = 7007
    GPIO.output(cam1, GPIO.HIGH)
    GPIO.output(cam2, GPIO.HIGH)
    GPIO.output(cam3, GPIO.HIGH)
    GPIO.output(cam4, GPIO.HIGH)
    GPIO.output(cam5, GPIO.HIGH)
    GPIO.output(cam6, GPIO.HIGH)
    frame_count = 0
    fps = 0.0
    log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), zone, center, round(fps, 2), cameratriggered])
    prev_time = time.time()

    cameratriggered = 0

    while True:
        frame = picam2.capture_array()

        timestamp = datetime.datetime.now()
        frame_count += 1
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time
        fps = 0.9 * fps + 0.1 * (1.0 / dt)

        if not paused:
            cameratriggered = 0
            log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), zone, center, round(fps, 2), cameratriggered])

            if video_writer:
                video_writer.write(frame)

        cv2.imshow("Tracking", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        elif key == ord('m'):
            paused = True
            print("Paused tracking and recording.")

            # Stop and save current video
            if video_writer:
                video_writer.release()
                video_writer = None
                print("Video file saved.")

            # Close current log file
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

            # Start a new video file
            video_filename = generate_filename(base_time, sample_number, session_number, "video.mp4")
            video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))
            print(f"Started new video file: {video_filename}")

            # Start a new log file
            log_filename = generate_filename(base_time, sample_number, session_number, "log.csv")
            log_file = open(log_filename, mode='w', newline='')
            log_writer = csv.writer(log_file)
            log_writer.writerow(["Frame", "Timestamp", "LEDS State", "InCenter", "FPS", "Camera"])
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
