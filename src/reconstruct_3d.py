import json
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d


# ==================================================
# INPUTS
# ==================================================

IMAGE_PATH = Path("input/test.png")
DEPTH_PATH = Path("input/depth.npy")
CAMERA_PATH = Path("camera_params.json")

OUTPUT_PATH = Path("output/pointcloud.ply")


# ==================================================
# LOAD CAMERA PARAMETERS
# ==================================================

with open(CAMERA_PATH, "r") as file:
    camera = json.load(file)

fx = float(camera["fx"])
fy = float(camera["fy"])
cx = float(camera["cx"])
cy = float(camera["cy"])

print("\nCamera parameters")
print("-----------------")
print(f"fx = {fx}")
print(f"fy = {fy}")
print(f"cx = {cx}")
print(f"cy = {cy}")


# ==================================================
# LOAD IMAGE
# ==================================================

image = cv2.imread(str(IMAGE_PATH))

if image is None:
    raise FileNotFoundError(
        f"Could not load image: {IMAGE_PATH}"
    )

image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

image_height, image_width = image.shape[:2]

print("\nImage")
print("-----")
print(f"Width  = {image_width}")
print(f"Height = {image_height}")


# ==================================================
# LOAD DEPTH
# ==================================================

depth = np.load(DEPTH_PATH).astype(np.float32)

print("\nOriginal depth")
print("--------------")
print("Shape:", depth.shape)


# ==================================================
# RESIZE DEPTH IF NECESSARY
# ==================================================

if depth.shape != (image_height, image_width):

    print("Depth resolution does not match image.")
    print("Resizing depth map...")

    depth = cv2.resize(
        depth,
        (image_width, image_height),
        interpolation=cv2.INTER_LINEAR
    )


# ==================================================
# DEPTH STATISTICS
# ==================================================

print("\nDepth statistics")
print("----------------")
print("Minimum:", np.nanmin(depth))
print("Maximum:", np.nanmax(depth))
print("Mean:", np.nanmean(depth))


# ==================================================
# CREATE PIXEL GRID
# ==================================================

u, v = np.meshgrid(
    np.arange(image_width),
    np.arange(image_height)
)


# ==================================================
# VALID DEPTH MASK
# ==================================================

valid = (
    np.isfinite(depth)
    & (depth > 0)
)

print("\nValid pixels:", np.sum(valid))


# ==================================================
# EXTRACT VALID VALUES
# ==================================================

z = depth[valid]

u_valid = u[valid]
v_valid = v[valid]

colors = image[valid] / 255.0


# ==================================================
# RAY CASTING / BACK-PROJECTION
# ==================================================

x = (u_valid - cx) * z / fx

y = (v_valid - cy) * z / fy


# ==================================================
# CREATE 3D POINTS
# ==================================================

points = np.column_stack(
    (x, y, z)
)

print("\n3D reconstruction")
print("-----------------")
print("Generated points:", len(points))


# ==================================================
# CREATE OPEN3D POINT CLOUD
# ==================================================

point_cloud = o3d.geometry.PointCloud()

point_cloud.points = (
    o3d.utility.Vector3dVector(points)
)

point_cloud.colors = (
    o3d.utility.Vector3dVector(colors)
)


# ==================================================
# VOXEL DOWNSAMPLING
# ==================================================

print("\nDownsampling...")

point_cloud = point_cloud.voxel_down_sample(
    voxel_size=0.2
)

print(
    "After downsampling:",
    len(point_cloud.points)
)


# ==================================================
# OUTLIER REMOVAL
# ==================================================

print("\nRemoving outliers...")

point_cloud, _ = (
    point_cloud.remove_statistical_outlier(
        nb_neighbors=20,
        std_ratio=2.0
    )
)

print(
    "After outlier removal:",
    len(point_cloud.points)
)


# ==================================================
# SAVE
# ==================================================

OUTPUT_PATH.parent.mkdir(
    exist_ok=True
)

success = o3d.io.write_point_cloud(
    str(OUTPUT_PATH),
    point_cloud
)

if not success:
    raise RuntimeError(
        "Failed to save point cloud."
    )

print("\n================================")
print("3D reconstruction successful!")
print("Saved:", OUTPUT_PATH)
print("================================")