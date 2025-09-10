from picamera2 import Picamera2
import pygame
import numpy as np

# Initialize camera
picam2 = Picamera2()
config = picam2.preview_configuration(main={"format": "RGB888", "size": (640, 480)})
picam2.configure(config)
picam2.start()

# Initialize pygame window
pygame.init()
screen = pygame.display.set_mode((640, 480))
pygame.display.set_caption("Live Camera Feed")

running = True
while running:
    # Capture frame
    frame = picam2.capture_array()

    # Convert to pygame surface
    frame_surface = pygame.surfarray.make_surface(np.rot90(frame))

    # Display frame
    screen.blit(frame_surface, (0, 0))
    pygame.display.update()

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

# Cleanup
pygame.quit()
picam2.stop()
