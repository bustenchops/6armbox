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
    # allow auto-exposure and AWB to settle
    time.sleep(2)
    return picam2

def find_initial_bbox(frame, thresh_val=50):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # invert threshold: black object → white in mask
    _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise RuntimeError("No black object detected in initial frame.")
    # pick largest contour
    c = max(contours, key=cv2.contourArea)
    return cv2.boundingRect(c)  # x, y, w, h

def create_kcf_tracker():
    # try modern and legacy APIs
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
    # set up camera
    WIDTH, HEIGHT = 640, 480
    picam2 = initialize_camera((WIDTH, HEIGHT))

    # grab first frame and detect black object
    first_frame = picam2.capture_array()
    bbox = find_initial_bbox(first_frame, thresh_val=50)

    # initialize KCF tracker
    tracker = create_kcf_tracker()
    tracker.init(first_frame, bbox)

    # set up video writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter('output.avi', fourcc, 30.0, (WIDTH, HEIGHT))

    while True:
        frame = picam2.capture_array()
        success, bbox = tracker.update(frame)

        # draw quadrant grid
        cv2.line(frame, (WIDTH//2, 0), (WIDTH//2, HEIGHT), (255, 0, 0), 1)
        cv2.line(frame, (0, HEIGHT//2), (WIDTH, HEIGHT//2), (255, 0, 0), 1)

        if success:
            x, y, w, h = map(int, bbox)
            cx, cy = x + w//2, y + h//2
            quadrant = determine_quadrant(cx, cy, WIDTH, HEIGHT)

            # annotate frame
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"Q{quadrant}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)

            print(f"Object in quadrant {quadrant}")
        else:
            cv2.putText(frame, "Tracking failure", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            print("Tracking failure detected")

        # write and display
        writer.write(frame)
        cv2.imshow("KCF Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # cleanup
    writer.release()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
