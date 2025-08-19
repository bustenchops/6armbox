#!/usr/bin/env python3

import time
import cv2
import numpy as np
import random
from picamera2 import Picamera2

# Frame dimensions and tracking constraints
WIDTH, HEIGHT = 640, 480
MAX_W, MAX_H = WIDTH // 2, HEIGHT // 2
BORDER = 100  # 100px no-track border

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
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:
        return None

    x, y, w, h = cv2.boundingRect(c)
    if w > MAX_W or h > MAX_H:
        return None

    # enforce the 100px border
    if x < BORDER or y < BORDER or (x + w) > (WIDTH - BORDER) \
       or (y + h) > (HEIGHT - BORDER):
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

    # Randomly choose two distinct quadrants for bonus1 & bonus2
    quads = [1, 2, 3, 4]
    bonus1_quad = random.choice(quads)
    quads.remove(bonus1_quad)
    bonus2_quad = random.choice(quads)

    # Compute safe‐region limits
    sx0, sy0 = BORDER, BORDER
    sx1, sy1 = WIDTH - BORDER, HEIGHT - BORDER

    # === BONUS ZONE 1: circle, diameter ~25px ===
    r = 12  # radius
    if bonus1_quad == 1:
        x0 = sx0 + r;    x1 = WIDTH//2 - r
        y0 = sy0 + r;    y1 = HEIGHT//2 - r
    elif bonus1_quad == 2:
        x0 = WIDTH//2 + r; x1 = sx1 - r
        y0 = sy0 + r;    y1 = HEIGHT//2 - r
    elif bonus1_quad == 3:
        x0 = sx0 + r;    x1 = WIDTH//2 - r
        y0 = HEIGHT//2 + r; y1 = sy1 - r
    else:  # quad 4
        x0 = WIDTH//2 + r; x1 = sx1 - r
        y0 = HEIGHT//2 + r; y1 = sy1 - r

    bonus1_center = (
        random.randint(int(x0), int(x1)),
        random.randint(int(y0), int(y1))
    )
    bonus1_active = True

    # === BONUS ZONE 2: square, 30×30px ===
    s = 30
    if bonus2_quad == 1:
        x0 = sx0;        x1 = WIDTH//2 - s
        y0 = sy0;        y1 = HEIGHT//2 - s
    elif bonus2_quad == 2:
        x0 = WIDTH//2;   x1 = sx1 - s
        y0 = sy0;        y1 = HEIGHT//2 - s
    elif bonus2_quad == 3:
        x0 = sx0;        x1 = WIDTH//2 - s
        y0 = HEIGHT//2;  y1 = sy1 - s
    else:  # quad 4
        x0 = WIDTH//2;   x1 = sx1 - s
        y0 = HEIGHT//2;  y1 = sy1 - s

    bonus2_tlx = random.randint(int(x0), int(x1))
    bonus2_tly = random.randint(int(y0), int(y1))
    bonus2_active = True

    # Grab an initial frame and find the object
    frame = picam2.capture_array()
    bbox = find_object_bbox(frame)
    if bbox is None:
        raise RuntimeError("No valid object found within the 100px border.")

    tracker = create_kcf_tracker()
    tracker.init(frame, bbox)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = cv2.VideoWriter('output_kcf_bonus.avi',
                             fourcc, 30.0, (WIDTH, HEIGHT), True)

    while True:
        frame = picam2.capture_array()
        success, bbox = tracker.update(frame)

        # draw no-track border
        cv2.rectangle(frame,
                      (BORDER, BORDER),
                      (WIDTH - BORDER, HEIGHT - BORDER),
                      (0, 255, 255), 2)

        # draw quadrant crosshairs
        cv2.line(frame, (WIDTH//2, 0), (WIDTH//2, HEIGHT), (0, 255, 0), 1)
        cv2.line(frame, (0, HEIGHT//2), (WIDTH, HEIGHT//2), (0, 255, 0), 1)

        if success:
            x, y, w, h = map(int, bbox)
            cx, cy = x + w//2, y + h//2
            # if drift into border, drop
            if x < BORDER or y < BORDER \
               or (x + w) > (WIDTH - BORDER) \
               or (y + h) > (HEIGHT - BORDER):
                success = False

        if not success:
            new_bbox = find_object_bbox(frame)
            if new_bbox:
                tracker = create_kcf_tracker()
                tracker.init(frame, new_bbox)
                bbox = new_bbox
                success = True
                print("Re-initialized KCF tracker after failure")
            else:
                cv2.putText(frame, "Searching for object...",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 0, 255), 2)
                writer.write(frame)
                cv2.imshow("KCF Tracking + Bonuses", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

        x, y, w, h = map(int, bbox)
        cx, cy = x + w//2, y + h//2
        q = determine_quadrant(cx, cy)

        # --- check bonus1 (circle) ---
        if bonus1_active:
            dx, dy = cx - bonus1_center[0], cy - bonus1_center[1]
            if dx*dx + dy*dy <= r*r:
                print("Entered bonus1 zone!")
                bonus1_active = False

        # --- check bonus2 (square) ---
        if bonus2_active:
            if (bonus2_tlx <= cx <= bonus2_tlx + s
               and bonus2_tly <= cy <= bonus2_tly + s):
                print("Entered bonus2 zone!")
                bonus2_active = False

        # draw the bonuses
        # circle (bonus1)
        cv2.circle(frame, bonus1_center, r, (0, 165, 255), 2)
        # square (bonus2)
        cv2.rectangle(frame,
                      (bonus2_tlx, bonus2_tly),
                      (bonus2_tlx + s, bonus2_tly + s),
                      (0, 165, 255), 2)

        # annotate tracking & quadrant
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"Q{q}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        writer.write(frame)
        cv2.imshow("KCF Tracking + Bonuses", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    writer.release()
    cv2.destroyAllWindows()
    picam2.stop()


if __name__ == "__main__":
    main()
