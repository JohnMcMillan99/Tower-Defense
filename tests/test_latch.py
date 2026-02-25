import pytest
from models.assimilator import Assimilator
from models.path_wall import PathWallManager
from models.tower import Tower
from core.board import BoardManager
from core.game import Game


@pytest.fixture
def game():
    """Create a test game instance."""
    return Game(height=6, width=10, min_path_len=20, web_mode=False)


@pytest.fixture
def wall_manager(game):
    """Create a path wall manager."""
    return PathWallManager(game)


@pytest.fixture
def board_manager(game):
    """Create a board manager."""
    return BoardManager(game)


def test_latch_target(board_manager):
    """Test that assimilators can find and latch to valid targets."""
    # Create an assimilator
    assimilator = Assimilator([(5, 5), (6, 5)], wave_num=9)
    assimilator.set_game_reference(board_manager.game)

    # Add a hybrid wall near the assimilator
    board_manager.add_hybrid_wall(6, 5)

    # Scan for latch targets
    target_x, target_y, target_type = board_manager.scan_latch_targets(5, 5)

    # Should find the wall
    assert target_x == 6
    assert target_y == 5
    assert target_type == 'wall'

    # Test latching
    success = assimilator.latch_to(target_x, target_y, target_type, board_manager.wall_manager)
    assert success
    assert assimilator.is_latched
    assert assimilator.latch_target == (6, 5)


def test_pure_immune(board_manager):
    """Test that pure walls are immune to latching."""
    # Create an assimilator
    assimilator = Assimilator([(5, 5), (6, 5)], wave_num=9)
    assimilator.set_game_reference(board_manager.game)

    # Add a pure wall near the assimilator
    board_manager.add_pure_wall(6, 5)

    # Scan for latch targets - should not find the pure wall
    target_x, target_y, target_type = board_manager.scan_latch_targets(5, 5)

    # Should not find any target
    assert target_x is None
    assert target_y is None
    assert target_type is None


def test_layered_search(board_manager):
    """Test layered search finds walls through non-wall tiles."""
    # Create an assimilator
    assimilator = Assimilator([(5, 5)], wave_num=9)
    assimilator.set_game_reference(board_manager.game)

    # Add a hybrid wall two tiles away (not directly adjacent)
    board_manager.add_hybrid_wall(7, 5)

    # Scan for latch targets - should find wall through layered search
    target_x, target_y, target_type = board_manager.scan_latch_targets(5, 5)

    # Should find the wall through layered search
    assert target_x == 7
    assert target_y == 5
    assert target_type == 'wall'


def test_stack_scaling(board_manager):
    """Test that latch stacks scale corruption rate."""
    # Create multiple assimilators
    assimilators = []
    for i in range(3):
        assim = Assimilator([(6, 5)], wave_num=9)
        assim.set_game_reference(board_manager.game)
        assimilators.append(assim)

    # Add a hybrid wall
    board_manager.add_hybrid_wall(6, 5)

    # Latch all assimilators to the same wall
    for assim in assimilators:
        success = assim.latch_to(6, 5, 'wall', board_manager.wall_manager)
        assert success

    # Check that wall has correct latch count
    wall = board_manager.wall_manager.get_wall(6, 5)
    assert wall.get_latch_count() == 3

    # Check that assimilators have correct stack count
    for assim in assimilators:
        assert assim.stack_count == 3


def test_tower_latch_vulnerability(game):
    """Test that towers can be latched based on their type."""
    # Create a tower (default is latchable)
    tower = Tower(6, 5, "Oscillator")
    game.towers.append(tower)

    # Create assimilator
    assimilator = Assimilator([(5, 5), (6, 5)], wave_num=9)
    assimilator.set_game_reference(game)

    # Create board manager
    board_manager = BoardManager(game)

    # Scan for latch targets
    target_x, target_y, target_type = board_manager.scan_latch_targets(5, 5)

    # Should find the tower
    assert target_x == 6
    assert target_y == 5
    assert target_type == 'tower'

    # Test latching to tower
    success = assimilator.latch_to(target_x, target_y, target_type, board_manager.wall_manager)
    assert success
    assert assimilator.is_latched


def test_wall_integrity_drain(board_manager):
    """Test that walls lose integrity over time when latched."""
    # Add a hybrid wall
    board_manager.add_hybrid_wall(5, 5)

    # Create and latch an assimilator
    assimilator = Assimilator([(5, 5)], wave_num=9)
    assimilator.set_game_reference(board_manager.game)
    assimilator.latch_to(5, 5, 'wall', board_manager.wall_manager)

    # Get initial integrity
    initial_integrity = board_manager.integrity_from_latches(5, 5)
    assert initial_integrity == 100.0

    # Update wall (simulate time passing)
    board_manager.update_walls()

    # Integrity should have decreased
    new_integrity = board_manager.integrity_from_latches(5, 5)
    assert new_integrity < initial_integrity


def test_max_latch_depth(board_manager):
    """Test that layered search respects max depth limit."""
    # Create assimilator
    assimilator = Assimilator([(5, 5)], wave_num=9)
    assimilator.set_game_reference(board_manager.game)

    # Add wall at max depth + 1 (should not be found)
    board_manager.add_hybrid_wall(5, 5 + 6)  # 6 tiles away, beyond max depth of 5

    # Scan for targets
    target_x, target_y, target_type = board_manager.scan_latch_targets(5, 5)

    # Should not find the distant wall
    assert target_x is None
    assert target_y is None
    assert target_type is None