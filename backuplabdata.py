import os
import shutil
import datetime
import subprocess

# Configuration
source_folder = ""  # Replace with your actual source folder
videos_root = "./videos"
backup_target = "/media/6armboxDATA"

# Step 1: Create date-named folder if it doesn't exist
today = datetime.date.today().strftime("%Y-%m-%d")
target_folder = os.path.join(videos_root, today)

if not os.path.exists(target_folder):
    os.makedirs(target_folder)
    print(f"📁 Created folder: {target_folder}")
else:
    print(f"📁 Folder already exists: {target_folder}")

# Step 2: Move specified file types
file_extensions = [".csv", ".jpg", ".h264", ".mp4"]
for ext in file_extensions:
    print('checking for ', ext, ' files')
    files = [f for f in os.listdir(source_folder) if f.endswith(ext)]

    for file in files:
        src_path = os.path.join(source_folder, file)
        dst_path = os.path.join(target_folder, file)
        shutil.move(src_path, dst_path)
        print(f"📦 Moved: {file} → {target_folder}")

# Step 3: Use rclone to copy /videos to /media/6armbox/
try:
    subprocess.run(["rclone", "copy", videos_root, backup_target], check=True)
    print("✅ rclone copy completed successfully.")
except subprocess.CalledProcessError as e:
    print(f"⚠️ rclone failed: {e}")
