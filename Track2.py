import cv2

# Use the GStreamer pipeline to access the Pi camera
# Adjust the resolution and framerate as needed
gst_pipeline = (
    "libcamera-vid -t 0 --inline --width 640 --height 480 --framerate 30 --codec yuv420 --nopreview | "
    "gst-launch-1.0 fdsrc ! rawvideoparse width=640 height=480 format=yuy2 framerate=30/1 ! "
    "videoconvert ! appsink"
)

# Alternatively, use cv2.VideoCapture with default settings if V4L2 is enabled
cap = cv2.VideoCapture(0)  # If using /dev/video0

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break

    cv2.imshow('Live Feed', frame)

    if cv2.waitKey(1) & 0xFF == 27:  # Press ESC to exit
        break

cap.release()
cv2.destroyAllWindows()
