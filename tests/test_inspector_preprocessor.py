"""Unit tests for pipeline.inspector and pipeline.preprocessor."""

import io
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

from pipeline.inspector import inspect_image
from pipeline.preprocessor import preprocess_for_model


def test_plain_image_inspection_and_preprocessing():
    buf = io.BytesIO()
    img = Image.new("RGB", (320, 240), color=(120, 180, 210))
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    insp = inspect_image(raw_bytes)
    assert insp.is_georeferenced is False
    assert insp.original_shape == (240, 320)
    assert insp.crs is None
    assert insp.transform is None

    # Preprocessing must NEVER downsample to 256x256
    pre = preprocess_for_model(insp.image_array)
    assert pre.tensor.shape == (1, 3, 240, 320), f"Downsampled! Shape is {pre.tensor.shape}"
    assert pre.original_shape == (240, 320)
    assert pre.rgb_uint8.shape == (240, 320, 3)


def test_geotiff_inspection_preserves_crs_and_transform():
    w, h = 180, 150
    transform = from_bounds(10.0, 45.0, 10.5, 45.5, w, h)
    crs = CRS.from_epsg(4326)
    data = np.random.randint(0, 255, (3, h, w), dtype=np.uint8)

    buf = io.BytesIO()
    with rasterio.open(
        buf,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=3,
        dtype=rasterio.uint8,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)

    insp = inspect_image(buf.getvalue())
    assert insp.is_georeferenced is True
    assert insp.original_shape == (h, w)
    assert insp.crs == crs
    assert np.allclose(insp.transform[:6], transform[:6])


if __name__ == "__main__":
    test_plain_image_inspection_and_preprocessing()
    test_geotiff_inspection_preserves_crs_and_transform()
    print("All inspector and preprocessor tests passed!")
