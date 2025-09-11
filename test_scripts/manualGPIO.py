import RPi.GPIO as GPIO
import sys
import termios
import tty

# GPIO pin mapping
gpio_map = {
    '1': 14,
    '2': 15,
    '3': 18,
    '4': 23,
    '5': 24,
    '6': 25
}

# Setup
GPIO.setmode(GPIO.BCM)
for pin in gpio_map.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

def get_key():
    """Reads a single keypress from stdin."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return key

print("Press 1–6 to set GPIO HIGH, L to reset all to LOW, q to quit.")

try:
    while True:
        key = get_key()
        if key in gpio_map:
            GPIO.output(gpio_map[key], GPIO.HIGH)
            print(f"GPIO {gpio_map[key]} set to HIGH")
        elif key.lower() == 'l':
            for pin in gpio_map.values():
                GPIO.output(pin, GPIO.LOW)
            print("All GPIOs set to LOW")
        elif key.lower() == 'q':
            print("Exiting program.")
            break
finally:
    GPIO.cleanup()
