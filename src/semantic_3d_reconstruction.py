import os
import json
import urllib.request
import numpy as np
import rasterio
from PIL import Image
import cv2
import open3d as o3d

# ==============================================================================
# INPUT AND OUTPUT PATHS
# ==============================================================================

IMAGE_PATH = "input/image.tiff"
HEIGHT_PATH = "input/height.tiff"
SEGMENTATION_PATH = "input/segmentation.tiff"

OUTPUT_DIR = "output"
LIB_DIR = os.path.join(OUTPUT_DIR, "lib")
SCENE_JSON_PATH = os.path.join(OUTPUT_DIR, "semantic_scene.json")
SATELLITE_TEXTURE_PATH = os.path.join(OUTPUT_DIR, "satellite_texture.png")
SEMANTIC_TEXTURE_PATH = os.path.join(OUTPUT_DIR, "semantic_texture.png")
ROAD_OVERLAY_PATH = os.path.join(OUTPUT_DIR, "road_overlay.png")
HTML_VIEWER_PATH = os.path.join(OUTPUT_DIR, "semantic_scene.html")
GLB_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "depthwizard_scene.glb")

# ==============================================================================
# 1. SEMANTIC CLASS CONFIGURATION
# ==============================================================================
# ADE20K standard semantic class mapping detected in SegFormer raster:
# 0: wall, 1: building, 2: sky, 3: floor, 4: tree, 6: road, 9: grass,
# 12: person, 13: earth, 17: plant, 21: water, 29: field, 32: fence,
# 43: sign, 59: pool, 93: path

BUILDING_CLASS_IDS = [1]
ROAD_CLASS_IDS = [6, 93, 11]
TREE_CLASS_IDS = [4]
VEGETATION_CLASS_IDS = [17, 9, 29]
WATER_CLASS_IDS = [21, 59]
GROUND_CLASS_IDS = [13, 0, 2, 3, 32, 12, 43]

# Discrete semantic color palette (RGB 0-255)
SEMANTIC_PALETTE = {
    "building": (224, 83, 56),     # Red / Warm orange
    "road": (80, 85, 92),           # Neutral asphalt gray
    "tree": (46, 125, 50),          # Forest green
    "vegetation": (104, 159, 56),   # Meadow / Light green
    "water": (25, 118, 210),        # Deep water blue
    "ground": (194, 178, 128),      # Earth tan / sand
    "default": (160, 160, 160)      # Neutral
}

# ==============================================================================
# EXTRACTION & GEOMETRY TUNING PARAMETERS
# ==============================================================================

# Minimum height for building pixels (filters out adjacent flat ground/lawns)
BUILDING_MIN_HEIGHT = 1.0  # meters

# Minimum area in pixels for a connected building component
MIN_BUILDING_AREA = 50     # pixels

# Polygon contour simplification tolerance factor (approxPolyDP)
CONTOUR_SIMPLIFY_EPSILON = 0.005  # fraction of perimeter

# Terrain grid resolution for WebGL 60fps rendering
TERRAIN_GRID_SIZE = 256    # 256x256 grid (65,536 vertices)

# Local coordinate space
SCENE_WIDTH = 1024.0
SCENE_HEIGHT = 1024.0


