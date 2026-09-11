import cv2
import numpy as np
import open3d as o3d
import json


# ==================================================
# FILE PATHS
# ==================================================

IMAGE_PATH = "input/test.png"
DEPTH_PATH = "input/depth.npy"

CAMERA_PATH = "camera_params.json"

OUTPUT_PATH = "output/pointcloud.ply"


# ==================================================
# LOAD CAMERA PARAMETERS
# ==================================================

with open(CAMERA_PATH, "r") as file:
    camera = json.load(file)

fx = camera["fx"]
fy = camera["fy"]
cx = camera["cx"]
cy = camera["cy"]

print("Camera parameters:")
print("fx =", fx)
print("fy =", fy)
print("cx =", cx)
print("cy =", cy)


# ==================================================
# LOAD IMAGE
# ==================================================

image = cv2.imread(IMAGE_PATH)

if image is None:
    raise FileNotFoundError(
        f"Could not load image: {IMAGE_PATH}"
    )

image = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2RGB
)


# ==================================================
# LOAD DEPTH
# ==================================================

depth = np.load(DEPTH_PATH).astype(np.float32)

print("Image shape:", image.shape)
print("Depth shape:", depth.shape)


# ==================================================
# CHECK DIMENSIONS
# ==================================================

if image.shape[:2] != depth.shape[:2]:

    raise ValueError(
        "Image and depth map dimensions do not match."
    )


height, width = depth.shape


# ==================================================
# CREATE PIXEL GRID
# ==================================================

u, v = np.meshgrid(
    np.arange(width),
    np.arange(height)
)


# ==================================================
# FLATTEN ARRAYS
# ==================================================

z = depth.flatten()

u = u.flatten()
v = v.flatten()

colors = image.reshape(-1, 3) / 255.0


# ==================================================
# REMOVE INVALID DEPTH
# ==================================================

valid = (
    np.isfinite(z)
    & (z > 0)
)

z = z[valid]
u = u[valid]
v = v[valid]
colors = colors[valid]


# ==================================================
# 2D → 3D BACK-PROJECTION
# ==================================================

x = (u - cx) * z / fx

y = (v - cy) * z / fy


points = np.column_stack(
    (x, y, z)
)


print("Number of 3D points:", len(points))


# ==================================================
# CREATE POINT CLOUD
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

print("Downsampling point cloud...")

point_cloud = point_cloud.voxel_down_sample(
    voxel_size=0.2
)

print(
    "Points after downsampling:",
    len(point_cloud.points)
)


# ==================================================
# REMOVE OUTLIERS
# ==================================================

print("Removing outliers...")

point_cloud, inlier_indices = (
    point_cloud.remove_statistical_outlier(
        nb_neighbors=20,
        std_ratio=2.0
    )
)

print(
    "Points after filtering:",
    len(point_cloud.points)
)


# ==================================================
# SAVE POINT CLOUD
# ==================================================

o3d.io.write_point_cloud(
    OUTPUT_PATH,
    point_cloud
)

print(
    "3D point cloud saved to:",
    OUTPUT_PATH
)


# ==================================================
# VISUALIZE
# ==================================================

# vis = o3d.visualization.Visualizer()

# vis.create_window(
#    window_name="DepthWizard 3D Point Cloud",
#    width=1200,
#    height=800
# )

# vis.add_geometry(point_cloud)

# vis.poll_events()
# vis.update_renderer()

# vis.run()

# vis.destroy_window()