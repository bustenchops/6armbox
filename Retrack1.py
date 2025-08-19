
#!/usr/bin/env python3

import cv2
import numpy as np
import time
import datetime
import csv
import os
from picamera2 import Picamera2

# Constants
WIDTH, HEIGHT = 640, 480
FPS = 24
HEX_RADIUS = 225
CENTER_RADIUS = 100
STATIONARY_THRESHOLD = 3.0  # seconds
BOX_SIZE = 50

# Initialize camera
def initialize_camera():
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(main={"format": "BGR888", "size": (WIDTH, HEIGHT)})
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)
    return picam2

# Create hexagon and piezones
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

# Determine piezone
def determine_piezone(cx, cy):
    dx = cx - WIDTH // 2
    dy = cy - HEIGHT // 2
    angle = (np.arctan2(dy, dx) * 180 / np.pi) % 360
    zone = int(angle // 60) + 1
    return zone

# Check if in center zone
def in_center(cx, cy):
    dx = cx - WIDTH // 2
    dy = cy - HEIGHT // 2
    return dx * dx + dy * dy <= CENTER_RADIUS * CENTER_RADIUS

# Create tracker
def create_tracker():
    try:
        return cv2.TrackerKCF_create()
    except AttributeError:
        return cv2.legacy.TrackerKCF_create()

# Generate filename
def generate_filename(base_time, sample_number, session_number, suffix):
    timestamp = base_time.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_Sample{sample_number}_Session{session_number}_{suffix}"

# Main function
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

    tracker = None
    tracking = False
    paused = False
    last_position = None
    stationary_start = None
    video_writer = None
    log_writer = None
    log_file = None
    frame_count = 0

    while True:
        frame = picam2.capture_array()
        draw_zones(frame)
        timestamp = datetime.datetime.now()
        frame_count += 1

        if not paused:
            if tracker is None or not tracking:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                _, _, _, max_loc = cv2.minMaxLoc(blurred)
                cx, cy = max_loc
                x = max(0, min(cx - BOX_SIZE // 2, WIDTH - BOX_SIZE))
                y = max(0, min(cy - BOX_SIZE // 2, HEIGHT - BOX_SIZE))
                bbox = (x, y, BOX_SIZE, BOX_SIZE)
                tracker = create_tracker()
                tracker.init(frame, bbox)
                tracking = True
                stationary_start = time.time()

                # Start new video and log
                video_filename = generate_filename(base_time, sample_number, session_number, "video.mp4")
                log_filename = generate_filename(base_time, sample_number, session_number, "log.csv")
                video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))
                log_file = open(log_filename, mode='w', newline='')
                log_writer = csv.writer(log_file)
                log_writer.writerow(["Frame", "Timestamp", "Piezone", "InCenter"])

            success, bbox = tracker.update(frame)
            if success:
                x, y, w, h = map(int, bbox)
                cx, cy = x + w // 2, y + h // 2
                zone = determine_piezone(cx, cy)
                center = in_center(cx, cy)
                print(f"Object in piezone {zone}" + (" and centerzone" if center else ""))
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

                if video_writer:
                    video_writer.write(frame)
                if log_writer:
                    log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), zone, center])
            else:
                tracking = False
                tracker = None
                print("Tracking lost. Reinitializing...")

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
            if log_file:
                log_file.close()
                log_file = None
        elif key == ord('c') and paused:
            paused = False
            session_number += 1
            tracking = False
            tracker = None
            print("Resumed tracking and recording.")

    if video_writer:
        video_writer.release()
    if log_file:
        log_file.close()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