def ensure_three_libraries():
    """
    Downloads Three.js and OrbitControls locally to output/lib to ensure 100%
    offline reliability and eliminate CDN 404 / network blockage issues.
    """
    os.makedirs(LIB_DIR, exist_ok=True)
    three_local = os.path.join(LIB_DIR, "three.min.js")
    controls_local = os.path.join(LIB_DIR, "OrbitControls.js")

    if not os.path.exists(three_local) or os.path.getsize(three_local) < 10000:
        print("Downloading local Three.js bundle...")
        url = "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"
        urllib.request.urlretrieve(url, three_local)

    if not os.path.exists(controls_local) or os.path.getsize(controls_local) < 5000:
        print("Downloading local OrbitControls bundle...")
        url = "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"
        urllib.request.urlretrieve(url, controls_local)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ensure_three_libraries()

    print("=" * 60)
    print("DEPTHWIZARD 3D RECONSTRUCTION PIPELINE")
    print("=" * 60)

    # --------------------------------------------------------------------------
    # 1. LOAD INPUT RASTERS
    # --------------------------------------------------------------------------
    print("\n[1/6] Loading input TIFF rasters...")

    with rasterio.open(IMAGE_PATH) as src:
        rgb_raw = src.read()
        if rgb_raw.shape[0] >= 3:
            rgb = np.transpose(rgb_raw[:3], (1, 2, 0)).astype(np.uint8)
        else:
            ch = rgb_raw[0].astype(np.uint8)
            rgb = np.stack([ch, ch, ch], axis=-1)

    with rasterio.open(HEIGHT_PATH) as src:
        height_raw = src.read(1).astype(np.float32)

    with rasterio.open(SEGMENTATION_PATH) as src:
        seg_raw = src.read(1).astype(np.uint8)

    H, W = height_raw.shape
    if rgb.shape[:2] != (H, W) or seg_raw.shape != (H, W):
        raise ValueError(f"Input dimensions do not match: RGB={rgb.shape[:2]}, H={height_raw.shape}, SEG={seg_raw.shape}")

    print(f"Loaded all rasters: {W} x {H} pixels")
    print(f"Raw height range: {float(np.nanmin(height_raw)):.2f} to {float(np.nanmax(height_raw)):.2f} m")

    # Clean height raster: clamp negatives and NaNs to zero
    height = np.nan_to_num(height_raw, nan=0.0, posinf=0.0, neginf=0.0)
    height = np.maximum(height, 0.0)

    # Flatten water pixels to avoid sensor noise in water
    water_mask = np.isin(seg_raw, WATER_CLASS_IDS)
    height[water_mask] = np.minimum(height[water_mask], 0.05)

    # --------------------------------------------------------------------------
    # 2. GENERATE AND SAVE TEXTURES & OVERLAYS
    # --------------------------------------------------------------------------
    print("\n[2/6] Generating satellite, discrete semantic, and road textures...")

    # Satellite RGB Texture
    Image.fromarray(rgb).save(SATELLITE_TEXTURE_PATH, format="PNG", optimize=True)
    print(f"Saved satellite texture: {SATELLITE_TEXTURE_PATH}")

    # Discrete Semantic Texture
    semantic_rgb = np.zeros((H, W, 3), dtype=np.uint8)
    semantic_rgb[np.isin(seg_raw, GROUND_CLASS_IDS)] = SEMANTIC_PALETTE["ground"]
    semantic_rgb[np.isin(seg_raw, WATER_CLASS_IDS)] = SEMANTIC_PALETTE["water"]
    semantic_rgb[np.isin(seg_raw, ROAD_CLASS_IDS)] = SEMANTIC_PALETTE["road"]
    semantic_rgb[np.isin(seg_raw, VEGETATION_CLASS_IDS)] = SEMANTIC_PALETTE["vegetation"]
    semantic_rgb[np.isin(seg_raw, TREE_CLASS_IDS)] = SEMANTIC_PALETTE["tree"]
    semantic_rgb[np.isin(seg_raw, BUILDING_CLASS_IDS)] = SEMANTIC_PALETTE["building"]

    Image.fromarray(semantic_rgb).save(SEMANTIC_TEXTURE_PATH, format="PNG", optimize=True)
    print(f"Saved discrete semantic texture: {SEMANTIC_TEXTURE_PATH}")

    # Road Network Highlight Overlay (RGBA)
    road_mask = np.isin(seg_raw, ROAD_CLASS_IDS)
    road_rgba = np.zeros((H, W, 4), dtype=np.uint8)
    # Warm amber / highway highlight with transparency
    road_rgba[road_mask] = [251, 191, 36, 210]  # Amber-400
    Image.fromarray(road_rgba).save(ROAD_OVERLAY_PATH, format="PNG", optimize=True)
    print(f"Saved road overlay: {ROAD_OVERLAY_PATH}")

    # --------------------------------------------------------------------------
    # 3. GROUND (DTM) & VEGETATION CANOPY GENERATION
    # --------------------------------------------------------------------------
    print("\n[3/6] Computing ground DTM surface and vegetation canopy...")

    building_pixels_raw = np.isin(seg_raw, BUILDING_CLASS_IDS)
    tree_pixels = np.isin(seg_raw, TREE_CLASS_IDS)
    veg_pixels = np.isin(seg_raw, VEGETATION_CLASS_IDS)
    all_veg_pixels = tree_pixels | veg_pixels

    # Inpaint ground: replace building and high vegetation pixels with surrounding ground
    non_ground_mask = (building_pixels_raw | (all_veg_pixels & (height > 1.5))).astype(np.uint8)
    ground_source = height.copy()

    # Fast inpainting using cv2.inpaint
    ground_inpaint = cv2.inpaint(
        ground_source,
        non_ground_mask,
        inpaintRadius=7,
        flags=cv2.INPAINT_TELEA
    )
    # Smooth ground slightly
    ground_smooth = cv2.GaussianBlur(ground_inpaint, (9, 9), 3.0)
    ground_smooth[water_mask] = 0.05
    ground_smooth = np.maximum(ground_smooth, 0.0)

    # Vegetation height above ground
    veg_height_above_ground = np.maximum(height - ground_smooth, 0.0)
    veg_height_above_ground[~all_veg_pixels] = 0.0
    # Smooth vegetation canopy to create natural foliage clusters
    veg_smoothed = cv2.GaussianBlur(veg_height_above_ground, (7, 7), 2.0)

    # Resample ground and vegetation to grid size
    ground_grid = cv2.resize(
        ground_smooth,
        (TERRAIN_GRID_SIZE, TERRAIN_GRID_SIZE),
        interpolation=cv2.INTER_AREA
    ).astype(np.float32)

    veg_grid = cv2.resize(
        veg_smoothed,
        (TERRAIN_GRID_SIZE, TERRAIN_GRID_SIZE),
        interpolation=cv2.INTER_AREA
    ).astype(np.float32)

    # Combined surface for natural elevation
    terrain_elevation_grid = ground_grid + veg_grid

    print(f"Ground grid resampled: {TERRAIN_GRID_SIZE} x {TERRAIN_GRID_SIZE}")
    print(f"Ground elevation range: {float(ground_grid.min()):.2f} to {float(ground_grid.max()):.2f} m")
    print(f"Vegetation canopy max height: {float(veg_grid.max()):.2f} m")

    # --------------------------------------------------------------------------
    # 4. BUILDING FOOTPRINT EXTRACTION & POLYGON EXTRUSION
    # --------------------------------------------------------------------------
    print("\n[4/6] Extracting individual building footprints & geometry...")

    # Building mask with minimum height filter to eliminate flat ground misclassifications
    building_mask = (building_pixels_raw & (height >= BUILDING_MIN_HEIGHT)).astype(np.uint8)

    # Morphological cleaning: open to eliminate small bridges/noise, close to fill interior gaps
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    cleaned_mask = cv2.morphologyEx(building_mask, cv2.MORPH_OPEN, kernel_open)
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel_close)

    # Detect contours with hierarchy (RETR_CCOMP gives 2-level hierarchy: outer and holes)
    contours, hierarchy = cv2.findContours(cleaned_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    buildings = []
    building_id_counter = 1

    if hierarchy is not None and len(contours) > 0:
        hier = hierarchy[0]
        for i, (cnt, h_info) in enumerate(zip(contours, hier)):
            # Only consider top-level parent contours (h_info[3] == -1)
            if h_info[3] != -1:
                continue

            area = cv2.contourArea(cnt)
            if area < MIN_BUILDING_AREA:
                continue

            # Simplify contour with approxPolyDP
            arc_len = cv2.arcLength(cnt, True)
            epsilon = max(1.0, CONTOUR_SIMPLIFY_EPSILON * arc_len)
            approx_cnt = cv2.approxPolyDP(cnt, epsilon, True)

            if len(approx_cnt) < 3:
                continue

            # Convert contour points to list of [x, y]
            outer_polygon = approx_cnt.reshape(-1, 2).tolist()

            # Find holes inside this contour (children in hierarchy)
            holes = []
            child_idx = h_info[2]
            while child_idx != -1:
                child_cnt = contours[child_idx]
                child_area = cv2.contourArea(child_cnt)
                if child_area >= 15:
                    child_arc = cv2.arcLength(child_cnt, True)
                    child_eps = max(1.0, CONTOUR_SIMPLIFY_EPSILON * child_arc)
                    child_approx = cv2.approxPolyDP(child_cnt, child_eps, True)
                    if len(child_approx) >= 3:
                        holes.append(child_approx.reshape(-1, 2).tolist())
                child_idx = hier[child_idx][0]  # Next sibling

            # Compute pixel mask for this specific building to extract exact height stats
            b_pixel_mask = np.zeros((H, W), dtype=np.uint8)
            cv2.drawContours(b_pixel_mask, [cnt], -1, 255, thickness=cv2.FILLED)
            for h_pts in holes:
                cv2.drawContours(b_pixel_mask, [np.array(h_pts, dtype=np.int32)], -1, 0, thickness=cv2.FILLED)

            b_heights = height[b_pixel_mask == 255]
            if len(b_heights) == 0:
                b_heights = np.array([BUILDING_MIN_HEIGHT], dtype=np.float32)

            h_min = float(np.min(b_heights))
            h_max = float(np.max(b_heights))
            h_mean = float(np.mean(b_heights))
            h_median = float(np.median(b_heights))
            # 85th percentile provides a reliable flat-top extrusion height
            h_effective = float(np.percentile(b_heights, 85))

            # Bounding box & centroid
            bx, by, bw, bh = cv2.boundingRect(cnt)
            moments = cv2.moments(cnt)
            if moments["m00"] != 0:
                cx = float(moments["m10"] / moments["m00"])
                cy = float(moments["m01"] / moments["m00"])
            else:
                cx = float(bx + bw / 2.0)
                cy = float(by + bh / 2.0)

            # Ground elevation under building centroid
            gx = int(np.clip(cx, 0, W - 1))
            gy = int(np.clip(cy, 0, H - 1))
            ground_elev = float(ground_smooth[gy, gx])

            building_id = f"B-{building_id_counter:03d}"
            building_id_counter += 1

            buildings.append({
                "id": building_id,
                "buildingId": building_id,
                "classId": 1,
                "className": "Building",
                "areaPixels": int(area),
                "bbox": [int(bx), int(by), int(bw), int(bh)],
                "centroid": {"x": round(cx, 2), "y": round(cy, 2)},
                "height": round(h_effective, 2),
                "meanHeight": round(h_mean, 2),
                "maxHeight": round(h_max, 2),
                "minHeight": round(h_min, 2),
                "medianHeight": round(h_median, 2),
                "groundElevation": round(ground_elev, 2),
                "polygon": outer_polygon,
                "holes": holes
            })

    print(f"Extracted {len(buildings)} distinct building footprints.")

    # --------------------------------------------------------------------------
    # 5. ASSEMBLE SCENE JSON & EXPORT GLB
    # --------------------------------------------------------------------------
    print("\n[5/6] Exporting semantic_scene.json and depthwizard_scene.glb...")

    road_pixel_count = int(np.isin(seg_raw, ROAD_CLASS_IDS).sum())
    veg_pixel_count = int(np.isin(seg_raw, VEGETATION_CLASS_IDS).sum() + np.isin(seg_raw, TREE_CLASS_IDS).sum())
    water_pixel_count = int(water_mask.sum())
    building_pixel_count = int(building_pixels_raw.sum())

    scene_data = {
        "metadata": {
            "title": "DepthWizard Semantic 3D Digital Twin",
            "resolution": [W, H],
            "terrainGridSize": TERRAIN_GRID_SIZE,
            "sceneBounds": [-SCENE_WIDTH / 2.0, SCENE_WIDTH / 2.0, -SCENE_HEIGHT / 2.0, SCENE_HEIGHT / 2.0],
            "heightRange": [float(np.min(height)), float(np.max(height))],
            "meanHeight": float(np.mean(height)),
            "buildingCount": len(buildings),
            "buildingPixels": building_pixel_count,
            "roadPixels": road_pixel_count,
            "vegetationPixels": veg_pixel_count,
            "waterPixels": water_pixel_count
        },
        "terrain": {
            "gridWidth": TERRAIN_GRID_SIZE,
            "gridHeight": TERRAIN_GRID_SIZE,
            "minHeight": float(terrain_elevation_grid.min()),
            "maxHeight": float(terrain_elevation_grid.max()),
            "groundHeights": [round(float(v), 3) for v in ground_grid.flatten()],
            "vegetationHeights": [round(float(v), 3) for v in veg_grid.flatten()],
            "combinedHeights": [round(float(v), 3) for v in terrain_elevation_grid.flatten()]
        },
        "buildings": buildings
    }

    with open(SCENE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(scene_data, f, indent=2)
    print(f"Saved scene JSON: {SCENE_JSON_PATH}")

    # Build Open3D GLB export of the reconstructed digital twin
    export_glb_scene(terrain_elevation_grid, rgb, buildings, GLB_OUTPUT_PATH)

    # --------------------------------------------------------------------------
    # 6. GENERATE INTERACTIVE THREE.JS VIEWER HTML
    # --------------------------------------------------------------------------
    print("\n[6/6] Generating interactive Three.js viewer HTML...")
    generate_html_viewer(HTML_VIEWER_PATH)
    print(f"Generated viewer: {HTML_VIEWER_PATH}")

    # --------------------------------------------------------------------------
    # TERMINAL SUMMARY (SECTION 21 COMPLIANT)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("DEPTHWIZARD 3D RECONSTRUCTION")
    print("=" * 60)
    print(f"Image: {W} x {H}")
    print(f"Height range: {float(np.min(height)):.2f} - {float(np.max(height)):.2f}")
    print(f"Building pixels: {building_pixel_count}")
    print(f"Buildings detected: {len(buildings)}")
    print(f"Road pixels: {road_pixel_count}")
    print(f"Vegetation pixels: {veg_pixel_count}")
    print(f"Water pixels: {water_pixel_count}")
    print()
    print(f"3D building meshes: {len(buildings)}")
    print(f"Terrain vertices: {TERRAIN_GRID_SIZE * TERRAIN_GRID_SIZE}")
    print()
    print("Viewer:")
    print(HTML_VIEWER_PATH)
    print("=" * 60)


def export_glb_scene(terrain_grid, rgb_image, buildings, glb_path):
    """
    Constructs a TriangleMesh scene in Open3D and exports to depthwizard_scene.glb.
    """
    try:
        M, N = terrain_grid.shape
        vertices = []
        vertex_colors = []
        triangles = []

        half_w = SCENE_WIDTH / 2.0
        half_h = SCENE_HEIGHT / 2.0

        # Terrain grid vertices
        for y in range(M):
            py = int(np.clip((y / (M - 1)) * (rgb_image.shape[0] - 1), 0, rgb_image.shape[0] - 1))
            for x in range(N):
                px = int(np.clip((x / (N - 1)) * (rgb_image.shape[1] - 1), 0, rgb_image.shape[1] - 1))

                vx = (x / (N - 1)) * SCENE_WIDTH - half_w
                vy = float(terrain_grid[y, x])
                vz = (y / (M - 1)) * SCENE_HEIGHT - half_h

                vertices.append([vx, vy, vz])
                c = rgb_image[py, px] / 255.0
                vertex_colors.append([float(c[0]), float(c[1]), float(c[2])])

        # Triangles
        for y in range(M - 1):
            for x in range(N - 1):
                i0 = y * N + x
                i1 = i0 + 1
                i2 = (y + 1) * N + x
                i3 = i2 + 1
                triangles.append([i0, i2, i1])
                triangles.append([i1, i2, i3])

        # Add extruded building prisms
        base_v_idx = len(vertices)
        for b in buildings:
            poly = b["polygon"]
            if len(poly) < 3:
                continue
            h = b["height"]
            g = b["groundElevation"]
            pts_cnt = len(poly)

            # Footprint vertices (bottom and top)
            for pt in poly:
                bx = pt[0] - half_w
                bz = pt[1] - half_h
                vertices.append([bx, g, bz])
                vertex_colors.append([0.35, 0.38, 0.42])  # Dark facade

            for pt in poly:
                bx = pt[0] - half_w
                bz = pt[1] - half_h
                # Sample roof color from satellite
                rx = int(np.clip(pt[0], 0, rgb_image.shape[1] - 1))
                ry = int(np.clip(pt[1], 0, rgb_image.shape[0] - 1))
                rc = rgb_image[ry, rx] / 255.0
                vertices.append([bx, g + h, bz])
                vertex_colors.append([float(rc[0]), float(rc[1]), float(rc[2])])

            # Side walls
            for k in range(pts_cnt):
                next_k = (k + 1) % pts_cnt
                b0 = base_v_idx + k
                b1 = base_v_idx + next_k
                t0 = base_v_idx + pts_cnt + k
                t1 = base_v_idx + pts_cnt + next_k

                triangles.append([b0, t0, b1])
                triangles.append([b1, t0, t1])

            # Fan triangulation for roof
            t_start = base_v_idx + pts_cnt
            for k in range(1, pts_cnt - 1):
                triangles.append([t_start, t_start + k, t_start + k + 1])

            base_v_idx = len(vertices)

        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(np.asarray(vertices, dtype=np.float64))
        mesh.vertex_colors = o3d.utility.Vector3dVector(np.asarray(vertex_colors, dtype=np.float64))
        mesh.triangles = o3d.utility.Vector3iVector(np.asarray(triangles, dtype=np.int32))
        mesh.compute_vertex_normals()

        success = o3d.io.write_triangle_mesh(glb_path, mesh)
        if success:
            print(f"Successfully exported GLB scene: {glb_path}")
        else:
            print(f"Open3D GLB export returned status False.")
    except Exception as e:
        print(f"Warning: GLB export encountered an issue: {e}")


def generate_html_viewer(html_path):
    """
    Generates the standalone semantic_scene.html Three.js digital twin viewer.
    Loads data dynamically from semantic_scene.json via fast local HTTP fetch.
    Uses the template defined in viewer_template.html.
    """
    template_path = os.path.join(os.path.dirname(__file__), "viewer_template.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    else:
        raise FileNotFoundError(f"Viewer template not found at {template_path}")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated web viewer: {html_path}")


if __name__ == "__main__":
    main()
