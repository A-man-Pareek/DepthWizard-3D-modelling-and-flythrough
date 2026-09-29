import rasterio
import numpy as np

INPUT = "input/segmentation.tiff"

with rasterio.open(INPUT) as src:
    seg = src.read(1)

    print("=" * 50)
    print("SEGMENTATION INFORMATION")
    print("=" * 50)

    print("Shape:", seg.shape)
    print("Data type:", seg.dtype)
    print("Minimum:", np.min(seg))
    print("Maximum:", np.max(seg))

    classes, counts = np.unique(seg, return_counts=True)

    print("\nCLASS IDs:")
    for c, n in zip(classes, counts):
        percentage = (n / seg.size) * 100
        print(f"Class {c}: {n} pixels ({percentage:.2f}%)")

    print("=" * 50)