import random


class AugmentManager:
    """Manages map corruption and cell augments driven by YAML augment_rules."""

    def __init__(self, data_loader=None):
        self.tiles_placed_count = 0
        self.cell_augments = {}  # (x, y) -> list[str] of augment tags
        self.corruption_active = False
        self._data_loader = data_loader

    def _get_rules(self):
        if self._data_loader:
            return self._data_loader.get_augment_rules()
        return {}

    def on_tile_placed(self):
        """Called after a tile is successfully placed."""
        self.tiles_placed_count += 1

    def should_corrupt(self):
        """Return True when corruption should trigger."""
        rules = self._get_rules()
        corruption = rules.get("corruption", {})
        threshold = corruption.get("tiles_threshold", 5)
        return self.tiles_placed_count >= threshold

    def try_add_corruption(self, game):
        """Roll for corruption and place obstacles if triggered.

        Returns list of (x, y, obstacle_type) placed, or empty list.
        """
        if not self.should_corrupt():
            return []
        rules = self._get_rules()
        corruption = rules.get("corruption", {})
        prob = corruption.get("probability", 0.3)
        obstacle_types = corruption.get("obstacle_types", ["blocked"])

        if random.random() > prob:
            return []

        placed = []
        candidates = []
        for y in range(game.height):
            for x in range(game.width):
                if game.grid[y][x] == '.' and (x, y) not in self.cell_augments:
                    candidates.append((x, y))
        if candidates:
            pos = random.choice(candidates)
            obs_type = random.choice(obstacle_types)
            self.apply_augment(pos, obs_type)
            placed.append((pos[0], pos[1], obs_type))
        return placed

    def apply_augment(self, pos, tag):
        """Add an augment tag to a cell position."""
        if pos not in self.cell_augments:
            self.cell_augments[pos] = []
        if tag not in self.cell_augments[pos]:
            self.cell_augments[pos].append(tag)

    def remove_augment(self, pos, tag):
        """Remove an augment tag from a cell position."""
        if pos in self.cell_augments and tag in self.cell_augments[pos]:
            self.cell_augments[pos].remove(tag)
            if not self.cell_augments[pos]:
                del self.cell_augments[pos]

    def get_cell_augments(self, pos):
        """Return list of augment tags on a cell."""
        return list(self.cell_augments.get(pos, []))

    def get_augment_effects(self, pos):
        """Return combined stat modifiers for a cell from augment_rules YAML.

        Returns dict with keys like 'range_bonus', 'dmg_mult', 'enemy_speed_mult'.
        """
        tags = self.get_cell_augments(pos)
        if not tags:
            return {}
        rules = self._get_rules()
        augments_def = rules.get("augments", {})
        combined = {}
        for tag in tags:
            effects = augments_def.get(tag, {})
            for k, v in effects.items():
                if k in combined:
                    if "mult" in k:
                        combined[k] *= v
                    else:
                        combined[k] += v
                else:
                    combined[k] = v
        return combined

    def apply_cell_effects_to_tower(self, tower):
        """Modify tower stats in-place based on the cell it occupies."""
        effects = self.get_augment_effects((tower.x, tower.y))
        if not effects:
            return
        tower.dmg = max(1, int(tower.dmg * effects.get("dmg_mult", 1.0)))
        tower.range += effects.get("range_bonus", 0)
        fr_mult = effects.get("fire_rate_mult", 1.0)
        if fr_mult != 1.0:
            tower.fire_rate = max(1, int(tower.fire_rate / fr_mult))
