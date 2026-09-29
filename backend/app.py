"""Step 6: FastAPI server exposing the Production DepthWizard Pipeline.

Endpoints:
  - GET  /           : API service information
  - GET  /health     : Production health check and model status
  - POST /estimate-height : Height estimation & DSM generation (optional segmentation)
  - POST /segment    : Dedicated SegFormer semantic segmentation
  - GET  /download/{filename} : Secure raster download (directory traversal protected)
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from pipeline import HeightEstimationPipeline

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "outputs"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(
    title="DepthWizard Height & Segmentation API",
    description="Production-grade monocular height estimation (HTC-DC Net) and semantic segmentation (SegFormer).",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline with production checkpoint requirements
pipeline = HeightEstimationPipeline(
    dem_dir=os.path.join(PROJECT_ROOT, "data", "srtm"),
    require_checkpoint=True,
)


@app.get("/")
def index():
    return {
        "service": "DepthWizard Height & Segmentation API",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "GET /health": "System readiness, device, checkpoint, and model statuses",
            "POST /estimate-height": "Estimate relative/metric height and DSM (multipart image upload)",
            "POST /segment": "SegFormer semantic segmentation (multipart image upload)",
            "GET /download/{filename}": "Download exported GeoTIFF or TIFF rasters",
        },
    }


@app.get("/health")
def health():
    runner_status = pipeline.runner.status
    is_ready = runner_status.get("model_loaded") and runner_status.get("checkpoint_loaded")
    return {
        "status": "healthy" if is_ready else "degraded",
        "api_readiness": "ready" if is_ready else "not_ready",
        "device": str(pipeline.runner.device),
        "model_loaded": runner_status.get("model_loaded", False),
        "checkpoint_loaded": runner_status.get("checkpoint_loaded", False),
        "checkpoint_path": runner_status.get("checkpoint_path"),
        "dem_dir": pipeline.dem_dir,
        "dem_dir_exists": os.path.isdir(pipeline.dem_dir),
        "output_dir": OUTPUT_DIR,
    }


import shutil
from reconstruct_to_glb import create_terrain_mesh

SIH_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, ".."))
RECONSTRUCTION_INPUT = os.path.join(SIH_ROOT, "3d_reconstruction", "input")
RECONSTRUCTION_OUTPUT = os.path.join(SIH_ROOT, "3d_reconstruction", "output")
VIEWER_PUBLIC = os.path.join(SIH_ROOT, "3d_viewer", "public")


def sync_output_folders(
    base_name: str,
    image_bytes: bytes,
    dsm_path: str,
    seg_path: Optional[str],
    meta_path: str,
    glb_path: str,
):
    """Sync outputs to 3d_reconstruction input/output and 3d_viewer public folders."""
    try:
        if os.path.isdir(RECONSTRUCTION_INPUT):
            with open(os.path.join(RECONSTRUCTION_INPUT, "image.tiff"), "wb") as f:
                f.write(image_bytes)
            if os.path.isfile(dsm_path):
                shutil.copy2(dsm_path, os.path.join(RECONSTRUCTION_INPUT, "height.tiff"))
            if seg_path and os.path.isfile(seg_path):
                shutil.copy2(seg_path, os.path.join(RECONSTRUCTION_INPUT, "segmentation.tiff"))
            if os.path.isfile(meta_path):
                shutil.copy2(meta_path, os.path.join(RECONSTRUCTION_INPUT, "metadata.json"))

        if os.path.isdir(RECONSTRUCTION_OUTPUT) and os.path.isfile(glb_path):
            shutil.copy2(glb_path, os.path.join(RECONSTRUCTION_OUTPUT, "depthwizard_final.glb"))
            shutil.copy2(glb_path, os.path.join(RECONSTRUCTION_OUTPUT, "imgg_fresh.glb"))
            shutil.copy2(glb_path, os.path.join(RECONSTRUCTION_OUTPUT, f"{base_name}.glb"))

        if os.path.isdir(VIEWER_PUBLIC):
            if os.path.isfile(glb_path):
                shutil.copy2(glb_path, os.path.join(VIEWER_PUBLIC, "terrain.glb"))
                shutil.copy2(glb_path, os.path.join(VIEWER_PUBLIC, "street.glb"))
                shutil.copy2(glb_path, os.path.join(VIEWER_PUBLIC, "depthwizard_final.glb"))
                shutil.copy2(glb_path, os.path.join(VIEWER_PUBLIC, "imgg_fresh.glb"))
            if os.path.isfile(meta_path):
                shutil.copy2(meta_path, os.path.join(VIEWER_PUBLIC, "metadata.json"))
    except Exception as e:
        print(f"[app] Warning: Output folders sync error: {e}")


@app.post("/estimate-height")
async def estimate_height(
    file: UploadFile = File(...),
    run_segmentation: bool = Form(False),
    generate_3d: bool = Form(True),
):
    """Run full height estimation pipeline, metadata JSON export, and optional 3D GLB generation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    allowed_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".avif"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {sorted(list(allowed_exts))}",
        )

    try:
        content = await file.read()
        base_name = Path(file.filename).stem

        result = pipeline.process(
            input_source=content,
            run_segmentation=run_segmentation or generate_3d,
            output_dir=OUTPUT_DIR,
            base_name=base_name,
        )

        response_dict = result.to_dict()

        # Generate 3D GLB model via 2D-to-3D engine
        if generate_3d:
            try:
                dsm_path = result.raster_path
                seg_prod = result.exported_products.get("segmentation", {})
                seg_path = seg_prod.get("file_path") if seg_prod else None

                # Save raw input image to disk for mesh texturing
                raw_img_path = os.path.join(OUTPUT_DIR, f"{base_name}_input{ext}")
                with open(raw_img_path, "wb") as f:
                    f.write(content)

                glb_filename = f"{base_name}.glb"
                glb_path = os.path.join(OUTPUT_DIR, glb_filename)
                ply_path = os.path.join(OUTPUT_DIR, f"{base_name}_mesh.ply")

                stats_3d = create_terrain_mesh(
                    image_path=raw_img_path,
                    height_path=dsm_path,
                    segmentation_path=seg_path,
                    output_glb=glb_path,
                    output_ply=ply_path,
                    downsample=2,
                    vertical_scale=1.0,
                )

                response_dict["glb_url"] = f"/download/{glb_filename}"
                response_dict["stats_3d"] = stats_3d

                # Sync to 3D reconstruction and 3D viewer public folders
                sync_output_folders(
                    base_name=base_name,
                    image_bytes=content,
                    dsm_path=dsm_path,
                    seg_path=seg_path,
                    meta_path=result.metadata_json_path,
                    glb_path=glb_path,
                )
            except Exception as ex:
                print(f"[app] 3D mesh generation note: {ex}")

        return JSONResponse(content=response_dict)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Height estimation failed: {str(e)}")


