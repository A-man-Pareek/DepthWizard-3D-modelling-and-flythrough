import os
import numpy as np
import open3d as o3d
import rasterio
from PIL import Image
import plotly.graph_objects as go


# ============================================================
# SETTINGS
# ============================================================

MESH_INPUT = "output/depthwizard_final_mesh.ply"
SEGMENTATION_INPUT = "input/segmentation.tiff"

OUTPUT_PLY = "output/depthwizard_colored.ply"
OUTPUT_HTML = "output/depthwizard_3d_colored.html"


# ============================================================
# CLASS COLOURS
# ============================================================

# SegFormer / LoveDA-style class IDs from your segmentation
CLASS_COLORS = {

    0:  [0.55, 0.55, 0.55],   # background / unknown
    1:  [0.85, 0.15, 0.15],   # building
    2:  [0.55, 0.35, 0.20],   # road
    3:  [0.30, 0.50, 0.20],   # vegetation
    4:  [0.10, 0.65, 0.20],   # tree
    5:  [0.20, 0.45, 0.80],   # water
    6:  [0.45, 0.30, 0.20],   # wall
    7:  [0.70, 0.70, 0.30],   # plant
    8:  [0.60, 0.60, 0.60],
    9:  [0.40, 0.40, 0.40],
    10: [0.20, 0.60, 0.80],
    11: [0.30, 0.30, 0.30],
    12: [0.75, 0.75, 0.75],
    13: [0.65, 0.45, 0.25],
    14: [0.20, 0.50, 0.20],
    15: [0.80, 0.50, 0.20],
    16: [0.50, 0.25, 0.15],
    17: [0.45, 0.75, 0.25],
    18: [0.70, 0.40, 0.70],
    19: [0.40, 0.70, 0.70],
    20: [0.70, 0.70, 0.70],
    21: [0.25, 0.55, 0.75],
    22: [0.80, 0.80, 0.40],
    23: [0.50, 0.70, 0.30],
    24: [0.65, 0.35, 0.35],
    25: [0.35, 0.35, 0.65],
    26: [0.75, 0.35, 0.15],
    27: [0.35, 0.65, 0.35],
    28: [0.60, 0.45, 0.30],
    29: [0.45, 0.60, 0.75],
    30: [0.75, 0.60, 0.35],
    31: [0.35, 0.75, 0.60],
    32: [0.60, 0.35, 0.60],
    33: [0.80, 0.45, 0.45],
    34: [0.45, 0.80, 0.45],
    35: [0.45, 0.45, 0.80],
    36: [0.80, 0.65, 0.45],
    37: [0.45, 0.65, 0.80],
    38: [0.65, 0.45, 0.80],
    39: [0.80, 0.45, 0.65],
    40: [0.65, 0.80, 0.45],
    41: [0.45, 0.80, 0.65],
    42: [0.65, 0.45, 0.45],
    43: [0.45, 0.65, 0.45],
    44: [0.45, 0.45, 0.65],
    45: [0.65, 0.65, 0.45],
    46: [0.45, 0.65, 0.65],
    47: [0.65, 0.45, 0.65],
    48: [0.75, 0.55, 0.55],
    49: [0.55, 0.75, 0.55],
    50: [0.55, 0.55, 0.75],
}


# ============================================================
# LOAD MESH
# ============================================================

print("=" * 60)
print("DEPTHWIZARD 3D SEMANTIC VIEWER")
print("=" * 60)

print("\nLoading 3D mesh...")

mesh = o3d.io.read_triangle_mesh(MESH_INPUT)

if len(mesh.vertices) == 0:
    raise RuntimeError("Mesh is empty.")

vertices = np.asarray(mesh.vertices)

print("Vertices:", len(vertices))
print("Triangles:", len(mesh.triangles))


# ============================================================
# LOAD SEGMENTATION
# ============================================================

print("\nLoading segmentation...")

with rasterio.open(SEGMENTATION_INPUT) as src:
    segmentation = src.read(1)

print("Segmentation shape:", segmentation.shape)
print("Segmentation type:", segmentation.dtype)


# ============================================================
# MATCH SEGMENTATION TO 3D VERTICES
# ============================================================

vertex_count = len(vertices)

grid_size = int(round(np.sqrt(vertex_count)))

print("\nDetected 3D grid:", grid_size, "x", grid_size)

