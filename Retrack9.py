
import cv2
import numpy as np
import datetime
import csv
import os
from picamera2 import Picamera2

# Initialize variables
sample_number = input("Enter sample number: ")
session_number = 1
movement_threshold = 5  # pixels
tracking_lost_time = 2  # seconds
video_width, video_height = 640, 480
fps = 24

# Get current date and time
date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Initialize camera
picam2 = Picamera2()
picam2.preview_configuration.main.size = (video_width, video_height)
picam2.preview_configuration.main.format = "RGB"
picam2.preview_configuration.controls.FrameRate = fps
picam2.configure("preview")
picam2.start()

# Wait for spacebar to start recording
print("Press spacebar to start recording...")
while True:
    key = cv2.waitKey(1)
    if key == 32:  # Spacebar
        break

# Setup video writer and log file
def get_file_names():
    base_name = f"{date_str}_Sample{sample_number}_Session{session_number}"
    video_filename = f"{base_name}.mp4"
    log_filename = f"{base_name}_log.csv"
    return video_filename, log_filename

video_filename, log_filename = get_file_names()
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(video_filename, fourcc, fps, (video_width, video_height))

log_file = open(log_filename, mode='w', newline='')
log_writer = csv.writer(log_file)
log_writer.writerow(["Frame", "Timestamp", "Piezone", "Centerzone", "Tracking", "FPS"])

# Define zones
hex_center = (video_width // 2, video_height // 2)
hex_radius = 225
center_radius = 100
no_track_width = 50

# Helper functions
def draw_zones(frame):
    # Draw hexagon
    hexagon = []
    for i in range(6):
        angle = np.deg2rad(60 * i)
        x = int(hex_center[0] + hex_radius * np.cos(angle))
        y = int(hex_center[1] + hex_radius * np.sin(angle))
        hexagon.append((x, y))
    cv2.polylines(frame, [np.array(hexagon)], isClosed=True, color=(0, 255, 0), thickness=2)

    # Draw piezones
    for i in range(6):
        angle1 = np.deg2rad(60 * i)
        angle2 = np.deg2rad(60 * (i + 1))
        pt1 = hex_center
        pt2 = (int(hex_center[0] + hex_radius * np.cos(angle1)), int(hex_center[1] + hex_radius * np.sin(angle1)))
        pt3 = (int(hex_center[0] + hex_radius * np.cos(angle2)), int(hex_center[1] + hex_radius * np.sin(angle2)))
        cv2.drawContours(frame, [np.array([pt1, pt2, pt3])], 0, (0, 255, 0), 1)

    # Draw centerzone
    cv2.circle(frame, hex_center, center_radius, (0, 0, 255), 2)

    # Draw no tracking zones
    cv2.rectangle(frame, (0, 0), (no_track_width, video_height), (255, 0, 0), -1)
    cv2.rectangle(frame, (video_width - no_track_width, 0), (video_width, video_height), (255, 0, 0), -1)

# Tracking variables
tracking = False
paused = False
last_position = None
last_move_time = datetime.datetime.now()
frame_count = 0

while True:
    frame = picam2.capture_array()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")
    draw_zones(frame)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    if not tracking:
        bg = blurred
        tracking = True
        continue

    diff = cv2.absdiff(bg, blurred)
    thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    object_found = False
    for contour in contours:
        if cv2.contourArea(contour) < 500:
            continue
        M = cv2.moments(contour)
        if M["m00"] == 0:
            continue
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        if cx < no_track_width or cx > video_width - no_track_width:
            continue
        current_position = (cx, cy)
        object_found = True
        break

    if object_found:
        if last_position:
            dist = np.linalg.norm(np.array(current_position) - np.array(last_position))
            if dist < movement_threshold:
                if (datetime.datetime.now() - last_move_time).total_seconds() > tracking_lost_time:
                    tracking = False
                    piezone = 0
                    centerzone = 0
            else:
                last_move_time = datetime.datetime.now()
        last_position = current_position
        piezone = 1 + int((np.arctan2(cy - hex_center[1], cx - hex_center[0]) + np.pi) / (np.pi / 3)) % 6
        centerzone = int(np.linalg.norm(np.array(current_position) - np.array(hex_center)) < center_radius)
        print(f"Object in Piezone {piezone}, Centerzone: {bool(centerzone)}")
    else:
        piezone = 0
        centerzone = 0

    # Write frame and log
    if not paused:
        out.write(frame)
        log_writer.writerow([frame_count, timestamp, piezone, centerzone, int(tracking), fps])
        frame_count += 1

    cv2.imshow("Tracking Feed", frame)
    key = cv2.waitKey(1)
    if key == ord('q'):
        break
    elif key == ord('m'):
        paused = True
        print("Paused")
    elif key == ord('c') and paused:
        paused = False
        session_number += 1
        video_filename, log_filename = get_file_names()
        out = cv2.VideoWriter(video_filename, fourcc, fps, (video_width, video_height))
        log_file = open(log_filename, mode='w', newline='')
        log_writer = csv.writer(log_file)
        log_writer.writerow(["Frame", "Timestamp", "Piezone", "Centerzone", "Tracking", "FPS"])
        frame_count = 0
        print("Resumed")

# Cleanup
out.release()
log_file.close()
cv2.destroyAllWindows()
picam2.stop()
