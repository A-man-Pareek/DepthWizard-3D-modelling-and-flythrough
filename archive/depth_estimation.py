import os
import numpy as np
import torch
import matplotlib.pyplot as plt

from PIL import Image
from transformers import (
    AutoImageProcessor,
    AutoModelForDepthEstimation
)


# ============================================================
# 1. SETTINGS
# ============================================================

IMAGE_PATH = "input/image.png"

OUTPUT_DIR = "output"

DEPTH_PATH = os.path.join(
    OUTPUT_DIR,
    "depth.npy"
)

DEPTH_IMAGE_PATH = os.path.join(
    OUTPUT_DIR,
    "depth_visualization.png"
)

MODEL_NAME = "depth-anything/Depth-Anything-V2-Small-hf"


# ============================================================
# 2. CREATE OUTPUT FOLDER
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 3. LOAD IMAGE
# ============================================================

print("Loading image...")

image = Image.open(IMAGE_PATH).convert("RGB")

print("Image loaded.")
print("Image size:", image.size)


# ============================================================
# 4. SELECT DEVICE
# ============================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Device:", device)


# ============================================================
# 5. LOAD DEPTH ANYTHING V2
# ============================================================

print("Loading Depth Anything V2...")

processor = AutoImageProcessor.from_pretrained(
    MODEL_NAME
)

model = AutoModelForDepthEstimation.from_pretrained(
    MODEL_NAME
)

model.to(device)
model.eval()

print("Model loaded.")


# ============================================================
# 6. PREPARE IMAGE
# ============================================================

inputs = processor(
    images=image,
    return_tensors="pt"
)

inputs = {
    key: value.to(device)
    for key, value in inputs.items()
}


# ============================================================
# 7. RUN DEPTH ESTIMATION
# ============================================================

print("Estimating depth...")

with torch.no_grad():
    outputs = model(**inputs)

print("Depth estimation complete.")


# ============================================================
# 8. CONVERT MODEL OUTPUT TO IMAGE SIZE
# ============================================================

original_width, original_height = image.size

post_processed = processor.post_process_depth_estimation(
    outputs,
    target_sizes=[
        (original_height, original_width)
    ]
)

depth = post_processed[0]["predicted_depth"]

depth = depth.cpu().numpy().astype(np.float32)


# ============================================================
# 9. PRINT DEPTH INFORMATION
# ============================================================

print()
print("========== DEPTH INFORMATION ==========")

print("Depth shape:", depth.shape)

print("Depth data type:", depth.dtype)

print("Depth minimum:", float(depth.min()))

print("Depth maximum:", float(depth.max()))

print("Depth mean:", float(depth.mean()))

print("========================================")
print()


# ============================================================
# 10. SAVE RAW FLOAT DEPTH
# ============================================================

np.save(
    DEPTH_PATH,
    depth
)

print("Saved raw depth:")
print(DEPTH_PATH)


# ============================================================
# 11. CREATE VISUALIZATION
# ============================================================

plt.figure(figsize=(10, 8))

plt.imshow(depth)

plt.colorbar(
    label="Relative Depth"
)

plt.title(
    "Depth Anything V2 - Relative Depth"
)

plt.axis("off")

plt.savefig(
    DEPTH_IMAGE_PATH,
    bbox_inches="tight",
    dpi=150
)

plt.close()

print("Saved depth visualization:")
print(DEPTH_IMAGE_PATH)

print()
print("DEPTH ESTIMATION SUCCESSFUL!")