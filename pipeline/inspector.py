"""Step 1: Load and inspect the input image.

Determines whether an image is georeferenced (valid CRS + transform) or plain RGB.
Preserves original raster metadata, spatial dimensions, CRS, affine transform,
bounds, data type, and nodata values.
"""

from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image
import rasterio
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.transform import Affine


class ImageInspectionResult:
    """Encapsulates raw image data and spatial/raster metadata."""

    def __init__(
        self,
        image_array: np.ndarray,
        is_georeferenced: bool,
        crs: Optional[CRS] = None,
        transform: Optional[Affine] = None,
        bounds: Optional[Any] = None,
        driver: Optional[str] = None,
        original_shape: Optional[Tuple[int, int]] = None,
        num_bands: int = 3,
        dtype: str = "uint8",
        nodata: Optional[float] = None,
        nodata_mask: Optional[np.ndarray] = None,
    ):
        self.image_array = image_array
        self.is_georeferenced = is_georeferenced
        self.crs = crs
        self.transform = transform
        self.bounds = bounds
        self.driver = driver
        self.original_shape = original_shape or image_array.shape[:2]
        self.num_bands = num_bands
        self.dtype = dtype
        self.nodata = nodata
        self.nodata_mask = nodata_mask  # True = valid, False = nodata

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata for logging and API responses."""
        return {
            "is_georeferenced": self.is_georeferenced,
            "crs": self.crs.to_string() if (self.crs and hasattr(self.crs, "to_string")) else (str(self.crs) if self.crs else None),
            "transform": list(self.transform) if self.transform is not None else None,
            "bounds": list(self.bounds) if self.bounds is not None else None,
            "driver": self.driver,
            "original_shape": list(self.original_shape),
            "num_bands": self.num_bands,
            "dtype": str(self.dtype),
            "nodata": float(self.nodata) if self.nodata is not None else None,
            "has_nodata_mask": self.nodata_mask is not None,
        }


def inspect_image(input_source: Any) -> ImageInspectionResult:
    """Accepts file path (str or Path), file-like object, or bytes.

    Attempts opening with Rasterio to inspect CRS, affine transform, and nodata.
    Falls back to PIL for standard plain formats (PNG/JPG/WEBP) or unreferenced images.
    """
    image_bytes: Optional[bytes] = None
    file_path: Optional[str] = None

    if isinstance(input_source, np.ndarray):
        h, w = input_source.shape[:2]
        c = input_source.shape[2] if input_source.ndim == 3 else 1
        return ImageInspectionResult(
            image_array=input_source,
            is_georeferenced=False,
            crs=None,
            transform=None,
            bounds=None,
            driver="NumPy",
            original_shape=(h, w),
            num_bands=c,
            dtype=str(input_source.dtype),
            nodata=None,
            nodata_mask=None,
        )

    if isinstance(input_source, (bytes, bytearray)):
        image_bytes = bytes(input_source)
    elif isinstance(input_source, str):
        file_path = input_source
    elif hasattr(input_source, "read"):
        image_bytes = input_source.read()
    else:
        raise ValueError(f"Unsupported input source type: {type(input_source)}")

    # 1. Try opening with Rasterio
    try:
        if file_path:
            with rasterio.open(file_path) as src:
                return _process_rasterio_dataset(src)
        elif image_bytes:
            with MemoryFile(image_bytes) as memfile:
                with memfile.open() as src:
                    return _process_rasterio_dataset(src)
    except Exception:
        # Rasterio could not open or file is plain image
        pass

    # 2. Fallback to PIL for plain images
    return _load_plain_image(image_bytes=image_bytes, file_path=file_path)


def _process_rasterio_dataset(src: rasterio.DatasetReader) -> ImageInspectionResult:
    crs = src.crs
    transform = src.transform
    bounds = src.bounds
    driver = src.driver
    num_bands = src.count
    raw_dtype = str(src.dtypes[0])
    nodata_val = src.nodata

    # Read data: rasterio returns (bands, H, W)
    data = src.read()
    if data.ndim == 3:
        # Convert (bands, H, W) to (H, W, bands)
        image_array = np.transpose(data, (1, 2, 0))
    elif data.ndim == 2:
        image_array = data[:, :, None]
    else:
        image_array = data

    h, w = image_array.shape[:2]

    # Compute nodata mask if nodata is defined
    nodata_mask: Optional[np.ndarray] = None
    if nodata_val is not None:
        if np.isnan(nodata_val):
            nodata_mask = ~np.isnan(image_array).any(axis=-1)
        else:
            nodata_mask = ~(image_array == nodata_val).any(axis=-1)

    # Validate georeferencing
    is_georeferenced = False
    if crs is not None and transform is not None:
        try:
            if hasattr(crs, "to_string") and bool(crs.to_string()):
                is_georeferenced = True
            elif str(crs):
                is_georeferenced = True
        except Exception:
            is_georeferenced = False

    return ImageInspectionResult(
        image_array=image_array,
        is_georeferenced=is_georeferenced,
        crs=crs if is_georeferenced else None,
        transform=transform if is_georeferenced else None,
        bounds=bounds if is_georeferenced else None,
        driver=driver,
        original_shape=(h, w),
        num_bands=num_bands,
        dtype=raw_dtype,
        nodata=nodata_val,
        nodata_mask=nodata_mask,
    )


def _load_plain_image(
    image_bytes: Optional[bytes] = None, file_path: Optional[str] = None
) -> ImageInspectionResult:
    """Load standard image using PIL."""
    if file_path:
        img = Image.open(file_path)
    elif image_bytes:
        img = Image.open(BytesIO(image_bytes))
    else:
        raise ValueError("Either file_path or image_bytes must be provided.")

    driver = img.format or "PIL"
    img_rgb = img.convert("RGB")
    image_array = np.array(img_rgb, dtype=np.uint8)
    h, w = image_array.shape[:2]

    return ImageInspectionResult(
        image_array=image_array,
        is_georeferenced=False,
        crs=None,
        transform=None,
        bounds=None,
        driver=driver,
        original_shape=(h, w),
        num_bands=3,
        dtype="uint8",
        nodata=None,
        nodata_mask=None,
    )
