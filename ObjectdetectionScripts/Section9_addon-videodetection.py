import os
import cv2
import numpy as np
import tensorflow as tf
from object_detection.utils import label_map_util, visualization_utils as viz_utils

# Load label map
category_index = label_map_util.create_category_index_from_labelmap(files['LABELMAP'])

# Paths
video_name = 'test1.mp4'
video_path = os.path.join(paths['IMAGE_PATH'], 'test', video_name)
output_folder = os.path.join(paths['IMAGE_PATH'], 'visualfeedback')
os.makedirs(output_folder, exist_ok=True)

# Output video paths
resized_video_path = os.path.join(output_folder, video_name.replace('.mp4', '_RS.mp4'))
annotated_video_path = os.path.join(output_folder, video_name.replace('.mp4', '_RS_annotated.mp4'))

# Open original video
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)

# Define video writer for resized video
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
resized_writer = cv2.VideoWriter(resized_video_path, fourcc, fps, (320, 320))

# Step 1: Crop and resize original video
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Crop 80 pixels from left and right (assumes original width is 640)
    cropped_frame = frame[:, 80:-80]  # Resulting in 480x480

    # Resize to 320x320
    resized_frame = cv2.resize(cropped_frame, (320, 320))

    # Write resized frame
    resized_writer.write(resized_frame)

cap.release()
resized_writer.release()

# Step 2: Analyze the resized video
cap_rs = cv2.VideoCapture(resized_video_path)
annotated_writer = cv2.VideoWriter(annotated_video_path, fourcc, fps, (320, 320))

while cap_rs.isOpened():
    ret, frame = cap_rs.read()
    if not ret:
        break

    image_np = np.array(frame)
    input_tensor = tf.convert_to_tensor(np.expand_dims(image_np, 0), dtype=tf.float32)

    # Run detection
    detections = detect_fn(input_tensor)

    # Process detections
    num_detections = int(detections.pop('num_detections'))
    detections = {key: value[0, :num_detections].numpy()
                  for key, value in detections.items()}
    detections['num_detections'] = num_detections
    detections['detection_classes'] = detections['detection_classes'].astype(np.int64)

    # Visualize results
    label_id_offset = 1
    image_np_with_detections = image_np.copy()

    viz_utils.visualize_boxes_and_labels_on_image_array(
        image_np_with_detections,
        detections['detection_boxes'],
        detections['detection_classes'] + label_id_offset,
        detections['detection_scores'],
        category_index,
        use_normalized_coordinates=True,
        max_boxes_to_draw=5,
        min_score_thresh=0.8,
        agnostic_mode=False)

    # Write annotated frame
    annotated_writer.write(image_np_with_detections)

cap_rs.release()
annotated_writer.release()