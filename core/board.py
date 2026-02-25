"""
Game Board Manager for Circuit Stronghold.

Handles wall placement, latch target scanning, and integrity calculations.
"""

from models.path_wall import PathWallManager

class BoardManager:
    """Manages the game board state including walls and latch mechanics."""

    def __init__(self, game):
        self.game = game
        self.wall_manager = PathWallManager(game)
        self.latch_scan_range = 5  # Max depth for latch target scanning

    def scan_latch_targets(self, assimilator_x, assimilator_y):
        """
        Scan for available latch targets around an assimilator position.

        Uses layered search algorithm to find first vulnerable wall/tower.

        Args:
            assimilator_x, assimilator_y: Position of the assimilator

        Returns:
            tuple: (target_x, target_y, target_type) or (None, None, None) if no target found
        """
        # First check direct adjacency (Layer 0)
        adjacent_positions = self._get_adjacent_positions(assimilator_x, assimilator_y)

        for x, y in adjacent_positions:
            # Check for walls
            wall = self.wall_manager.get_wall(x, y)
            if wall and wall.is_vulnerable():
                return (x, y, 'wall')

            # Check for towers
            tower = self._get_tower_at(x, y)
            if tower and tower.can_be_latched():
                return (x, y, 'tower')

        # If no direct adjacency, use layered search
        target_pos = self.wall_manager.find_first_vulnerable(
            assimilator_x, assimilator_y, self.latch_scan_range
        )

        if target_pos:
            x, y = target_pos
            # Determine if it's a wall or tower
            wall = self.wall_manager.get_wall(x, y)
            if wall and wall.is_vulnerable():
                return (x, y, 'wall')

            tower = self._get_tower_at(x, y)
            if tower and tower.can_be_latched():
                return (x, y, 'tower')

        return (None, None, None)

    def integrity_from_latches(self, wall_x, wall_y):
        """
        Calculate integrity drain from latches on a wall.

        Args:
            wall_x, wall_y: Position of the wall

        Returns:
            float: Integrity percentage (0.0-100.0), or None if no wall
        """
        wall = self.wall_manager.get_wall(wall_x, wall_y)
        if wall:
            return wall.get_integrity_percentage()
        return None

    def add_hybrid_wall(self, x, y, max_integrity=100.0):
        """
        Add a hybrid wall at the specified position.

        Args:
            x, y: Position to place wall
            max_integrity: Maximum integrity for the wall
        """
        self.wall_manager.add_wall(x, y, "hybrid", max_integrity)

    def add_pure_wall(self, x, y):
        """
        Add a pure wall at the specified position (immune to latching).

        Args:
            x, y: Position to place wall
        """
        self.wall_manager.add_wall(x, y, "pure", 100.0)

    def update_walls(self):
        """Update all walls (integrity, regeneration, etc.)."""
        self.wall_manager.update_all_walls()

    def get_destroyed_walls(self):
        """
        Get positions of walls that have been destroyed.

        Returns:
            list: List of (x, y) positions of destroyed walls
        """
        return self.wall_manager.get_destroyed_walls()

    def cleanup_destroyed_walls(self):
        """
        Remove destroyed walls from the board.

        Returns:
            list: List of (x, y) positions that were cleaned up
        """
        return self.wall_manager.cleanup_destroyed_walls()

    def get_wall_info(self, x, y):
        """
        Get information about a wall at the specified position.

        Args:
            x, y: Position to check

        Returns:
            dict: Wall information or None if no wall
        """
        wall = self.wall_manager.get_wall(x, y)
        if wall:
            return {
                'type': wall.wall_type,
                'integrity': wall.integrity,
                'max_integrity': wall.max_integrity,
                'integrity_percentage': wall.get_integrity_percentage(),
                'latch_count': wall.get_latch_count(),
                'is_destroyed': wall.is_destroyed(),
                'can_latch_more': wall.can_latch_more()
            }
        return None

    def get_all_walls(self):
        """
        Get information about all walls on the board.

        Returns:
            dict: {position: wall_info} for all walls
        """
        walls_info = {}
        for pos, wall in self.wall_manager.walls.items():
            walls_info[pos] = {
                'type': wall.wall_type,
                'integrity': wall.integrity,
                'max_integrity': wall.max_integrity,
                'integrity_percentage': wall.get_integrity_percentage(),
                'latch_count': wall.get_latch_count(),
                'is_destroyed': wall.is_destroyed(),
                'can_latch_more': wall.can_latch_more()
            }
        return walls_info

    def _get_adjacent_positions(self, x, y):
        """
        Get positions directly adjacent to (x, y).

        Returns:
            list: List of (x, y) tuples for adjacent positions
        """
        adjacent = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # N, S, W, E
            nx, ny = x + dx, y + dy
            if self._is_valid_position(nx, ny):
                adjacent.append((nx, ny))
        return adjacent

    def _is_valid_position(self, x, y):
        """Check if position is valid on the game grid."""
        return (0 <= x < self.game.width and 0 <= y < self.game.height)

    def _get_tower_at(self, x, y):
        """Get tower at the specified position."""
        for tower in self.game.towers:
            if tower.x == x and tower.y == y:
                return tower
        return None

    def initialize_from_map(self):
        """
        Initialize walls based on the current map layout.
        This would be called after map generation to place hybrid walls.
        """
        # This could scan the path graph for positions to place hybrid walls
        # For now, it's a placeholder for future implementation
        pass