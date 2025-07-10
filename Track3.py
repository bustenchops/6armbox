from picamera2 import Picamera2
import cv2

# Initialize PiCamera2
picam2 = Picamera2()

# Configure the camera
camera_config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(camera_config)

# Start the camera
picam2.start()

try:
    while True:
        # Capture a frame
        frame = picam2.capture_array()

        # Display the frame using OpenCV
        cv2.imshow("Camera Feed", frame)

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Release resources
    picam2.stop()
    cv2.destroyAllWindows()