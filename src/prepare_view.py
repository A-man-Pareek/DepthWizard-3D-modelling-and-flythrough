import open3d as o3d

INPUT = "output/scene_3d.ply"
OUTPUT = "output/scene_3d_preview.ply"

print("Loading mesh...")

mesh = o3d.io.read_triangle_mesh(INPUT)

print("Original vertices:", len(mesh.vertices))
print("Original triangles:", len(mesh.triangles))

print("Creating preview...")

# Reduce the number of triangles for easier viewing
target_triangles = 200000

mesh = mesh.simplify_quadric_decimation(
    target_number_of_triangles=target_triangles
)

mesh.compute_vertex_normals()

o3d.io.write_triangle_mesh(
    OUTPUT,
    mesh
)

print()
print("==============================")
print("3D PREVIEW CREATED")
print("==============================")
print("Vertices:", len(mesh.vertices))
print("Triangles:", len(mesh.triangles))
print("Saved:", OUTPUT)
print("==============================")