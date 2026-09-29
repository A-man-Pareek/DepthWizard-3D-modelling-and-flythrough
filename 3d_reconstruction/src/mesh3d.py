import cv2
import json
import numpy as np
import open3d as o3d


# ==================================================
# FILES
# ==================================================

IMAGE_PATH = "input/test.png"
DEPTH_PATH = "input/depth.npy"
CAMERA_PATH = "camera_params.json"

OUTPUT_PATH = "output/scene_3d.ply"


# ==================================================
# LOAD CAMERA
# ==================================================

with open(CAMERA_PATH, "r") as file:
    camera = json.load(file)

fx = float(camera["fx"])
fy = float(camera["fy"])
cx = float(camera["cx"])
cy = float(camera["cy"])


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

depth = np.load(
    DEPTH_PATH
).astype(np.float32)


height, width = image.shape[:2]


# ==================================================
# RESIZE DEPTH
# ==================================================

if depth.shape != (height, width):

    depth = cv2.resize(
        depth,
        (width, height),
        interpolation=cv2.INTER_LINEAR
    )


# ==================================================
# CREATE PIXEL GRID
# ==================================================

u, v = np.meshgrid(
    np.arange(width),
    np.arange(height)
)


# ==================================================
# VALID DEPTH
# ==================================================

valid = (
    np.isfinite(depth)
    & (depth > 0)
)


# ==================================================
# BACK-PROJECTION
# ==================================================

z = depth

x = (u - cx) * z / fx

y = (v - cy) * z / fy


# ==================================================
# CREATE VERTICES
# ==================================================

vertices = np.column_stack(
    (
        x[valid],
        y[valid],
        z[valid]
    )
)


# ==================================================
# CREATE COLORS
# ==================================================

colors = image[valid] / 255.0


# ==================================================
# MAP IMAGE PIXELS TO VERTEX INDICES
# ==================================================

vertex_index = -np.ones(
    (height, width),
    dtype=np.int32
)

vertex_index[valid] = np.arange(
    len(vertices)
)


# ==================================================
# CREATE TRIANGLES
# ==================================================

triangles = []


for y_pixel in range(height - 1):

    for x_pixel in range(width - 1):

        a = vertex_index[
            y_pixel,
            x_pixel
        ]

        b = vertex_index[
            y_pixel,
            x_pixel + 1
        ]

        c = vertex_index[
            y_pixel + 1,
            x_pixel
        ]

        d = vertex_index[
            y_pixel + 1,
            x_pixel + 1
        ]


        # First triangle
        if a >= 0 and b >= 0 and c >= 0:

            triangles.append(
                [a, b, c]
            )


        # Second triangle
        if b >= 0 and c >= 0 and d >= 0:

            triangles.append(
                [b, d, c]
            )


triangles = np.asarray(
    triangles,
    dtype=np.int32
)


# ==================================================
# CREATE MESH
# ==================================================

mesh = o3d.geometry.TriangleMesh()

mesh.vertices = (
    o3d.utility.Vector3dVector(
        vertices
    )
)

mesh.triangles = (
    o3d.utility.Vector3iVector(
        triangles
    )
)

mesh.vertex_colors = (
    o3d.utility.Vector3dVector(
        colors
    )
)


# ==================================================
# COMPUTE NORMALS
# ==================================================

print("Computing mesh normals...")

mesh.compute_vertex_normals()


# ==================================================
# SAVE
# ==================================================

print("Saving 3D mesh...")

o3d.io.write_triangle_mesh(
    OUTPUT_PATH,
    mesh
)


print()
print("================================")
print("3D MESH CREATED")
print("================================")
print("Vertices:", len(mesh.vertices))
print("Triangles:", len(mesh.triangles))
print("Saved:", OUTPUT_PATH)
print("================================")