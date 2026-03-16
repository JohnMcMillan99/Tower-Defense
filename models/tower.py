# ==============================
# TOWER (Hardware + Software Upgrades)
# ==============================
import random
from data.upgrades import UPGRADE_DEFS, EGREM_SPAWN_CONFIG
from data.units import TOWER_TRAITS

def _type_to_slug(name):
    """Convert 'Neural Processor' -> 'neural_processor'."""
    return name.lower().replace(" ", "_")

class Tower:
    UPGRADE_CAPACITY = 3
    _data_loader = None  # set once by Game.__init__

    BASE_TYPES = {
        "Neural Processor": {"dmg": 6,  "range": 2, "fire_rate": 1, "display": "Neural Processor", "fire_type": "TargetBeam"},
        "Plasma Capacitor":  {"dmg": 10, "range": 2, "fire_rate": 4, "display": "Plasma Capacitor", "fire_type": "Ball"},
        "Thermal Regulator":   {"dmg": 4,  "range": 3, "fire_rate": 2, "display": "Thermal Regulator", "fire_type": "DirectionalBeam"},
        "Signal Router":      {"dmg": 7,  "range": 4, "fire_rate": 2, "display": "Signal Router", "fire_type": "Track"},
        "Quantum Field Gen":   {"dmg": 2,  "range": 99, "fire_rate": 10, "display": "Quantum Field Gen", "fire_type": "Overwatch"},
        "Nanite Swarm":      {"dmg": 0,  "range": 0, "fire_rate": 0, "display": "Nanite Swarm", "fire_type": "Spawner"},
    }

    @classmethod
    def set_data_loader(cls, loader):
        """Register the DataLoader so all Tower instances can access YAML data."""
        cls._data_loader = loader
        for ht in loader.get_hybrid_trees():
            result_name = ht["result"]
            if result_name not in cls.BASE_TYPES:
                cls.BASE_TYPES[result_name] = {
                    "dmg": ht.get("dmg", 6),
                    "range": ht.get("range", 2),
                    "fire_rate": ht.get("fire_rate", 2),
                    "fire_type": ht.get("fire_type", "TargetBeam"),
                    "display": result_name,
                }

    def __init__(self, x, y, tower_type="Neural Processor", parents=None):
        self.x = x
        self.y = y
        self.base_type = tower_type if tower_type in self.BASE_TYPES else "Neural Processor"
        base = self.BASE_TYPES.get(self.base_type, self.BASE_TYPES["Neural Processor"])
        self.fire_type = base.get("fire_type", "Ball")
        self.parents = parents or []
        self.merge_generation = 0  # Track tier: 0=T0, 1=T1, 2=T2, etc.
        self.cooldown = 0
        self.last_shot_target = None
        self.last_shot_frame = 0
        self.gold_invested = 0
        self.upgrades = []          # list of upgrade ids
        self.heat = 0.0             # NEW: heat buildup mechanic
        self.max_heat = 10.0
        self.status_effects = {}    # e.g. {'stun': 120 frames}
        self.buffs = {}             # buff_type: {'amount': val, 'frames_left': int}

        # Fire type specific attributes
        self.beam_targets = {}      # For Beam: enemy_id: (damage_per_frame, frames_applied)
        self.track_direction = 0    # For Track: 0=N, 1=E, 2=S, 3=W

        # Egrem spawning state (only set for Egrem towers)
        self.egrem_source_types = []  # List of base_type strings that created this egrem
        self.egrem_spawn_timer = 0    # Frames until next spawn
        self.egrem_spawn_interval = 0 # Interval between spawns

        self._calculate_stats()

    def get_traits(self):
        """Return base traits + auto-generated purity/hybrid tags."""
        base_traits = list(TOWER_TRAITS.get(self.base_type, []))
        if self._data_loader:
            slug = _type_to_slug(self.base_type)
            loader_traits = self._data_loader.traits.get(slug, [])
            for t in loader_traits:
                if t not in base_traits:
                    base_traits.append(t)

        if self.merge_generation >= 1 and self.parents:
            purity = self.calculate_purity()
            slug = _type_to_slug(self.base_type)
            gen = min(self.merge_generation, 3)
            if purity == 100:
                base_traits.append(f"pure_{slug}_gen{gen}")
                base_traits.append("pure_lineage")
                if gen >= 2:
                    base_traits.append("mastery")
                if gen >= 3:
                    base_traits.append("apex")
            elif purity < 100:
                base_traits.append("hybrid")
                combo = self._get_hybrid_combo_tag()
                if combo:
                    base_traits.append(combo)
        return base_traits

    def _get_hybrid_combo_tag(self):
        """Derive hybrid combo tag from parent types (e.g. 'neural_plasma')."""
        if not self.parents:
            return None
        unique_types = sorted(set(self.parents))
        if len(unique_types) >= 2:
            slugs = sorted([_type_to_slug(t) for t in unique_types[:2]])
            short = [s.split("_")[0] for s in slugs]
            return "_".join(short)
        return None

    def get_effective_traits(self):
        traits = set(self.get_traits())
        for uid in self.upgrades:
            for t in UPGRADE_DEFS.get(uid, {}).get("traits", []):
                if t != "wildcard":
                    traits.add(t)
        return traits

    def calculate_purity(self):
        """Return purity score 0-100. 100 = all parents match self.base_type."""
        if not self.parents:
            return 100
        matching = sum(1 for p in self.parents if p == self.base_type)
        return int(matching / len(self.parents) * 100)

    def _apply_lineage_bonuses(self):
        """Apply purity / hybrid bonuses from trait_bonuses YAML data."""
        if self.merge_generation < 1:
            return
        loader = self._data_loader
        if not loader:
            return
        bonuses = loader.get_trait_bonuses()
        if not bonuses:
            return

        purity = self.calculate_purity()
        gen = self.merge_generation

        if purity == 100:
            pure_b = bonuses.get("pure_lineage", {})
            req = pure_b.get("purity_requirement", 100)
            if purity >= req:
                self.dmg = int(self.dmg * pure_b.get("dmg_mult", 1.0))
                self.range += pure_b.get("range_bonus", 0)
                self.fire_rate = max(1, int(self.fire_rate / pure_b.get("fire_rate_mult", 1.0)))
            exp_b = bonuses.get("exponential_bonus", {})
            stack = exp_b.get("stack_mult", 1.25)
            self.dmg = int(self.dmg * (stack ** gen))
            if gen >= 2:
                mastery_b = bonuses.get("mastery", {})
                self.dmg = int(self.dmg * mastery_b.get("dmg_mult", 1.0))
            if gen >= 3:
                apex_b = bonuses.get("apex", {})
                self.dmg = int(self.dmg * apex_b.get("dmg_mult", 1.0))
        else:
            hybrid_b = bonuses.get("hybrid", {})
            self.dmg = int(self.dmg * hybrid_b.get("dmg_mult", 1.0))
            combo_tag = self._get_hybrid_combo_tag()
            if combo_tag:
                combo_b = bonuses.get(combo_tag, {})
                self.dmg = int(self.dmg * combo_b.get("dmg_mult", 1.0))
                self.range += combo_b.get("range_bonus", 0)
                fr = combo_b.get("fire_rate_mult", 1.0)
                if fr != 1.0:
                    self.fire_rate = max(1, int(self.fire_rate / fr))

    def get_display_name(self):
        """Return the display name based on purity and merge generation."""
        if self.merge_generation < 1:
            return self.base_type

        loader = self._data_loader
        purity = self.calculate_purity()

        if purity == 100:
            rules = {}
            if loader:
                rules = loader.get_pure_naming_rules()
            if not rules:
                rules = loader.get_trait_rules().get("naming_conventions", {}).get("pure", {}) if loader else {}
            gen_key = f"gen{min(self.merge_generation, 3)}"
            template = rules.get(gen_key, self.base_type)
            return template.replace("{base_type}", self.base_type)
        else:
            if loader:
                for ht in loader.get_hybrid_trees():
                    if self.base_type == ht.get("result"):
                        return self.base_type
            return self.base_type

    def _calculate_stats(self):
        base = self.BASE_TYPES.get(self.base_type, self.BASE_TYPES["Neural Processor"])
        merge_level = self.merge_generation
        boost = 1.0 + merge_level * 0.3

        self.dmg = int(base["dmg"] * boost)
        self.range = base["range"] + merge_level
        self.fire_rate = max(1, int(base["fire_rate"] / boost) or 1)

        self._apply_lineage_bonuses()

        for uid in self.upgrades:
            u = UPGRADE_DEFS.get(uid, {})
            self.dmg = max(1, int(self.dmg * (1 + u.get("dmg_mult", 0))))
            self.range = max(1, self.range + u.get("range_bonus", 0))
            self.fire_rate = max(1, int(self.fire_rate * (1 + u.get("fire_rate_mult", 0))))

        for uid in self.upgrades:
            u = UPGRADE_DEFS.get(uid, {})
            if any(s in TOWER_TRAITS.get(self.base_type, []) for s in u.get("synergizes_with", [])):
                self.dmg = int(self.dmg * 1.10)
                self.range += 0.2

    def get_merge_tier(self):
        return self.merge_generation

    def get_merge_type(self):
        """Returns 'egrem' | 'pure' | 'hybrid' | 'base' for visual styling."""
        if self.base_type == "Nanite Swarm":
            return "egrem"
        if self.merge_generation < 1:
            return "base"
        return "pure" if self.calculate_purity() == 100 else "hybrid"

    @staticmethod
    def merge_towers(tower1, tower2):
        result_type = tower1.base_type

        loader = Tower._data_loader
        if loader and tower1.base_type != tower2.base_type:
            pair = tuple(sorted([tower1.base_type, tower2.base_type]))
            for ht in loader.get_hybrid_trees():
                ht_pair = tuple(sorted(ht["parents"]))
                if pair == ht_pair:
                    result_type = ht["result"]
                    break

        new_tower = Tower(0, 0, tower_type=result_type)
        new_tower.merge_generation = tower1.merge_generation + 1
        new_tower.parents = tower1.parents + tower2.parents + [tower1.base_type, tower2.base_type]
        new_tower.gold_invested = tower1.gold_invested + tower2.gold_invested
        new_tower.upgrades = list(set(tower1.upgrades + tower2.upgrades))
        new_tower._calculate_stats()
        return new_tower

    @staticmethod
    def can_merge(tower1, tower2):
        """Check if two towers can merge (same tier + same type or hybrid tree match)."""
        if tower1.get_merge_tier() != tower2.get_merge_tier():
            return False
        if tower1.base_type == tower2.base_type:
            return True
        loader = Tower._data_loader
        if loader:
            pair = tuple(sorted([tower1.base_type, tower2.base_type]))
            for ht in loader.get_hybrid_trees():
                ht_pair = tuple(sorted(ht["parents"]))
                if pair == ht_pair:
                    return True
        return False

    def _configure_egrem_spawning(self):
        """Configure egrem spawning based on source tower types."""
        if not self.egrem_source_types or len(self.egrem_source_types) < 2:
            return

        # Average spawn parameters from both source towers
        total_spawn_count = 0
        total_spawn_interval = 0
        enemy_types = []

        for tower_type in self.egrem_source_types:
            config = EGREM_SPAWN_CONFIG.get(tower_type, {})
            total_spawn_count += config.get("base_spawn", 1)
            total_spawn_interval += config.get("spawn_interval", 90)
            enemy_types.append(config.get("enemy_type", "Drone"))

        # Average the values
        self.egrem_spawn_count = max(1, total_spawn_count // 2)
        self.egrem_spawn_interval = max(30, total_spawn_interval // 2)
        self.egrem_enemy_types = enemy_types  # Can spawn mixed types
        self.egrem_spawn_timer = 0  # Spawn immediately on first frame of wave

    def update(self, enemies, current_frame, game):
        if 'stun' in self.status_effects and self.status_effects['stun'] > 0:
            self.status_effects['stun'] -= 1
            return None

        if self.cooldown > 0:
            self.cooldown -= 1
            return None

        # Heat buildup (from shooting)
        self.heat += 0.8  # base per shot; tune later
        if self.heat >= self.max_heat:
            self.cooldown += 12  # overheat penalty
            self.heat = self.max_heat
            # could add visual red glow here

        if self.fire_type == "Spawner":
            # Egrem towers spawn enemies on timer
            if hasattr(self, 'egrem_spawn_interval') and self.egrem_spawn_interval > 0:
                self.egrem_spawn_timer -= 1
                if self.egrem_spawn_timer <= 0:
                    self.egrem_spawn_timer = self.egrem_spawn_interval
                    for _ in range(self.egrem_spawn_count):
                        enemy_type = random.choice(self.egrem_enemy_types)
                        game.spawn_enemy_at_position(enemy_type, self.x, self.y, game.round_num)
            return None  # Spawner towers don't attack

        elif self.fire_type == "Radius":
            # Damage all enemies in range each frame
            killed_any = False
            for dy in range(-int(self.range), int(self.range) + 1):
                for dx in range(-int(self.range), int(self.range) + 1):
                    if abs(dx) + abs(dy) > self.range:
                        continue
                    nx, ny = self.x + dx, self.y + dy
                    if 0 <= nx < len(game.enemy_grid[0]) and 0 <= ny < len(game.enemy_grid):
                        for e in game.enemy_grid[ny][nx][:]:  # copy to avoid modification issues
                            if e.alive and not e.leaked:
                                killed = e.take_damage(self.dmg)
                                if killed:
                                    killed_any = True
            return (None, killed_any) if killed_any else None

        elif self.fire_type == "Track":
            # Damage enemies on path segments in the selected direction
            killed_any = False
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # N, S, W, E
            dx, dy = directions[self.track_direction]
            # Find path segments adjacent to tower in that direction
            adjacent_x = self.x + dx
            adjacent_y = self.y + dy
            if 0 <= adjacent_x < len(game.enemy_grid[0]) and 0 <= adjacent_y < len(game.enemy_grid):
                for e in game.enemy_grid[adjacent_y][adjacent_x][:]:
                    if e.alive and not e.leaked:
                        killed = e.take_damage(self.dmg)
                        if killed:
                            killed_any = True
            self.cooldown = self.fire_rate
            return (None, killed_any) if killed_any else None

        elif self.fire_type == "DirectionalBeam":
            # Shoot a beam in one direction, hitting all tiles in that line
            killed_any = False
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # N, S, W, E
            dx, dy = directions[self.track_direction]
            for dist in range(1, self.range + 1):
                nx = self.x + dx * dist
                ny = self.y + dy * dist
                if 0 <= nx < len(game.enemy_grid[0]) and 0 <= ny < len(game.enemy_grid):
                    for e in game.enemy_grid[ny][nx][:]:  # copy to avoid modification issues
                        if e.alive and not e.leaked:
                            killed = e.take_damage(self.dmg)
                            if killed:
                                killed_any = True
            self.cooldown = self.fire_rate
            return (None, killed_any) if killed_any else None

        elif self.fire_type == "Beam":
            # Find target, damage increases over time on same target
            target = None
            best_dist = float('inf')
            enemy_count = 0
            max_enemies = 10
            for dy in range(-int(self.range), int(self.range) + 1):
                for dx in range(-int(self.range), int(self.range) + 1):
                    if abs(dx) + abs(dy) > self.range:
                        continue
                    nx, ny = self.x + dx, self.y + dy
                    if 0 <= nx < len(game.enemy_grid[0]) and 0 <= ny < len(game.enemy_grid):
                        for e in game.enemy_grid[ny][nx]:
                            if enemy_count >= max_enemies:
                                break
                            if e.alive and not e.leaked:
                                enemy_count += 1
                                dist = abs(dx) + abs(dy)
                                if dist < best_dist:
                                    best_dist = dist
                                    target = e
                    if enemy_count >= max_enemies:
                        break

            if target:
                enemy_id = id(target)
                if enemy_id in self.beam_targets:
                    dmg_mult, frames = self.beam_targets[enemy_id]
                    dmg_mult += 0.5  # increase damage over time
                    frames += 1
                else:
                    dmg_mult = 1.0
                    frames = 1
                actual_dmg = int(self.dmg * dmg_mult)
                killed = target.take_damage(actual_dmg)
                self.beam_targets[enemy_id] = (dmg_mult, frames)
                self.cooldown = self.fire_rate
                self.last_shot_target = target.get_position()
                self.last_shot_frame = current_frame
                return (target, killed)
            else:
                # Clear beam targets if no target
                self.beam_targets.clear()
            return None

        else:  # Ball or Overwatch (default)
            # Standard projectile targeting - optimized using enemy grid
            target = None
            best_dist = float('inf')
            enemy_count = 0
            max_enemies = 10
            effective_range = 99 if self.fire_type == "Overwatch" else self.range

            # Iterate over diamond-shaped area within range using grid
            for dy in range(-int(effective_range), int(effective_range) + 1):
                for dx in range(-int(effective_range), int(effective_range) + 1):
                    if abs(dx) + abs(dy) > effective_range:
                        continue
                    nx, ny = self.x + dx, self.y + dy
                    if 0 <= nx < len(game.enemy_grid[0]) and 0 <= ny < len(game.enemy_grid):
                        for e in game.enemy_grid[ny][nx]:
                            if enemy_count >= max_enemies:
                                break
                            if e.alive and not e.leaked:
                                enemy_count += 1
                                dist = abs(dx) + abs(dy)
                                if dist < best_dist:
                                    best_dist = dist
                                    target = e
                    if enemy_count >= max_enemies:
                        break

            if target:
                killed = target.take_damage(self.dmg)
                self.cooldown = self.fire_rate
                self.last_shot_target = target.get_position()
                self.last_shot_frame = current_frame
                return (target, killed)
            return None

    def can_be_latched(self):
        """
        Check if this tower can be latched by assimilators.

        Returns:
            bool: True if tower is vulnerable to latching (hybrid), False if immune (pure)
        """
        # Check tier_traits.immune from merges.yaml data
        if hasattr(self, 'game') and self.game and hasattr(self.game, 'data_loader'):
            tower_data = self.game.data_loader.get_tower_data(self.base_type)
            if tower_data and 'tier_traits' in tower_data and 'immune' in tower_data['tier_traits']:
                immune_tiers = tower_data['tier_traits']['immune']
                if isinstance(immune_tiers, list) and self.merge_generation in immune_tiers:
                    return False  # Immune at this tier

        # Default: all towers are vulnerable (hybrid) unless specified otherwise
        return True

    def camouflage_repels(self):
        """
        Check if this tower's camouflage repels assimilators.

        Returns:
            bool: True if camouflage is active and repels assimilators
        """
        # Camouflage is a meta-unlock that makes pure towers repel assimilators
        # Check if game has the enable_camouflage meta-unlock active
        if hasattr(self, 'game') and self.game and hasattr(self.game, 'meta_unlocks_active'):
            return 'enable_camouflage' in self.game.meta_unlocks_active and self.can_be_latched() is False
        return False