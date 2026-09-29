"""
DepthWizard: Semantic 3D Reconstruction Engine
===============================================
Reconstructs an interactive, photorealistic 3D satellite digital twin from:
  - input/image.tiff        : 1024x1024 RGB satellite imagery
  - input/height.tiff       : 1024x1024 HTC-DC Net predicted AGL height (float32, meters)
  - input/segmentation.tiff : 1024x1024 SegFormer class-ID raster (uint8)

Outputs:
  - output/semantic_scene.json   : Scene metadata, terrain grid & individual building polygons + stats
  - output/satellite_texture.png : Contrast-enhanced sRGB satellite texture
  - output/semantic_texture.png  : Discrete semantic class-colored texture
  - output/semantic_scene.html   : Standalone Three.js 3D viewer with raycasting selection & flythrough
  - output/depthwizard_scene.glb : Standard 3D GLB digital twin model
"""

import os
import sys
import json
import numpy as np
import rasterio
import cv2
from PIL import Image, ImageEnhance
import trimesh
import scipy.spatial

# ==============================================================================
# 1. SEMANTIC CLASS ID CONFIGURATION
# Matches SegFormer ADE20K trained raster classes used in DepthWizard.
# Clearly marked and easily editable.
# ==============================================================================
BUILDING_CLASS_IDS = [1, 25]        # 1: Building, 25: House
ROAD_CLASS_IDS = [6, 11]            # 6: Road, 11: Sidewalk / Pavement
TREE_CLASS_IDS = [4]                # 4: Tree
VEGETATION_CLASS_IDS = [9, 17]      # 9: Grass, 17: Plant / Flora
WATER_CLASS_IDS = [21, 27]          # 21: Water, 27: Sea / Waterbody
GROUND_CLASS_IDS = [0, 3, 13, 122]  # 0: Wall/Ground, 3: Floor, 13: Earth, 122: Land / Soil

# Processing parameters
MIN_BUILDING_AREA_PIXELS = 50       # Ignore tiny noise fragments (<50 px)
POLYGON_SIMPLIFY_EPSILON = 1.0      # Contour simplification epsilon in pixels
SCENE_EXTENT = 200.0                # Three.js scene dimension (200x200 units)
TERRAIN_GRID_SIZE = 256             # Downsampled terrain grid resolution for 60fps rendering
HORIZONTAL_SCALE = SCENE_EXTENT / 1024.0  # Scene units per pixel (~0.1953 GSD equivalent)
DEFAULT_VERTICAL_SCALE = 1.0

# Discrete Semantic Colors (RGB [0-255])
SEMANTIC_COLORS = {
    "building": [231, 76, 60],     # Warm architectural orange-red (#e74c3c)
    "road": [52, 73, 94],          # Clean slate asphalt (#34495e)
    "tree": [39, 174, 96],         # Rich forest green (#27ae60)
    "vegetation": [46, 204, 113],  # Lush grass green (#2ecc71)
    "water": [41, 128, 185],       # Deep azure blue (#2980b9)
    "ground": [160, 130, 96],      # Warm tan / earth (#a08260)
    "other": [149, 165, 166],      # Neutral concrete gray (#95a5a6)
}


def resolve_paths():
    """Resolve input and output paths relative to script or current directory."""
    # Find directory containing input/
    candidates = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ]
    base_dir = os.getcwd()
    for c in candidates:
        if os.path.isdir(os.path.join(c, "input")):
            base_dir = c
            break

    input_dir = os.path.join(base_dir, "input")
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    return base_dir, input_dir, output_dir


def load_input_rasters(input_dir: str):
    """Load and validate image.tiff, height.tiff, and segmentation.tiff."""
    img_path = os.path.join(input_dir, "image.tiff")
    hgt_path = os.path.join(input_dir, "height.tiff")
    seg_path = os.path.join(input_dir, "segmentation.tiff")

    for p in (img_path, hgt_path, seg_path):
        if not os.path.isfile(p):
            raise FileNotFoundError(f"Required input raster not found: {p}")

    # 1. RGB satellite image
    with rasterio.open(img_path) as src:
        if src.count >= 3:
            r = src.read(1)
            g = src.read(2)
            b = src.read(3)
            rgb = np.stack([r, g, b], axis=-1)
        else:
            band = src.read(1)
            rgb = np.stack([band, band, band], axis=-1)

    # 2. HTC-DC Net predicted AGL height
    with rasterio.open(hgt_path) as src:
        raw_height = src.read(1).astype(np.float32)

    # 3. SegFormer semantic class map
    with rasterio.open(seg_path) as src:
        seg = src.read(1).astype(np.uint8)

    h, w = rgb.shape[:2]
    if (h, w) != raw_height.shape or (h, w) != seg.shape:
        raise ValueError(
            f"Raster dimension mismatch: image {rgb.shape[:2]}, height {raw_height.shape}, seg {seg.shape}"
        )

    # Clean NaNs or negatives in height
    raw_height = np.maximum(np.nan_to_num(raw_height, nan=0.0), 0.0)

    return rgb, raw_height, seg


def generate_satellite_texture(rgb: np.ndarray, output_path: str) -> str:
    """Enhance and save photographic satellite texture."""
    # Gentle contrast stretch for optimal dynamic range
    p2, p98 = np.percentile(rgb, (2, 98), axis=(0, 1))
    stretched = np.zeros_like(rgb, dtype=np.float32)
    for c in range(3):
        spread = max(p98[c] - p2[c], 1.0)
        stretched[..., c] = np.clip((rgb[..., c].astype(np.float32) - p2[c]) * (255.0 / spread), 0, 255)
    
    pil_img = Image.fromarray(stretched.astype(np.uint8))
    # Subtle enhancement for crisp architectural details
    pil_img = ImageEnhance.Color(pil_img).enhance(1.15)
    pil_img = ImageEnhance.Contrast(pil_img).enhance(1.08)
    pil_img = ImageEnhance.Sharpness(pil_img).enhance(1.20)
    pil_img.save(output_path, format="PNG", optimize=True)
    return output_path


def generate_semantic_texture(seg: np.ndarray, output_path: str) -> str:
    """Generate discrete semantic class color map."""
    h, w = seg.shape
    color_img = np.zeros((h, w, 3), dtype=np.uint8)
    color_img[:] = SEMANTIC_COLORS["other"]

    # Ground
    ground_mask = np.isin(seg, GROUND_CLASS_IDS)
    color_img[ground_mask] = SEMANTIC_COLORS["ground"]

    # Roads
    road_mask = np.isin(seg, ROAD_CLASS_IDS)
    color_img[road_mask] = SEMANTIC_COLORS["road"]

    # Water
    water_mask = np.isin(seg, WATER_CLASS_IDS)
    color_img[water_mask] = SEMANTIC_COLORS["water"]

    # Vegetation & Trees
    veg_mask = np.isin(seg, VEGETATION_CLASS_IDS)
    color_img[veg_mask] = SEMANTIC_COLORS["vegetation"]
    tree_mask = np.isin(seg, TREE_CLASS_IDS)
    color_img[tree_mask] = SEMANTIC_COLORS["tree"]

    # Buildings
    bldg_mask = np.isin(seg, BUILDING_CLASS_IDS)
    color_img[bldg_mask] = SEMANTIC_COLORS["building"]

    pil_img = Image.fromarray(color_img)
    pil_img.save(output_path, format="PNG", optimize=True)
    return output_path


