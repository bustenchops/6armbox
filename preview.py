from picamera2 import Picamera2
import cv2

# Initialize the camera
picam2 = Picamera2()
picam2.configure(picam2.preview_configuration(main={"format": "RGB888", "size": (1920, 1080)}))
picam2.start()

print("Press 'q' to quit.")

while True:
    # Capture a frame
    frame = picam2.capture_array()

    # Display the frame
    cv2.imshow("Camera Preview", frame)

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cv2.destroyAllWindows()
picam2.stop()