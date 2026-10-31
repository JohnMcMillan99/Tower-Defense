"""Slice D: egrem pool noise + forecast confidence."""
from core.game import Game
from config import INTEL_CONFIG, SORT_CONFIG


def test_forecast_includes_confidence():
    g = Game(minimal_mode=True)
    g.intel = 50
    preview = g.wave_manager.preview_upcoming()
    assert "confidence" in preview
    assert 0 < preview["confidence"] <= 1
    for entry in preview["waves"]:
        assert "confidence" in entry


def test_noise_injection_raises_counter(monkeypatch):
    g = Game(minimal_mode=True)
    monkeypatch.setitem(INTEL_CONFIG, "egrem_noise_chance", 1.0)
    monkeypatch.setitem(INTEL_CONFIG, "egrem_noise_min", 2)
    monkeypatch.setitem(INTEL_CONFIG, "egrem_noise_max", 2)
    before = g.sort_orchestrator.remaining_count
    n = g.wave_manager.try_inject_egrem_noise()
    assert n == 2
    assert g.noise_injections == 1
    assert g.sort_orchestrator.remaining_count == before + 2


def test_egrem_inject_reshapes_next_wave_composition(monkeypatch):
    from collections import Counter
    from models.drone_data import DroneData

    g = Game(minimal_mode=True)
    orch = g.sort_orchestrator
    assert orch and orch.peek_wave(0)
    # Force a known next wave of all Drones
    size = len(orch.peek_wave(0))
    orch.remaining[0] = [DroneData.from_type("Drone", wave_num=1) for _ in range(size)]
    before = Counter(d.enemy_type for d in orch.peek_wave(0))
    scouts = [DroneData.from_type("Scout", wave_num=1) for _ in range(2)]
    orch.inject(scouts, swaps=2)
    after = Counter(d.enemy_type for d in orch.peek_wave(0))
    assert after["Scout"] >= 2
    assert after != before
    assert sum(after.values()) == size + 2


def test_try_inject_records_last_egrem_noise(monkeypatch):
    g = Game(minimal_mode=True)
    monkeypatch.setitem(INTEL_CONFIG, "egrem_noise_chance", 1.0)
    monkeypatch.setitem(INTEL_CONFIG, "egrem_noise_min", 1)
    monkeypatch.setitem(INTEL_CONFIG, "egrem_noise_max", 1)
    monkeypatch.setitem(INTEL_CONFIG, "egrem_reshape_swaps", 2)
    assert g.wave_manager.try_inject_egrem_noise() == 1
    info = g.last_egrem_noise
    assert info and info["added"] == 1
    assert info["composition_changed"] is True
    preview = g.wave_manager.preview_upcoming()
    assert preview.get("egrem_noise", 0) >= 1


def test_noise_lowers_confidence(monkeypatch):
    g = Game(minimal_mode=True)
    g.intel = 80
    base = g.wave_manager._forecast_confidence(80, 0)
    g.noise_injections = 3
    noisy = g.wave_manager._forecast_confidence(80, 0)
    assert noisy < base


def test_matrix_still_shows_directive_hint(monkeypatch):
    monkeypatch.setitem(SORT_CONFIG, "force_directive", "PowerSort")
    monkeypatch.setitem(SORT_CONFIG, "force_hidden", False)
    g = Game(minimal_mode=True)
    g.intel = 80
    preview = g.wave_manager.preview_upcoming()
    assert preview.get("directive_hint")
