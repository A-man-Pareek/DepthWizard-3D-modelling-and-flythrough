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


@app.post("/estimate-height")
async def estimate_height(
    file: UploadFile = File(...),
    run_segmentation: bool = Form(False),
):
    """Run full height estimation pipeline with optional SegFormer segmentation."""
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
            run_segmentation=run_segmentation,
            output_dir=OUTPUT_DIR,
            base_name=base_name,
        )

        return JSONResponse(content=result.to_dict())
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Height estimation failed: {str(e)}")


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
    """Download generated GeoTIFF or TIFF raster with directory traversal defense."""
    # Sanitize and resolve absolute path to prevent directory traversal
    safe_filename = os.path.basename(filename)
    target_path = os.path.realpath(os.path.join(OUTPUT_DIR, safe_filename))

    if not target_path.startswith(os.path.realpath(OUTPUT_DIR)):
        raise HTTPException(status_code=403, detail="Access denied: invalid file path.")

    if not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail=f"File '{safe_filename}' not found.")

    media_type = "image/tiff" if safe_filename.endswith((".tif", ".tiff")) else "application/octet-stream"
    return FileResponse(path=target_path, filename=safe_filename, media_type=media_type)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
