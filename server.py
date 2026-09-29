import os
import shutil
import json
import sys
import uuid
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tif", "tiff"}
MAX_FILE_SIZE = 25 * 1024 * 1024

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def log(msg):
    print(f"[DepthWizard] {msg}")


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/upload", methods=["POST"])
def upload_image():
    log("Received upload request")
    if "image" not in request.files:
        log("Upload failed: no image field")
        return jsonify({"success": False, "error": "No image file was uploaded."}), 400

    file = request.files["image"]
    if file.filename == "":
        log("Upload failed: empty filename")
        return jsonify({"success": False, "error": "No file selected."}), 400

    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        log(f"Upload rejected: unsupported extension {ext}")
        return jsonify({"success": False, "error": "Unsupported image format. Please upload PNG, JPG, JPEG or TIFF."}), 400

    if file.content_length and file.content_length > MAX_FILE_SIZE:
        log(f"Upload rejected: file too large ({file.content_length} bytes)")
        return jsonify({"success": False, "error": "File is too large. Please upload an image under 25 MB."}), 400

    safe_name = secure_filename(file.filename)
    if not safe_name:
        safe_name = f"uploaded_{uuid.uuid4().hex}.png"

    if safe_name.rsplit(".", 1)[-1].lower() not in ALLOWED_EXTENSIONS:
        log(f"Upload rejected: bad extension {safe_name}")
        return jsonify({"success": False, "error": "Unsupported image format. Please upload PNG, JPG, JPEG or TIFF."}), 400

    unique_name = f"upload_{uuid.uuid4().hex}_{safe_name}"
    target_path = INPUT_DIR / unique_name

    try:
        file.save(str(target_path))
    except Exception as exc:
        log(f"Upload save failed: {exc}")
        return jsonify({"success": False, "error": "Failed to save uploaded image."}), 500

    log(f"Saved uploaded image to {target_path}")
    return jsonify({
        "success": True,
        "filename": unique_name,
        "path": str(target_path.relative_to(BASE_DIR)),
        "message": "Upload complete"
    })


@app.route("/api/process", methods=["POST"])
def process_image():
    log("Processing request received")
    payload = request.get_json(silent=True) or {}
    filename = payload.get("filename")

    if not filename:
        return jsonify({"success": False, "error": "No uploaded filename was provided."}), 400

    image_path = INPUT_DIR / filename
    if not image_path.exists():
        return jsonify({"success": False, "error": f"Uploaded file was not found: {filename}"}), 404

    log(f"Starting processing for {image_path}")

    try:
        processed = run_pipeline(image_path)
    except Exception as exc:
        log(f"Processing pipeline failed: {exc}")
        return jsonify({"success": False, "error": f"Processing failed: {exc}"}), 500

    if not processed:
        return jsonify({"success": False, "error": "Processing pipeline did not generate the expected outputs."}), 500

    log("Processing complete")
    return jsonify({
        "success": True,
        "message": "Processing complete",
        "outputs": {
            "scene": "/output/semantic_scene.html",
            "sceneData": "/output/semantic_scene.json",
            "terrain": "/output/terrain_data.json",
            "texture": "/output/satellite_texture.png"
        }
    })


