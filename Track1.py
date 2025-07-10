import cv2

# Initialize video capture from the default camera
cap = cv2.VideoCapture(0)

# Wait for a few frames to let the camera adjust
for _ in range(30):
    ret, frame = cap.read()

# Select a bounding box manually from the first frame
bbox = cv2.selectROI("Tracking", frame, False)
cv2.destroyWindow("Tracking")

# Initialize the KCF tracker
tracker = cv2.TrackerKCF_create()
tracker.init(frame, bbox)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    success, bbox = tracker.update(frame)
    if success:
        # Draw bounding box
        x, y, w, h = [int(v) for v in bbox]
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Determine the horizontal position
        center_x = x + w // 2
        frame_center = frame.shape[1] // 2

        if center_x < frame_center:
            print("Left")
        else:
            print("Right")

    cv2.imshow("Tracking", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # Exit on ESC key
        break

cap.release()
cv2.destroyAllWindows()