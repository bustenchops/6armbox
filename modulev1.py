import cv2

# Capture video from the default camera
cap = cv2.VideoCapture(0)

# Set camera parameters
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
cap.set(cv2.CAP_PROP_CONTRAST, 0.8)

if not cap.isOpened():
    print('camera done not work')
    exit()

while True:
    ret, frame = cap.read()
    print(ret)
    if not ret:
        print('end of vid or cant read')
    cv2.imshow('Camera', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()