def prepare_matching_rasters(target_image_path: Path):
    """
    Ensures input/image.tiff, input/height.tiff, and input/segmentation.tiff
    all exist and share identical (H, W) raster dimensions.
    """
    import rasterio
    import cv2
    import numpy as np
    from PIL import Image

    # 1. Read input image and write GTiff RGB image
    try:
        if target_image_path.suffix.lower() in {".tif", ".tiff"}:
            with rasterio.open(target_image_path) as src:
                rgb_raw = src.read()
                if rgb_raw.shape[0] >= 3:
                    rgb = np.transpose(rgb_raw[:3], (1, 2, 0)).astype(np.uint8)
                else:
                    ch = rgb_raw[0].astype(np.uint8)
                    rgb = np.stack([ch, ch, ch], axis=-1)
        else:
            with Image.open(target_image_path) as img:
                img = img.convert("RGB")
                max_dim = 2048
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                rgb = np.array(img, dtype=np.uint8)

        img_h, img_w, _ = rgb.shape
        target_image = INPUT_DIR / "image.tiff"

        meta = {
            "driver": "GTiff",
            "height": img_h,
            "width": img_w,
            "count": 3,
            "dtype": "uint8"
        }
        with rasterio.open(target_image, "w", **meta) as dst:
            for i in range(3):
                dst.write(rgb[:, :, i], i + 1)
        log(f"Standardized input/image.tiff to {img_w}x{img_h}")
    except Exception as exc:
        log(f"Failed to process image file: {exc}")
        raise

    target_height = INPUT_DIR / "height.tiff"
    target_seg = INPUT_DIR / "segmentation.tiff"

    # 2. Synchronize height.tiff
    if target_height.exists():
        try:
            with rasterio.open(target_height) as h_src:
                h_data = h_src.read(1)
                if h_data.shape != (img_h, img_w):
                    log(f"Resizing height map from {h_data.shape} to {(img_h, img_w)}")
                    h_resized = cv2.resize(h_data, (img_w, img_h), interpolation=cv2.INTER_LINEAR)
                    h_meta = {
                        "driver": "GTiff",
                        "height": img_h,
                        "width": img_w,
                        "count": 1,
                        "dtype": "float32"
                    }
                    with rasterio.open(target_height, "w", **h_meta) as h_dst:
                        h_dst.write(h_resized.astype(np.float32), 1)
        except Exception as exc:
            log(f"Error reading height map, recreating: {exc}")
            target_height.unlink(missing_ok=True)

    if not target_height.exists():
        log(f"Generating synthetic height map of shape {(img_h, img_w)}")
        y = np.linspace(2.0, 18.0, img_h, dtype=np.float32)
        h_data = np.repeat(y[:, np.newaxis], img_w, axis=1)
        h_meta = {
            "driver": "GTiff",
            "height": img_h,
            "width": img_w,
            "count": 1,
            "dtype": "float32"
        }
        with rasterio.open(target_height, "w", **h_meta) as h_dst:
            h_dst.write(h_data, 1)

    # 3. Synchronize segmentation.tiff
    if target_seg.exists():
        try:
            with rasterio.open(target_seg) as s_src:
                s_data = s_src.read(1)
                if s_data.shape != (img_h, img_w):
                    log(f"Resizing segmentation map from {s_data.shape} to {(img_h, img_w)}")
                    s_resized = cv2.resize(s_data, (img_w, img_h), interpolation=cv2.INTER_NEAREST)
                    s_meta = {
                        "driver": "GTiff",
                        "height": img_h,
                        "width": img_w,
                        "count": 1,
                        "dtype": "uint8"
                    }
                    with rasterio.open(target_seg, "w", **s_meta) as s_dst:
                        s_dst.write(s_resized.astype(np.uint8), 1)
        except Exception as exc:
            log(f"Error reading segmentation map, recreating: {exc}")
            target_seg.unlink(missing_ok=True)

    if not target_seg.exists():
        log(f"Generating synthetic segmentation map of shape {(img_h, img_w)}")
        s_data = np.full((img_h, img_w), 13, dtype=np.uint8)  # 13 = earth ground
        s_meta = {
            "driver": "GTiff",
            "height": img_h,
            "width": img_w,
            "count": 1,
            "dtype": "uint8"
        }
        with rasterio.open(target_seg, "w", **s_meta) as s_dst:
            s_dst.write(s_data, 1)


def run_pipeline(image_path: Path):
    log(f"Preparing input image: {image_path}")

    prepare_matching_rasters(image_path)

    # Run prepare_3d if available to update terrain_data.json
    prepare_script = BASE_DIR / "src" / "prepare_3d.py"
    if prepare_script.exists():
        log(f"Running prepare_3d script: {prepare_script}")
        import subprocess
        p_res = subprocess.run([sys.executable, str(prepare_script)], cwd=str(BASE_DIR), capture_output=True, text=True)
        if p_res.returncode != 0:
            log(f"prepare_3d output: {p_res.stdout}\n{p_res.stderr}")

    # Always execute 3D reconstruction script
    script = BASE_DIR / "src" / "semantic_3d_reconstruction.py"
    if script.exists():
        log(f"Running reconstruction script: {script}")
        import subprocess
        result = subprocess.run([sys.executable, str(script)], cwd=str(BASE_DIR), capture_output=True, text=True)
        log(result.stdout)
        if result.stderr:
            log(result.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"Reconstruction script failed with exit code {result.returncode}: {result.stderr or result.stdout}")
    else:
        raise RuntimeError("The 3D reconstruction pipeline script was not found.")

    required = [
        OUTPUT_DIR / "semantic_scene.json",
        OUTPUT_DIR / "semantic_scene.html",
        OUTPUT_DIR / "terrain_data.json",
        OUTPUT_DIR / "satellite_texture.png"
    ]

    if not all(p.exists() for p in required):
        raise RuntimeError("Processing did not produce the required output artifacts.")

    return True


@app.route("/output/<path:filename>", methods=["GET"])
def serve_output(filename):
    return send_from_directory(str(OUTPUT_DIR), filename)


@app.route("/input/<path:filename>", methods=["GET"])
def serve_input(filename):
    return send_from_directory(str(INPUT_DIR), filename)


@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
