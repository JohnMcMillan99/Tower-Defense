"""Upgrades only apply to matching hardware; aura range stays an int."""
from models.tower import Tower
from core.economy import EconomyManager
from tests.test_rewards_economy import _make_game


def test_resist_upgrade_rejected_on_quantum():
    game = _make_game()
    eco = EconomyManager(game)
    qfg = Tower(0, 0, "Quantum Field Gen")
    assert eco.can_apply_upgrade(qfg, "resist_2") is False
    game.loot_bag[0] = "resist_2"
    assert eco.apply_upgrade_from_bench(qfg, "resist_2", 0) is False
    assert qfg.upgrades == []
    assert game.loot_bag[0] == "resist_2"


def test_resist_upgrade_allowed_on_thermal():
    game = _make_game()
    eco = EconomyManager(game)
    thermal = Tower(0, 0, "Thermal Regulator")
    assert eco.can_apply_upgrade(thermal, "resist_2") is True
    game.loot_bag[0] = "resist_2"
    assert eco.apply_upgrade_from_bench(thermal, "resist_2", 0) is True
    assert "resist_2" in thermal.upgrades


def test_wildcard_applies_to_any_tower():
    game = _make_game()
    eco = EconomyManager(game)
    neural = Tower(0, 0, "Neural Processor")
    assert eco.can_apply_upgrade(neural, "wild_1") is True


def test_range_stays_int_after_synergy_upgrade():
    game = _make_game()
    eco = EconomyManager(game)
    thermal = Tower(0, 0, "Thermal Regulator")
    game.loot_bag[0] = "resist_1"
    eco.apply_upgrade_from_bench(thermal, "resist_1", 0)
    assert isinstance(thermal.range, int)
    # Must be legal in range()
    list(range(-thermal.range, thermal.range + 1))


def test_aura_loop_does_not_crash_on_wide_range():
    """Even a 99-range tower with resist_2 (legacy/bad state) must not blow up."""
    from core.game import Game

    g = Game(minimal_mode=True)
    g.paused = False
    g.wave_active = True
    g.enemies = []
    g.spawn_queue = []
    t = Tower(3, 3, "Quantum Field Gen")
    t.upgrades.append("resist_2")
    t.range = 99.2
    g.towers = [t]
    g.wave_manager.update_wave(10)
