
import cv2
import time
import datetime
import csv
from picamera2 import Picamera2

# Constants
WIDTH, HEIGHT = 1640, 1232
FPS = 24
lens_pos = 0

# Initialize camera
def initialize_camera():
    picam2 = Picamera2()
    cfg = picam2.create_preview_configuration(main={"format": "BGR888", "size": (WIDTH, HEIGHT)})
    picam2.configure(cfg)
    picam2.set_controls({
        "AfMode": 0,
        "LensPosition": lens_pos
    })
    picam2.start()
    time.sleep(2)
    return picam2

# Generate filename with timestamp
def generate_filename():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}"

# Main function
def main():
    picam2 = initialize_camera()
    base_filename = generate_filename()
    video_filename = f"{base_filename}_video.mp4"
    log_filename = f"{base_filename}_log.csv"

    video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))

    # Open CSV file for logging timestamps
    with open(log_filename, mode='w', newline='') as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(["Frame Number", "Timestamp"])

        print("Recording video. Press 'q' to stop.")
        frame_count = 0
        while True:
            frame = picam2.capture_array()
            video_writer.write(frame)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            log_writer.writerow([frame_count, timestamp])
            frame_count += 1

            cv2.imshow("Video Capture", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    video_writer.release()
    cv2.destroyAllWindows()
    picam2.stop()
    print(f"Video saved as {video_filename}")
    print(f"Log saved as {log_filename}")

if __name__ == "__main__":
    main()
