"""Tests for towers-only shop, egrem tile drops, and boss upgrade loot."""
import random
from unittest.mock import MagicMock

from config import REWARD_CONFIG
from core.economy import EconomyManager
from data.upgrades import UPGRADE_DEFS


def _make_game():
    game = MagicMock()
    game.shop = [None] * 5
    game.bench = [None] * 10
    game.map_tile_bench = [None] * 3
    game.upgrade_bench = [None] * 3
    game.gold = 100
    game.reroll_cost = 2
    game.minimal_mode = True
    game.current_frame = 0
    game.reward_toast_text = ""
    game.reward_toast_until = 0
    game.wave_bonus_text = ""
    game.wave_bonus_show_until = 0
    game.selected_tower = None
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
    # Force deterministic different offers on next generate
    random.seed(1)
    assert eco.reroll_shop() is True
    assert game.gold == 98
    assert all(slot is not None for slot in game.shop)
    # Reroll always rebuilds; types may coincide but slots must be filled
    assert len([s for s in game.shop if s is not None]) == 5
    _ = first  # keep for readability


def test_egrem_tile_drop_fills_map_bench(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "egrem_tile_drop_chance", 1.0)
    assert eco.try_grant_egrem_tile_drop() is True
    assert sum(1 for s in game.map_tile_bench if s is not None) == 1
    assert game.map_tile_bench[0]["name"]


def test_egrem_tile_drop_respects_chance(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "egrem_tile_drop_chance", 0.0)
    assert eco.try_grant_egrem_tile_drop() is False
    assert all(s is None for s in game.map_tile_bench)


def test_mini_boss_upgrade_loot(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_wave_interval", 5)
    monkeypatch.setitem(REWARD_CONFIG, "boss_wave_interval", 20)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_upgrade_count", 1)
    granted = eco.grant_wave_upgrade_rewards(5)
    assert granted == 1
    assert game.upgrade_bench[0] in UPGRADE_DEFS
    assert eco.grant_wave_upgrade_rewards(4) == 0


def test_boss_upgrade_loot_count(monkeypatch):
    game = _make_game()
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "boss_wave_interval", 20)
    monkeypatch.setitem(REWARD_CONFIG, "boss_upgrade_count", 2)
    granted = eco.grant_wave_upgrade_rewards(20)
    assert granted == 2
    assert sum(1 for s in game.upgrade_bench if s is not None) == 2


def test_egrem_gold_charged_on_confirm_only():
    from models.tower import Tower

    game = _make_game()
    game.gold = 50
    game.bench[0] = Tower(0, 0, "Neural Processor")
    game.bench[1] = Tower(0, 0, "Plasma Capacitor")
    # Force different tiers
    game.bench[1].merge_generation = 1
    game.bench[1]._calculate_stats()
    eco = EconomyManager(game)
    eco.select_for_merge(0, frame=1)
    eco.select_for_merge(1, frame=1)
    assert game.egrem_preview is True
    gold_after_preview = game.gold
    assert gold_after_preview == 50  # not charged yet
    assert eco._complete_egrem() is True
    assert game.gold < 50