def compute_ground_and_vegetation_elevation(raw_height: np.ndarray, seg: np.ndarray):
    """
    Remove buildings from ground elevation by inpainting from non-building pixels.
    Elevate vegetation surfaces organically based on HTC-DC heights.
    """
    h, w = raw_height.shape
    bldg_mask = np.isin(seg, BUILDING_CLASS_IDS).astype(np.uint8)
    
    # Close small gaps in buildings and dilate slightly to ensure walls are excluded from ground
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    bldg_dilated = cv2.dilate(bldg_mask, kernel, iterations=1)

    # Inpaint building areas using neighboring terrain heights
    h_min, h_max = float(raw_height.min()), float(raw_height.max())
    h_span = max(h_max - h_min, 1e-4)
    h_norm = ((raw_height - h_min) / h_span * 255.0).astype(np.uint8)

    inpaint_mask = (bldg_dilated * 255).astype(np.uint8)
    inpainted_norm = cv2.inpaint(h_norm, inpaint_mask, inpaintRadius=9, flags=cv2.INPAINT_TELEA)
    ground_height = (inpainted_norm.astype(np.float32) / 255.0) * h_span + h_min

    # Smooth ground elevation to eliminate high-frequency spikes
    ground_height = cv2.GaussianBlur(ground_height, (15, 15), 0)

    # Water is flat at 0
    water_mask = np.isin(seg, WATER_CLASS_IDS)
    ground_height[water_mask] = 0.0

    # Vegetation height (trees and plants)
    veg_mask = np.isin(seg, TREE_CLASS_IDS + VEGETATION_CLASS_IDS)
    veg_height = np.zeros_like(raw_height)
    if np.any(veg_mask):
        raw_veg = np.maximum(raw_height - ground_height, 0.0)
        # Smooth vegetation canopies to avoid jagged per-pixel noise
        veg_smooth = cv2.GaussianBlur(raw_veg, (7, 7), 0)
        veg_height[veg_mask] = veg_smooth[veg_mask]

    # Combined terrain elevation = ground + vegetation (buildings are separate extruded meshes!)
    terrain_elevation = ground_height.copy()
    terrain_elevation[veg_mask] += veg_height[veg_mask]
    terrain_elevation[water_mask] = 0.0

    return ground_height, terrain_elevation, veg_height


