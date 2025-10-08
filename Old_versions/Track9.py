#!/usr/bin/env python3

import time
import cv2
import numpy as np
from picamera2 import Picamera2

def initialize_camera(resolution=(640, 480), fmt="BGR888"):
    picam2 = Picamera2()
    preview_config = picam2.create_preview_configuration(
        main={"format": fmt, "size": resolution}
    )
    picam2.configure(preview_config)
    picam2.start()
    time.sleep(2)  # allow AE/AWB to settle
    return picam2

def find_object_bbox(frame, thresh_val=50, max_w=None, max_h=None):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:
        return None

    x, y, w, h = cv2.boundingRect(c)
    if (max_w and w > max_w) or (max_h and h > max_h):
        return None

    return (x, y, w, h)

def create_mosse_tracker():
    try:
        return cv2.TrackerMOSSE_create()
    except AttributeError:
        return cv2.legacy.TrackerMOSSE_create()

def determine_quadrant(cx, cy, width, height):
    if cx < width/2 and cy < height/2:
        return 1
    if cx >= width/2 and cy < height/2:
        return 2
    if cx < width/2 and cy >= height/2:
        return 3
    return 4

def main():
    WIDTH, HEIGHT = 640, 480
    MAX_W, MAX_H = WIDTH // 2, HEIGHT // 2

    picam2 = initialize_camera((WIDTH, HEIGHT))
    frame = picam2.capture_array()

    # initial detection
    bbox = find_object_bbox(frame, thresh_val=50, max_w=MAX_W, max_h=MAX_H)
    if bbox is None:
        raise RuntimeError("No suitable object found in the initial frame.")

    # initialize MOSSE on grayscale
    tracker = create_mosse_tracker()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tracker.init(gray, bbox)

    # video writer for color output
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter('output_mosse.avi', fourcc, 30.0, (WIDTH, HEIGHT), True)

    while True:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        success, bbox = tracker.update(gray)

        # draw quadrant grid on color frame
        cv2.line(frame, (WIDTH//2, 0),     (WIDTH//2, HEIGHT), (0, 255, 0), 1)
        cv2.line(frame, (0, HEIGHT//2),    (WIDTH, HEIGHT//2), (0, 255, 0), 1)

        if not success:
            # re-detect upon failure
            new_bbox = find_object_bbox(frame, thresh_val=50, max_w=MAX_W, max_h=MAX_H)
            if new_bbox:
                tracker = create_mosse_tracker()
                tracker.init(gray, new_bbox)
                bbox = new_bbox
                print("Re-initialized MOSSE tracker after failure")
                success = True
            else:
                cv2.putText(frame, "Searching for object...",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            (0, 0, 255), 2)
                writer.write(frame)
                cv2.imshow("MOSSE Tracking", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

        x, y, w, h = map(int, bbox)
        cx, cy = x + w//2, y + h//2
        q = determine_quadrant(cx, cy, WIDTH, HEIGHT)

        # annotate tracking results
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"Q{q}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        print(f"Object in quadrant {q}")

        writer.write(frame)
        cv2.imshow("MOSSE Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    writer.release()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
