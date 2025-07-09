import time
import picamera
import keyboard

def main():
    camera = picamera.PiCamera()
    camera.resolution = (1920, 1080)  # Set resolution (optional)
    print("Camera initialized. Press 't' to start recording and 'p' to stop.")

    try:
        while True:
            if keyboard.is_pressed('t'):  # Start recording when 't' is pressed
                if not camera.recording:
                    print("Recording started...")
                    camera.start_recording('video.h264')
                    while keyboard.is_pressed('t'):  # Wait for key release
                        time.sleep(0.1)

            if keyboard.is_pressed('p'):  # Stop recording when 'p' is pressed
                if camera.recording:
                    print("Recording stopped.")
                    camera.stop_recording()
                    while keyboard.is_pressed('p'):  # Wait for key release
                        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting program.")
    finally:
        camera.close()

if __name__ == "__main__":
    main()
