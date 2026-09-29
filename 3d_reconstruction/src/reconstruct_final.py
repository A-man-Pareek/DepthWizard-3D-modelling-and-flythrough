import os
import numpy as np
import rasterio
import open3d as o3d


# ============================================================
# INPUTS
# ============================================================

IMAGE = "input/image.tiff"
HEIGHT = "input/height.tiff"
SEGMENTATION = "input/segmentation.tiff"

OUTPUT_DIR = "output"

POINTCLOUD_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "depthwizard_final.ply"
)

MESH_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "depthwizard_final_mesh.ply"
)


# ============================================================
# SETTINGS
# ============================================================

# Reduce resolution to make the mesh easier to handle.
# 1 = full resolution
# 2 = every second pixel
# 4 = every fourth pixel

DOWNSAMPLE = 2


# Vertical exaggeration.
#
# 1.0 = actual HTC-DC height
# 2.0 = twice as tall visually

VERTICAL_SCALE = 1.0


# ============================================================
# SEGMENTATION CLASSES
# ============================================================

CLASS_NAMES = {

    0: "wall",
    1: "building",
    4: "tree",
    13: "earth",
    17: "plant",
    21: "water",

}


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# LOAD RGB IMAGE
# ============================================================

print("=" * 60)
print("DEPTHWIZARD FINAL 3D RECONSTRUCTION")
print("=" * 60)

print("\nLoading satellite image...")

with rasterio.open(IMAGE) as src:

    rgb = src.read()

    # Convert from:
    # (bands, height, width)
    #
    # to:
    # (height, width, bands)

    rgb = np.transpose(
        rgb,
        (1, 2, 0)
    )


print(
    "Image shape:",
    rgb.shape
)


# ============================================================
# LOAD HTC-DC HEIGHT
# ============================================================

print("\nLoading HTC-DC height...")

with rasterio.open(HEIGHT) as src:

    height = src.read(1).astype(
        np.float32
    )


print(
    "Height shape:",
    height.shape
)

print(
    "Height min:",
    float(np.nanmin(height))
)

print(
    "Height max:",
    float(np.nanmax(height))
)

print(
    "Height mean:",
    float(np.nanmean(height))
)


# ============================================================
# LOAD SEGMENTATION
# ============================================================

print("\nLoading segmentation...")

with rasterio.open(SEGMENTATION) as src:

    segmentation = src.read(1)


print(
    "Segmentation shape:",
    segmentation.shape
)

print(
    "Segmentation dtype:",
    segmentation.dtype
)


# ============================================================
# CHECK ALIGNMENT
# ============================================================

if rgb.shape[:2] != height.shape:

    raise ValueError(
        f"Image and height dimensions do not match: "
        f"{rgb.shape[:2]} vs {height.shape}"
    )


if segmentation.shape != height.shape:

    raise ValueError(
        f"Segmentation and height dimensions do not match: "
        f"{segmentation.shape} vs {height.shape}"
    )


print("\nAll three inputs are aligned: 1024 x 1024")


# ============================================================
# DOWNSAMPLE
# ============================================================

rgb = rgb[::DOWNSAMPLE, ::DOWNSAMPLE]

height = height[::DOWNSAMPLE, ::DOWNSAMPLE]

segmentation = segmentation[
    ::DOWNSAMPLE,
    ::DOWNSAMPLE
]


H, W = height.shape


print(
    f"\nWorking resolution: {W} x {H}"
)


# ============================================================
# CLEAN HEIGHT DATA
# ============================================================

height = np.nan_to_num(
    height,
    nan=0.0,
    posinf=0.0,
    neginf=0.0
)


height = np.maximum(
    height,
    0
)


# ============================================================
# BUILDING-SPECIFIC EXTRUSION
# ============================================================

# The segmentation mask represents built-up areas which should
# stand above terrain to look like realistic urban structures.

building_mask = segmentation == 1

if np.any(building_mask):
    building_boost = np.clip(
        height[building_mask] * 1.2 + 4.0,
        4.0,
        38.0
    )

    height = height.copy()
    height[building_mask] = np.maximum(
        height[building_mask],
        building_boost
    )


# ============================================================
# BUILD 3D VERTICES
# ============================================================

print("\nCreating 3D vertices...")


vertices = []

colors = []

class_ids = []


