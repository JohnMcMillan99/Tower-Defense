"""Slice E: pre-run modifiers + directive pick/hidden."""
from core.run_setup import (
    MODIFIER_DEFS,
    RunSetup,
    apply_modifiers_to_size,
    build_modified_pool,
    pick_directive,
    unlocked_directives,
)
from core.sort_orchestrator import SortOrchestrator, unlocked_types_for_wave, default_wave_size
from core.game import Game
from config import SORT_CONFIG


def test_pick_directive_hidden_label():
    name, hidden, label = pick_directive(1, name="PowerSort", hidden=True)
    assert name == "PowerSort"
    assert hidden is True
    assert label == "???"
    _, _, shown = pick_directive(1, name="PowerSort", hidden=False)
    assert shown == "Power Sort"


def test_dense_swarm_increases_pool():
    base = build_modified_pool(7, 5, default_wave_size, unlocked_types_for_wave, [])
    dense = build_modified_pool(7, 5, default_wave_size, unlocked_types_for_wave, ["dense_swarm"])
    assert len(dense) > len(base)


def test_thin_signal_decreases_pool():
    base = build_modified_pool(7, 5, default_wave_size, unlocked_types_for_wave, [])
    thin = build_modified_pool(7, 5, default_wave_size, unlocked_types_for_wave, ["thin_signal"])
    assert len(thin) < len(base)


def test_early_unlock_shifts_types():
    # Wave 1 normally Drone-only; with early_unlock shift -2 still wave-like unlocks earlier
    types = unlocked_types_for_wave(1)
    assert types == ["Drone"]
    from core.run_setup import unlock_types_with_modifiers
    early = unlock_types_with_modifiers(1, unlocked_types_for_wave, ["early_unlock"])
    # wave 1 + (-2) clamped to 1 still Drone; wave 5 with shift unlocks earlier content
    mid = unlock_types_with_modifiers(5, unlocked_types_for_wave, ["early_unlock"])
    # effective wave 3 → Scout unlocked
    assert "Scout" in mid


def test_orchestrator_honors_modifiers():
    setup = RunSetup(seed=11, directive_name="PowerSort", modifier_ids=["dense_swarm"])
    orch = SortOrchestrator.create(run_setup=setup, planned_waves=5)
    plain = SortOrchestrator.create(seed=11, directive_name="PowerSort", planned_waves=5)
    assert orch.remaining_count > plain.remaining_count
    assert orch.modifier_ids == ["dense_swarm"]


def test_game_wires_run_setup(monkeypatch):
    monkeypatch.setitem(SORT_CONFIG, "force_directive", "DroneBubble")
    monkeypatch.setitem(SORT_CONFIG, "force_modifiers", ["speed_skew"])
    monkeypatch.setitem(SORT_CONFIG, "force_hidden", True)
    monkeypatch.setitem(SORT_CONFIG, "seed", 99)
    g = Game(minimal_mode=True)
    assert g.run_setup.directive_name == "DroneBubble"
    assert g.run_setup.directive_hidden is True
    assert "speed_skew" in g.run_setup.modifier_ids
    preview = g.wave_manager.preview_upcoming()
    # Hidden until Matrix intel
    g.intel = 0
    preview = g.wave_manager.preview_upcoming()
    assert preview.get("directive_hint") == "???"
    g.intel = 80
    preview = g.wave_manager.preview_upcoming()
    assert preview.get("directive_hint") == "Drone Bubble"
    assert preview.get("modifier_labels")


def test_random_offer_deterministic():
    a = RunSetup.random_offer(seed=123)
    b = RunSetup.random_offer(seed=123)
    assert a.to_dict() == b.to_dict()


def test_unlocked_directives_nonempty():
    assert "PowerSort" in unlocked_directives()
    assert set(MODIFIER_DEFS.keys())
