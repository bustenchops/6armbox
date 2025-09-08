
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
FLASHDURATION = 2
cam1 = 14
cam2 = 15
cam3 = 18
cam4 = 23
cam5 = 24
cam6 = 25

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
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(FLASHDURATION)
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
    cfg = picam2.create_preview_configuration(main={"format": "BGR888", "size": (WIDTH, HEIGHT)})
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)
    return picam2

def draw_zones(frame):
    center = (WIDTH // 2, HEIGHT // 2)
    angle_step = 360 // 6
    for i in range(6):
        angle1 = np.deg2rad(i * angle_step)
        angle2 = np.deg2rad((i + 1) * angle_step)
        pt1 = center
        pt2 = (int(center[0] + HEX_RADIUS * np.cos(angle1)), int(center[1] + HEX_RADIUS * np.sin(angle1)))
        pt3 = (int(center[0] + HEX_RADIUS * np.cos(angle2)), int(center[1] + HEX_RADIUS * np.sin(angle2)))
        cv2.drawContours(frame, [np.array([pt1, pt2, pt3])], 0, (0, 255, 0), 1)
    cv2.circle(frame, center, CENTER_RADIUS, (255, 0, 0), 1)
    cv2.rectangle(frame, (0, 0), (NO_TRACKING_MARGIN, HEIGHT), (0, 0, 255), 2)
    cv2.rectangle(frame, (WIDTH - NO_TRACKING_MARGIN, 0), (WIDTH, HEIGHT), (0, 0, 255), 2)

def determine_piezone(cx, cy):
    dx = cx - WIDTH // 2
    dy = cy - HEIGHT // 2
    angle = (np.arctan2(dy, dx) * 180 / np.pi) % 360
    return int(angle // 60) + 1

def in_center(cx, cy):
    dx = cx - WIDTH // 2
    dy = cy - HEIGHT // 2
    return dx * dx + dy * dy <= CENTER_RADIUS * CENTER_RADIUS

def create_tracker():
    try:
        return cv2.TrackerKCF_create()
    except AttributeError:
        return cv2.legacy.TrackerKCF_create()

def generate_filename(base_time, sample_number, session_number, suffix):
    timestamp = base_time.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_Sample{sample_number}_Session{session_number}_{suffix}"

def find_moving_object_bbox(current_frame, previous_frame):
    gray_current = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    gray_previous = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
    frame_diff = cv2.absdiff(gray_previous, gray_current)
    blurred = cv2.GaussianBlur(frame_diff, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 25, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    moving_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > MIN_AREA]
    if not moving_contours:
        return None
    moving_object = max(moving_contours, key=cv2.contourArea)
    moments = cv2.moments(moving_object)
    if moments["m00"] == 0:
        return None
    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])
    if cx < NO_TRACKING_MARGIN or cx > WIDTH - NO_TRACKING_MARGIN:
        return None
    x, y, w, h = cv2.boundingRect(moving_object)
    return (x, y, w, h)

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
    log_writer.writerow(["Frame", "Timestamp", "Piezone", "InCenter", "FPS", "Camera"])
    start_led_thread()

    frame_count = 0
    prev_time = time.time()
    fps = 0.0
    cameratriggered = 0

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
            if tracker is None or not tracking:
                bbox = find_moving_object_bbox(frame, previous_frame)
                if bbox:
                    tracker = create_tracker()
                    tracker.init(frame, bbox)
                    tracking = True
                    stationary_start = time.time()

            if tracker is not None:
                success, bbox = tracker.update(frame)
            else:
                success = False

            if success:
                x, y, w, h = map(int, bbox)
                cx, cy = x + w // 2, y + h // 2
                zone = determine_piezone(cx, cy)
                center = in_center(cx, cy)
                print(f"Object in piezone {zone}" + (" and centerzone" if center else ""))
                if center:
                    GPIO.output(cam1,GPIO.LOW)
                    GPIO.output(cam2,GPIO.LOW)
                    GPIO.output(cam3,GPIO.LOW)
                    GPIO.output(cam4,GPIO.LOW)
                    GPIO.output(cam5,GPIO.LOW)
                    GPIO.output(cam6,GPIO.LOW)
                    cameratriggered = 0
                    print('no camera on')
                else:
                    if zone == 1:
                        GPIO.output(cam1, GPIO.HIGH)
                        GPIO.output(cam2, GPIO.LOW)
                        GPIO.output(cam3, GPIO.LOW)
                        GPIO.output(cam4, GPIO.LOW)
                        GPIO.output(cam5, GPIO.LOW)
                        GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 1
                        print('GPIO ', cam1, ' triggered')
                    if zone == 2:
                        GPIO.output(cam1, GPIO.LOW)
                        GPIO.output(cam2, GPIO.HIGH)
                        GPIO.output(cam3, GPIO.LOW)
                        GPIO.output(cam4, GPIO.LOW)
                        GPIO.output(cam5, GPIO.LOW)
                        GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 2
                        print('GPIO ', cam2, ' triggered')
                    if zone == 3:
                        GPIO.output(cam1, GPIO.LOW)
                        GPIO.output(cam2, GPIO.LOW)
                        GPIO.output(cam3, GPIO.HIGH)
                        GPIO.output(cam4, GPIO.LOW)
                        GPIO.output(cam5, GPIO.LOW)
                        GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 3
                        print('GPIO ', cam3, ' triggered')
                    if zone == 4:
                        GPIO.output(cam1, GPIO.LOW)
                        GPIO.output(cam2, GPIO.LOW)
                        GPIO.output(cam3, GPIO.LOW)
                        GPIO.output(cam4, GPIO.HIGH)
                        GPIO.output(cam5, GPIO.LOW)
                        GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 4
                        print('GPIO ', cam4, ' triggered')
                    if zone == 5:
                        GPIO.output(cam1, GPIO.LOW)
                        GPIO.output(cam2, GPIO.LOW)
                        GPIO.output(cam3, GPIO.LOW)
                        GPIO.output(cam4, GPIO.LOW)
                        GPIO.output(cam5, GPIO.HIGH)
                        GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 5
                        print('GPIO ', cam5, ' triggered')
                    if zone == 6:
                        GPIO.output(cam1, GPIO.LOW)
                        GPIO.output(cam2, GPIO.LOW)
                        GPIO.output(cam3, GPIO.LOW)
                        GPIO.output(cam4, GPIO.LOW)
                        GPIO.output(cam5, GPIO.LOW)
                        GPIO.output(cam6, GPIO.HIGH)
                        cameratriggered = 6
                        print('GPIO ', cam6, ' triggered')


                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                cv2.putText(frame, f"Zone {zone}" + (" + Center" if center else ""), (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

                if last_position and (cx, cy) == last_position:
                    if time.time() - stationary_start > STATIONARY_THRESHOLD:
                        tracking = False
                        tracker = None
                        print("Object stationary too long. Reinitializing tracker.")
                else:
                    stationary_start = time.time()
                last_position = (cx, cy)

                log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), zone, center, round(fps, 2), cameratriggered])
            else:
                tracking = False
                tracker = None
                print("Tracking lost. Reinitializing...")
                log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), 0, False, round(fps, 2), cameratriggered])

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
