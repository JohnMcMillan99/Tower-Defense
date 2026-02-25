"""
Path Wall System for Swarm Latch mechanics.

Handles hybrid walls (vulnerable to assimilator latching) and pure path tiles (immune).
Implements layered search algorithm to find latch targets.
"""

class PathWall:
    """Represents a path-adjacent wall tile that can be latched by assimilators."""

    def __init__(self, x, y, wall_type="hybrid", integrity=100.0, max_integrity=100.0):
        self.x = x
        self.y = y
        self.wall_type = wall_type  # "hybrid" or "pure"
        self.integrity = integrity
        self.max_integrity = max_integrity
        self.latched_assimilators = []  # List of assimilator IDs currently latched
        self.integrity_regen_rate = 0.0  # Regen per frame for reinforced/fortified walls

    def is_vulnerable(self):
        """Check if this wall can be latched by assimilators."""
        return self.wall_type == "hybrid" and self.integrity > 0

    def can_latch_more(self, max_latches=10):
        """Check if this wall can accept more latches."""
        return self.is_vulnerable() and len(self.latched_assimilators) < max_latches

    def add_latch(self, assimilator_id):
        """Add an assimilator latch to this wall."""
        if self.can_latch_more() and assimilator_id not in self.latched_assimilators:
            self.latched_assimilators.append(assimilator_id)
            return True
        return False

    def remove_latch(self, assimilator_id):
        """Remove an assimilator latch from this wall."""
        if assimilator_id in self.latched_assimilators:
            self.latched_assimilators.remove(assimilator_id)
            return True
        return False

    def get_latch_count(self):
        """Get the number of latches on this wall."""
        return len(self.latched_assimilators)

    def update_integrity(self, drain_rate):
        """Update wall integrity based on latches."""
        if self.wall_type == "pure":
            return  # Pure walls don't lose integrity

        latch_count = self.get_latch_count()
        if latch_count > 0:
            # Drain 0.02 per stack per frame
            drain_per_frame = drain_rate * latch_count
            self.integrity = max(0.0, self.integrity - drain_per_frame)

        # Apply regeneration
        if self.integrity_regen_rate > 0 and self.integrity < self.max_integrity:
            self.integrity = min(self.max_integrity, self.integrity + self.integrity_regen_rate)

    def is_destroyed(self):
        """Check if wall is destroyed (integrity <= 0)."""
        return self.integrity <= 0

    def get_integrity_percentage(self):
        """Get integrity as a percentage (0-100)."""
        return (self.integrity / self.max_integrity) * 100.0 if self.max_integrity > 0 else 0.0


class PathWallManager:
    """Manages all path walls on the game board."""

    def __init__(self, game):
        self.game = game
        self.walls = {}  # (x, y) -> PathWall
        self.base_drain_rate = 0.02  # Base 2% per frame per latch

    def add_wall(self, x, y, wall_type="hybrid", max_integrity=100.0):
        """Add a wall at the specified position."""
        if (x, y) not in self.walls:
            self.walls[(x, y)] = PathWall(x, y, wall_type, max_integrity, max_integrity)
            # Set regen rates for different wall types
            if max_integrity > 100:
                self.walls[(x, y)].integrity_regen_rate = 0.005  # 0.5% regen for reinforced
            if max_integrity > 150:
                self.walls[(x, y)].integrity_regen_rate = 0.01   # 1% regen for fortified

    def get_wall(self, x, y):
        """Get wall at position, or None if no wall exists."""
        return self.walls.get((x, y))

    def remove_wall(self, x, y):
        """Remove wall at position."""
        if (x, y) in self.walls:
            del self.walls[(x, y)]

    def find_first_vulnerable(self, start_x, start_y, max_depth=5):
        """
        Find the first vulnerable hybrid wall using layered search algorithm.

        Args:
            start_x, start_y: Starting position (typically assimilator position)
            max_depth: Maximum layers to search (prevents infinite search)

        Returns:
            (x, y) of first vulnerable wall found, or None if none found
        """
        visited = set()
        layers = self._get_search_layers(start_x, start_y, max_depth)

        for layer in layers:
            for x, y in layer:
                if (x, y) in visited:
                    continue
                visited.add((x, y))

                wall = self.get_wall(x, y)
                if wall and wall.is_vulnerable():
                    return (x, y)

                # Also check for towers at this position
                tower = self._get_tower_at(x, y)
                if tower and self._can_latch_tower(tower):
                    return (x, y)

        return None

    def latch_spots(self, center_x, center_y, radius=3):
        """
        Find all available latch spots (walls/towers) within radius.

        Args:
            center_x, center_y: Center position to search around
            radius: Manhattan distance radius to search

        Returns:
            List of (x, y, type) tuples where type is 'wall' or 'tower'
        """
        spots = []

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if abs(dx) + abs(dy) > radius:
                    continue

                x, y = center_x + dx, center_y + dy

                # Check for walls
                wall = self.get_wall(x, y)
                if wall and wall.can_latch_more():
                    spots.append((x, y, 'wall'))

                # Check for towers
                tower = self._get_tower_at(x, y)
                if tower and self._can_latch_tower(tower):
                    spots.append((x, y, 'tower'))

        return spots

    def _get_search_layers(self, start_x, start_y, max_depth):
        """
        Generate search layers using BFS-style expansion from start position.

        Returns list of layers, where each layer is a list of (x, y) positions.
        """
        layers = []
        visited = set()
        current_layer = [(start_x, start_y)]
        visited.add((start_x, start_y))

        for depth in range(max_depth):
            next_layer = []

            for x, y in current_layer:
                # Check adjacent positions (Manhattan neighbors)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy

                    if (nx, ny) not in visited and self._is_valid_position(nx, ny):
                        visited.add((nx, ny))
                        next_layer.append((nx, ny))

            if not next_layer:
                break

            layers.append(next_layer)
            current_layer = next_layer

        return layers

    def _is_valid_position(self, x, y):
        """Check if position is valid on the game grid."""
        return (0 <= x < self.game.width and 0 <= y < self.game.height)

    def _get_tower_at(self, x, y):
        """Get tower at position from game state."""
        # This assumes towers are stored in self.game.towers as objects with x,y attributes
        for tower in self.game.towers:
            if tower.x == x and tower.y == y:
                return tower
        return None

    def _can_latch_tower(self, tower):
        """Check if a tower can be latched (hybrid wall behavior)."""
        # Towers can be latched if they're not "pure" type
        return hasattr(tower, 'can_be_latched') and tower.can_be_latched()

    def update_all_walls(self):
        """Update integrity for all walls."""
        for wall in self.walls.values():
            wall.update_integrity(self.base_drain_rate)

    def get_destroyed_walls(self):
        """Get list of positions of destroyed walls."""
        return [(x, y) for (x, y), wall in self.walls.items() if wall.is_destroyed()]

    def cleanup_destroyed_walls(self):
        """Remove destroyed walls and return their positions."""
        destroyed = self.get_destroyed_walls()
        for x, y in destroyed:
            self.remove_wall(x, y)
        return destroyed