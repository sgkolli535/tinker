from pathlib import Path

from tinker.db.lookup import fuzzy_match, load_json


def test_fuzzy_match_controls() -> None:
    root = Path(__file__).resolve().parents[1] / "tinker" / "domains" / "synth_midi" / "db"
    controls = load_json(root / "controls.json")
    match, score = fuzzy_match("rotary encoder", controls, key="type")
    assert match is not None
    assert match["id"] == "encoder_24det_push"
    assert score > 0.5
