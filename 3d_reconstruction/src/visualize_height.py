import numpy as np
import rasterio
import matplotlib.pyplot as plt

INPUT = "input/height.tiff"
OUTPUT = "output/height_visualization.png"


with rasterio.open(INPUT) as src:
    height = src.read(1).astype(np.float32)


plt.figure(figsize=(12, 6))

plt.imshow(height)

plt.colorbar(label="Height (m)")

plt.title("HTC-DC Net Height Estimation")

plt.axis("off")

plt.savefig(
    OUTPUT,
    dpi=150,
    bbox_inches="tight"
)

plt.close()

print("Height visualization saved:")
print(OUTPUT)