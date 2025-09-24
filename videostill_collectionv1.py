import cv2
import os
import random

# Set the path to the directory containing your videos
video_directory = "videos"  # Change this to your actual video directory
output_directory = "collectedimages"

# Create the output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)

# Supported video file extensions
video_extensions = ['.mp4', '.avi', '.mov', '.mkv']

# Initialize image counter
image_counter = 1

# Iterate through all files in the video directory
for filename in os.listdir(video_directory):
    if any(filename.lower().endswith(ext) for ext in video_extensions):
        video_path = os.path.join(video_directory, filename)
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"Failed to open video: {filename}")
            continue

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Generate 50 unique random frame indices
        random_frames = sorted(random.sample(range(frame_count), min(50, frame_count)))

        for frame_num in random_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if ret:
                image_filename = f"rodent_{image_counter}.jpg"
                image_path = os.path.join(output_directory, image_filename)
                cv2.imwrite(image_path, frame)
                image_counter += 1

        cap.release()

print(f"Extraction complete. {image_counter - 1} images saved in '{output_directory}' directory.")


# === Step 2: Crop and resize images ===

resized_directory = "resized"
os.makedirs(resized_directory, exist_ok=True)

for filename in os.listdir(output_directory):
    if filename.lower().endswith('.jpg'):
        image_path = os.path.join(output_directory, filename)
        image = cv2.imread(image_path)

        if image is None:
            print(f"Failed to read image: {filename}")
            continue

        height, width, _ = image.shape
        if height < 160 or width < 160:
            print(f"Image too small to crop: {filename}")
            continue

        # Crop 80 pixels from each side
        cropped_image = image[:, 80:width-80]

        # Resize to 300x300 pixels
        resized_image = cv2.resize(cropped_image, (320 320))

        # Save the resized image
        resized_path = os.path.join(resized_directory, filename)
        cv2.imwrite(resized_path, resized_image)

print(f"Cropping and resizing complete. Images saved in '{resized_directory}' directory.")
