import numpy as np
import open3d as o3d
import os


# ============================================================
# SETTINGS
# ============================================================

DEPTH_PATH = "output/depth.npy"

OUTPUT_PATH = "output/raycast_pointcloud.ply"


# ============================================================
# LOAD DEPTH MAP
# ============================================================

print("Loading depth map...")

depth = np.load(DEPTH_PATH).astype(np.float32)

height, width = depth.shape

print("Depth shape:", depth.shape)


# ============================================================
# CAMERA PARAMETERS
# ============================================================
#
# IMPORTANT:
# These are temporary parameters for testing the
# ray-casting pipeline.
#
# We will replace them with calibrated/geometric
# parameters later.
# ============================================================

fx = width
fy = width

cx = width / 2.0
cy = height / 2.0


print()
print("Camera parameters:")
print("fx =", fx)
print("fy =", fy)
print("cx =", cx)
print("cy =", cy)


# ============================================================
# CREATE PIXEL GRID
# ============================================================

u, v = np.meshgrid(
    np.arange(width),
    np.arange(height)
)


# ============================================================
# DEPTH VALUES
# ============================================================

Z = depth


# ============================================================
# RAY CASTING / BACK-PROJECTION
# ============================================================

X = (u - cx) * Z / fx

Y = (v - cy) * Z / fy


# ============================================================
# STACK INTO 3D POINTS
# ============================================================

points = np.stack(
    (X, Y, Z),
    axis=-1
)


# ============================================================
# REMOVE INVALID VALUES
# ============================================================

valid = np.isfinite(points).all(axis=2)

points = points[valid]


print()
print("3D reconstruction complete.")
print("Number of points:", len(points))


# ============================================================
# CREATE OPEN3D POINT CLOUD
# ============================================================

point_cloud = o3d.geometry.PointCloud()

point_cloud.points = o3d.utility.Vector3dVector(
    points
)


# ============================================================
# SAVE POINT CLOUD
# ============================================================

os.makedirs("output", exist_ok=True)

o3d.io.write_point_cloud(
    OUTPUT_PATH,
    point_cloud
)

print()
print("Point cloud saved:")
print(OUTPUT_PATH)


# ============================================================
# SUMMARY
# ============================================================

print()
print("========== POINT CLOUD ==========")

print("Points:", len(points))

print(
    "X range:",
    float(points[:, 0].min()),
    "to",
    float(points[:, 0].max())
)

print(
    "Y range:",
    float(points[:, 1].min()),
    "to",
    float(points[:, 1].max())
)

print(
    "Z range:",
    float(points[:, 2].min()),
    "to",
    float(points[:, 2].max())
)

print("=================================")