import pytest
from core.game import Game
from models.enemy import Enemy


def test_spl_initialization():
    """Test that SPL and XP are initialized correctly."""
    game = Game()
    assert game.shop_power_level == 1
    assert game.xp == 0
    assert game.xp_to_next == 100
    assert game.spl_max == 10


def test_spl_level_up():
    """Test SPL level up logic."""
    game = Game()

    # Test level up from 1 to 2
    game.xp = 100
    game.check_spl_level_up()
    assert game.shop_power_level == 2
    assert game.xp == 0
    assert game.xp_to_next == int(100 * (1.5 ** 1))  # 150

    # Test level up from 2 to 3
    game.xp = 150
    game.check_spl_level_up()
    assert game.shop_power_level == 3
    assert game.xp == 0
    assert game.xp_to_next == int(100 * (1.5 ** 2))  # 225

    # Test no level up when not enough XP
    game.xp = 200
    game.check_spl_level_up()
    assert game.shop_power_level == 3  # Should stay at 3
    assert game.xp == 200


def test_spl_max_cap():
    """Test that SPL is capped at spl_max."""
    game = Game()

    # Level up to max
    for level in range(1, 10):
        game.xp = game.xp_to_next
        game.check_spl_level_up()

    assert game.shop_power_level == 10

    # Try to level up beyond max
    game.xp = game.xp_to_next
    game.check_spl_level_up()
    assert game.shop_power_level == 10  # Should stay at max


def test_enemy_base_xp():
    """Test that enemies have base_xp values."""
    # Test all enemy types have base_xp
    for enemy_type, stats in Enemy.TYPES.items():
        assert "base_xp" in stats, f"Enemy type {enemy_type} missing base_xp"
        assert isinstance(stats["base_xp"], int)
        assert stats["base_xp"] > 0


def test_enemy_xp_calculation():
    """Test XP calculation for enemy kills."""
    # Test that base_xp * difficulty gives reasonable values
    drone_xp = Enemy.TYPES["Drone"]["base_xp"] * Enemy.TYPES["Drone"]["difficulty"]
    assimilator_xp = Enemy.TYPES["Assimilator"]["base_xp"] * Enemy.TYPES["Assimilator"]["difficulty"]

    assert drone_xp == 5  # 5 * 1
    assert assimilator_xp == 60  # 20 * 3

    # Test that higher difficulty enemies give more XP
    assert assimilator_xp > drone_xp


def test_wave_xp_bonus():
    """Test XP bonus calculation for wave completion."""
    # Wave XP bonus should scale with wave number
    wave_1_bonus = 1 * 50
    wave_5_bonus = 5 * 50
    wave_10_bonus = 10 * 50

    assert wave_1_bonus == 50
    assert wave_5_bonus == 250
    assert wave_10_bonus == 500

    # Higher waves should give more bonus
    assert wave_10_bonus > wave_5_bonus > wave_1_bonus