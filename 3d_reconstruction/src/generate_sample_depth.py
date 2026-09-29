import cv2
import numpy as np


# -----------------------------------
# Input image
# -----------------------------------

IMAGE_PATH = "input/test.png"
DEPTH_PATH = "input/depth.npy"


# -----------------------------------
# Load image
# -----------------------------------

image = cv2.imread(IMAGE_PATH)

if image is None:
    raise FileNotFoundError(
        f"Could not find {IMAGE_PATH}"
    )

height, width = image.shape[:2]

print("Image size:", width, "x", height)


# -----------------------------------
# Create synthetic metric depth
# -----------------------------------

# Create a smooth depth gradient.
# Values represent metres.

y = np.linspace(
    10,
    50,
    height,
    dtype=np.float32
)

depth = np.repeat(
    y[:, np.newaxis],
    width,
    axis=1
)


# -----------------------------------
# Add some variation
# -----------------------------------

# Slight variation across the image
x_variation = np.linspace(
    -5,
    5,
    width,
    dtype=np.float32
)

depth += x_variation[np.newaxis, :]


# -----------------------------------
# Save depth
# -----------------------------------

np.save(DEPTH_PATH, depth)

print("Sample depth map created!")
print("Saved to:", DEPTH_PATH)
print("Minimum depth:", depth.min(), "m")
print("Maximum depth:", depth.max(), "m")