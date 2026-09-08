"""
Assimilator enemy class - handles Swarm Latch mechanics.

Assimilators can latch onto hybrid walls and towers, stacking to corrupt them.
"""

from models.enemy import Enemy

class Assimilator(Enemy):
    """Assimilator enemy that can latch onto walls and towers."""

    def __init__(self, path, wave_num=1, is_egrem_spawned=False, web_mode=False):
        # Initialize as base Enemy with Assimilator type
        super().__init__(path, enemy_type="Assimilator", wave_num=wave_num,
                        is_egrem_spawned=is_egrem_spawned, web_mode=web_mode)

        # Swarm Latch state
        self.is_latched = False
        self.latch_target = None  # (x, y) position of latched wall/tower
        self.latch_target_type = None  # 'wall' or 'tower'
        self.stack_count = 1  # Number of assimilators latched to same target
        self.assimilate_progress = 0.0  # Progress toward corrupting target (0.0-1.0)

        # Movement state when latched
        self.was_moving = True  # Track if we were moving before latching

    def latch_to(self, target_x, target_y, target_type, wall_manager):
        """
        Attempt to latch to a wall or tower at the specified position.

        Args:
            target_x, target_y: Position to latch to
            target_type: 'wall' or 'tower'
            wall_manager: PathWallManager instance

        Returns:
            bool: True if latch successful, False otherwise
        """
        if self.is_latched:
            return False  # Already latched

        if target_type == 'wall':
            wall = wall_manager.get_wall(target_x, target_y)
            if wall and wall.add_latch(id(self)):
                self._perform_latch(target_x, target_y, target_type)
                # Update stack count from wall
                self.stack_count = wall.get_latch_count()
                return True

        elif target_type == 'tower':
            tower = self._get_tower_at(target_x, target_y)
            if tower and self._can_latch_tower(tower):
                self._perform_latch(target_x, target_y, target_type)
                self._sync_tower_stacks(self.latch_target)
                if self.stack_count < 1:
                    self.stack_count = 1
                return True

        return False

    def _perform_latch(self, target_x, target_y, target_type):
        """Internal method to set latch state."""
        self.is_latched = True
        self.latch_target = (target_x, target_y)
        self.latch_target_type = target_type
        self.was_moving = True  # Assume we were moving before latching
        # Stop moving when latched
        self.move_counter = float('inf')  # Prevent movement

    def unlatch(self, wall_manager=None):
        """Remove this assimilator from its latch target and resume walking."""
        if not self.is_latched:
            return

        pos = self.latch_target
        ttype = self.latch_target_type
        if ttype == 'wall' and wall_manager and pos:
            wall = wall_manager.get_wall(pos[0], pos[1])
            if wall:
                wall.remove_latch(id(self))

        self.is_latched = False
        self.latch_target = None
        self.latch_target_type = None
        self.stack_count = 1
        self.assimilate_progress = 0.0
        self.move_counter = 0.0
        if ttype == 'tower':
            self._sync_tower_stacks(pos)

    def update_latch(self, wall_manager, delta_time=1.0):
        """
        Update latch state and corruption progress.

        Args:
            wall_manager: PathWallManager instance
            delta_time: Time delta for frame-based updates
        """
        if not self.is_latched:
            return

        # Check if target still exists and is valid
        if not self._is_target_valid(wall_manager):
            self.unlatch(wall_manager)
            return

        # Update corruption progress based on stack scaling
        corruption_rate = self._calculate_corruption_rate()
        self.assimilate_progress = min(1.0, self.assimilate_progress + corruption_rate * delta_time)

        # If fully corrupted, trigger wall destruction or tower takeover
        if self.assimilate_progress >= 1.0:
            self._trigger_corruption(wall_manager)

    def _sync_tower_stacks(self, pos):
        """Count live assimilators stuck to the same tower tile."""
        game = getattr(self, "game", None)
        if not game or not pos:
            return
        latched = [
            e for e in getattr(game, "enemies", [])
            if isinstance(e, Assimilator) and e.is_latched and e.latch_target == pos
        ]
        if self.is_latched and self.latch_target == pos and self not in latched:
            latched.append(self)
        n = max(1, len(latched)) if latched else 1
        for e in latched:
            e.stack_count = n
        if self.is_latched and self.latch_target == pos:
            self.stack_count = n

    def _calculate_corruption_rate(self):
        """Fill rate per frame; stacks speed the soak."""
        from config import LATCH_CONFIG
        from core.sort_directives import combat_hooks_from_game
        base_rate = float(LATCH_CONFIG.get("fill_per_frame", 0.01))
        game = getattr(self, "game", None)
        if game is not None:
            base_rate *= float(combat_hooks_from_game(game).get("fill_per_frame_mult", 1.0))
        if self.stack_count <= 2:
            return base_rate * 2.0
        if self.stack_count <= 6:
            return base_rate * 5.0
        return base_rate * 10.0

    def _is_target_valid(self, wall_manager):
        """Check if current latch target is still valid."""
        if not self.latch_target:
            return False

        x, y = self.latch_target

        if self.latch_target_type == 'wall':
            wall = wall_manager.get_wall(x, y)
            return wall is not None and not wall.is_destroyed()

        elif self.latch_target_type == 'tower':
            tower = self._get_tower_at(x, y)
            return tower is not None and self._can_latch_tower(tower)

        return False

    def _trigger_corruption(self, wall_manager):
        """Trigger the final corruption effect."""
        if self.latch_target_type == 'wall':
            # Wall destruction - handled by wall manager
            wall = wall_manager.get_wall(self.latch_target[0], self.latch_target[1])
            if wall:
                wall.integrity = 0.0  # Force destruction
            self.unlatch(wall_manager)

        elif self.latch_target_type == 'tower':
            if self.latch_target:
                tower = self._get_tower_at(self.latch_target[0], self.latch_target[1])
                if tower and hasattr(tower, "apply_latch_payoff"):
                    tower.apply_latch_payoff()
            self.unlatch(wall_manager)

    def move(self):
        """Override move to handle latched state."""
        if self.is_latched:
            # Latched assimilators don't move along path
            return

        # Normal movement when not latched
        super().move()

    def take_damage(self, dmg, attacker_tags=None):
        killed = super().take_damage(dmg, attacker_tags)
        if killed and self.is_latched:
            wm = None
            game = getattr(self, "game", None)
            if game is not None and getattr(game, "board", None) is not None:
                wm = game.board.wall_manager
            self.unlatch(wm)
        return killed

    def get_display_info(self):
        """Get display information including latch state."""
        info = super().get_display_info()
        if self.is_latched:
            info['latched'] = True
            info['target'] = self.latch_target
            info['target_type'] = self.latch_target_type
            info['stack_count'] = self.stack_count
            info['corruption_progress'] = self.assimilate_progress
        else:
            info['latched'] = False
        return info

    def _get_tower_at(self, x, y):
        """Helper to get tower at position (needs game reference)."""
        # This should be passed in or accessed via game reference
        # For now, return None - will be implemented when integrated
        return None

    def _can_latch_tower(self, tower):
        """Helper to check if tower can be latched."""
        return hasattr(tower, 'can_be_latched') and tower.can_be_latched()

    def set_game_reference(self, game):
        """Set game reference for accessing towers."""
        self.game = game

    def _get_tower_at(self, x, y):
        """Get tower at position using game reference."""
        if not hasattr(self, 'game') or not self.game:
            return None

        for tower in self.game.towers:
            if tower.x == x and tower.y == y:
                return tower
        return None