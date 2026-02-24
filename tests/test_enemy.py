import pytest
from models.enemy import Enemy


def test_move():
    """Test enemy movement along path."""
    path = [(0, 0), (1, 0), (2, 0), (3, 0)]
    enemy = Enemy(path, "Drone", 1)

    # Initially at position 0
    assert enemy.get_position() == (0, 0)
    assert enemy.position_index == 0

    # Move once (speed is 10, so move_counter needs to reach 10)
    enemy.move_counter = 10
    enemy.move()
    assert enemy.position_index == 1
    assert enemy.get_position() == (1, 0)

    # Move to end of path
    enemy.position_index = len(path) - 1
    enemy.move_counter = enemy.move_speed
    enemy.move()
    assert enemy.leaked == True
    assert enemy.alive == False


def test_take_damage():
    """Test enemy taking damage."""
    path = [(0, 0), (1, 0)]
    enemy = Enemy(path, "Drone", 1)

    initial_health = enemy.health

    # Take some damage
    killed = enemy.take_damage(5)
    assert enemy.health == initial_health - 5
    assert killed == False
    assert enemy.alive == True

    # Take lethal damage
    remaining_health = enemy.health
    killed = enemy.take_damage(remaining_health)
    assert enemy.health <= 0
    assert killed == True
    assert enemy.alive == False


def test_apply_debuff():
    """Test applying debuffs to enemies."""
    path = [(0, 0), (1, 0)]
    enemy = Enemy(path, "Drone", 1)

    # Apply slow debuff
    enemy.apply_debuff('slow', 50, 10)  # 50% slow for 10 frames

    assert 'slow' in enemy.debuffs
    assert enemy.debuffs['slow']['amount'] == 50
    assert enemy.debuffs['slow']['frames_left'] == 10

    # Apply same debuff with higher duration
    enemy.apply_debuff('slow', 30, 20)  # Lower amount but higher duration
    assert enemy.debuffs['slow']['amount'] == 50  # Should keep higher amount
    assert enemy.debuffs['slow']['frames_left'] == 20  # Should update to higher duration

    # Simulate frames passing
    for _ in range(10):
        enemy.move()  # This decrements debuff frames

    assert enemy.debuffs['slow']['frames_left'] == 10

    # Debuff should expire
    for _ in range(11):
        enemy.move()

    assert 'slow' not in enemy.debuffs


def test_enemy_stats_scaling():
    """Test that enemy stats scale with wave number."""
    path = [(0, 0), (1, 0)]

    # Wave 1 enemy
    enemy1 = Enemy(path, "Drone", 1)
    health1 = enemy1.max_health

    # Wave 5 enemy
    enemy5 = Enemy(path, "Drone", 5)
    health5 = enemy5.max_health

    # Higher wave should have more health
    assert health5 > health1

    # Test different enemy types have different stats
    drone = Enemy(path, "Drone", 1)
    scout = Enemy(path, "Scout", 1)

    assert drone.max_health != scout.max_health
    assert drone.move_speed != scout.move_speed


def test_enemy_position_bounds():
    """Test enemy position handling at path boundaries."""
    path = [(0, 0), (1, 0)]
    enemy = Enemy(path, "Drone", 1)

    # Valid position
    assert enemy.get_position() == (0, 0)

    # Move past end
    enemy.position_index = len(path)  # Past end
    assert enemy.get_position() is None

    # Negative index
    enemy.position_index = -1
    assert enemy.get_position() is None