import numpy as np
import rasterio
import matplotlib.pyplot as plt


DEPTH_PATH = "output/depth.npy"
HEIGHT_PATH = "input/height.tif"

OUTPUT_DEPTH = "output/fused_depth.npy"
OUTPUT_IMAGE = "output/fused_visualization.png"


# --------------------------------------------------
# Load depth
# --------------------------------------------------

depth = np.load(DEPTH_PATH).astype(np.float32)

print("Depth shape:", depth.shape)


# --------------------------------------------------
# Load HTC-DC height
# --------------------------------------------------

with rasterio.open(HEIGHT_PATH) as src:
    height = src.read(1).astype(np.float32)

print("Height shape:", height.shape)


# --------------------------------------------------
# Check dimensions
# --------------------------------------------------

if depth.shape != height.shape:
    raise ValueError(
        f"Dimension mismatch: depth={depth.shape}, "
        f"height={height.shape}"
    )


# --------------------------------------------------
# Normalize depth
# --------------------------------------------------

depth_min = np.nanmin(depth)
depth_max = np.nanmax(depth)

depth_norm = (
    (depth - depth_min)
    / (depth_max - depth_min + 1e-8)
)


# --------------------------------------------------
# Normalize height
# --------------------------------------------------

height_min = np.nanmin(height)
height_max = np.nanmax(height)

height_norm = (
    (height - height_min)
    / (height_max - height_min + 1e-8)
)


# --------------------------------------------------
# Fuse
# --------------------------------------------------

fused = depth_norm * 0.5 + height_norm * 0.5


# --------------------------------------------------
# Save
# --------------------------------------------------

np.save(
    OUTPUT_DEPTH,
    fused.astype(np.float32)
)

print("Saved:", OUTPUT_DEPTH)


# --------------------------------------------------
# Visualization
# --------------------------------------------------

plt.figure(figsize=(12, 8))

plt.imshow(fused)

plt.colorbar(label="Fused Depth/Height")

plt.title("Depth + HTC-DC Height Fusion")

plt.axis("off")

plt.savefig(
    OUTPUT_IMAGE,
    dpi=150,
    bbox_inches="tight"
)

plt.close()

print("Saved:", OUTPUT_IMAGE)

print()
print("FUSION SUCCESSFUL!")