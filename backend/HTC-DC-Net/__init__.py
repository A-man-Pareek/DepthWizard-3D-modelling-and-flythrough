"""HTC-DC-Net package initialization."""
import os
import sys

# Ensure HTC-DC-Net directory is on sys.path so its internal module references work seamlessly
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)
