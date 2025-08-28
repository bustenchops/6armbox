
import RPi.GPIO as GPIO
import keyboard
import time

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(2, GPIO.OUT)

# Initial state
pin_state = False
GPIO.output(2, pin_state)
print("GPIO 2 is OFF")

try:
    print("Press SPACE to toggle GPIO 2. Press 'q' to quit.")
    while True:
        if keyboard.is_pressed(' '):
            pin_state = not pin_state
            GPIO.output(2, pin_state)
            print(f"GPIO 2 is {'ON' if pin_state else 'OFF'}")
            time.sleep(0.3)  # Debounce delay

        elif keyboard.is_pressed('q'):
            print("Exiting program.")
            break

        time.sleep(0.05)  # Reduce CPU usage

finally:
    GPIO.cleanup()