@app.post("/process-3d")
async def process_3d(file: UploadFile = File(...)):
    """Unified pipeline: Image -> Height Estimation & SegFormer -> 2D-to-3D GLB -> Flythrough ready."""
    return await estimate_height(file=file, run_segmentation=True, generate_3d=True)


@app.post("/segment")
async def segment_image(file: UploadFile = File(...)):
    """Run dedicated high-resolution SegFormer semantic segmentation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    allowed_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".avif"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {sorted(list(allowed_exts))}",
        )

    try:
        content = await file.read()
        base_name = Path(file.filename).stem

        # Run pipeline with segmentation only
        insp = pipeline.process(
            input_source=content,
            run_segmentation=True,
            output_dir=OUTPUT_DIR,
            base_name=f"{base_name}_seg",
        )

        return JSONResponse(content={
            "filename": file.filename,
            "resolution": [insp.inspection.original_shape[1], insp.inspection.original_shape[0]],
            "is_georeferenced": insp.inspection.is_georeferenced,
            "segmentation": insp.segmentation.get("class_distribution", []) if insp.segmentation else [],
            "products": insp.exported_products,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")


@app.get("/download/{filename}")
def download_raster(filename: str):
    """Download generated GeoTIFF, TIFF, GLB, PLY, or JSON with directory traversal defense."""
    safe_filename = os.path.basename(filename)
    target_path = os.path.realpath(os.path.join(OUTPUT_DIR, safe_filename))

    if not target_path.startswith(os.path.realpath(OUTPUT_DIR)):
        raise HTTPException(status_code=403, detail="Access denied: invalid file path.")

    if not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail=f"File '{safe_filename}' not found.")

    if safe_filename.endswith((".tif", ".tiff")):
        media_type = "image/tiff"
    elif safe_filename.endswith(".json"):
        media_type = "application/json"
    elif safe_filename.endswith((".png", ".jpg", ".jpeg")):
        media_type = "image/png"
    elif safe_filename.endswith(".glb"):
        media_type = "model/gltf-binary"
    elif safe_filename.endswith((".ply", ".gltf")):
        media_type = "application/octet-stream"
    else:
        media_type = "application/octet-stream"

    return FileResponse(path=target_path, filename=safe_filename, media_type=media_type)


# ── Disaster Simulation Integration ──────────────────────────────────
# Wire the src/disaster simulation engine into the API so the frontend
# hazards page can run actual simulations instead of being proposal-only.

import sys
import json

_src_dir = os.path.abspath(os.path.join(SIH_ROOT, "src"))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

_disaster_service = None

def _get_disaster_service():
    """Lazy-load the DisasterService to avoid import failures if numpy/scipy not installed."""
    global _disaster_service
    if _disaster_service is None:
        try:
            from disaster.disaster_service import DisasterService
            _disaster_service = DisasterService()
        except ImportError as e:
            print(f"[app] Disaster service not available: {e}")
            return None
    return _disaster_service


@app.post("/simulate-disaster")
async def simulate_disaster(
    disaster_type: str = Form("FLOOD"),
    intensity: str = Form("medium"),
    seed: int = Form(42),
):
    """Run a synthetic disaster simulation over the current terrain scene."""
    service = _get_disaster_service()
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Disaster simulation module is not available. Ensure numpy and scipy are installed.",
        )

    # Load building footprints from the latest scene JSON if available
    buildings = []
    scene_json_path = os.path.join(SIH_ROOT, "output", "semantic_scene.json")
    if os.path.isfile(scene_json_path):
        try:
            with open(scene_json_path, "r") as f:
                scene_data = json.load(f)
            if "buildings" in scene_data:
                buildings = scene_data["buildings"]
            elif "objects" in scene_data:
                buildings = [
                    obj for obj in scene_data["objects"]
                    if obj.get("type", "").lower() in ("building", "structure")
                ]
        except Exception as e:
            print(f"[app] Could not load scene JSON for disaster sim: {e}")

    try:
        result = service.run_simulation(
            disaster_type=disaster_type,
            buildings=buildings,
            intensity=intensity,
            seed=seed,
        )
        return JSONResponse(content=result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Disaster simulation failed: {str(e)}")


@app.get("/disaster-types")
def list_disaster_types():
    """List all supported disaster types for the frontend dropdown."""
    try:
        from disaster.disaster_types import get_all_disaster_types
        return JSONResponse(content=get_all_disaster_types())
    except ImportError:
        return JSONResponse(content={
            "FLOOD": {"name": "Flood", "icon": "droplets"},
            "WILDFIRE": {"name": "Wildfire", "icon": "flame"},
            "CYCLONE": {"name": "Cyclone", "icon": "wind"},
            "LANDSLIDE": {"name": "Landslide", "icon": "mountain"},
        })


@app.get("/scene-data")
def get_scene_data():
    """Return the latest generated scene JSON for 3D visualization layers."""
    scene_json = os.path.join(SIH_ROOT, "output", "semantic_scene.json")
    terrain_json = os.path.join(SIH_ROOT, "output", "terrain_data.json")

    data = {}
    if os.path.isfile(scene_json):
        try:
            with open(scene_json, "r") as f:
                data["scene"] = json.load(f)
        except Exception:
            pass
    if os.path.isfile(terrain_json):
        try:
            with open(terrain_json, "r") as f:
                data["terrain"] = json.load(f)
        except Exception:
            pass

    if not data:
        raise HTTPException(status_code=404, detail="No scene data available. Process an image first.")
    return JSONResponse(content=data)


from pydantic import BaseModel
from geollm_engine import geo_engine


class GeoLLMQueryRequest(BaseModel):
    query: str
    context: Optional[dict] = None


@app.post("/geollm/chat")
def geollm_chat(req: GeoLLMQueryRequest):
    """GeoLLM Natural Language Chat endpoint for terrain, height, and disaster analysis."""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    reply = geo_engine.query(req.query, req.context)
    return JSONResponse(content={
        "status": "success",
        "model": geo_engine.model_name,
        "response": reply,
        "query": req.query,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)

