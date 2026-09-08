# DepthWizard: High-Resolution Aerial Height Estimation & Geospatial Intelligence Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

DepthWizard is an enterprise-grade geospatial machine learning pipeline designed to estimate high-resolution Normalized Digital Surface Models (nDSM), calibrate metric heights using real Digital Elevation Models (DEM), and extract dense land-cover semantic segmentation (via SegFormer) directly from overhead optical imagery (drone, aerial, and satellite).

---

## Pipeline Architecture

```
                 Optical Image (RGB, GeoTIFF, JPG, PNG, AVIF)
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │     IMAGE INSPECTION      │
                        │ (Metadata, CRS, GSD, EXIF)│
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │       PREPROCESSING       │
                        │ (Aspect Ratio, Bit-Depth) │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   SLIDING-WINDOW TILER    │
                        │ (Hann 2D Blending, No     │
                        │      Downsampling)        │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │        HTC-DC NET         │
                        │ (Relative nDSM Inference) │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │     DEM & CALIBRATION     │
                        │  (Real DEM Lookup, RANSAC │
                        │  Calibration, DSM Output) │
                        └─────────────┬─────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
       ┌───────────────────────────┐     ┌───────────────────────────┐
       │   EXPORT & GEOTIFF API    │     │   SEGFORMER SEGMENTATION  │
       │ (Float32 Single-band TIF, │     │  (Land-Cover Mask, Class  │
       │     Summary Metadata)     │     │   Percentages, ADE20K)    │
       └───────────────────────────┘     └───────────────────────────┘
```

---

## Core Features & Engineering Highlights

1. **Sliding-Window Hann Tiling (Zero Downsampling)**
   - Arbitrary dimension images ($626 \times 626$, $4000 \times 4000$, etc.) are processed at **full native resolution**.
   - Slices into overlapping $256 \times 256$ tiles with 2D Hann window blending, completely eliminating border discontinuities and tile boundary seams.

2. **HTC-DC Net Model Runner**
   - Relative normalized Digital Surface Model (nDSM) estimation.
   - Enforces `strict=True` weight loading, PyTorch JIT/eval mode, and robust dimension alignment.

3. **Geospatial DEM Management & DSM Composition**
   - Queries real local/cached DEM tiles (SRTM, Copernicus, 3DEP) for true ground reference.
   - Automates Coordinate Reference System (CRS) reprojection and affine grid alignment via `rasterio`.
   - Produces calibrated metric height:
     $$\text{DSM} = \text{DEM} + \text{nDSM}$$

4. **RANSAC Ground Calibration**
   - Rejects non-ground outliers (tall trees, buildings, moving vehicles) using RANSAC linear regression with fallback scale-factor estimation.
   - Dynamic calibration confidence reporting ($0.0 - 1.0$).

5. **SegFormer Semantic Segmentation**
   - Integrated with `nvidia/segformer-b0-finetuned-ade-512-512`.
   - Returns full-resolution categorical class mask, per-pixel confidence scores, and land-cover percentage breakdowns (building %, vegetation %, water %, etc.).

6. **Production FastAPI Service**
   - `POST /estimate-height`: Upload image with optional GPS/bounds to receive relative or metric nDSM GeoTIFF and metadata.
   - `POST /segment`: Run SegFormer semantic segmentation.
   - `GET /download`: Path-traversal-protected endpoint for retrieving generated GeoTIFF and visualization rasters.
   - `GET /health`: Comprehensive service and GPU diagnostic checks.

---

## Repository Structure

```
.
├── app.py                      # Production FastAPI server & REST API
├── HTC-DC-Net/                 # HTC-DC Net PyTorch architecture
│   ├── models/
│   └── ...
├── pipeline/                   # Modular end-to-end processing pipeline
│   ├── image_inspection.py     # Image metadata, CRS, GSD, and EXIF extraction
│   ├── preprocessor.py         # Bit-depth normalization, RGB conversion, validation
│   ├── tiler.py                # Sliding-window Hann window inference
│   ├── model_runner.py         # PyTorch HTC-DC Net checkpoint runner
│   ├── dem_manager.py          # Real DEM fetching, caching, and reprojection
│   ├── calibration.py          # RANSAC ground calibration & confidence scoring
│   └── dsm.py                  # DSM = DEM + nDSM calculator
├── segmentation/               # Semantic land-cover segmentation
│   └── segformer.py            # SegFormer model runner & class distribution
├── tests/                      # Pytest automated test suite
├── verify_46_issues.py         # Comprehensive verification test suite
├── sanity_check.py             # Pipeline integration test script
├── run_on_imgggh.py            # Native resolution execution script
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## Quickstart Guide

### 1. Installation

Clone the repository and install required packages:
```bash
git clone <repository_url>
cd DepthWizard
pip install -r requirements.txt
```

### 2. Model Checkpoints
Place the HTC-DC Net trained weights in `checkpoints/`:
```bash
mkdir -p checkpoints
# Place checkpoint_best_rmse.pth.tar into checkpoints/
```

### 3. Run Pipeline via CLI
Run on any target image at native resolution:
```bash
python run_on_imgggh.py
```
This produces:
- Calibrated Float32 GeoTIFF: `outputs/<image_id>_relative_ndsm.tif`
- Production Summary JSON: `outputs/<image_id>_production_metadata.json`
- Visualization Plot: `outputs/<image_id>_execution_plot.png`

### 4. Launch the FastAPI Server
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```
Open interactive documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Verification & Testing

To run the complete 46-issue technical compliance test suite:
```bash
python verify_46_issues.py
```
All 46 unit, geospatial, and neural pipeline assertions pass with zero failures.

---

## License
MIT License.
