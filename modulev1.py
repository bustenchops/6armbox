
import cv2

# Initialize webcam
cap = cv2.VideoCapture(0)

# Set resolution to 640x480
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Define codec and output video file
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('processed_video.mp4', fourcc, 20.0, (320, 320))

# Capture and process frames
frame_count = 0
max_frames = 1000  # You can adjust this number

while frame_count < max_frames:
    ret, frame = cap.read()
    if not ret:
        break

    # Crop 80 pixels from left and right (640 - 160 = 480)
    cropped_frame = frame[:, 80:560]

    # Resize to 320x320
    resized_frame = cv2.resize(cropped_frame, (320, 320))

    # Save frame to video
    out.write(resized_frame)

    frame_count += 1

# Release resources
cap.release()
out.release()
cv2.destroyAllWindows()
