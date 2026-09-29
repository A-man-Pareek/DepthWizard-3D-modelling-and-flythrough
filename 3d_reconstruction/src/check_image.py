import rasterio

IMAGE = "input/image.tiff"

with rasterio.open(IMAGE) as src:
    print("=" * 50)
    print("SATELLITE IMAGE")
    print("=" * 50)

    print("Width:", src.width)
    print("Height:", src.height)
    print("Bands:", src.count)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Transform:", src.transform)
    print("Bounds:", src.bounds)
    print("Driver:", src.driver)

    print("=" * 50)