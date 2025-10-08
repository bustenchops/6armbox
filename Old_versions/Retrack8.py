
import cv2
import numpy as np
import datetime
import csv
from picamera2 import Picamera2
from time import time

# Constants
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_RATE = 24
HEX_RADIUS = 225
CENTER_RADIUS = 100
NO_TRACK_ZONE_WIDTH = 50

# Initialization
now = datetime.datetime.now()
date_str = now.strftime("%Y%m%d_%H%M%S")
sample_number = input("Enter sample number: ")
session_number = 1

# Camera setup
picam2 = Picamera2()
picam2.preview_configuration.main.size = (FRAME_WIDTH, FRAME_HEIGHT)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.controls.FrameRate = FRAME_RATE
picam2.configure("preview")
picam2.start()

# Hexagon and center zone setup
def create_hexagon_mask():
    mask = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8)
    center = (FRAME_WIDTH // 2, FRAME_HEIGHT // 2)
    angle = np.pi / 3
    points = [
        (int(center[0] + HEX_RADIUS * np.cos(i * angle)),
         int(center[1] + HEX_RADIUS * np.sin(i * angle)))
        for i in range(6)
    ]
    cv2.fillConvexPoly(mask, np.array(points, np.int32), 255)
    return mask, center

hex_mask, center = create_hexagon_mask()

# No tracking zones
def in_no_track_zone(x):
    return x < NO_TRACK_ZONE_WIDTH or x > FRAME_WIDTH - NO_TRACK_ZONE_WIDTH

# File creation
def create_output_files():
    filename = f"{date_str}_Sample{sample_number}_Session{session_number}"
    video_writer = cv2.VideoWriter(f"{filename}.mp4", cv2.VideoWriter_fourcc(*'mp4v'), FRAME_RATE, (FRAME_WIDTH, FRAME_HEIGHT))
    log_file = open(f"{filename}_log.csv", mode='w', newline='')
    log_writer = csv.writer(log_file)
    log_writer.writerow(["Frame", "Timestamp", "Piezone", "Centerzone", "Tracking", "FPS"])
    return video_writer, log_file, log_writer

# Wait for spacebar to start
print("Press SPACE to start recording...")
while True:
    frame = picam2.capture_array()
    cv2.imshow("Camera", frame)
    if cv2.waitKey(1) & 0xFF == ord(' '):
        break

video_writer, log_file, log_writer = create_output_files()

tracker = cv2.TrackerKCF_create()
tracking = False
paused = False
frame_count = 0
last_move_time = time()

while True:
    start_time = time()
    piezone = 0
    centerzone = False

    frame = picam2.capture_array()
    masked_frame = cv2.bitwise_and(frame, frame, mask=hex_mask)
    gray = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)

    if not tracking:
        if 'background' not in locals():
            background = blurred
            continue
        frame_delta = cv2.absdiff(background, blurred)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 500:
                (x, y, w, h) = cv2.boundingRect(c)
                if not in_no_track_zone(x + w // 2):
                    tracker.init(frame, (x, y, w, h))
                    tracking = True
                    last_move_time = time()
    else:
        success, box = tracker.update(frame)
        if success:
            (x, y, w, h) = [int(v) for v in box]
            cx, cy = x + w // 2, y + h // 2
            if not in_no_track_zone(cx):
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                distance = np.sqrt((cx - center[0])**2 + (cy - center[1])**2)
                angle = (np.arctan2(cy - center[1], cx - center[0]) + 2 * np.pi) % (2 * np.pi)
                piezone = int(angle // (np.pi / 3)) + 1 if distance <= HEX_RADIUS else 0
                centerzone = distance <= CENTER_RADIUS
                last_move_time = time()
        else:
            if time() - last_move_time > 2:
                tracking = False
                del tracker
                tracker = cv2.TrackerKCF_create()

    # Draw overlays
    hex_overlay = np.zeros_like(frame)
    angle = np.pi / 3
    hex_points = [
        (int(center[0] + HEX_RADIUS * np.cos(i * angle)),
         int(center[1] + HEX_RADIUS * np.sin(i * angle)))
        for i in range(6)
    ]
    cv2.polylines(hex_overlay, [np.array(hex_points)], isClosed=True, color=(255, 0, 0), thickness=2)
    cv2.circle(hex_overlay, center, CENTER_RADIUS, (0, 0, 255), 2)
    frame = cv2.addWeighted(frame, 1, hex_overlay, 0.5, 0)

    if tracking:
        print(f"Piezone: {piezone}, Centerzone: {centerzone}")

    if not paused:
        video_writer.write(frame)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")
        fps = 1 / (time() - start_time)
        log_writer.writerow([frame_count, timestamp, piezone, int(centerzone), int(tracking), round(fps, 2)])
        frame_count += 1

    cv2.imshow("Camera", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break
    elif key == ord('m'):
        paused = True
        print("Paused.")
    elif key == ord('c') and paused:
        paused = False
        session_number += 1
        video_writer.release()
        log_file.close()
        video_writer, log_file, log_writer = create_output_files()
        print("Resumed.")

# Cleanup
video_writer.release()
log_file.close()
cv2.destroyAllWindows()
picam2.stop()
