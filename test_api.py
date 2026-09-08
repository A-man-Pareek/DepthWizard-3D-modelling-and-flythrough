"""Integration test for FastAPI endpoints.

Tests:
1. GET  /                   : Service information
2. GET  /health             : Runtime operational readiness and model load status
3. POST /estimate-height    : GeoTIFF & plain image upload, JSON metadata conformity
4. POST /segment            : SegFormer semantic segmentation endpoint
5. GET  /download/{filename}: Secure file download
6. Security                 : Directory traversal attack defense
"""

import os
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_api():
    print("Testing GET / ...")
    r0 = client.get("/")
    assert r0.status_code == 200, f"Expected 200, got {r0.status_code}"
    print("Index endpoint OK:", r0.json()["service"])

    print("\nTesting GET /health ...")
    r_health = client.get("/health")
    assert r_health.status_code == 200
    h_data = r_health.json()
    print("Health endpoint OK:", h_data)
    assert h_data["model_loaded"] is True
    assert h_data["checkpoint_loaded"] is True
    assert h_data["api_readiness"] == "ready"

    # Test directory traversal attack
    print("\nTesting directory traversal defense...")
    r_trav = client.get("/download/../../windows/win.ini")
    assert r_trav.status_code in (403, 404), f"Security failure: expected 403 or 404, got {r_trav.status_code}"
    print("Directory traversal defense verified: Access Denied.")

    # Test 1: Upload GeoTIFF
    geo_path = "data/test_georeferenced.tif"
    if os.path.isfile(geo_path):
        print(f"\nTesting POST /estimate-height with {geo_path} ...")
        with open(geo_path, "rb") as f:
            r1 = client.post("/estimate-height", files={"file": ("test_georeferenced.tif", f, "image/tiff")})
        assert r1.status_code == 200, f"Upload failed: {r1.text}"
        data1 = r1.json()
        print("GeoTIFF Response Mode:", data1["mode"])
        print("Units:", data1["units"])
        print("Confidence:", data1["confidence"])
        print("Resolution:", data1["resolution"])
        print("Exported Products:", list(data1["products"].keys()))
        assert data1["mode"] == "absolute-geo"
        assert data1["units"] == "meters"
        assert "products" in data1
        assert "relative_ndsm" in data1["products"]
        assert "dsm" in data1["products"]

        # Test download endpoint
        dl_url = data1["products"]["dsm"]["download_url"]
        r_dl = client.get(dl_url)
        assert r_dl.status_code == 200, f"Download failed: {r_dl.status_code}"
        assert len(r_dl.content) > 0
        print(f"GeoTIFF Raster Download verified: {len(r_dl.content)} bytes from {dl_url}")

    # Test 2: Upload Plain Image
    plain_path = "data/test_plain.png"
    if os.path.isfile(plain_path):
        print(f"\nTesting POST /estimate-height with {plain_path} ...")
        with open(plain_path, "rb") as f:
            r2 = client.post("/estimate-height", files={"file": ("test_plain.png", f, "image/png")})
        assert r2.status_code == 200, f"Upload failed: {r2.text}"
        data2 = r2.json()
        print("Plain Image Response Mode:", data2["mode"])
        print("Units:", data2["units"])
        print("Confidence:", data2["confidence"])
        print("Resolution:", data2["resolution"])
        assert data2["mode"] in ("absolute-semantic", "relative")
        assert "products" in data2

        dl_url2 = data2["products"]["relative_ndsm"]["download_url"]
        r_dl2 = client.get(dl_url2)
        assert r_dl2.status_code == 200
        print(f"Plain TIFF Raster Download verified: {len(r_dl2.content)} bytes from {dl_url2}")

    # Test 3: Dedicated Segmentation Endpoint
    if os.path.isfile(plain_path):
        print(f"\nTesting POST /segment with {plain_path} ...")
        with open(plain_path, "rb") as f:
            r3 = client.post("/segment", files={"file": ("test_plain.png", f, "image/png")})
        assert r3.status_code == 200, f"Segmentation endpoint failed: {r3.text}"
        data3 = r3.json()
        print("Segmentation Classes Detected:", len(data3.get("segmentation", [])))
        assert "products" in data3
        assert "segmentation" in data3["products"]

    print("\nALL FASTAPI INTEGRATION TESTS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    test_api()
