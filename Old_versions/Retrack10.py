
import cv2
import numpy as np
import csv
import time
from datetime import datetime
from picamera2 import Picamera2
import os

# Initialize camera settings
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_RATE = 24
CENTER_RADIUS = 100  # Radius for center zone (diameter 200)
HEX_RADIUS = 225     # Radius for hexagon (width/height 450)
NO_TRACKING_WIDTH = 50
MIN_MOVEMENT_THRESHOLD = 5
MOVEMENT_TIMEOUT = 2  # seconds

# Get current date and time
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
sample_number = input("Enter sample number: ")
session_number = 1

# Initialize camera
picam2 = Picamera2()
picam2.preview_configuration.main.size = (FRAME_WIDTH, FRAME_HEIGHT)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.controls.FrameRate = FRAME_RATE
picam2.configure("preview")
picam2.start()

# Wait for spacebar to start
print("Press SPACEBAR to start recording...")
while True:
    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):
        break

# Setup video writer and log file
video_filename = f"{current_time}_Sample{sample_number}_Session{session_number}.mp4"
log_filename = f"{current_time}_Sample{sample_number}_Session{session_number}_log.csv"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(video_filename, fourcc, FRAME_RATE, (FRAME_WIDTH, FRAME_HEIGHT))
log_file = open(log_filename, mode='w', newline='')
log_writer = csv.writer(log_file)
log_writer.writerow(["Frame", "Timestamp", "Piezone", "Centerzone", "Tracking", "FPS"])

# Define hexagon and piezones
center = (FRAME_WIDTH // 2, FRAME_HEIGHT // 2)
hexagon = []
for i in range(6):
    angle = np.deg2rad(60 * i)
    x = int(center[0] + HEX_RADIUS * np.cos(angle))
    y = int(center[1] + HEX_RADIUS * np.sin(angle))
    hexagon.append((x, y))

# Tracking variables
tracking = False
last_position = None
last_movement_time = time.time()
frame_count = 0
paused = False

while True:
    frame = picam2.capture_array()
    frame_count += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")

    # Draw zones
    cv2.polylines(frame, [np.array(hexagon)], isClosed=True, color=(0, 255, 0), thickness=2)
    for i in range(6):
        cv2.line(frame, center, hexagon[i], (0, 255, 0), 1)
    cv2.circle(frame, center, CENTER_RADIUS, (0, 0, 255), 2)
    cv2.rectangle(frame, (0, 0), (NO_TRACKING_WIDTH, FRAME_HEIGHT), (255, 0, 0), -1)
    cv2.rectangle(frame, (FRAME_WIDTH - NO_TRACKING_WIDTH, 0), (FRAME_WIDTH, FRAME_HEIGHT), (255, 0, 0), -1)

    # Convert to grayscale and blur
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)

    # Detect motion
    if last_position is None:
        last_frame = blurred
        out.write(frame)
        cv2.imshow("Tracking", frame)
        continue

    frame_delta = cv2.absdiff(last_frame, blurred)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
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
        if cx < NO_TRACKING_WIDTH or cx > FRAME_WIDTH - NO_TRACKING_WIDTH:
            continue
        current_position = (cx, cy)
        object_found = True
        break

    if object_found:
        tracking = True
        last_position = current_position
        last_movement_time = time.time()
    else:
        if time.time() - last_movement_time > MOVEMENT_TIMEOUT:
            tracking = False
            last_position = None

    # Determine zones
    piezone = 0
    centerzone = False
    if tracking:
        dx = last_position[0] - center[0]
        dy = last_position[1] - center[1]
        angle = (np.arctan2(dy, dx) * 180 / np.pi + 360) % 360
        piezone = int(angle // 60) + 1
        distance = np.sqrt(dx**2 + dy**2)
        centerzone = distance <= CENTER_RADIUS
        cv2.circle(frame, last_position, 10, (0, 255, 255), -1)
        print(f"Object in Piezone {piezone}, Centerzone: {'Yes' if centerzone else 'No'}")

    # Write frame and log
    out.write(frame)
    log_writer.writerow([frame_count, timestamp, piezone if tracking else 0, int(centerzone), int(tracking), FRAME_RATE])

    # Display frame
    if paused:
        cv2.putText(frame, "PAUSED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.imshow("Tracking", frame)

    # Handle key presses
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('m'):
        paused = True
        out.release()
    elif key == ord('c') and paused:
        paused = False
        session_number += 1
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        video_filename = f"{current_time}_Sample{sample_number}_Session{session_number}.mp4"
        log_filename = f"{current_time}_Sample{sample_number}_Session{session_number}_log.csv"
        out = cv2.VideoWriter(video_filename, fourcc, FRAME_RATE, (FRAME_WIDTH, FRAME_HEIGHT))
        log_file = open(log_filename, mode='w', newline='')
        log_writer = csv.writer(log_file)
        log_writer.writerow(["Frame", "Timestamp", "Piezone", "Centerzone", "Tracking", "FPS"])

    last_frame = blurred

# Cleanup
out.release()
log_file.close()
picam2.stop()
cv2.destroyAllWindows()
