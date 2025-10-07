import pygame
import pygame.camera

pygame.camera.init()

# Get available cameras
cams = pygame.camera.list_cameras()
if cams:
    cam = pygame.camera.Camera(cams[0], (640, 480))
    cam.start()
    img = cam.get_image()
    pygame.image.save(img, "capture.jpg") # Save the captured image
    cam.stop()
else:
print("No camera found.")