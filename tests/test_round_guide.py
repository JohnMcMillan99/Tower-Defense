"""Round Guide preview + intel fog-of-war."""
from config import INTEL_CONFIG, REWARD_CONFIG
from core.game import Game
from core.wave_manager import WaveManager


def test_unlocked_types_ramp():
    assert WaveManager.unlocked_types_for_wave(1) == ["Drone"]
    assert "Scout" in WaveManager.unlocked_types_for_wave(3)
    assert "Harvester" in WaveManager.unlocked_types_for_wave(5)
    assert "Adaptor" in WaveManager.unlocked_types_for_wave(7)
    assert "Assimilator" in WaveManager.unlocked_types_for_wave(9)


def test_preview_low_intel_hides_types():
    g = Game(minimal_mode=True)
    g.intel = 0
    g.round_num = 1
    preview = g.wave_manager.preview_upcoming()
    assert preview["tier_label"] == "Contact"
    assert len(preview["waves"]) == 1
    entry = preview["waves"][0]
    assert entry["wave"] == 1
    assert entry["count"] == g.wave_manager.wave_size_for(1)
    assert entry["composition"] == {}
    assert entry["show_types"] is False


def test_preview_scan_shows_percents():
    g = Game(minimal_mode=True)
    g.intel = 25
    g.round_num = 1
    preview = g.wave_manager.preview_upcoming()
    assert preview["tier_label"] == "Scan"
    entry = preview["waves"][0]
    assert entry["show_types"] is True
    assert entry["show_percents"] is True
    # Orchestrator exact chunk → percent breakdown (may be softened by confidence)
    assert entry["composition"]
    assert set(entry["composition"].keys()) <= set(WaveManager.unlocked_types_for_wave(40))
    assert abs(sum(entry["composition"].values()) - 100.0) < 1.5
    assert entry["is_exact"] is True
    assert "confidence" in preview


def test_preview_horizon_grows_with_intel():
    g = Game(minimal_mode=True)
    g.round_num = 1
    g.intel = 0
    assert len(g.wave_manager.preview_upcoming()["waves"]) == 1
    g.intel = 50
    assert len(g.wave_manager.preview_upcoming()["waves"]) == 2
    g.intel = 75
    assert len(g.wave_manager.preview_upcoming()["waves"]) == 3


def test_loot_countdown():
    g = Game(minimal_mode=True)
    g.round_num = 3
    loot = g.wave_manager.waves_until_loot()
    assert loot["kind"] == "mini_boss"
    assert loot["waves"] == 2  # clear wave 5
    g.round_num = 5
    assert g.wave_manager.waves_until_loot()["waves"] == 0
    g.round_num = 20
    assert g.wave_manager.waves_until_loot()["kind"] == "boss"


def test_add_intel_clamps_and_egrem_gain(monkeypatch):
    g = Game(minimal_mode=True)
    g.intel = 0
    gain = INTEL_CONFIG.get("egrem_intel_gain", 8)
    g.add_intel(gain)
    assert g.intel == gain
    g.add_intel(9999)
    assert g.intel == g.intel_max


def test_round_guide_rect_below_auto():
    from ui.layout import UILayout

    g = Game(minimal_mode=True)
    L = UILayout(g)
    _, _, auto = L.panel_control_rects(show_spl=False)
    guide = L.round_guide_rect(show_spl=False)
    assert guide.y >= auto.bottom
    insp = L.inspector_rect()
    assert insp.y >= guide.bottom
