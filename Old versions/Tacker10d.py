
#!/usr/bin/env python3

import time
import cv2
import numpy as np
from picamera2 import Picamera2

WIDTH, HEIGHT = 640, 480
BORDER = 100

def initialize_camera(resolution=(WIDTH, HEIGHT), fmt="BGR888"):
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(main={"format": fmt, "size": resolution})
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)
    return picam2

def find_object_moments(frame, thresh_val=50):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
    moments = cv2.moments(mask)
    if moments["m00"] == 0:
        return None
    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])
    if cx < BORDER or cy < BORDER or cx > (WIDTH - BORDER) or cy > (HEIGHT - BORDER):
        return None
    return (cx, cy)

def draw_hexagon(frame, cx, cy, size, color=(255, 0, 0), thickness=2):
    points = []
    for i in range(6):
        angle = np.deg2rad(60 * i)
        x = int(cx + size * np.cos(angle))
        y = int(cy + size * np.sin(angle))
        points.append((x, y))
    for i in range(6):
        cv2.line(frame, points[i], points[(i + 1) % 6], color, thickness)

def main():
    picam2 = initialize_camera()
    hex_size = 50
    tracking = False
    writer = None
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    prev_time = time.time()
    fps = 0.0
    tracker = None
    bbox = None

    while True:
        frame = picam2.capture_array()
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time
        fps = 0.9 * fps + 0.1 * (1.0 / dt)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('b'):
            hex_size += 10
        elif key == ord('v'):
            hex_size = max(10, hex_size - 10)
        elif key == ord('y'):
            print(f"Hexagon size confirmed: {hex_size}")
        elif key == ord('p'):
            tracking = not tracking
            if tracking:
                print("Tracking started")
                filename = input("Enter filename to save video (with .avi extension): ")
                writer = cv2.VideoWriter(filename, fourcc, 30.0, (WIDTH, HEIGHT), True)
                bbox = find_object_moments(frame)
                if bbox:
                    tracker = cv2.TrackerKCF_create()
                    x = max(bbox[0] - hex_size, 0)
                    y = max(bbox[1] - hex_size, 0)
                    w = h = hex_size * 2
                    tracker.init(frame, (x, y, w, h))
            else:
                print("Tracking stopped")
                if writer:
                    writer.release()
                    writer = None

        if tracking and tracker:
            success, box = tracker.update(frame)
            if success:
                x, y, w, h = map(int, box)
                cx, cy = x + w // 2, y + h // 2
                draw_hexagon(frame, cx, cy, hex_size)
                cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                if writer:
                    writer.write(frame)
        else:
            bbox = find_object_moments(frame)
            if bbox:
                draw_hexagon(frame, bbox[0], bbox[1], hex_size)
                cv2.putText(frame, "Adjust hexagon size with B/V, confirm with Y, start/stop with P",
                            (10, HEIGHT - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        cv2.imshow("Hexagon Tracking", frame)
        if key == ord('q'):
            break

    if writer:
        writer.release()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
