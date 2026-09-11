"""DepthWizard Production CLI Inference Tool.

Runs height estimation and DSM generation on:
1. Any arbitrary image/raster (--image path/to/image.tif)
2. Any scene ID from the benchmark dataset (--scene JAX_269_012)

Always generates all required outputs:
- <base_name>_dsm.tif (Single-band Float32 GeoTIFF or plain TIFF)
- <base_name>_pred_height.tif (Single-band Float32 predicted height)
- <base_name>_metadata.json (Exact 5-key schema)
- <base_name>_summary.json (Summary statistics, metrics, download paths)
- <base_name>_comparison_plot.png (Visual multi-panel inspection)
"""

import argparse
import json
import os
import shutil
import sys
from typing import Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import rasterio

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline import HeightEstimationPipeline

ART_DIR = r"C:\Users\Aman\.gemini\antigravity-ide\brain\26b960e3-776f-4e80-a368-f88189ab387d"


def compute_evaluation_metrics(pred: np.ndarray, target: np.ndarray) -> dict:
    """Compute standard height estimation error metrics against ground truth."""
    mask = np.isfinite(pred) & np.isfinite(target) & (target >= 0.0) & (target < 400.0)
    if not np.any(mask):
        return {"error": "No valid pixels for ground truth evaluation"}

    p = pred[mask].astype(np.float64)
    t = target[mask].astype(np.float64)

    diff = p - t
    abs_diff = np.abs(diff)
    mae = float(np.mean(abs_diff))
    rmse = float(np.sqrt(np.mean(diff ** 2)))

    # Correlation / R2
    ss_tot = np.sum((t - np.mean(t)) ** 2)
    ss_res = np.sum(diff ** 2)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-6 else 0.0

    # Delta accuracies: max(p/t, t/p) < threshold
    valid_ratio = (p > 0.1) & (t > 0.1)
    if np.any(valid_ratio):
        pv = p[valid_ratio]
        tv = t[valid_ratio]
        thresh = np.maximum(pv / tv, tv / pv)
        delta1 = float(np.mean(thresh < 1.25))
        delta2 = float(np.mean(thresh < 1.25 ** 2))
        delta3 = float(np.mean(thresh < 1.25 ** 3))
    else:
        delta1 = delta2 = delta3 = 0.0

    return {
        "valid_pixel_count": int(np.count_nonzero(mask)),
        "mae_meters": mae,
        "rmse_meters": rmse,
        "r2_score": r2,
        "delta_1.25": delta1,
        "delta_1.25_sq": delta2,
        "delta_1.25_cu": delta3,
    }


def find_scene_files(scene_id: str, data_dir: str) -> Tuple[str, Optional[str]]:
    """Resolve scene image and ground truth nDSM paths."""
    # Look for image
    img_candidates = [
        os.path.join(data_dir, "image", f"{scene_id}_IMG.tif"),
        os.path.join(data_dir, "image", f"{scene_id}.tif"),
        os.path.join(data_dir, f"{scene_id}_IMG.tif"),
        os.path.join(data_dir, f"{scene_id}.tif"),
    ]
    img_path = next((c for c in img_candidates if os.path.isfile(c)), None)
    if not img_path:
        raise FileNotFoundError(f"Could not find image for scene '{scene_id}' in {data_dir}")

    # Look for ground truth
    gt_candidates = [
        os.path.join(data_dir, "ndsm", f"{scene_id}_AGL.tif"),
        os.path.join(data_dir, "ndsm", f"{scene_id}_DSM.tif"),
        os.path.join(data_dir, "ndsm", f"{scene_id}_ndsm.tif"),
        os.path.join(data_dir, f"{scene_id}_AGL.tif"),
    ]
    gt_path = next((c for c in gt_candidates if os.path.isfile(c)), None)

    return img_path, gt_path


