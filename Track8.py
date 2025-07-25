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
    time.sleep(2)  # let AE/AWB settle
    return picam2

def find_object_bbox(gray, thresh_val=50, max_w=None, max_h=None):
    """
    Find the largest dark object on a light background in a grayscale frame.
    Ignore detections outside size limits.
    Returns (x, y, w, h) or None.
    """
    _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # pick the largest contour
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:
        return None

    x, y, w, h = cv2.boundingRect(c)
    if (max_w and w > max_w) or (max_h and h > max_h):
        return None

    return (x, y, w, h)

def create_kcf_tracker():
    try:
        return cv2.TrackerKCF_create()
    except AttributeError:
        return cv2.legacy.TrackerKCF_create()

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
    MAX_BOX_W = WIDTH // 2
    MAX_BOX_H = HEIGHT // 2

    picam2 = initialize_camera((WIDTH, HEIGHT))
    color_frame = picam2.capture_array()
    gray = cv2.cvtColor(color_frame, cv2.COLOR_BGR2GRAY)

    # initial detection
    bbox = find_object_bbox(gray, thresh_val=50, max_w=MAX_BOX_W, max_h=MAX_BOX_H)
    if bbox is None:
        raise RuntimeError("No suitable object found in initial frame.")

    tracker = create_kcf_tracker()
    tracker.init(gray, bbox)

    # grayscale writer (isColor=False)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter('output_gray.avi', fourcc, 30.0, (WIDTH, HEIGHT), False)

    while True:
        color_frame = picam2.capture_array()
        gray = cv2.cvtColor(color_frame, cv2.COLOR_BGR2GRAY)

        success, bbox = tracker.update(gray)

        # draw quadrant grid (white lines)
        cv2.line(gray, (WIDTH//2, 0), (WIDTH//2, HEIGHT), 255, 1)
        cv2.line(gray, (0, HEIGHT//2), (WIDTH, HEIGHT//2), 255, 1)

        if not success:
            # try re-detecting when tracking fails
            new_bbox = find_object_bbox(gray, thresh_val=50, max_w=MAX_BOX_W, max_h=MAX_BOX_H)
            if new_bbox:
                tracker = create_kcf_tracker()
                tracker.init(gray, new_bbox)
                bbox = new_bbox
                print("Re-initialized tracker after failure")
                success = True
            else:
                cv2.putText(gray, "Searching...", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)
                writer.write(gray)
                cv2.imshow("Grayscale Tracking", gray)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

        x, y, w, h = map(int, bbox)
        cx, cy = x + w//2, y + h//2
        q = determine_quadrant(cx, cy, WIDTH, HEIGHT)

        # annotate
        cv2.rectangle(gray, (x, y), (x+w, y+h), 255, 2)
        cv2.circle(gray, (cx, cy), 5, 255, -1)
        cv2.putText(gray, f"Q{q}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2)
        print(f"Object in quadrant {q}")

        writer.write(gray)
        cv2.imshow("Grayscale Tracking", gray)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    writer.release()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
