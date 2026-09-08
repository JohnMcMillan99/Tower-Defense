"""Tests for towers-only shop, shared loot bag, and boss upgrade loot."""
import random
from unittest.mock import MagicMock

from config import REWARD_CONFIG, ECONOMY_CONFIG, LOOT_CONFIG, BENCH_CONFIG
from core.economy import EconomyManager
from data.upgrades import UPGRADE_DEFS


def _make_game():
    game = MagicMock()
    game.shop = [None] * 5
    game.bench = [None] * int(BENCH_CONFIG.get("tower_slots", 5))
    bag = [None] * int(LOOT_CONFIG.get("bag_slots", 4))
    game.loot_bag = bag
    game.loot_misses = 0
    game.last_loot_miss = None
    game.gold = 100
    game.reroll_cost = int(ECONOMY_CONFIG.get("reroll_cost", 3))
    game.minimal_mode = True
    game.current_frame = 0
    game.reward_toast_text = ""
    game.reward_toast_until = 0
    game.wave_bonus_text = ""
    game.wave_bonus_show_until = 0
    game.selected_tower = None
    game.selected_loot = None
    game.selected_tile_rotation = 0
    game.merge_tower_1 = None
    game.merge_tower_2 = None
    game.merge_preview = None
    game.egrem_preview = False
    game.incompatible_preview = False
    game.egrem_consecutive = 0
    return game


def test_generate_shop_towers_only():
    game = _make_game()
    eco = EconomyManager(game)
    eco.generate_shop()
    assert all(slot is not None for slot in game.shop)
    assert all("type" in slot and "cost" in slot for slot in game.shop)
    assert all("tile_data" not in slot and "name" not in slot for slot in game.shop)


def test_reroll_clears_all_slots():
    game = _make_game()
    eco = EconomyManager(game)
    eco.generate_shop()
    first = [s["type"] for s in game.shop]
    random.seed(1)
    assert eco.reroll_shop() is True
    assert game.gold == 100 - game.reroll_cost
    assert all(slot is not None for slot in game.shop)
    assert len([s for s in game.shop if s is not None]) == 5
    _ = first


def test_egrem_tile_drop_fills_loot_bag(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "egrem_tile_drop_chance", 1.0)
    assert eco.try_grant_egrem_tile_drop() is True
    assert sum(1 for s in game.loot_bag if s is not None) == 1
    assert isinstance(game.loot_bag[0], dict) and game.loot_bag[0]["name"]


def test_egrem_tile_drop_respects_chance(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "egrem_tile_drop_chance", 0.0)
    assert eco.try_grant_egrem_tile_drop() is False
    assert all(s is None for s in game.loot_bag)


def test_tile_and_upgrade_share_bag(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "egrem_tile_drop_chance", 1.0)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_tile_count", 0)
    assert eco.try_grant_egrem_tile_drop() is True
    granted = eco.grant_wave_upgrade_rewards(5)
    assert granted == 1
    kinds = [type(s).__name__ if not isinstance(s, dict) else "tile" for s in game.loot_bag if s]
    assert "tile" in kinds
    assert any(isinstance(s, str) for s in game.loot_bag if s)


def test_loot_bag_full_drops_lost(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "egrem_tile_drop_chance", 1.0)
    for _ in range(len(game.loot_bag)):
        assert eco.try_grant_egrem_tile_drop() is True
    assert eco.try_grant_egrem_tile_drop() is False
    assert all(s is not None for s in game.loot_bag)
    assert game.loot_misses == 1
    assert game.last_loot_miss["kind"] == "tile"
    assert game.last_loot_miss["source"] == "egrem"


def test_mini_boss_full_bag_records_run_miss(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_wave_interval", 5)
    monkeypatch.setitem(REWARD_CONFIG, "boss_wave_interval", 99)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_tile_count", 1)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_upgrade_count", 1)
    for i in range(len(game.loot_bag)):
        game.loot_bag[i] = {"name": "Straight", "width": 2}
    assert eco.grant_wave_upgrade_rewards(5) == 0
    assert game.loot_misses >= 2  # tile + upgrade refused
    assert game.last_loot_miss["source"] == "mini_boss"
    assert game.last_loot_miss["wave"] == 5
    assert all(isinstance(s, dict) for s in game.loot_bag)


def test_preview_bag_pressure_when_full_near_loot():
    from core.game import Game
    g = Game(minimal_mode=True)
    for i in range(len(g.loot_bag)):
        if g.loot_bag[i] is None:
            g.loot_bag[i] = {"name": "Straight", "width": 2}
    g.round_num = 5  # mini-boss now
    preview = g.wave_manager.preview_upcoming()
    assert preview["bag_full"] is True
    assert preview["bag_pressure"] is True
    assert preview["loot"]["waves"] == 0


def test_mini_boss_upgrade_loot(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_wave_interval", 5)
    monkeypatch.setitem(REWARD_CONFIG, "boss_wave_interval", 20)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_upgrade_count", 1)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_tile_count", 0)
    granted = eco.grant_wave_upgrade_rewards(5)
    assert granted == 1
    assert any(isinstance(s, str) and s in UPGRADE_DEFS for s in game.loot_bag)
    assert eco.grant_wave_upgrade_rewards(4) == 0


def test_boss_upgrade_loot_count(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "boss_wave_interval", 20)
    monkeypatch.setitem(REWARD_CONFIG, "boss_upgrade_count", 1)
    monkeypatch.setitem(REWARD_CONFIG, "boss_tile_count", 0)
    granted = eco.grant_wave_upgrade_rewards(20)
    assert granted == 1
    assert sum(1 for s in game.loot_bag if isinstance(s, str)) == 1


def test_tower_bench_is_five_slots():
    from core.game import Game
    g = Game(minimal_mode=True)
    assert len(g.bench) == 5
    assert len(g.loot_bag) == int(LOOT_CONFIG.get("bag_slots", 4))
    assert any(isinstance(s, dict) and s.get("name") == "Straight" for s in g.loot_bag)
    assert g.selected_map_tile is None
    assert g.selected_upgrade is None
    assert g.gold == int(ECONOMY_CONFIG.get("starting_gold", 25))


def test_egrem_gold_charged_on_confirm_only():
    from models.tower import Tower

    game = _make_game()
    game.gold = 50
    game.bench[0] = Tower(0, 0, "Neural Processor")
    game.bench[1] = Tower(0, 0, "Plasma Capacitor")
    game.bench[1].merge_generation = 1
    game.bench[1]._calculate_stats()
    eco = EconomyManager(game)
    eco.select_for_merge(0, frame=1)
    eco.select_for_merge(1, frame=1)
    assert game.egrem_preview is True
    gold_after_preview = game.gold
    assert gold_after_preview == 50
    assert eco._complete_egrem() is True
    assert game.gold < 50
