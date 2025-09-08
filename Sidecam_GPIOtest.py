
import RPi.GPIO as GPIO
import time

# Use BCM pin numbering
GPIO.setmode(GPIO.BCM)

# Set up GPIO pins
GPIO.setup(14, GPIO.OUT)  # LED always ON
GPIO.setup(18, GPIO.OUT)  # LED flashing
GPIO.setup(15, GPIO.IN)   # Input pin

# Turn on LED on GPIO 14
GPIO.output(14, GPIO.HIGH)

try:
    while True:
        # Read and report status of GPIO 15
        input_state = GPIO.input(15)
        print(f"GPIO 15 state: {'HIGH' if input_state else 'LOW'}")
        if input_state:
            GPIO.output(18, GPIO.HIGH)
        else:
            GPIO.output(10, GPIO.LOW)
except KeyboardInterrupt:
    print("Program interrupted by user.")

finally:
    GPIO.cleanup()
