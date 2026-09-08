"""Execute the DepthWizard pipeline on data/imgggh.avif."""

import os
import json
import shutil
import matplotlib.pyplot as plt
import numpy as np

from pipeline import HeightEstimationPipeline

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
ART_DIR = r"C:\Users\Aman\.gemini\antigravity-ide\brain\4e993859-5ac2-4d39-8f17-6f8afeac09bd"
os.makedirs(OUTPUT_DIR, exist_ok=True)

IMG_PATH = os.path.join(DATA_DIR, "imgggh.avif")


def main():
    print("=" * 70)
    print(f"RUNNING MODEL ON: {IMG_PATH}")
    print("=" * 70)

    if not os.path.isfile(IMG_PATH):
        raise FileNotFoundError(f"Input image not found: {IMG_PATH}")

    # Initialize production pipeline with verified checkpoint
    pipeline = HeightEstimationPipeline(
        checkpoint_path=os.path.join(PROJECT_ROOT, "checkpoints", "checkpoint_best_rmse.pth.tar"),
        dem_dir=os.path.join(DATA_DIR, "srtm"),
        require_checkpoint=True,
    )

    print("\nExecuting end-to-end pipeline with SegFormer semantic segmentation...")
    result = pipeline.process(
        input_source=IMG_PATH,
        run_segmentation=True,
        output_dir=OUTPUT_DIR,
        base_name="imgggh",
    )

    meta = result.metadata
    print("\n--- Pipeline Execution Summary ---")
    print(f"  Input Source:     {os.path.basename(IMG_PATH)}")
    print(f"  Georeferenced:    {result.inspection.is_georeferenced}")
    print(f"  Mode:             {meta['mode']}")
    print(f"  Units:            {meta['units']}")
    print(f"  Confidence:       {meta['confidence']}")
    print(f"  Native Shape:     {result.inspection.original_shape} (Height x Width)")
    print(f"  Output Res:       {meta['resolution']} [Width, Height]")
    print(f"  Exported Products:{list(result.exported_products.keys())}")

    # Product stats
    rel_stats = result.exported_products.get("relative_ndsm", {}).get("statistics", {})
    print(f"\n--- HTC-DC Net Height Statistics (626x626) ---")
    print(f"  Min:  {rel_stats.get('min'):.4f}")
    print(f"  Max:  {rel_stats.get('max'):.4f}")
    print(f"  Mean: {rel_stats.get('mean'):.4f}")
    print(f"  Std:  {rel_stats.get('std'):.4f}")

    if result.segmentation:
        print("\n--- SegFormer Semantic Segmentation Breakdown ---")
        for cls_info in result.segmentation.get("class_distribution", [])[:6]:
            print(f"  - {cls_info['class_name']}: {cls_info['percentage']}% ({cls_info['pixel_count']} pixels)")

    # Save metadata JSON
    json_path = os.path.join(OUTPUT_DIR, "imgggh_production_metadata.json")
    with open(json_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nMetadata JSON saved: {json_path}")

    # Generate rich 4-panel visual comparison plot
    print("\nGenerating visualization plots...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 13))
    fig.suptitle("DepthWizard Production Execution on 'imgggh.avif' (626x626)", fontsize=16, fontweight="bold")

    # Panel 1: Original RGB
    axes[0, 0].imshow(result.preprocessed.rgb_uint8)
    axes[0, 0].set_title("Input Image: imgggh.avif\nNative Resolution: 626x626 (RGB)", fontsize=12)
    axes[0, 0].axis("off")

    # Panel 2: HTC-DC Net Relative nDSM
    im1 = axes[0, 1].imshow(result.relative_ndsm, cmap="magma")
    axes[0, 1].set_title(
        f"HTC-DC Net Relative Height Map (nDSM)\nRes: 626x626 | Mean: {rel_stats.get('mean', 0):.2f}",
        fontsize=12,
    )
    axes[0, 1].axis("off")
    plt.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04, label="Relative Height Value")

    # Panel 3: SegFormer Semantic Segmentation
    if result.segmentation and "class_map" in result.segmentation:
        im2 = axes[1, 0].imshow(result.segmentation["class_map"], cmap="tab20")
        top_cls = result.segmentation["class_distribution"][0]["class_name"] if result.segmentation["class_distribution"] else "N/A"
        axes[1, 0].set_title(f"SegFormer Semantic Segmentation Map\nPrimary Class: {top_cls} (626x626)", fontsize=12)
    else:
        axes[1, 0].text(0.5, 0.5, "Segmentation N/A", ha="center", va="center")
    axes[1, 0].axis("off")

    # Panel 4: Relative Height Surface Contour
    im3 = axes[1, 1].imshow(result.relative_ndsm, cmap="terrain")
    axes[1, 1].set_title("Topographic / Elevation Surface View\nColormap: Terrain", fontsize=12)
    axes[1, 1].axis("off")
    plt.colorbar(im3, ax=axes[1, 1], fraction=0.046, pad=0.04, label="Elevation Contour")

    plt.tight_layout()
    plot_path = os.path.join(OUTPUT_DIR, "imgggh_execution_plot.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Visual plot saved to: {plot_path}")

    # Copy plot to artifacts directory for display
    if os.path.isdir(ART_DIR):
        dest_art = os.path.join(ART_DIR, "imgggh_execution_plot.png")
        shutil.copy(plot_path, dest_art)
        print(f"Copied plot to artifact directory: {dest_art}")

    print("\n" + "=" * 70)
    print("IMGGGH MODEL EXECUTION COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
