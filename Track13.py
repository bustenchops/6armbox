#!/usr/bin/env python3

import time
import cv2
import numpy as np
import random
import threading
from picamera2 import Picamera2

WIDTH, HEIGHT = 640, 480
MAX_W, MAX_H = WIDTH // 2, HEIGHT // 2
BORDER = 100

class FrameGrabber(threading.Thread):
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        self.frame = None
        self.running = True
        self.lock = threading.Lock()

    def run(self):
        while self.running:
            frame = self.picam2.capture_array()
            with self.lock:
                self.frame = frame

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False

def initialize_camera(resolution=(WIDTH, HEIGHT), fmt="BGR888"):
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(main={"format": fmt, "size": resolution})
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2)
    return picam2

def find_object_bbox(frame, thresh_val=50):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
    moments = cv2.moments(mask)
    if moments["m00"] == 0:
        return None

    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])

    w, h = 40, 40  # fixed size bounding box
    x, y = cx - w // 2, cy - h // 2

    if x < BORDER or y < BORDER or x + w > WIDTH - BORDER or y + h > HEIGHT - BORDER:
        return None

    return (x, y, w, h)

def create_tracker():
    try:
        return cv2.TrackerMOSSE_create()
    except AttributeError:
        return cv2.legacy.TrackerMOSSE_create()

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
    grabber = FrameGrabber(picam2)
    grabber.start()

    quads = [1, 2, 3, 4]
    bonus1_quad = random.choice(quads)
    quads.remove(bonus1_quad)
    bonus2_quad = random.choice(quads)

    sx0, sy0 = BORDER, BORDER
    sx1, sy1 = WIDTH - BORDER, HEIGHT - BORDER

    r = 12
    if bonus1_quad == 1:
        x0, x1 = sx0 + r, WIDTH // 2 - r
        y0, y1 = sy0 + r, HEIGHT // 2 - r
    elif bonus1_quad == 2:
        x0, x1 = WIDTH // 2 + r, sx1 - r
        y0, y1 = sy0 + r, HEIGHT // 2 - r
    elif bonus1_quad == 3:
        x0, x1 = sx0 + r, WIDTH // 2 - r
        y0, y1 = HEIGHT // 2 + r, sy1 - r
    else:
        x0, x1 = WIDTH // 2 + r, sx1 - r
        y0, y1 = HEIGHT // 2 + r, sy1 - r

    bonus1_center = (random.randint(int(x0), int(x1)), random.randint(int(y0), int(y1)))
    bonus1_active = True

    s = 30
    if bonus2_quad == 1:
        x0, x1 = sx0, WIDTH // 2 - s
        y0, y1 = sy0, HEIGHT // 2 - s
    elif bonus2_quad == 2:
        x0, x1 = WIDTH // 2, sx1 - s
        y0, y1 = sy0, HEIGHT // 2 - s
    elif bonus2_quad == 3:
        x0, x1 = sx0, WIDTH // 2 - s
        y0, y1 = HEIGHT // 2, sy1 - s
    else:
        x0, x1 = WIDTH // 2, sx1 - s
        y0, y1 = HEIGHT // 2, sy1 - s

    bonus2_tlx = random.randint(int(x0), int(x1))
    bonus2_tly = random.randint(int(y0), int(y1))
    bonus2_active = True

    start_time = time.time()
    last_bonus1_time = None
    last_bonus2_time = None

    while True:
        frame = grabber.get_frame()
        if frame is None:
            continue

        bbox = find_object_bbox(frame)
        if bbox is None:
            cv2.putText(frame, "Searching for object...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.imshow("Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        tracker = create_tracker()
        tracker.init(frame, bbox)

        while True:
            frame = grabber.get_frame()
            if frame is None:
                continue

            success, bbox = tracker.update(frame)
            if not success:
                break

            x, y, w, h = map(int, bbox)
            cx, cy = x + w // 2, y + h // 2
            q = determine_quadrant(cx, cy)
            print(f"Current quadrant: Q{q}")

            if bonus1_active:
                dx, dy = cx - bonus1_center[0], cy - bonus1_center[1]
                if dx * dx + dy * dy <= r * r:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    print(f"Entered bonus1 zone! Time since start: {elapsed:.2f} seconds")
                    if last_bonus1_time is not None:
                        print(f"Time since last bonus1 entry: {elapsed - last_bonus1_time:.2f} seconds")
                    last_bonus1_time = elapsed
                    bonus1_active = False

            if bonus2_active:
                if bonus2_tlx <= cx <= bonus2_tlx + s and bonus2_tly <= cy <= bonus2_tly + s:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    print(f"Entered bonus2 zone! Time since start: {elapsed:.2f} seconds")
                    if last_bonus2_time is not None:
                        print(f"Time since last bonus2 entry: {elapsed - last_bonus2_time:.2f} seconds")
                    last_bonus2_time = elapsed
                    bonus2_active = False

            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"Q{q}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.circle(frame, bonus1_center, r, (0,