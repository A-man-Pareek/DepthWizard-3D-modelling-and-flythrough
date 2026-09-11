import cv2

IMAGE_PATH = "input/test.png"

image = cv2.imread(IMAGE_PATH)

if image is None:
    print("ERROR: Could not load image.")
else:
    height, width, channels = image.shape

    print("Image loaded successfully!")
    print(f"Width: {width}")
    print(f"Height: {height}")
    print(f"Channels: {channels}")