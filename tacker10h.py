
#!/usr/bin/env python3

import time
import cv2
import numpy as np
from picamera2 import Picamera2

# Frame dimensions
WIDTH, HEIGHT = 640, 480

def initialize_camera(resolution=(WIDTH, HEIGHT), fmt="BGR888"):
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(
        main={"format": fmt, "size": resolution}
    )
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)  # Let exposure & white balance settle
    return picam2

def find_moving_object_bbox(current_frame, previous_frame, min_area=500):
    gray_current = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    gray_previous = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)

    frame_diff = cv2.absdiff(gray_previous, gray_current)
    blurred = cv2.GaussianBlur(frame_diff, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 25, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    moving_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

    if not moving_contours:
        return None

    moving_object = max(moving_contours, key=cv2.contourArea)
    moments = cv2.moments(moving_object)

    if moments["m00"] == 0:
        return None

    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])

    x, y, w, h = cv2.boundingRect(moving_object)
    return (x, y, w, h)

def create_kcf_tracker():
    try:
        return cv2.TrackerKCF_create()
    except AttributeError:
        return cv2.legacy.TrackerKCF_create()

def determine_quadrant(cx, cy):
    if cx < WIDTH / 2 and cy < HEIGHT / 2:
        return 1
    if cx >= WIDTH / 2 and cy < HEIGHT / 2:
        return 2
    if cx < WIDTH / 2 and cy >= HEIGHT / 2:
        return 3
    return 4

def main():
    picam2 = initialize_camera()
    previous_frame = picam2.capture_array()
    bbox = None

    # Wait until motion is detected
    while bbox is None:
        current_frame = picam2.capture_array()
        bbox = find_moving_object_bbox(current_frame, previous_frame)
        previous_frame = current_frame.copy()
        cv2.putText(current_frame, "Waiting for motion...", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow("Initializing Tracker", current_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            picam2.stop()
            cv2.destroyAllWindows()
            return

    tracker = create_kcf_tracker()
    tracker.init(current_frame, bbox)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter('output_moments_tracking.avi', fourcc, 24.0, (WIDTH, HEIGHT), True)

    prev_time = time.time()
    fps = 0.0

    while True:
        frame = picam2.capture_array()
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time
        fps = 0.9 * fps + 0.1 * (1.0 / dt)

        success, bbox = tracker.update(frame)

        cv2.line(frame, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), (0, 255, 0), 1)
        cv2.line(frame, (0, HEIGHT // 2), (WIDTH, HEIGHT // 2), (0, 255, 0), 1)

        if not success:
            new_bbox = find_moving_object_bbox(frame, previous_frame)
            if new_bbox:
                tracker = create_kcf_tracker()
                tracker.init(frame, new_bbox)
                bbox = new_bbox
                print("Re-initialized tracker after loss")
                success = True
            else:
                cv2.putText(frame, "Searching for moving object...", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        if success:
            x, y, w, h = map(int, bbox)
            cx, cy = x + w // 2, y + h // 2
            q = determine_quadrant(cx, cy)

            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"Q{q}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            print(f"Object in quadrant {q}")

        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        writer.write(frame)
        cv2.imshow("Motion Tracking", frame)

        previous_frame = frame.copy()

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    writer.release()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
