"""Wave pressure catalog: unlocks, adaptation, milestone scale, gold knobs."""
import pytest
from config import ADAPTATION_CONFIG, LATCH_CONFIG, REWARD_CONFIG, ECONOMY_CONFIG
from core.devtools import catalog, reset_catalog_for_tests
from core.game import Game
from core.sort_orchestrator import unlocked_types_for_wave
from core.strategy_analyzer import StrategyAnalyzer
from data.loader import DataLoader
from models.enemy import Enemy
from models.tower import Tower


@pytest.fixture(autouse=True)
def _tower_loader():
    Tower.set_data_loader(DataLoader())
    yield
    Tower._data_loader = None


def test_unlocks_follow_first_wave():
    assert unlocked_types_for_wave(1) == ["Drone"]
    assert "Scout" in unlocked_types_for_wave(3)
    assert "Assimilator" in unlocked_types_for_wave(9)


def test_unlocks_read_live_types(monkeypatch):
    monkeypatch.setitem(Enemy.TYPES["Scout"], "first_wave", 1)
    assert "Scout" in unlocked_types_for_wave(1)


def test_adapt_uses_adaptation_config(monkeypatch):
    monkeypatch.setitem(ADAPTATION_CONFIG["hybrid_exposure"], "factor_per_point", 0.1)
    monkeypatch.setitem(ADAPTATION_CONFIG["hybrid_exposure"], "max_factor", 0.5)
    e = Enemy([(0, 0), (1, 0)], "Drone", 1)
    e.adapt_to_profile({"_hybrid_exposure": 4.0})
    assert e.resistances["hybrid"] == 0.6
    assert e.speed_mult > 1.0


def test_analyzer_snapshots_each_wave(monkeypatch):
    monkeypatch.setitem(ADAPTATION_CONFIG, "recompute_every_n_waves", 1)
    hybrid = Tower.merge_towers(
        Tower(0, 0, "Neural Processor"),
        Tower(0, 0, "Plasma Capacitor"),
    )
    game = type("G", (), {})()
    game.towers = []
    game.round_num = 1
    analyzer = StrategyAnalyzer()
    first = analyzer.analyze(game)
    assert first["_hybrid_exposure"] == 0.0
    game.towers = [hybrid]
    game.round_num = 2
    second = analyzer.analyze(game)
    assert second["_hybrid_exposure"] > 0


def test_milestone_hp_mult_on_mini_boss_wave(monkeypatch):
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_wave_interval", 5)
    monkeypatch.setitem(REWARD_CONFIG, "boss_wave_interval", 99)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_hp_mult", 2.0)
    g = Game(minimal_mode=True)
    g.round_num = 5
    g.wave_manager.start_next_wave(frame=0, forced=True)
    assert g.spawn_queue
    sample = g.spawn_queue[0]
    baseline = Enemy(g.path, sample.enemy_type, 5, web_mode=g.web_mode)
    assert sample.max_health == baseline.max_health * 2


def _scaled_hp(path, enemy_type, wave, web_mode, mult):
    base = Enemy(path, enemy_type, wave, web_mode=web_mode)
    return max(1, int(base.max_health * float(mult)))


def test_mini_boss_defaults_spike_hp_and_speed():
    assert REWARD_CONFIG["mini_boss_hp_mult"] > 1.0
    assert REWARD_CONFIG["mini_boss_speed_mult"] > 1.0
    g = Game(minimal_mode=True)
    g.round_num = 5
    g.wave_manager.start_next_wave(frame=0, forced=True)
    sample = g.spawn_queue[0]
    assert sample.max_health == _scaled_hp(
        g.path, sample.enemy_type, 5, g.web_mode, REWARD_CONFIG["mini_boss_hp_mult"]
    )
    assert sample.speed_mult == pytest.approx(float(REWARD_CONFIG["mini_boss_speed_mult"]))


def test_non_milestone_wave_is_unscaled():
    g = Game(minimal_mode=True)
    g.round_num = 4
    g.wave_manager.start_next_wave(frame=0, forced=True)
    sample = g.spawn_queue[0]
    baseline = Enemy(g.path, sample.enemy_type, 4, web_mode=g.web_mode)
    assert sample.max_health == baseline.max_health
    assert sample.speed_mult == pytest.approx(1.0)


def test_event_milestone_does_not_stack_yaml_hp():
    assert REWARD_CONFIG["boss_hp_mult"] > 1.0
    g = Game(minimal_mode=True)
    event = g.data_loader.get_event_wave(20)
    assert event is not None
    yaml_hp = float(event.get("hp_mult", 1.0))
    assert yaml_hp != float(REWARD_CONFIG["boss_hp_mult"])
    g.round_num = 20
    g.wave_manager.start_next_wave(frame=0, forced=True)
    sample = g.spawn_queue[0]
    expected = _scaled_hp(g.path, sample.enemy_type, 20, g.web_mode, REWARD_CONFIG["boss_hp_mult"])
    stacked = _scaled_hp(g.path, sample.enemy_type, 20, g.web_mode, yaml_hp * REWARD_CONFIG["boss_hp_mult"])
    assert sample.max_health == expected
    assert sample.max_health != stacked
    assert sample.speed_mult == pytest.approx(float(REWARD_CONFIG["boss_speed_mult"]))


def test_kill_gold_formula_keys_match_old_math():
    difficulty = 2
    base = int(ECONOMY_CONFIG["kill_gold_base"])
    per = int(ECONOMY_CONFIG["kill_gold_per_difficulty"])
    raw = max(1, (base + difficulty * per) // 2)
    assert raw == max(1, (3 + 2 * 3) // 2)


def test_catalog_exposes_pressure_tables():
    reset_catalog_for_tests()
    cat = catalog()
    cat.ensure()
    ids = [t.id for t in cat.tables]
    assert "adaptation" in ids
    assert "latch" in ids
    assert "enemies" in ids
    keys = {lf.path[-1] for lf in cat.leaves("adaptation")}
    assert "recompute_every_n_waves" in keys
    assert "factor_per_point" in keys
    latch_keys = {lf.path[-1] for lf in cat.leaves("latch")}
    assert "chance_base" in latch_keys
    assert "enabled" in latch_keys
    enemy_keys = {lf.path[-1] for lf in cat.leaves("enemies")}
    assert "first_wave" in enemy_keys
    cat.reset_all()
    reset_catalog_for_tests()


def test_latch_config_defaults_match_old_yaml():
    assert LATCH_CONFIG["chance_base"] == 0.4
    assert LATCH_CONFIG["enabled"] is True