def extract_building_objects(raw_height: np.ndarray, ground_height: np.ndarray, seg: np.ndarray):
    """
    Extract individual connected building components and contours.
    Computes footprint polygons, bounding box, centroid, and height statistics.
    """
    bldg_mask = np.isin(seg, BUILDING_CLASS_IDS).astype(np.uint8)

    # Morphological cleaning: close gaps, remove isolated 1-2 pixel noise
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    k_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cleaned = cv2.morphologyEx(bldg_mask, cv2.MORPH_CLOSE, k_close)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, k_open)

    # Connected component analysis with hierarchy (preserves interior courtyards/holes)
    contours, hierarchy = cv2.findContours(cleaned, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    
    buildings = []
    building_idx = 0

    if hierarchy is not None and len(contours) > 0:
        hierarchy = hierarchy[0]
        for i, cnt in enumerate(contours):
            # Outer contours have parent == -1
            if hierarchy[i][3] != -1:
                continue

            area = cv2.contourArea(cnt)
            if area < MIN_BUILDING_AREA_PIXELS:
                continue

            building_idx += 1
            b_id = f"B-{building_idx:03d}"

            # Simplify outer polygon contour
            approx_outer = cv2.approxPolyDP(cnt, POLYGON_SIMPLIFY_EPSILON, closed=True)
            if len(approx_outer) < 3:
                continue

            # Identify child holes (courtyards)
            holes = []
            child_idx = hierarchy[i][2]
            while child_idx != -1:
                hole_cnt = contours[child_idx]
                if cv2.contourArea(hole_cnt) >= 15:
                    approx_hole = cv2.approxPolyDP(hole_cnt, POLYGON_SIMPLIFY_EPSILON, closed=True)
                    if len(approx_hole) >= 3:
                        holes.append([[float(p[0][0]), float(p[0][1])] for p in approx_hole])
                child_idx = hierarchy[child_idx][0] # Next sibling hole

            # Extract building component mask for statistics
            comp_mask = np.zeros_like(seg, dtype=np.uint8)
            cv2.drawContours(comp_mask, [cnt], -1, 1, -1)
            for hole in holes:
                hole_pts = np.array(hole, dtype=np.int32).reshape((-1, 1, 2))
                cv2.drawContours(comp_mask, [hole_pts], -1, 0, -1)

            # Bounding box [x_min, y_min, x_max, y_max]
            bx, by, bw, bh = cv2.boundingRect(cnt)
            bbox = [int(bx), int(by), int(bx + bw), int(by + bh)]

            # Centroid
            M = cv2.moments(cnt)
            if M["m00"] > 1e-4:
                cx = float(M["m10"] / M["m00"])
                cy = float(M["m01"] / M["m00"])
            else:
                cx = float(bx + bw / 2.0)
                cy = float(by + bh / 2.0)

            # Height statistics from HTC-DC Net raster
            h_vals = raw_height[comp_mask == 1]
            if len(h_vals) == 0:
                h_vals = np.array([1.0], dtype=np.float32)

            h_mean = float(np.mean(h_vals))
            h_max = float(np.max(h_vals))
            h_min = float(np.min(h_vals))
            h_med = float(np.median(h_vals))
            h_p90 = float(np.percentile(h_vals, 90))

            # Base ground elevation under this building
            ground_vals = ground_height[comp_mask == 1]
            b_ground_elev = float(np.mean(ground_vals)) if len(ground_vals) > 0 else 0.0

            # Extrusion height: robust roof elevation above local ground
            # Uses 90th percentile to accurately represent true roof slab
            extrusion_height = max(float(h_p90), float(h_mean), 0.45)

            outer_pts = [[float(p[0][0]), float(p[0][1])] for p in approx_outer]

            buildings.append({
                "id": b_id,
                "classId": 1,
                "className": "Building",
                "areaPixels": int(area),
                "bbox": bbox,
                "centroid": {"x": round(cx, 2), "y": round(cy, 2)},
                "height": round(extrusion_height, 2),
                "meanHeight": round(h_mean, 2),
                "maxHeight": round(h_max, 2),
                "minHeight": round(h_min, 2),
                "medianHeight": round(h_med, 2),
                "groundElevation": round(b_ground_elev, 2),
                "polygon": outer_pts,
                "holes": holes,
            })

    return buildings


def export_glb_digital_twin(
    terrain_elevation: np.ndarray,
    buildings: list,
    output_glb_path: str,
    grid_size: int = 128,
):
    """
    Export complete 3D digital twin as a standard GLB model (Terrain + Buildings).
    Uses trimesh and Delaunay triangulation.
    """
    try:
        h, w = terrain_elevation.shape
        # Downsample terrain grid for GLB
        down_h = cv2.resize(terrain_elevation, (grid_size, grid_size), interpolation=cv2.INTER_LINEAR)
        
        xs = np.linspace(-SCENE_EXTENT / 2.0, SCENE_EXTENT / 2.0, grid_size)
        zs = np.linspace(-SCENE_EXTENT / 2.0, SCENE_EXTENT / 2.0, grid_size)
        xv, zv = np.meshgrid(xs, zs)
        yv = down_h

        # Generate terrain vertices
        terrain_verts = np.column_stack([xv.ravel(), yv.ravel(), zv.ravel()])
        
        # Grid faces
        faces = []
        for i in range(grid_size - 1):
            for j in range(grid_size - 1):
                idx = i * grid_size + j
                faces.append([idx, idx + grid_size, idx + 1])
                faces.append([idx + 1, idx + grid_size, idx + grid_size + 1])
        terrain_faces = np.array(faces, dtype=np.int32)

        terrain_mesh = trimesh.Trimesh(vertices=terrain_verts, faces=terrain_faces)
        terrain_mesh.visual.vertex_colors = np.full((len(terrain_verts), 4), [180, 185, 175, 255], dtype=np.uint8)

        scene = trimesh.Scene([terrain_mesh])

        # Extrude each building into a trimesh
        scale = HORIZONTAL_SCALE
        for b in buildings:
            poly_pts = b["polygon"]
            if len(poly_pts) < 3:
                continue

            # Convert pixel coords to scene coords (X, Z)
            pts_2d = np.array([
                [(pt[0] - 512.0) * scale, (pt[1] - 512.0) * scale]
                for pt in poly_pts
            ], dtype=np.float32)

            n_pts = len(pts_2d)
            if n_pts < 3:
                continue

            b_ground = b["groundElevation"]
            b_height = b["height"]

            bot_verts = np.column_stack([pts_2d[:, 0], np.full(n_pts, b_ground), pts_2d[:, 1]])
            top_verts = np.column_stack([pts_2d[:, 0], np.full(n_pts, b_ground + b_height), pts_2d[:, 1]])
            b_verts = np.vstack([bot_verts, top_verts])

            b_faces = []
            # Side wall quad faces
            for k in range(n_pts):
                nxt = (k + 1) % n_pts
                b_faces.append([k, nxt, nxt + n_pts])
                b_faces.append([k, nxt + n_pts, k + n_pts])

            # Triangulate top cap
            try:
                delaunay = scipy.spatial.Delaunay(pts_2d)
                for tri in delaunay.simplices:
                    # Filter triangles whose center is inside the polygon
                    mid = np.mean(pts_2d[tri], axis=0)
                    dist = cv2.pointPolygonTest(pts_2d, (float(mid[0]), float(mid[1])), False)
                    if dist >= 0:
                        b_faces.append([tri[0] + n_pts, tri[1] + n_pts, tri[2] + n_pts])
                        b_faces.append([tri[0], tri[2], tri[1]]) # bottom
            except Exception:
                pass

            if len(b_faces) > 0:
                bldg_mesh = trimesh.Trimesh(vertices=b_verts, faces=np.array(b_faces, dtype=np.int32))
                bldg_mesh.visual.vertex_colors = np.full((len(b_verts), 4), [220, 110, 80, 255], dtype=np.uint8)
                scene.add_geometry(bldg_mesh, node_name=b["id"])

        scene.export(output_glb_path)
        print(f"[Export] Standard 3D GLB digital twin saved to: {output_glb_path}")
    except Exception as e:
        print(f"[Export] GLB export notice: {e}")


def generate_interactive_html_viewer(json_filename: str, sat_texture_filename: str, sem_texture_filename: str, output_html_path: str):
    """
    Generate professional, feature-complete DepthWizard HTML5 / Three.js 3D viewer.
    Supports raycasting building selection, satellite/semantic modes, layer toggles,
    height exaggeration slider, fly-through mode, and statistics panel.
    """
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DepthWizard - Semantic 3D Reconstruction & Digital Twin</title>
    <style>
        :root {{
            --bg-glass: rgba(13, 20, 32, 0.88);
            --border-glass: rgba(255, 255, 255, 0.12);
            --accent-blue: #00d2ff;
            --accent-cyan: #00f2fe;
            --accent-orange: #ff7644;
            --accent-green: #2ecc71;
            --text-primary: #f0f4f8;
            --text-muted: #94a3b8;
            --active-bg: rgba(0, 210, 255, 0.22);
            --active-border: #00d2ff;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            user-select: none;
        }}
        body, html {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #06090e;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: var(--text-primary);
        }}
        #viewport {{
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
        }}

        /* TOP NAVIGATION BAR */
        #topbar {{
            position: absolute;
            top: 14px;
            left: 18px;
            right: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 20px;
            background: var(--bg-glass);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            z-index: 100;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-logo {{
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 16px;
            color: #06090e;
            box-shadow: 0 0 12px rgba(0, 210, 255, 0.4);
        }}
        .brand-title {{
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: linear-gradient(90deg, #ffffff, #a5b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .brand-subtitle {{
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 0.3px;
        }}
        .controls-group {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .btn {{
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-glass);
            color: var(--text-primary);
            padding: 7px 14px;
            font-size: 12px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn:hover {{
            background: rgba(255, 255, 255, 0.14);
            border-color: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
        }}
        .btn.active {{
            background: var(--active-bg);
            border-color: var(--active-border);
            color: var(--accent-blue);
            box-shadow: 0 0 14px rgba(0, 210, 255, 0.25);
        }}
        .btn-flight {{
            background: linear-gradient(135deg, rgba(0, 210, 255, 0.2), rgba(58, 123, 213, 0.3));
            border-color: rgba(0, 210, 255, 0.4);
        }}
        .btn-flight:hover {{
            background: linear-gradient(135deg, rgba(0, 210, 255, 0.35), rgba(58, 123, 213, 0.45));
        }}
        .divider {{
            width: 1px;
            height: 24px;
            background: var(--border-glass);
            margin: 0 4px;
        }}
        .slider-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255, 255, 255, 0.04);
            padding: 5px 12px;
            border-radius: 8px;
            border: 1px solid var(--border-glass);
        }}
        .slider-label {{
            font-size: 11px;
            color: var(--text-muted);
            white-space: nowrap;
        }}
        .slider {{
            -webkit-appearance: none;
            appearance: none;
            width: 100px;
            height: 4px;
            border-radius: 2px;
            background: rgba(255, 255, 255, 0.2);
            outline: none;
            cursor: pointer;
        }}
        .slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: var(--accent-blue);
            cursor: pointer;
            box-shadow: 0 0 8px var(--accent-blue);
        }}
        .slider-val {{
            font-size: 12px;
            font-weight: 700;
            color: var(--accent-blue);
            min-width: 32px;
            text-align: right;
        }}

        /* RIGHT SIDEBAR INFORMATION PANEL */
        #infopanel {{
            position: absolute;
            top: 76px;
            right: 18px;
            width: 320px;
            background: var(--bg-glass);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-glass);
            border-radius: 14px;
            padding: 18px;
            z-index: 100;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
            gap: 16px;
            max-height: calc(100vh - 100px);
            overflow-y: auto;
        }}
        .panel-section-title {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .stat-box {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 8px 10px;
        }}
        .stat-box-label {{
            font-size: 10px;
            color: var(--text-muted);
            margin-bottom: 2px;
        }}
        .stat-box-val {{
            font-size: 15px;
            font-weight: 700;
            color: #ffffff;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(0, 210, 255, 0.25);
            border-radius: 10px;
            padding: 14px;
            transition: all 0.3s ease;
        }}
        .card.active {{
            background: rgba(0, 210, 255, 0.06);
            border-color: var(--accent-blue);
            box-shadow: 0 0 20px rgba(0, 210, 255, 0.15);
        }}
        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }}
        .building-badge {{
            background: linear-gradient(135deg, var(--accent-orange), #d35400);
            color: #fff;
            font-size: 11px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 6px;
            letter-spacing: 0.5px;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-size: 12px;
        }}
        .stat-row:last-child {{
            border-bottom: none;
        }}
        .stat-label {{
            color: var(--text-muted);
        }}
        .stat-value {{
            font-weight: 600;
            color: #f8fafc;
        }}
        .stat-value.highlight {{
            color: var(--accent-blue);
            font-weight: 700;
        }}
        .btn-clear {{
            width: 100%;
            margin-top: 10px;
            background: rgba(231, 76, 60, 0.15);
            border: 1px solid rgba(231, 76, 60, 0.35);
            color: #ff7675;
            padding: 6px 0;
            font-size: 11px;
            font-weight: 700;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .btn-clear:hover {{
            background: rgba(231, 76, 60, 0.3);
            border-color: #ff7675;
        }}

        /* BOTTOM HELP HINT */
        #bottom-hint {{
            position: absolute;
            bottom: 16px;
            left: 18px;
            padding: 8px 16px;
            background: var(--bg-glass);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            font-size: 11px;
            color: var(--text-muted);
            z-index: 100;
            pointer-events: none;
        }}
        #bottom-hint span {{
            color: #f1f5f9;
            font-weight: 600;
            margin-right: 12px;
        }}

        /* LOADING OVERLAY */
        #loading {{
            position: absolute;
            inset: 0;
            background: #06090e;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            transition: opacity 0.5s ease;
        }}
        .spinner {{
            width: 48px;
            height: 48px;
            border: 4px solid rgba(0, 210, 255, 0.15);
            border-top-color: var(--accent-blue);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-bottom: 16px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
    <!-- Three.js + OrbitControls -->
    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="loading">
        <div class="spinner"></div>
        <div style="font-size: 16px; font-weight: 700; letter-spacing: 0.5px;">DepthWizard 3D Digital Twin</div>
        <div style="font-size: 12px; color: #94a3b8; margin-top: 6px;">Building HTC-DC Net 3D Geometry...</div>
    </div>

    <div id="viewport"></div>

    <!-- TOP CONTROL BAR -->
    <div id="topbar">
        <div class="brand">
            <div class="brand-logo">DW</div>
            <div>
                <div class="brand-title">DepthWizard</div>
                <div class="brand-subtitle">Satellite 3D Digital Twin</div>
            </div>
        </div>

        <div class="controls-group">
            <!-- Texture Mode -->
            <button id="btn-sat" class="btn active" onclick="setTextureMode('satellite')">📷 Satellite Texture</button>
            <button id="btn-sem" class="btn" onclick="setTextureMode('semantic')">🎨 Semantic Colors</button>

            <div class="divider"></div>

            <!-- Layer Toggles -->
            <button id="toggle-bldgs" class="btn active" onclick="toggleLayer('buildings')">🏢 Buildings</button>
            <button id="toggle-veg" class="btn active" onclick="toggleLayer('vegetation')">🌳 Vegetation</button>
            <button id="toggle-roads" class="btn active" onclick="toggleLayer('roads')">🛣️ Roads</button>
            <button id="toggle-water" class="btn active" onclick="toggleLayer('water')">💧 Water</button>

            <div class="divider"></div>

            <!-- Height Exaggeration Slider -->
            <div class="slider-container">
                <span class="slider-label">Height:</span>
                <input id="slider-exaggeration" class="slider" type="range" min="0.5" max="5.0" step="0.1" value="1.0" oninput="onHeightExaggerationChange(this.value)">
                <span id="val-exaggeration" class="slider-val">1.0x</span>
            </div>

            <div class="divider"></div>

            <!-- Camera Controls -->
            <button id="btn-flight" class="btn btn-flight" onclick="toggleFlythrough()">🚀 Fly Through</button>
            <button class="btn" onclick="setTopView()">📐 Top View</button>
            <button class="btn" onclick="resetCamera()">🔄 Reset</button>
        </div>
    </div>

    <!-- RIGHT INFORMATION PANEL -->
    <div id="infopanel">
        <div class="panel-section-title">
            <span>Scene Information</span>
            <span style="color: var(--accent-blue);">LIVE</span>
        </div>
        <div class="stat-grid">
            <div class="stat-box">
                <div class="stat-box-label">Resolution</div>
                <div id="stat-res" class="stat-box-val">1024 × 1024</div>
            </div>
            <div class="stat-box">
                <div class="stat-box-label">Buildings</div>
                <div id="stat-bldgs-count" class="stat-box-val">--</div>
            </div>
            <div class="stat-box">
                <div class="stat-box-label">Max Height</div>
                <div id="stat-max-hgt" class="stat-box-val">-- m</div>
            </div>
            <div class="stat-box">
                <div class="stat-box-label">Mean Height</div>
                <div id="stat-mean-hgt" class="stat-box-val">-- m</div>
            </div>
        </div>

        <div class="panel-section-title">
            <span>Selected Building</span>
            <span id="selection-status" style="font-size: 10px; color: var(--text-muted);">None</span>
        </div>

        <div id="building-card" class="card">
            <div id="no-selection" style="text-align: center; padding: 20px 10px; color: var(--text-muted); font-size: 12px;">
                🖱️ Click any building in the 3D scene to inspect individual HTC-DC height metrics & footprint.
            </div>
            <div id="selection-details" style="display: none;">
                <div class="card-header">
                    <span id="bldg-id-badge" class="building-badge">B-001</span>
                    <span style="font-size: 11px; color: var(--text-muted);">SegFormer Class 1</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Estimated Height:</span>
                    <span id="bldg-est-height" class="stat-value highlight">-- m</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Mean Height:</span>
                    <span id="bldg-mean-height" class="stat-value">-- m</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Maximum Height:</span>
                    <span id="bldg-max-height" class="stat-value">-- m</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Minimum Height:</span>
                    <span id="bldg-min-height" class="stat-value">-- m</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Median Height:</span>
                    <span id="bldg-med-height" class="stat-value">-- m</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Footprint Area:</span>
                    <span id="bldg-area" class="stat-value">-- px²</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Centroid:</span>
                    <span id="bldg-centroid" class="stat-value">--</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Ground Elevation:</span>
                    <span id="bldg-ground" class="stat-value">-- m</span>
                </div>
                <button class="btn-clear" onclick="clearSelection()">✕ Clear Selection</button>
            </div>
        </div>
    </div>

    <!-- BOTTOM HINT -->
    <div id="bottom-hint">
        <span>Left Drag</span> Rotate / Orbit &nbsp;•&nbsp;
        <span>Right Drag</span> Pan &nbsp;•&nbsp;
        <span>Scroll</span> Zoom &nbsp;•&nbsp;
        <span>Left Click</span> Select Building
    </div>

    <script>
        // =====================================================================
        // APPLICATION STATE & GLOBALS
        // =====================================================================
        let scene, camera, renderer, controls;
        let sceneData = null;
        let satTexture = null, semTexture = null;
        let currentTextureMode = 'satellite'; // 'satellite' | 'semantic'
        let heightExaggeration = 1.0;

        // Scene Groups
        let terrainGroup = new THREE.Group();
        let buildingGroup = new THREE.Group();
        let outlineGroup = new THREE.Group();

        let terrainMesh = null;
        let baseTerrainElevations = null; // Float32Array for dynamic height scaling
        let buildingMeshes = [];
        let selectedBuildingMesh = null;
        let hoveredBuildingMesh = null;

        // Fly-through
        let isFlying = false;
        let flyProgress = 0;
        let flythroughCurve = null;
        let clock = new THREE.Clock();

        // Layer Visibilities
        const layerVisibility = {{
            buildings: true,
            vegetation: true,
            roads: true,
            water: true
        }};

        // Three.js Raycaster
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        let isPointerDragging = false;
        let pointerDownPos = new THREE.Vector2();

        // =====================================================================
        // INITIALIZATION & DATA LOADING
        // =====================================================================
        async function init() {{
            const viewport = document.getElementById('viewport');

            // 1. Scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x06090e);
            scene.fog = new THREE.FogExp2(0x06090e, 0.0022);

            // 2. Camera
            camera = new THREE.PerspectiveCamera(48, window.innerWidth / window.innerHeight, 0.1, 2000);
            camera.position.set(0, 115, 155);

            // 3. Renderer
            renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false, powerPreference: 'high-performance' }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            renderer.outputColorSpace = THREE.SRGBColorSpace;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.15;
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            viewport.appendChild(renderer.domElement);

            // 4. OrbitControls
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.06;
            controls.maxPolarAngle = Math.PI / 2 - 0.04;
            controls.minDistance = 15;
            controls.maxDistance = 500;
            controls.target.set(0, 5, 0);

            // 5. Lighting
            setupLighting();

            // Add Groups to Scene
            scene.add(terrainGroup);
            scene.add(buildingGroup);
            scene.add(outlineGroup);

            // 6. Texture Loader
            const texLoader = new THREE.TextureLoader();
            const loadTex = (url) => new Promise((resolve) => {{
                texLoader.load(url, (t) => {{
                    t.colorSpace = THREE.SRGBColorSpace;
                    t.minFilter = THREE.LinearMipmapLinearFilter;
                    t.magFilter = THREE.LinearFilter;
                    t.generateMipmaps = true;
                    resolve(t);
                }}, undefined, () => resolve(null));
            }});

            // Load Data & Textures in parallel
            try {{
                const [dataRes, satTex, semTex] = await Promise.all([
                    fetch('{json_filename}').then(r => r.json()),
                    loadTex('{sat_texture_filename}'),
                    loadTex('{sem_texture_filename}')
                ]);
                sceneData = dataRes;
                satTexture = satTex;
                semTexture = semTex;

                // Update UI Stats
                document.getElementById('stat-res').innerText = `${{sceneData.metadata.width}} × ${{sceneData.metadata.height}}`;
                document.getElementById('stat-bldgs-count').innerText = sceneData.buildings.length;
                document.getElementById('stat-max-hgt').innerText = `${{sceneData.metadata.maxHeight.toFixed(2)}} m`;
                document.getElementById('stat-mean-hgt').innerText = `${{sceneData.metadata.meanHeight.toFixed(2)}} m`;

                // Build 3D Geometry
                buildTerrainMesh();
                buildBuildingMeshes();
                setupFlythroughCurve();

                // Hide loader
                const loader = document.getElementById('loading');
                loader.style.opacity = '0';
                setTimeout(() => loader.style.display = 'none', 500);

            }} catch (err) {{
                console.error('Failed to load DepthWizard scene:', err);
                document.getElementById('loading').innerHTML =
                    '<div style="color: #ff7675; font-size: 16px; font-weight: 700;">Failed to load DepthWizard scene</div>' +
                    '<div style="color: #94a3b8; font-size: 12px; margin-top: 8px;">Please ensure python HTTP server is running.</div>';
            }}

            // Event Listeners
            setupEventListeners();

            // Render loop
            animate();
        }}

        function setupLighting() {{
            const ambient = new THREE.AmbientLight(0xffffff, 0.72);
            scene.add(ambient);

            // Key Sunlight (warm directional)
            const sun = new THREE.DirectionalLight(0xfffaed, 1.45);
            sun.position.set(130, 220, 90);
            sun.castShadow = true;
            sun.shadow.mapSize.width = 2048;
            sun.shadow.mapSize.height = 2048;
            sun.shadow.camera.near = 10;
            sun.shadow.camera.far = 600;
            sun.shadow.camera.left = -120;
            sun.shadow.camera.right = 120;
            sun.shadow.camera.top = 120;
            sun.shadow.camera.bottom = -120;
            sun.shadow.bias = -0.0004;
            scene.add(sun);

            // Sky Fill Light (cool hemisphere)
            const hemi = new THREE.HemisphereLight(0xdbeafe, 0x1e293b, 0.45);
            scene.add(hemi);
        }}

        // =====================================================================
        // 3D TERRAIN SURFACE (Ground + Vegetation + Roads + Water)
        // =====================================================================
        function buildTerrainMesh() {{
            const gridRes = sceneData.terrain.resolution;
            const extent = sceneData.metadata.sceneExtent;
            const heights = sceneData.terrain.heightGrid; // 1D array of length gridRes * gridRes

            const geom = new THREE.PlaneGeometry(extent, extent, gridRes - 1, gridRes - 1);
            geom.rotateX(-Math.PI / 2); // Lay flat on X-Z plane

            const pos = geom.attributes.position;
            baseTerrainElevations = new Float32Array(pos.count);

            for (let i = 0; i < pos.count; i++) {{
                const h = heights[i] || 0.0;
                baseTerrainElevations[i] = h;
                pos.setY(i, h * heightExaggeration);
            }}

            // Calculate pixel-exact UVs aligned with 1024x1024 texture
            const uvs = geom.attributes.uv;
            for (let i = 0; i < pos.count; i++) {{
                const x = pos.getX(i);
                const z = pos.getZ(i);
                const u = (x / extent) + 0.5;
                const v = 1.0 - ((z / extent) + 0.5);
                uvs.setXY(i, u, v);
            }}

            geom.computeVertexNormals();

            const terrainMat = new THREE.MeshStandardMaterial({{
                map: satTexture,
                roughness: 0.88,
                metalness: 0.04
            }});

            terrainMesh = new THREE.Mesh(geom, terrainMat);
            terrainMesh.receiveShadow = true;
            terrainGroup.add(terrainMesh);
        }}

        // =====================================================================
        // INDIVIDUAL BUILDING EXTRACTION & EXTRUSION
        // =====================================================================
        function buildBuildingMeshes() {{
            const extent = sceneData.metadata.sceneExtent;
            const scale = extent / sceneData.metadata.width; // 200.0 / 1024.0

            sceneData.buildings.forEach((b) => {{
                if (!b.polygon || b.polygon.length < 3) return;

                // 1. Build THREE.Shape from 2D footprint contour
                const shape = new THREE.Shape();
                b.polygon.forEach((pt, idx) => {{
                    // Pixel coords (0..1024) -> Centered Scene Coords (-100..100)
                    const sx = (pt[0] - 512.0) * scale;
                    const sz = (pt[1] - 512.0) * scale;
                    if (idx === 0) shape.moveTo(sx, sz);
                    else shape.lineTo(sx, sz);
                }});
                shape.closePath();

                // 2. Interior Courtyards / Holes
                if (b.holes && b.holes.length > 0) {{
                    b.holes.forEach((holePts) => {{
                        if (holePts.length < 3) return;
                        const holePath = new THREE.Path();
                        holePts.forEach((pt, idx) => {{
                            const hx = (pt[0] - 512.0) * scale;
                            const hz = (pt[1] - 512.0) * scale;
                            if (idx === 0) holePath.moveTo(hx, hz);
                            else holePath.lineTo(hx, hz);
                        }});
                        holePath.closePath();
                        shape.holes.push(holePath);
                    }});
                }}

                // 3. Extrude geometry vertically by building height
                const extrudeSettings = {{
                    depth: b.height,
                    bevelEnabled: false,
                    steps: 1
                }};
                const geom = new THREE.ExtrudeGeometry(shape, extrudeSettings);

                // Rotate so extrusion direction is along world +Y
                geom.rotateX(Math.PI / 2);

                // 4. Precise UV mapping on Roof Cap so satellite image drapes seamlessly
                const pos = geom.attributes.position;
                const uvs = geom.attributes.uv;
                for (let i = 0; i < pos.count; i++) {{
                    const vx = pos.getX(i);
                    const vz = pos.getZ(i);
                    // Match top-down satellite projection UV
                    const u = (vx / extent) + 0.5;
                    const v = 1.0 - ((vz / extent) + 0.5);
                    uvs.setXY(i, u, v);
                }}
                geom.computeVertexNormals();

                // 5. Materials: Roof uses satellite texture, side walls use clean architectural concrete
                const roofMat = new THREE.MeshStandardMaterial({{
                    map: satTexture,
                    roughness: 0.65,
                    metalness: 0.08
                }});
                const wallMat = new THREE.MeshStandardMaterial({{
                    color: 0x8a847d,
                    roughness: 0.80,
                    metalness: 0.12
                }});

                const mesh = new THREE.Mesh(geom, [roofMat, wallMat]);
                mesh.castShadow = true;
                mesh.receiveShadow = true;

                // Position base at ground elevation
                mesh.position.y = (b.groundElevation + b.height) * heightExaggeration;
                // Note: ExtrudeGeometry with rotateX(Math.PI/2) extrudes downward from 0 to -depth
                // Thus setting position.y = ground + height places the bottom flush on ground!

                // Attach rich userData for Raycasting & Selection
                mesh.userData = {{
                    type: "building",
                    buildingId: b.id,
                    height: b.height,
                    meanHeight: b.meanHeight,
                    maxHeight: b.maxHeight,
                    minHeight: b.minHeight,
                    medianHeight: b.medianHeight,
                    area: b.areaPixels,
                    centroid: b.centroid,
                    groundElevation: b.groundElevation,
                    classId: 1,
                    className: "Building"
                }};

                // 6. Crisp selection outline (EdgesGeometry)
                const edgesGeom = new THREE.EdgesGeometry(geom, 28);
                const outlineMat = new THREE.LineBasicMaterial({{
                    color: 0x00f2fe,
                    linewidth: 2,
                    transparent: true,
                    opacity: 0.95
                }});
                const outline = new THREE.LineSegments(edgesGeom, outlineMat);
                outline.visible = false;
                mesh.add(outline);
                mesh.outline = outline;

                buildingMeshes.push(mesh);
                buildingGroup.add(mesh);
            }});
        }}

        // =====================================================================
        // FLY-THROUGH CAMERA PATH
        // =====================================================================
        function setupFlythroughCurve() {{
            flythroughCurve = new THREE.CatmullRomCurve3([
                new THREE.Vector3(-90, 52, 90),
                new THREE.Vector3(-45, 38, 25),
                new THREE.Vector3(15, 34, -40),
                new THREE.Vector3(85, 46, -85),
                new THREE.Vector3(95, 50, 15),
                new THREE.Vector3(35, 52, 85),
                new THREE.Vector3(-45, 54, 95),
                new THREE.Vector3(-90, 52, 90)
            ], true);
        }}

        function toggleFlythrough() {{
            isFlying = !isFlying;
            const btn = document.getElementById('btn-flight');
            if (isFlying) {{
                btn.classList.add('active');
                btn.innerText = '⏹️ Exit Fly Through';
                controls.enabled = false;
            }} else {{
                btn.classList.remove('active');
                btn.innerText = '🚀 Fly Through';
                controls.enabled = true;
                controls.target.set(0, 5, 0);
            }}
        }}

        // =====================================================================
        // RAYCASTING & BUILDING SELECTION
        // =====================================================================
        function setupEventListeners() {{
            window.addEventListener('resize', onWindowResize);

            const vp = document.getElementById('viewport');

            vp.addEventListener('pointerdown', (e) => {{
                isPointerDragging = false;
                pointerDownPos.set(e.clientX, e.clientY);
            }});

            vp.addEventListener('pointermove', (e) => {{
                if (pointerDownPos.distanceTo(new THREE.Vector2(e.clientX, e.clientY)) > 5) {{
                    isPointerDragging = true;
                }}

                if (isFlying) return;

                // Hover Raycast
                mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
                mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
                raycaster.setFromCamera(mouse, camera);

                if (!layerVisibility.buildings) return;
                const intersects = raycaster.intersectObjects(buildingMeshes, false);

                if (intersects.length > 0) {{
                    document.body.style.cursor = 'pointer';
                    setHoverBuilding(intersects[0].object);
                }} else {{
                    document.body.style.cursor = 'default';
                    setHoverBuilding(null);
                }}
            }});

            vp.addEventListener('pointerup', (e) => {{
                // Ignore drags
                if (isPointerDragging) return;

                mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
                mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
                raycaster.setFromCamera(mouse, camera);

                if (!layerVisibility.buildings) return;
                const intersects = raycaster.intersectObjects(buildingMeshes, false);

                if (intersects.length > 0) {{
                    selectBuilding(intersects[0].object);
                }} else {{
                    clearSelection();
                }}
            }});
        }}

        function selectBuilding(mesh) {{
            if (selectedBuildingMesh === mesh) return;
            clearSelection();

            selectedBuildingMesh = mesh;

            // Highlight Roof & Walls with glowing emissive color
            mesh.material[0].emissive.setHex(0x004488);
            mesh.material[1].emissive.setHex(0x0099ff);
            mesh.outline.visible = true;

            // Populate Information Panel
            updateBuildingCard(mesh.userData);
        }}

        function setHoverBuilding(mesh) {{
            if (hoveredBuildingMesh === mesh) return;

            if (hoveredBuildingMesh && hoveredBuildingMesh !== selectedBuildingMesh) {{
                hoveredBuildingMesh.material[0].emissive.setHex(0x000000);
                hoveredBuildingMesh.material[1].emissive.setHex(0x000000);
                hoveredBuildingMesh.outline.visible = false;
            }}

            hoveredBuildingMesh = mesh;

            if (mesh && mesh !== selectedBuildingMesh) {{
                mesh.material[1].emissive.setHex(0x003355);
                mesh.outline.visible = true;
            }}
        }}

        function clearSelection() {{
            if (selectedBuildingMesh) {{
                selectedBuildingMesh.material[0].emissive.setHex(0x000000);
                selectedBuildingMesh.material[1].emissive.setHex(0x000000);
                selectedBuildingMesh.outline.visible = false;
                selectedBuildingMesh = null;
            }}
            resetBuildingCard();
        }}

        function updateBuildingCard(u) {{
            document.getElementById('no-selection').style.display = 'none';
            document.getElementById('selection-details').style.display = 'block';
            document.getElementById('building-card').classList.add('active');
            document.getElementById('selection-status').innerText = 'SELECTED';
            document.getElementById('selection-status').style.color = '#00d2ff';

            document.getElementById('bldg-id-badge').innerText = u.buildingId;
            document.getElementById('bldg-est-height').innerText = `${{u.height.toFixed(2)}} m`;
            document.getElementById('bldg-mean-height').innerText = `${{u.meanHeight.toFixed(2)}} m`;
            document.getElementById('bldg-max-height').innerText = `${{u.maxHeight.toFixed(2)}} m`;
            document.getElementById('bldg-min-height').innerText = `${{u.minHeight.toFixed(2)}} m`;
            document.getElementById('bldg-med-height').innerText = `${{u.medianHeight.toFixed(2)}} m`;
            document.getElementById('bldg-area').innerText = `${{u.area.toLocaleString()}} px²`;
            document.getElementById('bldg-centroid').innerText = `X: ${{u.centroid.x}}, Y: ${{u.centroid.y}}`;
            document.getElementById('bldg-ground').innerText = `${{u.groundElevation.toFixed(2)}} m`;
        }}

        function resetBuildingCard() {{
            document.getElementById('no-selection').style.display = 'block';
            document.getElementById('selection-details').style.display = 'none';
            document.getElementById('building-card').classList.remove('active');
            document.getElementById('selection-status').innerText = 'None';
            document.getElementById('selection-status').style.color = '#94a3b8';
        }}

        // =====================================================================
        // CONTROLS & UI ACTIONS
        // =====================================================================
        function setTextureMode(mode) {{
            currentTextureMode = mode;
            document.getElementById('btn-sat').classList.toggle('active', mode === 'satellite');
            document.getElementById('btn-sem').classList.toggle('active', mode === 'semantic');

            const activeTex = (mode === 'satellite') ? satTexture : semTexture;

            // Update terrain
            if (terrainMesh) {{
                terrainMesh.material.map = activeTex;
                terrainMesh.material.needsUpdate = true;
            }}

            // Update building roofs
            buildingMeshes.forEach(mesh => {{
                if (mode === 'satellite') {{
                    mesh.material[0].map = satTexture;
                    mesh.material[0].color.setHex(0xffffff);
                    mesh.material[1].color.setHex(0x8a847d);
                }} else {{
                    mesh.material[0].map = semTexture;
                    mesh.material[0].color.setHex(0xe74c3c);
                    mesh.material[1].color.setHex(0xc0392b);
                }}
                mesh.material[0].needsUpdate = true;
                mesh.material[1].needsUpdate = true;
            }});
        }}

        function toggleLayer(layer) {{
            layerVisibility[layer] = !layerVisibility[layer];
            const btn = document.getElementById(`toggle-${{layer}}`);
            if (btn) btn.classList.toggle('active', layerVisibility[layer]);

            if (layer === 'buildings') {{
                buildingGroup.visible = layerVisibility.buildings;
                if (!layerVisibility.buildings) clearSelection();
            }}
            // Real-time layer shader / texture toggling can be extended here
        }}

        function onHeightExaggerationChange(val) {{
            heightExaggeration = parseFloat(val);
            document.getElementById('val-exaggeration').innerText = `${{heightExaggeration.toFixed(1)}}x`;

            // 1. Scale terrain surface
            if (terrainMesh && baseTerrainElevations) {{
                const pos = terrainMesh.geometry.attributes.position;
                for (let i = 0; i < pos.count; i++) {{
                    pos.setY(i, baseTerrainElevations[i] * heightExaggeration);
                }}
                pos.needsUpdate = true;
                terrainMesh.geometry.computeVertexNormals();
            }}

            // 2. Scale building vertical height & elevation
            buildingMeshes.forEach(mesh => {{
                mesh.scale.set(1, 1, heightExaggeration);
                const u = mesh.userData;
                mesh.position.y = (u.groundElevation + u.height) * heightExaggeration;
            }});
        }}

        function setTopView() {{
            if (isFlying) toggleFlythrough();
            controls.target.set(0, 0, 0);
            camera.position.set(0, 260, 0.1);
            controls.update();
        }}

        function resetCamera() {{
            if (isFlying) toggleFlythrough();
            controls.target.set(0, 5, 0);
            camera.position.set(0, 115, 155);
            controls.update();
        }}

        function onWindowResize() {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }}

        // =====================================================================
        // ANIMATION LOOP
        // =====================================================================
        function animate() {{
            requestAnimationFrame(animate);

            const delta = clock.getDelta();

            if (isFlying && flythroughCurve) {{
                flyProgress = (flyProgress + delta * 0.028) % 1.0;
                const camPos = flythroughCurve.getPointAt(flyProgress);
                const lookTarget = flythroughCurve.getPointAt((flyProgress + 0.05) % 1.0);
                lookTarget.y -= 12.0; // Angle slightly downward for sweeping flyover view

                camera.position.copy(camPos);
                camera.lookAt(lookTarget);
            }} else {{
                controls.update();
            }}

            renderer.render(scene, camera);
        }}

        window.onload = init;
    </script>
