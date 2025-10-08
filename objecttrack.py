
#!/usr/bin/env python3

import cv2
import numpy as np
import time
import datetime
import csv
import threading
import RPi.GPIO as GPIO
from picamera2 import Picamera2, Preview
from tflite_runtime.interpreter import Interpreter
import re

# Constants
WIDTH, HEIGHT = 640, 480
FPS = 24
HEX_RADIUS = 225
CENTER_RADIUS = 30

xcenter = 0
ycenter = 0

LED_PIN = 2
FLASHDURATION = 2
cam1 = 14
cam2 = 15
cam3 = 18
cam4 = 23
cam5 = 24
cam6 = 25
lens_pos = 0

CROP_WIDTH = 480
RESIZE_DIM = (320, 320)

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(cam1, GPIO.OUT)
GPIO.setup(cam2, GPIO.OUT)
GPIO.setup(cam3, GPIO.OUT)
GPIO.setup(cam4, GPIO.OUT)
GPIO.setup(cam5, GPIO.OUT)
GPIO.setup(cam6, GPIO.OUT)

GPIO.output(cam1, GPIO.LOW)
GPIO.output(cam2, GPIO.LOW)
GPIO.output(cam3, GPIO.LOW)
GPIO.output(cam4, GPIO.LOW)
GPIO.output(cam5, GPIO.LOW)
GPIO.output(cam6, GPIO.LOW)

# LED flashing thread control
led_thread = None
led_thread_running = False

