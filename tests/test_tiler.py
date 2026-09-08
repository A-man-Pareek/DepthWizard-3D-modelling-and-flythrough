"""Unit tests for pipeline.tiler."""

import numpy as np
import torch
from pipeline.tiler import ImageTiler, compute_tile_slices, create_2d_window


def test_compute_tile_slices():
    # Length equal to tile size
    assert compute_tile_slices(256, 256, 192) == [(0, 256)]
    # Length smaller than tile size
    assert compute_tile_slices(128, 256, 192) == [(0, 128)]
    # Length 512 with tile size 256, stride 192 -> starts at 0, 192, and end clamped 256
    slices = compute_tile_slices(512, 256, 192)
    assert len(slices) >= 3
    assert slices[0] == (0, 256)
    assert slices[-1] == (256, 512)


def test_2d_hann_window():
    w = create_2d_window(256, blend_mode="hann")
    assert w.shape == (1, 1, 256, 256)
    assert w.min().item() > 0.0  # Must be strictly positive
    assert w.max().item() <= 1.0


def test_tiler_reconstruction_identity():
    tiler = ImageTiler(tile_size=256, overlap=64, blend_mode="hann")
    dummy_model = lambda x: x[:, :1, :, :] * 3.5

    for shape in [(3, 128, 128), (3, 256, 256), (3, 400, 300), (3, 512, 512)]:
        img = torch.randn(*shape)
        out = tiler.predict_tiled(img, dummy_model)
        assert out.shape == (1, shape[1], shape[2])
        expected = img[:1] * 3.5
        max_diff = (out - expected).abs().max().item()
        assert max_diff < 1e-4, f"Blending error {max_diff} exceeded tolerance on shape {shape}"


if __name__ == "__main__":
    test_compute_tile_slices()
    test_2d_hann_window()
    test_tiler_reconstruction_identity()
    print("All tiler tests passed!")
