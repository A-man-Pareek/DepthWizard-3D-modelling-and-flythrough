import os
import json
import numpy as np
import rasterio
from PIL import Image


HEIGHT_PATH = "input/height.tiff"
IMAGE_PATH = "input/image.tiff"
SEGMENTATION_PATH = "input/segmentation.tiff"

OUTPUT_DIR = "output"

HEIGHT_JSON = os.path.join(OUTPUT_DIR, "terrain_data.json")
TEXTURE_PNG = os.path.join(OUTPUT_DIR, "terrain_texture.png")


os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# LOAD HTC-DC HEIGHT
# ============================================================

print("Loading HTC-DC height map...")

with rasterio.open(HEIGHT_PATH) as src:
    height = src.read(1).astype(np.float32)

print("Height shape:", height.shape)
print("Height min:", float(np.nanmin(height)))
print("Height max:", float(np.nanmax(height)))
print("Height mean:", float(np.nanmean(height)))


# ============================================================
# CLEAN HEIGHT
# ============================================================

height = np.nan_to_num(
    height,
    nan=0.0,
    posinf=0.0,
    neginf=0.0
)

# AGL should not normally be negative.
height = np.maximum(height, 0.0)


# ============================================================
# BUILDING-BASED HEIGHT ENHANCEMENT
# ============================================================

print("Loading segmentation for building extrusion...")

with rasterio.open(SEGMENTATION_PATH) as src:
    segmentation = src.read(1).astype(np.uint8)

if segmentation.shape != height.shape:
    raise ValueError(
        f"Segmentation and height dimensions do not match: "
        f"{segmentation.shape} vs {height.shape}"
    )

# Raise building pixels above ground to create a city-like model.
# Class 1 is used for buildings in this dataset.
height_enhanced = height.copy()
building_mask = segmentation == 1

if np.any(building_mask):
    boost = np.clip(height[building_mask] * 1.2 + 4.0, 4.0, 38.0)
    height_enhanced[building_mask] = np.maximum(
        height[building_mask],
        boost
    )

# Keep water and low-vegetation areas flatter to preserve natural terrain.
water_mask = segmentation == 21
if np.any(water_mask):
    height_enhanced[water_mask] = np.minimum(height_enhanced[water_mask], 0.2)

height = height_enhanced


# ============================================================
# DOWNSAMPLE FOR WEB 3D
# ============================================================

MAX_RESOLUTION = 300

scale = max(
    height.shape[0] / MAX_RESOLUTION,
    height.shape[1] / MAX_RESOLUTION,
    1
)

new_height = max(2, int(height.shape[0] / scale))
new_width = max(2, int(height.shape[1] / scale))

print(
    "3D resolution:",
    new_width,
    "x",
    new_height
)


height_image = Image.fromarray(height)

height_image = height_image.resize(
    (new_width, new_height),
    Image.Resampling.BILINEAR
)

height_small = np.asarray(
    height_image,
    dtype=np.float32
)


# ============================================================
# LOAD RGB IMAGE
# ============================================================

print("Loading RGB image...")

image = Image.open(IMAGE_PATH).convert("RGB")

print("Original RGB:", image.size)


# Resize RGB to exactly match terrain
image = image.resize(
    (new_width, new_height),
    Image.Resampling.BILINEAR
)

image.save(
    TEXTURE_PNG
)

print("Saved texture:", TEXTURE_PNG)


# ============================================================
# CREATE JSON
# ============================================================

terrain_data = {
    "width": new_width,
    "height": new_height,

    "min_height": float(height_small.min()),
    "max_height": float(height_small.max()),
    "mean_height": float(height_small.mean()),

    "heights": height_small.flatten().tolist()
}


with open(
    HEIGHT_JSON,
    "w"
) as f:

    json.dump(
        terrain_data,
        f
    )


print("Saved terrain:", HEIGHT_JSON)

print()
print("================================")
print("3D DATA PREPARATION SUCCESSFUL")
print("================================")