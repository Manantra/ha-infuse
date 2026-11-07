"""Custom integration brand files conform to the Home Assistant dimensions."""

from pathlib import Path
from struct import unpack
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def test_local_brand_icons_are_rgba_pngs_of_correct_size():
    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        path = ROOT / "custom_components/infuse/brand" / name
        data = path.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert data[12:16] == b"IHDR"
        assert unpack(">II", data[16:24]) == (size, size)
        assert data[25] == 6  # RGBA (supports transparent rounded corners)


def test_icon_source_reuses_existing_repo_emblem():
    ns = "{http://www.w3.org/2000/svg}"
    banner = ET.parse(ROOT / "assets/infuse-home-assistant.svg").getroot()
    icon = ET.parse(ROOT / "assets/infuse-mark.svg").getroot()
    original = next(element for element in banner if element.tag == ns + "g" and element.attrib.get("transform") == "translate(74 87)")
    mark = next(element for element in icon if element.tag == ns + "g")
    assert len(mark) == len(original)
    for source, extracted in zip(original, mark):
        assert source.tag == extracted.tag
        assert source.attrib == extracted.attrib
