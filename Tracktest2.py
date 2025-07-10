import cv2
import numpy as np


#from: https://medium.com/@amit25173/opencv-object-tracking-project-29954e0f0418
cap = cv2.VideoCapture(0)  # For a webcam feed

ret, frame = cap.read()
frame = cv2.resize(frame, (640, 480))

gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

tracker = cv2.TrackerKCF.create()  # For KCF note from https://stackoverflow.com/questions/72736551/opencv-trackers-not-recognized-attributeerror-module-cv2-has-no-attribute-t

bbox = cv2.selectROI(frame, False)
tracker.init(frame, bbox)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    success, bbox = tracker.update(frame)
    if success:
        # Draw the bounding box
        p1 = (int(bbox[0]), int(bbox[1]))
        p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
        cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
    cv2.imshow('Tracking', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break