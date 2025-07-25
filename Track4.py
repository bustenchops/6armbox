import time
import cv2
import numpy as np
from picamera2 import Picamera2

def main():
    # Camera setup
    WIDTH, HEIGHT = 640, 480
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"format": "XRGB8888", "size": (WIDTH, HEIGHT)}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(2)  # let auto‐exposure/white balance settle

    # Grab first frame & detect the black object on white background
    frame = picam2.capture_array()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        print("No object detected. Exiting.")
        picam2.stop()
        return
    # Use the largest contour as our object
    c = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)
    init_bbox = (x, y, w, h)

    # Initialize KCF tracker
    tracker = cv2.legacy.TrackerKCF_create()
    tracker.init(frame, init_bbox)

    # Video writer for recording
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('tracked_output.avi', fourcc, 20.0, (WIDTH, HEIGHT))

    # Main loop
    print("Tracking started. Press 'q' to quit.")
    while True:
        raw = picam2.capture_array()
        img = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

        success, bbox = tracker.update(img)
        if success:
            x, y, w, h = map(int, bbox)
            cx = x + w / 2

            # Determine left vs right
            position = "Left" if cx < WIDTH / 2 else "Right"
            print(position, flush=True)

            # Overlay box and status
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                img, position, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
            )
        else:
            cv2.putText(
                img, "Tracking failure", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
            )

        # Record and display
        out.write(img)
        cv2.imshow("KCF Tracking", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    out.release()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
