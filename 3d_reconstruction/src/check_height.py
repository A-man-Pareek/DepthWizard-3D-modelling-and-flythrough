import rasterio
import numpy as np

path = "input/height.tiff"

with rasterio.open(path) as src:
    height = src.read(1)

    print("Height map shape:", height.shape)
    print("Data type:", height.dtype)
    print("Minimum:", np.nanmin(height))
    print("Maximum:", np.nanmax(height))
    print("Mean:", np.nanmean(height))
    print("CRS:", src.crs)
    print("Transform:", src.transform)