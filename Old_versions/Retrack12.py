#!/usr/bin/env python3

import cv2
import numpy as np
import time
import datetime
import csv
from picamera2 import Picamera2

# Constants
WIDTH, HEIGHT = 640, 480
FPS = 24
HEX_RADIUS = 225
CENTER_RADIUS = 100
STATIONARY_THRESHOLD = 3.0
MIN_AREA = 500
NO_TRACK_ZONE_WIDTH = 80    # width of left/right no-tracking zones

def initialize_camera():
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(
        main={"format": "BGR888", "size": (WIDTH, HEIGHT)}
    )
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)
    return picam2

def draw_zones(frame):
    center = (WIDTH // 2, HEIGHT // 2)
    angle_step = 360 // 6
    for i in range(6):
        a1 = np.deg2rad(i * angle_step)
        a2 = np.deg2rad((i + 1) * angle_step)
        pt1 = center
        pt2 = (
            int(center[0] + HEX_RADIUS * np.cos(a1)),
            int(center[1] + HEX_RADIUS * np.sin(a1))
        )
        pt3 = (
            int(center[0] + HEX_RADIUS * np.cos(a2)),
            int(center[1] + HEX_RADIUS * np.sin(a2))
        )
        cv2.drawContours(frame, [np.array([pt1, pt2, pt3])], 0, (0, 255, 0), 1)
    cv2.circle(frame, center, CENTER_RADIUS, (255, 0, 0), 1)

def draw_no_tracking_areas(frame):
    overlay = frame.copy()
    # semi-transparent red fill
    cv2.rectangle(overlay, (0, 0), (NO_TRACK_ZONE_WIDTH, HEIGHT), (0, 0, 255), -1)
    cv2.rectangle(overlay,
                  (WIDTH - NO_TRACK_ZONE_WIDTH, 0),
                  (WIDTH, HEIGHT),
                  (0, 0, 255), -1)
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    # labels
    cv2.putText(frame, "NO-TRACK", (10, HEIGHT//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, "NO-TRACK", (WIDTH - NO_TRACK_ZONE_WIDTH + 10, HEIGHT//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

def determine_piezone(cx, cy):
    dx = cx - WIDTH // 2
    dy = cy - HEIGHT // 2
    angle = (np.arctan2(dy, dx) * 180 / np.pi) % 360
    return int(angle // 60) + 1

def in_center(cx, cy):
    dx = cx - WIDTH // 2
    dy = cy - HEIGHT // 2
    return dx*dx + dy*dy <= CENTER_RADIUS*CENTER_RADIUS

def create_tracker():
    try:
        return cv2.TrackerKCF_create()
    except AttributeError:
        return cv2.legacy.TrackerKCF_create()

def generate_filename(base_time, sample_number, session_number, suffix):
    timestamp = base_time.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_Sample{sample_number}_Session{session_number}_{suffix}"

def find_moving_object_bbox(current_frame, previous_frame):
    gray_cur = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    gray_prev = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray_prev, gray_cur)
    blur = cv2.GaussianBlur(diff, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 25, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    moving = [c for c in contours if cv2.contourArea(c) > MIN_AREA]
    if not moving:
        return None
    obj = max(moving, key=cv2.contourArea)
    M = cv2.moments(obj)
    if M["m00"] == 0:
        return None
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    # skip detection if centroid is in no-track zones
    if cx < NO_TRACK_ZONE_WIDTH or cx > WIDTH - NO_TRACK_ZONE_WIDTH:
        return None
    x, y, w, h = cv2.boundingRect(obj)
    return (x, y, w, h)

def main():
    base_time = datetime.datetime.now()
    sample_number = input("Enter sample number: ")
    session_number = 1

    picam2 = initialize_camera()
    print("Press spacebar to start tracking...")
    while True:
        frame = picam2.capture_array()
        cv2.putText(frame, "Press SPACE to start", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow("Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord(' '):
            break

    previous_frame = picam2.capture_array()
    tracker = None
    tracking = False
    paused = False
    last_position = None
    stationary_start = None

    video_writer = None
    log_writer = None
    log_file = None

    frame_count = 0
    prev_time = time.time()
    fps = 0.0

    while True:
        frame = picam2.capture_array()
        draw_zones(frame)
        draw_no_tracking_areas(frame)

        timestamp = datetime.datetime.now()
        frame_count += 1

        # update FPS
        now = time.time()
        dt = now - prev_time
        prev_time = now
        fps = 0.9*fps + 0.1*(1.0/dt)

        if not paused:
            # if no active tracker, try to detect and init
            if tracker is None or not tracking:
                bbox = find_moving_object_bbox(frame, previous_frame)
                if bbox:
                    tracker = create_tracker()
                    tracker.init(frame, bbox)
                    tracking = True
                    stationary_start = time.time()
                    # open new video/log only if not already open
                    if video_writer is None:
                        video_filename = generate_filename(
                            base_time, sample_number, session_number, "video.mp4")
                        log_filename = generate_filename(
                            base_time, sample_number, session_number, "log.csv")
                        video_writer = cv2.VideoWriter(
                            video_filename,
                            cv2.VideoWriter_fourcc(*'mp4v'),
                            FPS,
                            (WIDTH, HEIGHT)
                        )
                        log_file = open(
                            log_filename, mode='w', newline=''
                        )
                        log_writer = csv.writer(log_file)
                        log_writer.writerow(
                            ["Frame", "Timestamp", "Piezone", "InCenter", "FPS"]
                        )

            # update existing tracker
            if tracker is not None:
                success, bbox = tracker.update(frame)
            else:
                success = False

            zone = 0
            center = False

            if success:
                x, y, w, h = map(int, bbox)
                cx, cy = x + w//2, y + h//2
                # do not track if in no-track zones
                if cx < NO_TRACK_ZONE_WIDTH or cx > WIDTH - NO_TRACK_ZONE_WIDTH:
                    success = False

            if success:
                # valid tracking
                zone = determine_piezone(cx, cy)
                center = in_center(cx, cy)
                cv2.rectangle(frame, (x, y), (x + w, y + h),
                              (255, 0, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                cv2.putText(frame,
                            f"Zone {zone}" + (" + Center" if center else ""),
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (255, 255, 255), 2)

                # stationary check
                if last_position and (cx, cy) == last_position:
                    if time.time() - stationary_start > STATIONARY_THRESHOLD:
                        tracking = False
                        tracker = None
                        print("Object stationary too long. Reinitializing tracker.")
                else:
                    stationary_start = time.time()
                last_position = (cx, cy)
            else:
                # lost tracking or invalid zone
                tracking = False
                tracker = None
                zone = 0
                center = False
                print("Tracking lost or in no-track zone. Continuing recording...")

        # write every frame, even when tracking is lost
        if video_writer:
            video_writer.write(frame)
        if log_writer:
            log_writer.writerow([
                frame_count,
                timestamp.strftime("%H:%M:%S.%f"),
                zone,
                center,
                round(fps, 2)
            ])

        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow("Tracking", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('m'):  # pause and close files
            paused = True
            print("Paused tracking and recording.")
            if video_writer:
                video_writer.release()
                video_writer = None
            if log_file:
                log_file.close()
                log_file = None
        elif key == ord('c') and paused:  # resume, new session
            paused = False
            session_number += 1
            tracker = None
            tracking = False
            print("Resumed tracking and recording.")

        previous_frame = frame.copy()

    # teardown
    if video_writer:
        video_writer.release()
    if log_file:
        log_file.close()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
