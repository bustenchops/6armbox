import os
import cv2
import numpy as np
import tensorflow as tf
import time
from object_detection.utils import label_map_util, visualization_utils as viz_utils

# Load label map
category_index = label_map_util.create_category_index_from_labelmap(files['LABELMAP'])

# Get path to test images
test_images_path = os.path.join(paths['IMAGE_PATH'], 'test')

# Create output folder if it doesn't exist
output_folder = os.path.join(paths['IMAGE_PATH'], 'visualfeedback')
os.makedirs(output_folder, exist_ok=True)

# Find all .jpg files in the test folder
image_files = [f for f in os.listdir(test_images_path) if f.lower().endswith('.jpg')]

# Loop through each image
for i in range(len(image_files)):
    image_path = os.path.join(test_images_path, image_files[i])
    img = cv2.imread(image_path)
    image_np = np.array(img)

    # Convert image to tensor
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

    # Save the annotated image
    output_path = os.path.join(output_folder, f"annotated_{image_files[i]}")
    cv2.imwrite(output_path, image_np_with_detections)

    # Optional: wait for 4 seconds between processing
    #time.sleep(4)
