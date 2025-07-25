#!/usr/bin/env python3

import time
import cv2
import numpy as np
from picamera2 import Picamera2

# width, height of frame
WIDTH, HEIGHT = 640, 480
# max object size (to filter out huge blobs)
MAX_W, MAX_H = WIDTH // 2, HEIGHT // 2
# border size we will not track inside of
BORDER = 100

def initialize_camera(resolution=(WIDTH, HEIGHT), fmt="BGR888"):
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(
        main={"format": fmt, "size": resolution}
    )
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)  # let exposure & white balance settle
    return picam2

def find_object_bbox(frame, thresh_val=50):
    """
    Threshold → find contours → pick largest
    Enforce min area, max size, and EDGE BORDER constraint.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:
        return None

    x, y, w, h = cv2.boundingRect(c)

    # size‐filter
    if w > MAX_W or h > MAX_H:
        return None

    # enforce 100px border
    if x < BORDER or y < BORDER or (x + w) > (WIDTH - BORDER) or (y + h) > (HEIGHT - BORDER):
        return None

    return (x, y, w, h)

def create_kcf_tracker():
    try:
        return cv2.TrackerKCF_create()
    except AttributeError:
        return cv2.legacy.TrackerKCF_create()

def determine_quadrant(cx, cy):
    if cx < WIDTH/2 and cy < HEIGHT/2:
        return 1
    if cx >= WIDTH/2 and cy < HEIGHT/2:
        return 2
    if cx < WIDTH/2 and cy >= HEIGHT/2:
        return 3
    return 4

def main():
    picam2 = initialize_camera()

    # grab one frame for initial detection
    frame = picam2.capture_array()
    bbox = find_object_bbox(frame)
    if bbox is None:
        raise RuntimeError("No suitable object found within the 100px border on startup.")

    # init KCF tracker
    tracker = create_kcf_tracker()
    tracker.init(frame, bbox)

    # prepare writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter('output_kcf_border.avi', fourcc, 30.0, (WIDTH, HEIGHT), True)

    while True:
        frame = picam2.capture_array()
        success, bbox = tracker.update(frame)

        # draw the “no‐track” border
        cv2.rectangle(frame,
                      (BORDER, BORDER),
                      (WIDTH - BORDER, HEIGHT - BORDER),
                      (0, 255, 255), 2)

        # draw center crosshairs
        cv2.line(frame, (WIDTH//2, 0), (WIDTH//2, HEIGHT), (0, 255, 0), 1)
        cv2.line(frame, (0, HEIGHT//2), (WIDTH, HEIGHT//2), (0, 255, 0), 1)

        if success:
            x, y, w, h = map(int, bbox)
            cx, cy = x + w//2, y + h//2

            # if tracker drifts into the forbidden border, mark as lost
            if x < BORDER or y < BORDER or (x + w) > (WIDTH - BORDER) or (y + h) > (HEIGHT - BORDER):
                success = False

        if not success:
            # try to re‐detect a valid object inside the safe area
            new_bbox = find_object_bbox(frame)
            if new_bbox:
                tracker = create_kcf_tracker()
                tracker.init(frame, new_bbox)
                bbox = new_bbox
                print("Re-initialized KCF tracker after failure")
                success = True
            else:
                cv2.putText(frame, "Searching for object...",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 0, 255), 2)
                writer.write(frame)
                cv2.imshow("KCF Tracking with Border", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

        # annotate valid track
        x, y, w, h = map(int, bbox)
        cx, cy = x + w//2, y + h//2
        q = determine_quadrant(cx, cy)

        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"Q{q}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        print(f"Object in quadrant {q}")

        writer.write(frame)
        cv2.imshow("KCF Tracking with Border", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    writer.release()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