if grid_size * grid_size != vertex_count:

    print(
        "WARNING: Vertex count is not a perfect square."
    )

    print(
        "Using flattened segmentation mapping."
    )

    seg_resized = np.array(
        Image.fromarray(segmentation.astype(np.uint8)).resize(
            (vertex_count, 1),
            Image.Resampling.NEAREST
        )
    ).flatten()

else:

    # Resize segmentation to exactly match
    # the 3D reconstruction grid.

    seg_resized = np.array(
        Image.fromarray(segmentation.astype(np.uint8)).resize(
            (grid_size, grid_size),
            Image.Resampling.NEAREST
        )
    ).flatten()


# ============================================================
# CREATE VERTEX COLOURS
# ============================================================

print("\nApplying semantic colours...")

colors = np.zeros((vertex_count, 3), dtype=np.float64)

for i, class_id in enumerate(seg_resized):

    class_id = int(class_id)

    if class_id in CLASS_COLORS:
        colors[i] = CLASS_COLORS[class_id]
    else:
        colors[i] = [0.5, 0.5, 0.5]


# ============================================================
# ASSIGN COLOURS TO MESH
# ============================================================

mesh.vertex_colors = o3d.utility.Vector3dVector(colors)


# ============================================================
# SAVE COLOURED PLY
# ============================================================

print("\nSaving coloured 3D model...")

o3d.io.write_triangle_mesh(
    OUTPUT_PLY,
    mesh,
    write_vertex_colors=True
)

print("Saved:", OUTPUT_PLY)


# ============================================================
# CREATE PLOTLY VIEWER
# ============================================================

print("\nCreating interactive viewer...")

triangles = np.asarray(mesh.triangles)

x = vertices[:, 0]
y = vertices[:, 1]
z = vertices[:, 2]

# Convert RGB → Plotly colour strings
plotly_colors = [
    "rgb({}, {}, {})".format(
        int(c[0] * 255),
        int(c[1] * 255),
        int(c[2] * 255)
    )
    for c in colors
]


# Plotly mesh supports vertex intensity,
# so we use class IDs for semantic colouring.

intensity = seg_resized.astype(float)


fig = go.Figure(

    data=[
        go.Mesh3d(

            x=x,
            y=y,
            z=z,

            i=triangles[:, 0],
            j=triangles[:, 1],
            k=triangles[:, 2],

            intensity=intensity,

            colorscale=[
                [0.00, "rgb(140,140,140)"],
                [0.05, "rgb(220,60,60)"],
                [0.10, "rgb(150,90,50)"],
                [0.15, "rgb(70,150,70)"],
                [0.20, "rgb(40,170,70)"],
                [0.25, "rgb(50,120,210)"],
                [0.30, "rgb(120,100,70)"],
                [0.35, "rgb(180,180,80)"],
                [1.00, "rgb(180,180,180)"],
            ],

            cmin=0,
            cmax=93,

            flatshading=False,

            lighting=dict(
                ambient=0.55,
                diffuse=0.75,
                specular=0.25,
                roughness=0.7
            ),

            lightposition=dict(
                x=100,
                y=100,
                z=200
            ),

            hovertemplate=
                "X: %{x:.2f}<br>"
                "Y: %{y:.2f}<br>"
                "Z: %{z:.2f}<br>"
                "Class: %{intensity}<extra></extra>"
        )
    ]
)


# ============================================================
# LAYOUT
# ============================================================

fig.update_layout(

    title="DepthWizard — Semantic 3D Reconstruction",

    scene=dict(

        xaxis_title="X",
        yaxis_title="Y",
        zaxis_title="Height / Z",

        aspectmode="data",

        bgcolor="rgb(15,20,25)",

        camera=dict(
            eye=dict(
                x=1.6,
                y=1.6,
                z=1.2
            )
        )
    ),

    margin=dict(
        l=0,
        r=0,
        t=50,
        b=0
    )
)


# ============================================================
# SAVE HTML
# ============================================================

fig.write_html(
    OUTPUT_HTML,
    include_plotlyjs=True
)

print("\n" + "=" * 60)
print("3D SEMANTIC RECONSTRUCTION SUCCESSFUL")
print("=" * 60)

print("Coloured PLY:")
print(OUTPUT_PLY)

print("\nInteractive viewer:")
print(OUTPUT_HTML)

print("=" * 60)