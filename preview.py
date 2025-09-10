import os
import time
from datetime import datetime
from picamera2 import Picamera2
import keyboard  # Requires sudo privileges on Raspberry Pi

# Initialize camera
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

# Ensure previewpics folder exists
preview_folder = "previewpics"
os.makedirs(preview_folder, exist_ok=True)

print("Ready to capture. Press 'P' to take a photo and upload. Press 'Q' to quit.")

try:
    while True:
        if keyboard.is_pressed('p'):
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.jpg"
            filepath = os.path.join(preview_folder, filename)

            # Capture and save image
            picam2.capture_file(filepath)
            print(f"Photo saved: {filename}")

            # Upload using rclone
            print("Uploading to OneDrive...")
            os.system(f'rclone copy "{preview_folder}" onedrive:/Videos')

            # Delete the file after upload
            os.remove(filepath)
            print(f"Deleted local copy: {filename}")

            # Wait for key release to avoid multiple triggers
            while keyboard.is_pressed('p'):
                time.sleep(0.1)

        elif keyboard.is_pressed('q'):
            print("Quitting...")
            break

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nInterrupted. Exiting...")

finally:
    picam2.stop()
