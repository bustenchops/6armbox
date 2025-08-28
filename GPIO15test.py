
import RPi.GPIO as GPIO
import time
import threading
import sys
import termios
import tty

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(15, GPIO.OUT)

# Function to read a single character from stdin
def get_char():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# Thread to monitor for 'q' key press
def monitor_keypress(stop_event):
    while not stop_event.is_set():
        if get_char().lower() == 'q':
            stop_event.set()

# Main loop
def main():
    stop_event = threading.Event()
    key_thread = threading.Thread(target=monitor_keypress, args=(stop_event,))
    key_thread.start()

    print("Press 'q' to quit.")
    try:
        while not stop_event.is_set():
            GPIO.output(2, GPIO.HIGH)
            print("GPIO 2 is ON")
            time.sleep(3)
            GPIO.output(2, GPIO.LOW)
            print("GPIO 2 is OFF")
            time.sleep(3)
    finally:
        GPIO.output(2, GPIO.LOW)
        GPIO.cleanup()
        print("GPIO cleaned up. Exiting.")

if __name__ == "__main__":
    main()
