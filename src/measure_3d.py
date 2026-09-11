import open3d as o3d
import numpy as np


POINTCLOUD_PATH = "output/pointcloud.ply"


# ---------------------------------------
# Load point cloud
# ---------------------------------------

pcd = o3d.io.read_point_cloud(
    POINTCLOUD_PATH
)

points = np.asarray(pcd.points)

print("Loaded points:", len(points))


# ---------------------------------------
# Select two example points
# ---------------------------------------

point_a = points[0]
point_b = points[len(points) // 2]


print("\nPoint A:")
print(point_a)

print("\nPoint B:")
print(point_b)


# ---------------------------------------
# Calculate 3D distance
# ---------------------------------------

distance = np.linalg.norm(
    point_a - point_b
)


print("\n==============================")
print("3D MEASUREMENT")
print("==============================")

print(
    f"Distance between points: "
    f"{distance:.2f} units"
)

print("==============================")