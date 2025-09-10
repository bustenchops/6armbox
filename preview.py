from picamera2 import Picamera2, Preview
import time

# Initialize the camera
picam2 = Picamera2()

# Configure for preview
config = picam2.preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)

# Start the preview using the built-in DRM window
picam2.start_preview(Preview.QTGL)  # You can also try Preview.DRM or Preview.NULL depending on your setup
picam2.start()

print("Live video feed started. Press Ctrl+C to quit.")

try:
    while True:
        time.sleep(0.1)  # Keep the program alive
except KeyboardInterrupt:
    print("\nStopping camera...")
    picam2.stop_preview()
    picam2.stop()