def load_labels(path='labels.txt'):
    """Loads the labels file. Supports files with or without index numbers."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        labels = {}
        for row_number, content in enumerate(lines):
            pair = re.split(r'[:\s]+', content.strip(), maxsplit=1)
            if len(pair) == 2 and pair[0].strip().isdigit():
                labels[int(pair[0])] = pair[1].strip()
            else:
                labels[row_number] = pair[0].strip()
    return labels

def set_input_tensor(interpreter, image):
    """Sets the input tensor."""
    tensor_index = interpreter.get_input_details()[0]['index']
    input_tensor = interpreter.tensor(tensor_index)()[0]
    input_tensor[:, :] = np.expand_dims((image - 255) / 255, axis=0)


def get_output_tensor(interpreter, index):
    """Returns the output tensor at the given index."""
    output_details = interpreter.get_output_details()[index]
    tensor = np.squeeze(interpreter.get_tensor(output_details['index']))
    return tensor

def detect_objects(interpreter, image, threshold):
    """Returns a list of detection results, each a dictionary of object info."""
    set_input_tensor(interpreter, image)
    interpreter.invoke()
    # Get all output details
    boxes = get_output_tensor(interpreter, 0)
    classes = get_output_tensor(interpreter, 1)
    scores = get_output_tensor(interpreter, 2)
    count = int(get_output_tensor(interpreter, 3))

    results = []
    for i in range(count):
        if scores[i] >= threshold:
            result = {
                'bounding_box': boxes[i],
                'class_id': classes[i],
                'score': scores[i]
            }
            results.append(result)
    return results

def led_flashing():
    global led_thread_running
    while led_thread_running:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(FLASHDURATION)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(FLASHDURATION)

def start_led_thread():
    global led_thread, led_thread_running
    led_thread_running = True
    led_thread = threading.Thread(target=led_flashing)
    led_thread.start()

def stop_led_thread():
    global led_thread_running
    led_thread_running = False
    GPIO.output(LED_PIN, GPIO.LOW)
    if led_thread:
        led_thread.join()

def initialize_camera():
    picam2 = Picamera2()
    picam2.start_preview(Preview.NULL)
    cfg = picam2.create_preview_configuration(main={"format": "BGR888", "size": (WIDTH, HEIGHT)})
    picam2.configure(cfg)
    picam2.set_controls({
        "AfMode": 0,
        "LensPosition": lens_pos
    })
    picam2.start()
    time.sleep(2)
    return picam2

def draw_zones(frame):
    center = (WIDTH // 2, HEIGHT // 2)
    angle_step = 360 // 6
    for i in range(6):
        angle1 = np.deg2rad(i * angle_step)
        angle2 = np.deg2rad((i + 1) * angle_step)
        pt1 = center
        pt2 = (int(center[0] + HEX_RADIUS * np.cos(angle1)), int(center[1] + HEX_RADIUS * np.sin(angle1)))
        pt3 = (int(center[0] + HEX_RADIUS * np.cos(angle2)), int(center[1] + HEX_RADIUS * np.sin(angle2)))
        cv2.drawContours(frame, [np.array([pt1, pt2, pt3])], 0, (0, 255, 0), 1)
    cv2.circle(frame, center, CENTER_RADIUS, (255, 0, 0), 1)

def determine_piezone(cx, cy):
    dx = cx - WIDTH // 2
    dy = cy - HEIGHT // 2
    angle = (np.arctan2(dy, dx) * 180 / np.pi) % 360
    return int(angle // 60) + 1

def in_center(cx, cy):
    dx = cx - WIDTH // 2
    dy = cy - HEIGHT // 2
    return dx * dx + dy * dy <= CENTER_RADIUS * CENTER_RADIUS


def generate_filename(base_time, sample_number, session_number, suffix):
    timestamp = base_time.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_Sample{sample_number}_Session{session_number}_{suffix}"



def main():
    base_time = datetime.datetime.now()
    sample_number = input("Enter sample number: ")
    session_number = 1

    labels = load_labels()
    interpreter = Interpreter('detect.tflite')
    interpreter.allocate_tensors()
    _, input_height, input_width, _ = interpreter.get_input_details()[0]['shape']

    picam2 = initialize_camera()
    print("Press spacebar to start tracking...")
    while True:
        frame = picam2.capture_array()
        cv2.putText(frame, "Press SPACE to start", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow("Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord(' '):
            break


    paused = False

    video_filename = generate_filename(base_time, sample_number, session_number, "video.mp4")
    log_filename = generate_filename(base_time, sample_number, session_number, "log.csv")
    video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))
    log_file = open(log_filename, mode='w', newline='')
    log_writer = csv.writer(log_file)
    log_writer.writerow(["Frame", "Timestamp", "Piezone", "InCenter", "FPS", "Camera"])
    start_led_thread()

    frame_count = 0
    prev_time = time.time()
    fps = 0.0
    cameratriggered = 0

    while True:
        frame = picam2.capture_array()

        cropped_frame = frame[:, 80:560]
        resized_frame = cv2.resize(cropped_frame, RESIZE_DIM)
        res = detect_objects(interpreter, resized_frame, 0.8)

        draw_zones(resized_frame)
        timestamp = datetime.datetime.now()
        frame_count += 1
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time
        fps = 0.9 * fps + 0.1 * (1.0 / dt)

        for result in res:
            ymin, xmin, ymax, xmax = result['bounding_box']
            xmin = int(max(1, xmin * WIDTH))
            xmax = int(min(WIDTH, xmax * WIDTH))
            ymin = int(max(1, ymin * HEIGHT))
            ymax = int(min(HEIGHT, ymax * HEIGHT))

            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 3)

            # Draw circle in center
            xcenter = xmin + (int(round((xmax - xmin) / 2)))  # something wrong here....need to troubleshoot. will figure this out later.
            ycenter = ymin + (int(round((ymax - ymin) / 2)))
            cv2.circle(frame, (xcenter, ycenter), 5, (0, 0, 255), thickness=-1)
        if not paused:
            if xcenter > 0:
                zone = determine_piezone(xcenter, ycenter)
                center = in_center(xcenter, ycenter)
                print(f"Object in piezone {zone}" + (" and centerzone" if center else ""))
                if center:
                    # GPIO.output(cam1,GPIO.LOW)
                    # GPIO.output(cam2,GPIO.LOW)
                    # GPIO.output(cam3,GPIO.LOW)
                    # GPIO.output(cam4,GPIO.LOW)
                    # GPIO.output(cam5,GPIO.LOW)
                    # GPIO.output(cam6,GPIO.LOW)
                    cameratriggered = 0
                    print('no camera on')
                else:
                    if zone == 1:
                        # GPIO.output(cam1, GPIO.HIGH) # normally high in 6 arm box
                        # GPIO.output(cam2, GPIO.LOW)
                        # GPIO.output(cam3, GPIO.LOW)
                        # GPIO.output(cam4, GPIO.LOW)
                        # GPIO.output(cam5, GPIO.LOW)
                        # GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 1
                        print('GPIO ', cam1, ' triggered')
                    if zone == 2:
                        # GPIO.output(cam1, GPIO.LOW)
                        # GPIO.output(cam2, GPIO.HIGH)
                        # GPIO.output(cam3, GPIO.LOW)
                        # GPIO.output(cam4, GPIO.LOW)
                        # GPIO.output(cam5, GPIO.LOW)
                        # GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 2
                        print('GPIO ', cam2, ' triggered')
                    if zone == 3:
                        # GPIO.output(cam1, GPIO.LOW)
                        # GPIO.output(cam2, GPIO.LOW)
                        # GPIO.output(cam3, GPIO.HIGH)
                        # GPIO.output(cam4, GPIO.LOW)
                        # GPIO.output(cam5, GPIO.LOW)
                        # GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 3
                        print('GPIO ', cam3, ' triggered')
                    if zone == 4:
                        # GPIO.output(cam1, GPIO.LOW)
                        # GPIO.output(cam2, GPIO.LOW)
                        # GPIO.output(cam3, GPIO.LOW)
                        # GPIO.output(cam4, GPIO.HIGH)
                        # GPIO.output(cam5, GPIO.LOW)
                        # GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 4
                        print('GPIO ', cam4, ' triggered')
                    if zone == 5:
                        # GPIO.output(cam1, GPIO.HIGH) #for 2 arms...normally low for 6 arm
                        # GPIO.output(cam2, GPIO.LOW)
                        # GPIO.output(cam3, GPIO.LOW)
                        # GPIO.output(cam4, GPIO.LOW)
                        # GPIO.output(cam5, GPIO.HIGH)
                        # GPIO.output(cam6, GPIO.LOW)
                        cameratriggered = 5
                        print('GPIO ', cam5, ' triggered')
                    if zone == 6:
                        # GPIO.output(cam1, GPIO.LOW)
                        # GPIO.output(cam2, GPIO.LOW)
                        # GPIO.output(cam3, GPIO.LOW)
                        # GPIO.output(cam4, GPIO.LOW)
                        # GPIO.output(cam5, GPIO.LOW)
                        # GPIO.output(cam6, GPIO.HIGH)
                        cameratriggered = 6
                        print('GPIO ', cam6, ' triggered')


                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                cv2.putText(frame, f"Zone {zone}" + (" + Center" if center else ""), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), zone, center, round(fps, 2), cameratriggered])
            else:


                print("Tracking lost. Reinitializing...")
                log_writer.writerow([frame_count, timestamp.strftime("%H:%M:%S.%f"), 0, False, round(fps, 2), cameratriggered])

            if video_writer:
                video_writer.write(resized_frame)

        cv2.putText(resized_frame, f"FPS: {fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow("Tracking", resized_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        elif key == ord('m'):
            paused = True
            print("Paused tracking and recording.")

            # Stop and save current video
            if video_writer:
                video_writer.release()
                video_writer = None
                print("Video file saved.")

            # Close current log file
            if log_file:
                log_file.close()
                log_file = None
                print("Log file saved.")

            stop_led_thread()

        elif key == ord('c') and paused:
            paused = False
            session_number += 1


            print("Resumed tracking and recording.")

            # Start a new video file
            video_filename = generate_filename(base_time, sample_number, session_number, "video.mp4")
            video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH, HEIGHT))
            print(f"Started new video file: {video_filename}")

            # Start a new log file
            log_filename = generate_filename(base_time, sample_number, session_number, "log.csv")
            log_file = open(log_filename, mode='w', newline='')
            log_writer = csv.writer(log_file)
            log_writer.writerow(["Frame", "Timestamp", "Piezone", "InCenter", "FPS"])
            print(f"Started new log file: {log_filename}")

            start_led_thread()



    if video_writer:
        video_writer.release()
    if log_file:
        log_file.close()
    stop_led_thread()
    GPIO.cleanup()
    cv2.destroyAllWindows()
    picam2.stop()

if __name__ == "__main__":
    main()
