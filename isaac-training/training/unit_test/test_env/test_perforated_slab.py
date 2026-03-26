import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENVS_PATH = ROOT / "envs"
if str(ENVS_PATH) not in sys.path:
    sys.path.insert(0, str(ENVS_PATH))

from env_gen import ArenaConfig, make_perforated_slab, validate_primitive


def test_valid_perforated_slab():
    cfg = ArenaConfig()
    primitive = make_perforated_slab(
        "panel_0001",
        size_x=4.0,
        size_y=3.0,
        thickness=0.2,
        x=0.0,
        y=0.0,
        z=1.5,
        slab_mode="vertical",
        holes=[{
            "shape": "rectangle",
            "center_u": 0.0,
            "center_v": 0.0,
            "width": 1.0,
            "height": 1.2,
        }],
        edge_margin_min=0.2,
        hole_spacing_min=0.2,
        support_mode="grounded",
    )
    report = validate_primitive(primitive, cfg.to_workspace())
    assert report["valid"] is True


def test_invalid_overlapping_holes():
    cfg = ArenaConfig()
    primitive = make_perforated_slab(
        "panel_0002",
        size_x=4.0,
        size_y=3.0,
        thickness=0.2,
        x=0.0,
        y=0.0,
        z=1.5,
        slab_mode="vertical",
        holes=[
            {"shape": "circle", "center_u": 0.0, "center_v": 0.0, "radius": 0.6},
            {"shape": "circle", "center_u": 0.2, "center_v": 0.0, "radius": 0.6},
        ],
        edge_margin_min=0.2,
        hole_spacing_min=0.2,
        support_mode="floating",
    )
    report = validate_primitive(primitive, cfg.to_workspace())
    assert report["valid"] is False
    assert any("hole" in error for error in report["errors"])
