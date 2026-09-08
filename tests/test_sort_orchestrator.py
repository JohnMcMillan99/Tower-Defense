"""SortOrchestrator + PowerSort directive (Slice B)."""
from models.drone_data import DroneData
from core.sort_directives import PowerSortDirective, chunk_by_sizes, get_directive
from core.sort_orchestrator import SortOrchestrator, build_run_pool, unlocked_types_for_wave
from core.game import Game
from config import SORT_CONFIG


def test_drone_data_orders_by_power():
    a = DroneData.from_type("Drone", wave_num=1)
    b = DroneData.from_type("Assimilator", wave_num=1)
    assert a.power < b.power
    assert sorted([b, a])[0].enemy_type == "Drone"


def test_power_sort_ascending_then_chunk():
    pool = [
        DroneData.from_type("Assimilator", 1),
        DroneData.from_type("Drone", 1),
        DroneData.from_type("Harvester", 1),
        DroneData.from_type("Scout", 1),
    ]
    waves = PowerSortDirective().restructure(pool, [2, 2], seed=1)
    assert len(waves) == 2
    flat = waves[0] + waves[1]
    powers = [d.power for d in flat]
    assert powers == sorted(powers)
    assert len(waves[0]) == 2 and len(waves[1]) == 2


def test_build_pool_seeded_deterministic():
    def size(w):
        return 5 + w * 2

    a = build_run_pool(42, 5, size, unlocked_types_for_wave)
    b = build_run_pool(42, 5, size, unlocked_types_for_wave)
    c = build_run_pool(99, 5, size, unlocked_types_for_wave)
    assert [(d.enemy_type, d.power) for d in a] == [(d.enemy_type, d.power) for d in b]
    assert [(d.enemy_type, d.power) for d in a] != [(d.enemy_type, d.power) for d in c]
    assert len(a) == sum(size(w) for w in range(1, 6))


def test_orchestrator_next_wave_consumes():
    orch = SortOrchestrator.create(seed=7, planned_waves=5, web_mode=False)
    first = orch.next_wave()
    assert len(first) == 6  # wave 1 = min(cap, 5 + 1)
    second = orch.peek_wave(0)
    assert first != second or len(orch.remaining) == 4
    assert orch.waves_emitted == 1
    fc = orch.forecast(2)
    assert len(fc) == 2
    assert fc[0]["count"] == len(orch.peek_wave(0))
    assert sum(fc[0]["composition"].values()) == fc[0]["count"]


def test_same_seed_same_first_wave():
    a = SortOrchestrator.create(seed=123, planned_waves=10)
    b = SortOrchestrator.create(seed=123, planned_waves=10)
    assert [d.enemy_type for d in a.next_wave()] == [d.enemy_type for d in b.next_wave()]


def test_game_wires_orchestrator(monkeypatch):
    monkeypatch.setitem(SORT_CONFIG, "force_directive", "PowerSort")
    monkeypatch.setitem(SORT_CONFIG, "force_modifiers", [])
    monkeypatch.setitem(SORT_CONFIG, "force_hidden", False)
    g = Game(minimal_mode=True)
    assert g.sort_orchestrator is not None
    assert g.sort_orchestrator.directive_name == "PowerSort"
    assert g.run_seed == g.sort_orchestrator.seed


def test_preview_matches_orchestrator_chunk(monkeypatch):
    monkeypatch.setitem(SORT_CONFIG, "force_directive", "PowerSort")
    monkeypatch.setitem(SORT_CONFIG, "force_modifiers", [])
    monkeypatch.setitem(SORT_CONFIG, "force_hidden", False)
    g = Game(minimal_mode=True)
    g.intel = 25
    g.round_num = 1
    orch = g.sort_orchestrator
    expected = orch.forecast(1)[0]
    preview = g.wave_manager.preview_upcoming()
    entry = preview["waves"][0]
    assert entry["count"] == expected["count"]
    assert entry["is_exact"] is True
    # Percents should sum ~100 from exact counts
    assert abs(sum(entry["composition"].values()) - 100.0) < 1.5
    assert preview.get("directive") == orch.directive_name
    assert "confidence" in preview


def test_spawn_consumes_same_chunk_as_preview(monkeypatch):
    monkeypatch.setitem(SORT_CONFIG, "force_directive", "PowerSort")
    monkeypatch.setitem(SORT_CONFIG, "force_modifiers", [])
    monkeypatch.setitem(SORT_CONFIG, "force_hidden", False)
    g = Game(minimal_mode=True)
    g.intel = 25
    g.round_num = 1
    preview = g.wave_manager.preview_upcoming()
    expected_count = preview["waves"][0]["count"]
    g.wave_manager.start_next_wave(frame=0)
    assert len(g.spawn_queue) == expected_count
    # After spawn, preview advances
    g.wave_active = False
    g.round_num = 2
    nxt = g.wave_manager.preview_upcoming()
    assert nxt["waves"][0]["wave"] == 2


def test_directive_hint_at_matrix_intel(monkeypatch):
    monkeypatch.setitem(SORT_CONFIG, "force_directive", "PowerSort")
    monkeypatch.setitem(SORT_CONFIG, "force_modifiers", [])
    monkeypatch.setitem(SORT_CONFIG, "force_hidden", False)
    g = Game(minimal_mode=True)
    g.intel = 80
    preview = g.wave_manager.preview_upcoming()
    assert preview.get("directive_hint") == "Power Sort"


def test_get_directive_fallback():
    d = get_directive("Nope")
    assert d.name == "PowerSort"


def test_chunk_by_sizes_overflow():
    drones = [DroneData.from_type("Drone", 1) for _ in range(5)]
    waves = chunk_by_sizes(drones, [2, 2])
    assert len(waves) == 3
    assert len(waves[2]) == 1
