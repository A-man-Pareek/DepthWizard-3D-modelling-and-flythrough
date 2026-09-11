# Implementation Plan: Always Generate All Required Height/DSM Products and Metadata

Ensure the DepthWizard height estimation pipeline, CLI scripts, and FastAPI endpoints **always** automatically generate all required outputs according to the specification:
1. **Height/DSM raster file**: Single-band Float32 raster — GeoTIFF (if georeferenced) or plain TIFF (if non-georeferenced), matching native dimensions $(W, H)$.
2. **JSON metadata**: Clean standalone JSON (`<base_name>_metadata.json`) containing the exact required schema:
   ```json
   {
     "mode": "absolute-geo" | "absolute-semantic" | "relative",
     "units": "meters" | "relative_units",
     "confidence": "high" | "medium" | "n/a",
     "resolution": [width, height],
     "height_grid": [[...]]
   }
   ```
3. **Product GeoTIFFs & Summary Artifacts**: All distinct separated products (`relative_ndsm`, `metric_ndsm`, `dem`, `dsm`, `pred_height`), summary statistics, and comparison plots.

---

## User Review Required

> [!IMPORTANT]
> **JSON Metadata Contract**:
> - `<base_name>_metadata.json` will be written directly to `outputs/` containing the exact 5 keys (`mode`, `units`, `confidence`, `resolution`, `height_grid`).
> - `confidence` is normalized to `"high" | "medium" | "n/a"` to conform to the required enum.
> - `height_grid` is a 2D list of floats with shape `[H, W]` containing the primary height product (`dsm` if available, otherwise `metric_ndsm`, otherwise `relative_ndsm`).
> - Rich pipeline metrics and download URLs are preserved in `<base_name>_summary.json` and in `result.to_dict()` under `"products"`.

> [!NOTE]
> **HTC-DC Net Architecture Compatibility**:
> - We will update `pipeline/model_runner.py` to auto-detect whether the loaded checkpoint was trained with `head_tail_cut` enabled (e.g. `checkpoint_best_rmse.pth.tar` trained in the user's latest 5-epoch run). This eliminates the `RuntimeError` on `convs_htc` / `convs_out_bg` while maintaining strict weight verification.

---

## Proposed Changes

### 1. `pipeline/model_runner.py`

#### [MODIFY] [model_runner.py](file:///c:/Users/Aman/Desktop/New%20folder/pipeline/model_runner.py)
- Auto-detect `head_tail_cut` from checkpoint keys during `load_checkpoint` (if `convs_htc` or `convs_out_bg` are present in state dict, enable `head_tail_cut: True`, `prob_loss: 'dirac'`, `prob_loss_bg: 'bg'`).
- Ensure `self.cfgs` matches checkpoint architecture dynamically, so `strict=True` passes for both standard checkpoints and head-tail cut checkpoints.

---

### 2. `pipeline/exporter.py`

#### [MODIFY] [exporter.py](file:///c:/Users/Aman/Desktop/New%20folder/pipeline/exporter.py)
- Update `export_pipeline_products` to:
  1. Always export the primary Height/DSM raster as `<base_name>_dsm.tif` (as GeoTIFF if georeferenced, or plain TIFF if not) and `<base_name>_pred_height.tif`.
  2. For non-georeferenced images or AOIs without DEM, ensure the primary height raster (`metric_ndsm` or `relative_ndsm`) is exported as the Height/DSM raster (`<base_name>_dsm.tif`), clearly flagged `is_geotiff=False`.
  3. Export `<base_name>_metadata.json` directly to `output_dir` containing the required specification:
     ```json
     {
       "mode": "absolute-geo" | "absolute-semantic" | "relative",
       "units": "meters" | "relative_units",
       "confidence": "high" | "medium" | "n/a",
       "resolution": [width, height],
       "height_grid": [[...]]
     }
     ```
  4. Export `<base_name>_summary.json` containing summary statistics (`min`, `max`, `mean`, `std`, file paths, download URLs).

---

### 3. `pipeline/pipeline.py`

#### [MODIFY] [pipeline.py](file:///c:/Users/Aman/Desktop/New%20folder/pipeline/pipeline.py)
- In `process(...)`:
  - Pass the active calibration result and inspection to `export_pipeline_products` to write `<base_name>_metadata.json`, `<base_name>_dsm.tif`, `<base_name>_pred_height.tif`, and `<base_name>_summary.json`.
- In `PipelineResult`:
  - Add property `required_metadata` returning the exact 5-key dict (`mode`, `units`, `confidence`, `resolution`, `height_grid`).
  - In `to_dict()`, include `height_grid` while retaining `products` so both specification compliance and API test requirements are met.
  - Expose `metadata_json_path` and `raster_path` for clean programmatic access.

---

### 4. `app.py`

#### [MODIFY] [app.py](file:///c:/Users/Aman/Desktop/New%20folder/app.py)
- Ensure `POST /estimate-height` returns the JSON containing `mode`, `units`, `confidence`, `resolution`, `height_grid`, and `products`.
- Ensure download paths resolve `<base_name>_dsm.tif` and `<base_name>_metadata.json`.

---

### 5. Production & Execution Scripts

#### [MODIFY] [run_on_user_data.py](file:///c:/Users/Aman/Desktop/New%20folder/run_on_user_data.py)
- Ensure running the script generates all required outputs:
  - `<base_name>_dsm.tif`
  - `<base_name>_pred_height.tif`
  - `<base_name>_metadata.json`
  - `<base_name>_summary.json`
  - visualization plot

#### [MODIFY] [run_on_imgggh.py](file:///c:/Users/Aman/Desktop/New%20folder/run_on_imgggh.py)
- Standardize outputs for `imgggh.avif` to always produce `imgggh_dsm.tif`, `imgggh_metadata.json`, `imgggh_summary.json`, and `imgggh_execution_plot.png`.

#### [NEW] [run_inference.py](file:///c:/Users/Aman/Desktop/New%20folder/run_inference.py)
- Standalone CLI utility to run the pipeline on any image file or any scene ID from `data/data_dir` (e.g. `python run_inference.py --scene JAX_269_012` or `python run_inference.py --image path/to/image.tif`).
- Automatically generates all required products:
  - `<scene_id>_dsm.tif` (plain TIFF or GeoTIFF)
  - `<scene_id>_pred_height.tif`
  - `<scene_id>_metadata.json` (exact 5 keys)
  - `<scene_id>_summary.json` (stats and error metrics against ground truth if available)
  - `<scene_id>_comparison_plot.png` (visual panel)

---

## Verification Plan

### Automated Tests
1. **Model Loading & Checkpoint Verification**:
   - Run `python verify_46_issues.py` and verify all 46 technical compliance checks pass.
2. **API Integration Tests**:
   - Run `python test_api.py` and verify FastAPI endpoints return compliant JSON and download URLs.
3. **Pipeline Output Verification**:
   - Run `python run_on_imgggh.py` and `python run_inference.py --scene JAX_269_012`.
   - Verify that in `outputs/`:
     - Both `<base_name>_dsm.tif` and `<base_name>_pred_height.tif` exist as valid single-band Float32 TIFF/GeoTIFFs.
     - `<base_name>_metadata.json` exists and matches the exact 5-key schema with `height_grid` matching `[resolution[1], resolution[0]]`.
     - `<base_name>_summary.json` exists and contains correct summary statistics.
