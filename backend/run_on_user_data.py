"""Execute complete production pipeline on real user imagery in data/ folder.

Runs:
1. High-resolution inspection and tiling
2. HTC-DC Net relative height inference
3. DEM query & RANSAC calibration (DSM generation if georeferenced)
4. SegFormer semantic segmentation
5. Multi-product GeoTIFF exports
6. Generates visual comparison plots saved to outputs/user_images_execution_plot.png
"""

import os
import json
import matplotlib.pyplot as plt
import numpy as np
from pipeline import HeightEstimationPipeline

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

images_to_run = [
    os.path.join(DATA_DIR, "test_georeferenced.tif"),
    os.path.join(DATA_DIR, "test_plain.png"),
    os.path.join(DATA_DIR, "Sentinel-2_L1C_from_2018-08-23_Mendocino_27.tif"),
    os.path.join(DATA_DIR, "satellite_maps_top_section_315aeb262d.webp"),
]



def main():
    print("=" * 70)
    print("EXECUTING PRODUCTION PIPELINE ON USER-PROVIDED IMAGES IN DATA/ FOLDER")
    print("=" * 70)

    pipeline = HeightEstimationPipeline(
        checkpoint_path=os.path.join(PROJECT_ROOT, "checkpoints", "checkpoint_best_rmse.pth.tar"),
        dem_dir=os.path.join(DATA_DIR, "srtm"),
        require_checkpoint=True,
    )
    results = []

    for img_path in images_to_run:
        if not os.path.isfile(img_path):
            print(f"Warning: File not found: {img_path}")
            continue

        filename = os.path.basename(img_path)
        base_name = os.path.splitext(filename)[0]
        print(f"\n---> Processing: {filename}")

        # Run complete pipeline including SegFormer semantic segmentation
        result = pipeline.process(
            input_source=img_path,
            run_segmentation=True,
            output_dir=OUTPUT_DIR,
            base_name=base_name,
        )

        meta = result.metadata
        print(f"  Georeferenced: {result.inspection.is_georeferenced}")
        print(f"  Mode:         {meta['mode']}")
        print(f"  Units:        {meta['units']}")
        print(f"  Confidence:   {meta['confidence']}")
        print(f"  Resolution:   {meta['resolution']}")
        print(f"  Products:     {list(result.exported_products.keys())}")

        if result.segmentation:
            top_classes = [(c['class_name'], c['percentage']) for c in result.segmentation['class_distribution'][:3]]
            print(f"  Top SegFormer Classes: {top_classes}")

        # Confirm all required artifacts
        print(f"  DSM Raster:       {os.path.join(OUTPUT_DIR, f'{base_name}_dsm.tif')}")
        print(f"  Pred Height:      {os.path.join(OUTPUT_DIR, f'{base_name}_pred_height.tif')}")
        print(f"  Metadata JSON:    {result.metadata_json_path}")
        print(f"  Summary JSON:     {result.summary_json_path}")

        results.append((filename, result))

    # Generate visual plot
    if results:
        n = len(results)
        fig, axes = plt.subplots(n, 4, figsize=(20, 5 * n))
        if n == 1:
            axes = axes[None, :]

        fig.suptitle("DepthWizard Production Execution on User Imagery", fontsize=16, fontweight="bold")

        for i, (name, res) in enumerate(results):
            # Column 1: Input image
            axes[i, 0].imshow(res.preprocessed.rgb_uint8)
            axes[i, 0].set_title(f"Input: {name}\nShape: {res.inspection.original_shape}")
            axes[i, 0].axis("off")

            # Column 2: HTC-DC Relative nDSM
            im1 = axes[i, 1].imshow(res.relative_ndsm, cmap="magma")
            axes[i, 1].set_title(f"HTC-DC Net Relative nDSM\nRes: {res.relative_ndsm.shape[1]}x{res.relative_ndsm.shape[0]}")
            axes[i, 1].axis("off")
            plt.colorbar(im1, ax=axes[i, 1], fraction=0.046, pad=0.04)

            # Column 3: Calibrated Height or DSM
            height_to_plot = res.calibration.dsm if res.calibration.dsm is not None else (
                res.calibration.metric_ndsm if res.calibration.metric_ndsm is not None else res.relative_ndsm
            )
            label = "DSM" if res.calibration.dsm is not None else ("Metric nDSM" if res.calibration.metric_ndsm is not None else "Relative nDSM")
            im2 = axes[i, 2].imshow(height_to_plot, cmap="terrain")
            axes[i, 2].set_title(f"Product: {label} ({res.calibration.units})\nConf: {res.calibration.confidence}")
            axes[i, 2].axis("off")
            plt.colorbar(im2, ax=axes[i, 2], fraction=0.046, pad=0.04)

            # Column 4: SegFormer Segmentation
            if res.segmentation and "class_map" in res.segmentation:
                axes[i, 3].imshow(res.segmentation["class_map"], cmap="tab20")
                axes[i, 3].set_title("SegFormer Segmentation Map")
            else:
                axes[i, 3].text(0.5, 0.5, "N/A", ha="center", va="center")
            axes[i, 3].axis("off")

        plt.tight_layout()
        plot_path = os.path.join(OUTPUT_DIR, "user_images_execution_plot.png")
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"\n[Plot] Visual comparison plot saved to: {plot_path}")

    print("\n" + "=" * 70)
    print("USER IMAGES EXECUTION COMPLETED")
    print(f"All products saved in: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
