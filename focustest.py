from picamera2 import Picamera2
import time

def test_manual_focus():
    # Initialize Picamera2 and configure for still capture
    picam2 = Picamera2()
    config = picam2.create_still_configuration()
    picam2.configure(config)
    picam2.start()

    try:
        # Loop through lens positions 0–15 with manual focus
        for lens_pos in range(16):
            # Set autofocus mode to manual (0) and lens position
            picam2.set_controls({
                "AfMode": 0,
                "LensPosition": lens_pos
            })

            # Give the lens time to settle
            time.sleep(3)

            # Capture and save the still image
            filename = f"focus_test-lensposition{lens_pos}.jpg"
            picam2.capture_file(filename)
            print(f"Captured {filename}")

    finally:
        picam2.stop()

if __name__ == "__main__":
    test_manual_focus()
