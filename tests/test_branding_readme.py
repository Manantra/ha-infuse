"""Ensure the Marketplace sees stable absolute image URLs and valid local brand assets."""

from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/Manantra/ha-infuse/main/"


def png_size(path: Path):
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), f"Invalid PNG: {path}"
    return struct.unpack(">II", data[16:24])


def test_marketplace_readme_previews_use_servable_absolute_urls():
    readme = (ROOT / "README.md").read_text()
    for name in ("single-device.png", "multiple-devices.png"):
        rel = f"assets/previews/{name}"
        assert (ROOT / rel).is_file()
        assert f"]({BASE}{rel})" in readme
        assert f"]({rel})" not in readme
    assert "render_readme" in (ROOT / "hacs.json").read_text()


def test_all_local_brand_assets_are_valid_png_with_correct_dimensions():
    brand = ROOT / "custom_components/infuse/brand"
    for name, size in (
        ("icon.png", (256,256)),
        ("icon@2x.png", (512,512)),
        ("logo.png", (256,256)),
        ("logo@2x.png", (512,512)),
    ):
        assert png_size(brand / name) == size