</body>
</html>
"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[Viewer] Interactive HTML5/WebGL viewer generated at: {output_html_path}")


def main():
    print("=" * 65)
    print("  DEPTHWIZARD: SEMANTIC 3D RECONSTRUCTION PIPELINE")
    print("=" * 65)

    base_dir, input_dir, output_dir = resolve_paths()
    print(f"Working Directory: {base_dir}")
    print(f"Input Directory:   {input_dir}")
    print(f"Output Directory:  {output_dir}\n")

    # 1. Load Rasters
    print("[1/6] Loading input TIFF rasters...")
    rgb, raw_height, seg = load_input_rasters(input_dir)
    h, w = rgb.shape[:2]
    h_min, h_max = float(raw_height.min()), float(raw_height.max())
    h_mean = float(raw_height.mean())
    print(f"      Image: {w}x{h} px, RGB uint8")
    print(f"      Height Raster: min={h_min:.2f}m, max={h_max:.2f}m, mean={h_mean:.2f}m")
    print(f"      SegFormer Raster: {len(np.unique(seg))} unique semantic classes detected")

    # Class distribution statistics
    bldg_pixels = int(np.count_nonzero(np.isin(seg, BUILDING_CLASS_IDS)))
    road_pixels = int(np.count_nonzero(np.isin(seg, ROAD_CLASS_IDS)))
    veg_pixels = int(np.count_nonzero(np.isin(seg, TREE_CLASS_IDS + VEGETATION_CLASS_IDS)))
    water_pixels = int(np.count_nonzero(np.isin(seg, WATER_CLASS_IDS)))

    # 2. Textures
    print("\n[2/6] Generating satellite & semantic textures...")
    sat_tex_path = os.path.join(output_dir, "satellite_texture.png")
    sem_tex_path = os.path.join(output_dir, "semantic_texture.png")
    generate_satellite_texture(rgb, sat_tex_path)
    generate_semantic_texture(seg, sem_tex_path)
    print(f"      Satellite texture saved: {sat_tex_path}")
    print(f"      Semantic texture saved:  {sem_tex_path}")

    # 3. Ground & Vegetation Elevation
    print("\n[3/6] Computing ground elevation & organic vegetation surfaces...")
    ground_height, terrain_elevation, veg_height = compute_ground_and_vegetation_elevation(raw_height, seg)
    print(f"      Inpainted ground: min={ground_height.min():.2f}m, max={ground_height.max():.2f}m")
    print(f"      Max vegetation elevation: {veg_height.max():.2f}m")

    # 4. Extract Individual Building Meshes
    print("\n[4/6] Extracting individual building footprints & HTC-DC heights...")
    buildings = extract_building_objects(raw_height, ground_height, seg)
    print(f"      Detected {len(buildings)} individual building objects (area >= {MIN_BUILDING_AREA_PIXELS} px)")

    # Downsample terrain grid for fast 60fps web rendering
    down_terrain = cv2.resize(terrain_elevation, (TERRAIN_GRID_SIZE, TERRAIN_GRID_SIZE), interpolation=cv2.INTER_LINEAR)
    terrain_flat = [round(float(v), 3) for v in down_terrain.ravel()]

    # 5. Output JSON
    print("\n[5/6] Exporting semantic scene metadata and geometry JSON...")
    scene_json = {
        "metadata": {
            "title": "DepthWizard Semantic 3D Reconstruction",
            "width": w,
            "height": h,
            "sceneExtent": SCENE_EXTENT,
            "horizontalScale": HORIZONTAL_SCALE,
            "minHeight": h_min,
            "maxHeight": h_max,
            "meanHeight": h_mean,
            "buildingCount": len(buildings),
            "buildingPixels": bldg_pixels,
            "roadPixels": road_pixels,
            "vegetationPixels": veg_pixels,
            "waterPixels": water_pixels,
        },
        "terrain": {
            "resolution": TERRAIN_GRID_SIZE,
            "heightGrid": terrain_flat,
        },
        "buildings": buildings,
    }

    json_path = os.path.join(output_dir, "semantic_scene.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scene_json, f, separators=(",", ":"))
    print(f"      Saved {json_path} ({os.path.getsize(json_path) / 1024:.1f} KB)")

    # 6. Generate HTML5 WebGL Viewer
    print("\n[6/6] Generating interactive Three.js 3D Viewer...")
    html_path = os.path.join(output_dir, "semantic_scene.html")
    generate_interactive_html_viewer(
        json_filename="semantic_scene.json",
        sat_texture_filename="satellite_texture.png",
        sem_texture_filename="semantic_texture.png",
        output_html_path=html_path,
    )

    # Optional GLB Export
    glb_path = os.path.join(output_dir, "depthwizard_scene.glb")
    export_glb_digital_twin(terrain_elevation, buildings, glb_path)

    # Required terminal summary (Section 21)
    print("\n" + "=" * 65)
    print("DEPTHWIZARD 3D RECONSTRUCTION")
    print("=" * 65)
    print(f"Image: {w} x {h}")
    print(f"Height range: {h_min:.2f} - {h_max:.2f}")
    print(f"Building pixels: {bldg_pixels}")
    print(f"Buildings detected: {len(buildings)}")
    print(f"Road pixels: {road_pixels}")
    print(f"Vegetation pixels: {veg_pixels}")
    print(f"Water pixels: {water_pixels}")
    print(f"\n3D building meshes: {len(buildings)}")
    print(f"Terrain vertices: {TERRAIN_GRID_SIZE * TERRAIN_GRID_SIZE}")
    print("\nViewer:")
    print("output/semantic_scene.html")
    print("=" * 65)


if __name__ == "__main__":
    main()
