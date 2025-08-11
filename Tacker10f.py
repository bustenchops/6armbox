
#!/usr/bin/env python3

import time
import cv2
import numpy as np
from picamera2 import Picamera2

# width, height of frame
WIDTH, HEIGHT = 640, 480

def initialize_camera(resolution=(WIDTH, HEIGHT), fmt="BGR888"):
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(
        main={"format": fmt, "size": resolution}
    )
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)  # let exposure & white balance settle
    return picam2

def find_object_moments(frame, thresh_val=50):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
    moments = cv2.moments(mask)

    if moments["m00"] == 0:
        return None

    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])


    # define a fixed-size bounding box around the centroid
    box_size = 50
    x = max(cx - box_size // 2, 0)
    y = max(cy - box_size // 2, 0)
    w = box_size
    h = box_size

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

    frame = picam2.capture_array()
    bbox = find_object_moments(frame)

    tracker = create_kcf_tracker()
    tracker.init(frame, bbox)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter('output_moments_tracking.avi', fourcc, 30.0, (WIDTH, HEIGHT), True)

    prev_time = time.time()
    fps = 0.0

    while True:
        frame = picam2.capture_array()
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time
        fps = 0.9 * fps + 0.1 * (1.0 / dt)

        success, bbox = tracker.update(frame)

        cv2.line(frame, (WIDTH//2, 0), (WIDTH//2, HEIGHT), (0, 255, 0), 1)
        cv2.line(frame, (0, HEIGHT//2), (WIDTH, HEIGHT//2), (0, 255, 0), 1)

        if success:
            x, y, w, h = map(int, bbox)
            cx, cy = x + w//2, y + h//2

        if not success:
            new_bbox = find_object_moments(frame)
            if new_bbox:
                tracker = create_kcf_tracker()
                tracker.init(frame, new_bbox)
                bbox = new_bbox
                print("Re-initialized tracker after failure")
                success = True
            else:
                cv2.putText(frame, "Searching for object...",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 0, 255), 2)
                cv2.putText(frame, f"FPS: {fps:.2f}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                writer.write(frame)
                cv2.imshow("Moments Tracking with Border", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

        x, y, w, h = map(int, bbox)
        cx, cy = x + w//2, y + h//2
        q = determine_quadrant(cx, cy)

        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"Q{q}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        print(f"Object in quadrant {q}")

        writer.write(frame)
        cv2.imshow("Moments Tracking with Border", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    writer.release()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