def main():
    parser = argparse.ArgumentParser(description="DepthWizard Height Estimation Inference Utility")
    parser.add_argument("--image", type=str, default=None, help="Path to input raster/image")
    parser.add_argument("--scene", type=str, default=None, help="Scene ID from benchmark dataset (e.g. JAX_269_012)")
    parser.add_argument("--data-dir", type=str, default=os.path.join(PROJECT_ROOT, "data", "data_dir"), help="Benchmark data root")
    parser.add_argument("--dem-dir", type=str, default=os.path.join(PROJECT_ROOT, "data", "srtm"), help="DEM tiles directory")
    parser.add_argument("--checkpoint", type=str, default=os.path.join(PROJECT_ROOT, "checkpoints", "checkpoint_best_rmse.pth.tar"))
    parser.add_argument("--output-dir", type=str, default=os.path.join(PROJECT_ROOT, "outputs"))
    parser.add_argument("--segmentation", dest="segmentation", action="store_true", default=True, help="Run SegFormer semantic segmentation (default: True)")
    parser.add_argument("--no-segmentation", dest="segmentation", action="store_false", help="Disable SegFormer semantic segmentation")

    args = parser.parse_args()

    if not args.image and not args.scene:
        # Default to sample scene if nothing provided
        args.scene = "JAX_269_012"
        print(f"[Inference] No image or scene specified. Defaulting to benchmark scene: '{args.scene}'")

    gt_arr = None
    if args.scene:
        img_path, gt_path = find_scene_files(args.scene, args.data_dir)
        base_name = args.scene
        if gt_path:
            print(f"[Inference] Found ground truth nDSM: {gt_path}")
            with rasterio.open(gt_path) as src:
                gt_arr = src.read(1).astype(np.float32)
                nodata = src.nodata
                if nodata is not None:
                    gt_arr[gt_arr == nodata] = np.nan
    else:
        img_path = os.path.abspath(args.image)
        if not os.path.isfile(img_path):
            raise FileNotFoundError(f"Input image not found: {img_path}")
        base_name = os.path.splitext(os.path.basename(img_path))[0]

    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 75)
    print(f"DEPTHWIZARD INFERENCE: {base_name}")
    print(f"Input image:  {img_path}")
    print(f"Output dir:   {args.output_dir}")
    print(f"Segmentation: {args.segmentation}")
    print("=" * 75)

    # Initialize production pipeline
    pipeline = HeightEstimationPipeline(
        checkpoint_path=args.checkpoint,
        dem_dir=args.dem_dir,
        require_checkpoint=True,
    )

    # Process through unified pipeline
    result = pipeline.process(
        input_source=img_path,
        run_segmentation=args.segmentation,
        reference_ndsm=gt_arr,
        output_dir=args.output_dir,
        base_name=base_name,
    )

    meta = result.metadata
    print("\n--- Execution Summary ---")
    print(f"  Georeferenced: {result.inspection.is_georeferenced}")
    print(f"  Mode:         {meta['mode']}")
    print(f"  Units:        {meta['units']}")
    print(f"  Confidence:   {meta['confidence']}")
    print(f"  Resolution:   {meta['resolution']} (Width x Height)")
    print(f"  Products:     {list(result.exported_products.keys())}")

    # Confirm required artifacts
    dsm_file = os.path.join(args.output_dir, f"{base_name}_dsm.tif")
    pred_file = os.path.join(args.output_dir, f"{base_name}_pred_height.tif")
    meta_file = result.metadata_json_path
    summary_file = result.summary_json_path
    seg_file = os.path.join(args.output_dir, f"{base_name}_segmentation.tif")

    print("\n--- Core Artifacts Generated ---")
    print(f"  [Raster]  Height/DSM GeoTIFF: {dsm_file} (exists: {os.path.isfile(dsm_file)})")
    print(f"  [Raster]  Predicted Height:   {pred_file} (exists: {os.path.isfile(pred_file)})")
    print(f"  [JSON]    Metadata (5 keys):  {meta_file} (exists: {os.path.isfile(meta_file)})")
    print(f"  [JSON]    Summary Details:    {summary_file} (exists: {os.path.isfile(summary_file)})")
    if result.segmentation:
        print(f"  [Raster]  Segmentation Raster:{seg_file} (exists: {os.path.isfile(seg_file)})")

    # Evaluate against ground truth if available
    eval_metrics = {}
    primary_height = result.primary_height_array
    if gt_arr is not None:
        eval_metrics = compute_evaluation_metrics(primary_height, gt_arr)
        print("\n--- Ground Truth Evaluation Metrics ---")
        for k, v in eval_metrics.items():
            if isinstance(v, float):
                print(f"  {k:20s}: {v:.4f}")
            else:
                print(f"  {k:20s}: {v}")

        # Update summary JSON with evaluation metrics
        if os.path.isfile(summary_file):
            with open(summary_file, "r") as f:
                summary_data = json.load(f)
            summary_data["evaluation_metrics"] = eval_metrics
            with open(summary_file, "w") as f:
                json.dump(summary_data, f, indent=2)

    # If segmentation is available, print breakdown and export dedicated segmentation plot
    if result.segmentation and "class_map" in result.segmentation:
        class_map = result.segmentation["class_map"]
        dist = result.segmentation.get("class_distribution", [])
        print("\n--- SegFormer Semantic Segmentation Breakdown ---")
        for d in dist[:6]:
            print(f"  Class {d['class_id']:3d} [{d['class_name']:15s}]: {d['percentage']:6.2f}% ({d['pixel_count']} pixels)")

        # Save dedicated segmentation plot
        import matplotlib.patches as mpatches
        fig_seg, axes_seg = plt.subplots(1, 3, figsize=(21, 7))
        fig_seg.suptitle(f"SegFormer Segmentation: {base_name}", fontsize=16, fontweight="bold")

        axes_seg[0].imshow(result.preprocessed.rgb_uint8)
        axes_seg[0].set_title("Input Satellite Image", fontsize=12)
        axes_seg[0].axis("off")

        im_c = axes_seg[1].imshow(class_map, cmap="tab20")
        axes_seg[1].set_title(f"Full 150-Class Map (Top: {dist[0]['class_name']} {dist[0]['percentage']}%)", fontsize=12)
        axes_seg[1].axis("off")
        cmap = plt.get_cmap("tab20")
        patches = [mpatches.Patch(color=cmap(d["class_id"] % 20), label=f"{d['class_name']}: {d['percentage']}%") for d in dist[:6]]
        axes_seg[1].legend(handles=patches, loc="upper right", bbox_to_anchor=(1.35, 1.0), fontsize=9)

        # Isolated Buildings & Trees Overlay
        b_mask = (class_map == 1) | (class_map == 25)
        t_mask = (class_map == 4) | (class_map == 17)
        axes_seg[2].imshow(result.preprocessed.rgb_uint8)
        axes_seg[2].imshow(np.ma.masked_where(~b_mask, b_mask), cmap="Reds_r", alpha=0.6)
        axes_seg[2].imshow(np.ma.masked_where(~t_mask, t_mask), cmap="Greens_r", alpha=0.5)
        axes_seg[2].set_title("Features Overlay: Buildings (Red) & Trees (Green)", fontsize=12)
        axes_seg[2].axis("off")

        plt.tight_layout()
        seg_plot_path = os.path.join(args.output_dir, f"{base_name}_segmentation_plot.png")
        plt.savefig(seg_plot_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Segmentation plot saved to: {seg_plot_path}")

        if os.path.isdir(ART_DIR):
            shutil.copy(seg_plot_path, os.path.join(ART_DIR, f"{base_name}_segmentation_plot.png"))

    # Generate visual comparison plot
    print("\nGenerating visual comparison plot...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 13))
    fig.suptitle(f"DepthWizard Height Estimation: {base_name}", fontsize=16, fontweight="bold")

    # Panel 1: Input RGB
    axes[0, 0].imshow(result.preprocessed.rgb_uint8)
    axes[0, 0].set_title(f"Input RGB ({meta['resolution'][0]}x{meta['resolution'][1]})", fontsize=12)
    axes[0, 0].axis("off")

    # Panel 2: Predicted Primary Height / DSM
    im_pred = axes[0, 1].imshow(primary_height, cmap="magma")
    axes[0, 1].set_title(f"Predicted Height / DSM ({meta['units']})\nMode: {meta['mode']} | Conf: {meta['confidence']}", fontsize=12)
    axes[0, 1].axis("off")
    plt.colorbar(im_pred, ax=axes[0, 1], fraction=0.046, pad=0.04)

    if gt_arr is not None:
        # Panel 3: Ground Truth
        im_gt = axes[1, 0].imshow(gt_arr, cmap="magma")
        axes[1, 0].set_title(f"Ground Truth nDSM (meters)\nMAE: {eval_metrics.get('mae_meters', 0):.2f}m | RMSE: {eval_metrics.get('rmse_meters', 0):.2f}m", fontsize=12)
        axes[1, 0].axis("off")
        plt.colorbar(im_gt, ax=axes[1, 0], fraction=0.046, pad=0.04)

        # Panel 4: Absolute Error Map
        err_map = np.abs(primary_height - gt_arr)
        err_map[np.isnan(gt_arr)] = 0.0
        im_err = axes[1, 1].imshow(err_map, cmap="hot")
        axes[1, 1].set_title("Absolute Error Map (|Pred - GT| in meters)", fontsize=12)
        axes[1, 1].axis("off")
        plt.colorbar(im_err, ax=axes[1, 1], fraction=0.046, pad=0.04)
    else:
        # Panel 3: Relative nDSM or Segmentation
        if result.segmentation and "class_map" in result.segmentation:
            axes[1, 0].imshow(result.segmentation["class_map"], cmap="tab20")
            axes[1, 0].set_title("SegFormer Semantic Segmentation Map", fontsize=12)
        else:
            im_rel = axes[1, 0].imshow(result.relative_ndsm, cmap="plasma")
            axes[1, 0].set_title("HTC-DC Net Relative nDSM", fontsize=12)
            plt.colorbar(im_rel, ax=axes[1, 0], fraction=0.046, pad=0.04)
        axes[1, 0].axis("off")

        # Panel 4: Surface Contour
        im_surf = axes[1, 1].imshow(primary_height, cmap="terrain")
        axes[1, 1].set_title("Elevation / Surface Terrain View", fontsize=12)
        axes[1, 1].axis("off")
        plt.colorbar(im_surf, ax=axes[1, 1], fraction=0.046, pad=0.04)

    plt.tight_layout()
    plot_path = os.path.join(args.output_dir, f"{base_name}_comparison_plot.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Visual plot saved to: {plot_path}")

    # Copy plot to artifact directory if available
    if os.path.isdir(ART_DIR):
        art_dest = os.path.join(ART_DIR, f"{base_name}_comparison_plot.png")
        shutil.copy(plot_path, art_dest)
        print(f"Copied plot to artifact directory: {art_dest}")

    print("\n" + "=" * 75)
    print("INFERENCE COMPLETED SUCCESSFULLY!")
    print("=" * 75)



if __name__ == "__main__":
    main()