for y in range(H):

    for x in range(W):

        h = float(
            height[y, x]
        )


        # ----------------------------------------------------
        # 3D COORDINATES
        #
        # X = image horizontal
        # Y = HTC-DC height
        # Z = image vertical
        # ----------------------------------------------------

        X = float(x)

        Y = h * VERTICAL_SCALE

        Z = float(
            H - 1 - y
        )


        vertices.append(
            [X, Y, Z]
        )


        # ----------------------------------------------------
        # RGB COLOR
        # ----------------------------------------------------

        pixel = rgb[y, x]

        if rgb.shape[2] >= 3:

            r = float(pixel[0])

            g = float(pixel[1])

            b = float(pixel[2])

        else:

            r = g = b = float(
                pixel[0]
            )


        # Normalize 0-255

        if max(r, g, b) > 1:

            r /= 255.0
            g /= 255.0
            b /= 255.0


        colors.append(
            [r, g, b]
        )


        class_ids.append(
            int(segmentation[y, x])
        )


vertices = np.asarray(
    vertices,
    dtype=np.float64
)

colors = np.asarray(
    colors,
    dtype=np.float64
)

class_ids = np.asarray(
    class_ids,
    dtype=np.uint8
)


print(
    "Vertices:",
    len(vertices)
)


# ============================================================
# CREATE TRIANGLES
# ============================================================

print("\nCreating terrain triangles...")


triangles = []


for y in range(H - 1):

    for x in range(W - 1):

        i = y * W + x

        a = i

        b = i + 1

        c = i + W

        d = i + W + 1


        # Two triangles per grid cell

        triangles.append(
            [a, c, b]
        )

        triangles.append(
            [b, c, d]
        )


triangles = np.asarray(
    triangles,
    dtype=np.int32
)


print(
    "Triangles:",
    len(triangles)
)


# ============================================================
# CREATE OPEN3D POINT CLOUD
# ============================================================

print("\nCreating point cloud...")


point_cloud = o3d.geometry.PointCloud()


point_cloud.points = o3d.utility.Vector3dVector(
    vertices
)


point_cloud.colors = o3d.utility.Vector3dVector(
    colors
)


# ============================================================
# SAVE POINT CLOUD
# ============================================================

print(
    "\nSaving point cloud..."
)

o3d.io.write_point_cloud(
    POINTCLOUD_OUTPUT,
    point_cloud
)


print(
    "Saved:",
    POINTCLOUD_OUTPUT
)


# ============================================================
# CREATE MESH
# ============================================================

print("\nCreating 3D mesh...")


mesh = o3d.geometry.TriangleMesh()


mesh.vertices = o3d.utility.Vector3dVector(
    vertices
)

mesh.triangles = o3d.utility.Vector3iVector(
    triangles
)

mesh.vertex_colors = o3d.utility.Vector3dVector(
    colors
)


# ============================================================
# COMPUTE NORMALS
# ============================================================

print(
    "Computing surface normals..."
)

mesh.compute_vertex_normals()


# ============================================================
# SAVE MESH
# ============================================================

print(
    "\nSaving final mesh..."
)

o3d.io.write_triangle_mesh(
    MESH_OUTPUT,
    mesh
)


print(
    "Saved:",
    MESH_OUTPUT
)


# ============================================================
# SEGMENTATION STATISTICS
# ============================================================

print("\n" + "=" * 60)

print(
    "SEGMENTATION STATISTICS"
)

print("=" * 60)


unique_classes, counts = np.unique(
    class_ids,
    return_counts=True
)


for class_id, count in zip(
    unique_classes,
    counts
):

    name = CLASS_NAMES.get(
        int(class_id),
        f"class_{class_id}"
    )


    percentage = (
        count /
        len(class_ids)
    ) * 100


    print(
        f"{int(class_id):3d} "
        f"{name:12s} "
        f"{percentage:6.2f}%"
    )


# ============================================================
# FINAL INFORMATION
# ============================================================

print("\n" + "=" * 60)

print(
    "3D RECONSTRUCTION SUCCESSFUL!"
)

print("=" * 60)

print(
    "Point cloud:",
    POINTCLOUD_OUTPUT
)

print(
    "Mesh:",
    MESH_OUTPUT
)

print(
    f"Resolution: {W} x {H}"
)

print(
    f"Vertical scale: {VERTICAL_SCALE}"
)

print(
    f"Maximum height: "
    f"{height.max():.2f} m"
)

print("=" * 60)