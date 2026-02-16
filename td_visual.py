import os
import sys
import random
import pygame
from TD3 import PathGenerator


# ==============================
# ENEMY
# ==============================
class Enemy:
    TYPES = {
        "Drone":    {"health": 10, "speed": 10, "difficulty": 1, "display": "Drone", "symbol": "D"},
        "Scout":    {"health": 8,  "speed": 6,  "difficulty": 1, "display": "Scout", "symbol": "S"},
        "Harvester": {"health": 15, "speed": 12, "difficulty": 2, "display": "Harvester", "symbol": "H"},
        "Adaptor":  {"health": 20, "speed": 8,  "difficulty": 2, "display": "Adaptor", "symbol": "A"},
        "Assimilator": {"health": 25, "speed": 10, "difficulty": 3, "display": "Assimilator", "symbol": "X"},
    }
    
    def __init__(self, path, enemy_type="Drone", wave_num=1, is_egrem_spawned=False):
        self.path = path
        self.position_index = 0
        self.enemy_type = enemy_type if enemy_type in self.TYPES else "Drone"
        self.wave_num = wave_num
        self.alive = True
        self.leaked = False
        self.move_counter = 0.0
        self.is_egrem_spawned = is_egrem_spawned
        self.debuffs = {}  # debuff_type: {'amount': val, 'frames_left': int}
        self._calculate_stats()
    
    def _calculate_stats(self):
        base_stats = self.TYPES.get(self.enemy_type, self.TYPES["Drone"])
        difficulty = base_stats["difficulty"]
        wave_scale = 1.0 + (self.wave_num - 1) * 3.5 * difficulty
        self.max_health = int(base_stats["health"] * wave_scale)
        self.health = self.max_health
        self.move_speed = base_stats["speed"]
        self.difficulty = difficulty
        self.display_name = base_stats["display"]
        self.symbol = base_stats["symbol"]

    def move(self):
        if not self.alive or self.leaked:
            return
        increment = 1.0
        if 'slow' in self.debuffs:
            slow_pct = self.debuffs['slow']['amount'] / 100.0
            increment = 1.0 * (1 - slow_pct)
            self.debuffs['slow']['frames_left'] -= 1
            if self.debuffs['slow']['frames_left'] <= 0:
                del self.debuffs['slow']
        self.move_counter += increment
        if self.move_counter >= self.move_speed:
            self.move_counter -= self.move_speed
            self.position_index += 1
            if self.position_index >= len(self.path):
                self.leaked = True
                self.alive = False

    def get_position(self):
        if 0 <= self.position_index < len(self.path):
            return self.path[self.position_index]
        return None

    def take_damage(self, dmg):
        self.health -= dmg
        if self.health <= 0:
            self.alive = False
            return True
        return False

    def apply_debuff(self, debuff_type, amount, duration):
        if debuff_type not in self.debuffs:
            self.debuffs[debuff_type] = {'amount': amount, 'frames_left': duration}
        else:
            if duration > self.debuffs[debuff_type]['frames_left']:
                self.debuffs[debuff_type]['frames_left'] = duration
            self.debuffs[debuff_type]['amount'] = max(self.debuffs[debuff_type]['amount'], amount)


# ==============================
# SHOP UNIT TYPES (Hardware Components)
# ==============================
UNIT_TYPES = [
    {"name": "Neural Processor", "base_cost": 3},
    {"name": "Plasma Capacitor",  "base_cost": 4},
    {"name": "Thermal Regulator",   "base_cost": 3},
    {"name": "Signal Router",      "base_cost": 4},
    {"name": "Quantum Field Gen",   "base_cost": 5},
]

# ==============================
# HARDWARE TRAITS (for software synergy)
# ==============================
TOWER_TRAITS = {
    "Neural Processor": ["switch", "logic"],
    "Plasma Capacitor":  ["charge", "burst"],
    "Thermal Regulator":   ["resist", "heat"],
    "Signal Router":      ["block", "flow"],
    "Quantum Field Gen":   ["filter", "magnetic"],
    "Nanite Swarm":      ["egrem", "spawner"],
}

# ==============================
# SOFTWARE UPGRADES (firmware patches)
# id → {name, desc, cost, traits, synergizes_with, dmg_mult, range_bonus, fire_rate_mult, heat_delta}
# heat_delta >0 = generates heat, <0 = cools / clears heat
# ==============================
UPGRADE_DEFS = {
    # Synergistic upgrades
    "switch_1": {"name": "Overclock Driver",     "desc": "+25% dmg, +heat",         "cost": 4,  "traits": ["switch"],   "synergizes_with": ["switch", "logic"],   "dmg_mult": 0.25, "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 1.5},
    "switch_2": {"name": "Burst Gate Firmware",  "desc": "+40% fire rate",          "cost": 6,  "traits": ["switch"],   "synergizes_with": ["switch"],             "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0.40, "heat_delta": 2.0},
    "charge_1": {"name": "Supercap Patch",       "desc": "+1 range, faster charge", "cost": 4,  "traits": ["charge"],   "synergizes_with": ["charge", "burst"],   "dmg_mult": 0,    "range_bonus": 1, "fire_rate_mult": 0,    "heat_delta": -0.5},
    "charge_2": {"name": "EMP Discharge",        "desc": "AoE stun on burst",       "cost": 7,  "traits": ["charge"],   "synergizes_with": ["charge"],             "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 1.0},  # stun logic added later
    "resist_1": {"name": "Cooling Heatsink",     "desc": "Aura: -heat nearby",      "cost": 5,  "traits": ["resist"],   "synergizes_with": ["resist", "heat"],     "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0.15, "heat_delta": -1.2},
    "resist_2": {"name": "Thermal Throttle",     "desc": "Slow enemies 30%",        "cost": 6,  "traits": ["resist"],   "synergizes_with": ["resist"],             "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 0},    # slow aura added later
    "block_1":  {"name": "Rectifier Shield",     "desc": "Block 20% debuffs",       "cost": 4,  "traits": ["block"],    "synergizes_with": ["block", "flow"],      "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": -0.8},
    "block_2":  {"name": "Laser Diode Focus",    "desc": "Piercing beam (2 hits)",  "cost": 6,  "traits": ["block"],    "synergizes_with": ["block"],              "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 0.5},
    "filter_1": {"name": "Inductive Trap",       "desc": "Pull enemies closer",     "cost": 5,  "traits": ["filter"],   "synergizes_with": ["filter", "magnetic"], "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 0},
    "filter_2": {"name": "EMI Filter",           "desc": "Stun fast enemies",       "cost": 7,  "traits": ["filter"],   "synergizes_with": ["filter"],             "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 1.0},

    # Wildcard / general upgrades
    "wild_1":   {"name": "Quantum Patch",        "desc": "+15% all stats",          "cost": 5,  "traits": ["wildcard"], "synergizes_with": [],                     "dmg_mult": 0.15, "range_bonus": 0, "fire_rate_mult": 0.15, "heat_delta": 0.5},
    "wild_2":   {"name": "Nanite Antivirus",     "desc": "Kill gives +1 gold",      "cost": 4,  "traits": ["wildcard"], "synergizes_with": [],                     "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": -0.3},
}

# Separate lists for choice logic
UPGRADE_SYNERGY = [k for k in UPGRADE_DEFS if not k.startswith("wild")]
UPGRADE_WILDCARD = [k for k in UPGRADE_DEFS if k.startswith("wild")]

# ==============================
# EGREM SPAWNING CONFIG
# ==============================
# Maps tower types to spawn parameters: {enemy_type, spawn_count, spawn_interval_frames}
EGREM_SPAWN_CONFIG = {
    "Neural Processor": {"enemy_type": "Drone",       "base_spawn": 2, "spawn_interval": 90, "wave_scale": 1.0},
    "Plasma Capacitor":  {"enemy_type": "Harvester",   "base_spawn": 1, "spawn_interval": 120, "wave_scale": 1.2},
    "Thermal Regulator":   {"enemy_type": "Drone",       "base_spawn": 3, "spawn_interval": 60, "wave_scale": 0.8},
    "Signal Router":      {"enemy_type": "Scout",       "base_spawn": 2, "spawn_interval": 75, "wave_scale": 1.1},
    "Quantum Field Gen":   {"enemy_type": "Adaptor",     "base_spawn": 1, "spawn_interval": 100, "wave_scale": 1.3},
}

# ==============================
# TOWER (Hardware + Software Upgrades)
# ==============================
class Tower:
    BASE_TYPES = {
        "Neural Processor": {"dmg": 6,  "range": 2, "fire_rate": 1, "display": "Neural Processor", "fire_type": "TargetBeam"},
        "Plasma Capacitor":  {"dmg": 10, "range": 2, "fire_rate": 4, "display": "Plasma Capacitor", "fire_type": "Ball"},   # slow charge, big burst
        "Thermal Regulator":   {"dmg": 4,  "range": 3, "fire_rate": 2, "display": "Thermal Regulator", "fire_type": "DirectionalBeam"},
        "Signal Router":      {"dmg": 7,  "range": 4, "fire_rate": 2, "display": "Signal Router", "fire_type": "Track"},
        "Quantum Field Gen":   {"dmg": 2,  "range": 99, "fire_rate": 10, "display": "Quantum Field Gen", "fire_type": "Overwatch"},
        "Nanite Swarm":      {"dmg": 0,  "range": 0, "fire_rate": 0, "display": "Nanite Swarm", "fire_type": "Spawner"},       # spawns enemies, no attack
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
        return list(TOWER_TRAITS.get(self.base_type, []))

    def get_effective_traits(self):
        traits = set(self.get_traits())
        for uid in self.upgrades:
            for t in UPGRADE_DEFS.get(uid, {}).get("traits", []):
                if t != "wildcard":
                    traits.add(t)
        return traits

    def _calculate_stats(self):
        base = self.BASE_TYPES.get(self.base_type, self.BASE_TYPES["Neural Processor"])
        merge_level = self.merge_generation  # Use merge_generation for tier-based calculation
        boost = 1.0 + merge_level * 0.3

        self.dmg = int(base["dmg"] * boost)
        self.range = base["range"] + merge_level
        self.fire_rate = max(1, int(base["fire_rate"] / boost) or 1)

        # Apply upgrades
        for uid in self.upgrades:
            u = UPGRADE_DEFS.get(uid, {})
            self.dmg = max(1, int(self.dmg * (1 + u.get("dmg_mult", 0))))
            self.range = max(1, self.range + u.get("range_bonus", 0))
            self.fire_rate = max(1, int(self.fire_rate * (1 + u.get("fire_rate_mult", 0))))

        # Synergy bonus: +10% effect if upgrade synergizes with base trait
        for uid in self.upgrades:
            u = UPGRADE_DEFS.get(uid, {})
            if any(s in self.get_traits() for s in u.get("synergizes_with", [])):
                self.dmg = int(self.dmg * 1.10)
                self.range += 0.2   # small bonus
                # could add more here

    def get_merge_tier(self):
        return self.merge_generation

    @staticmethod
    def merge_towers(tower1, tower2):
        new_tower = Tower(0, 0, tower_type=tower1.base_type)
        new_tower.merge_generation = tower1.merge_generation + 1  # Increment tier
        new_tower.parents = tower1.parents + tower2.parents + [tower1.base_type, tower2.base_type]
        new_tower.gold_invested = tower1.gold_invested + tower2.gold_invested
        new_tower.upgrades = list(set(tower1.upgrades + tower2.upgrades))  # combine unique upgrades
        new_tower._calculate_stats()
        return new_tower

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
            # Standard projectile targeting
            target = None
            best_dist = float('inf')
            enemy_count = 0
            max_enemies = 10
            effective_range = 99 if self.fire_type == "Overwatch" else self.range
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

# ==============================
# GAME
# ==============================
class Game:
    def __init__(self, height=10, width=20, min_path_len=40):
        self.height = height
        self.width = width
        self.grid = [["." for _ in range(width)] for _ in range(height)]
        self.path_gen = PathGenerator(height, width)
        self.regenerate_map(min_path_len)
        self.enemies = []
        self.enemy_grid = [[[] for _ in range(self.width)] for _ in range(self.height)]
        self.towers = []
        self.gold = 50
        self.lives = 20
        self.round_num = 1
        self.wave_active = False
        self.paused = False
        self.reroll_cost = 2
        self.shop = [None] * 5
        self.bench = [None] * 10
        self.selected_tower = None
        self.merge_tower_1 = None
        self.merge_tower_2 = None
        self.merge_preview = None
        self.current_merge_cost = 0  # Display cost of current merge/egrem
        self.game_over = False
        self.final_wave = 1
        self.final_gold = 50
        self.spawn_queue = []
        self.spawn_timer = 0
        self.spawn_interval = 30
        self.wave_bonus_text = ""
        self.wave_bonus_show_until = 0
        self.upgrade_dialog_tower = None  # Tower on grid when upgrade dialog is open
        self.upgrade_dialog_choices = []  # Current 3 upgrade options when dialog is open
        # Egrem (wrong-tier merge) state
        self.egrem_preview = False
        self.egrem_consecutive = 0
        self.egrem_combo = None       # (type1, type2) sorted, for tracking total spent
        self.egrem_total_spent = 0
        self.egrem_flash_until = 0    # frame when flash ends
        self.egrem_flash_bench_idx = None
        self.auto_mode = False  # Auto wave toggle
        self.generate_shop()

    def regenerate_map(self, min_len):
        while True:
            self.path_gen.generate_path()
            loops = 0
            while self.path_gen.generate_loop() and loops < 3:
                loops += 1
            if len(self.path_gen.path) >= min_len:
                break
        self.path = self.path_gen.path

    def generate_shop(self):
        for i in range(5):
            if self.shop[i] is None:
                typ = random.choice([u["name"] for u in UNIT_TYPES])
                cost = next(u["base_cost"] for u in UNIT_TYPES if u["name"] == typ)
                self.shop[i] = {"type": typ, "cost": cost}

    def move_to_bench(self, shop_idx):
        if shop_idx < 0 or shop_idx >= 5 or self.shop[shop_idx] is None:
            return False
        card = self.shop[shop_idx]
        if self.gold < card["cost"]:
            return False
        tower = Tower(0, 0, card["type"])
        tower.gold_invested = card["cost"]
        for i in range(10):
            if self.bench[i] is None:
                self.bench[i] = tower
                self.gold -= card["cost"]
                self.shop[shop_idx] = None
                self.selected_tower = None
                self.merge_tower_1 = None
                self.merge_tower_2 = None
                self.merge_preview = None
                self.egrem_preview = False
                self.reset_egrem_consecutive()
                return True
        return False

    def reroll_shop(self):
        if self.gold < self.reroll_cost:
            return False
        self.gold -= self.reroll_cost
        self.generate_shop()
        return True

    def get_merge_preview_info(self):
        """Return dict with merge preview drawing info, or None if not active."""
        if not (self.merge_preview and self.merge_tower_1 is not None and self.merge_tower_2 is not None):
            return None
        idx1, idx2 = min(self.merge_tower_1, self.merge_tower_2), max(self.merge_tower_1, self.merge_tower_2)
        return {
            "idx1": idx1,
            "idx2": idx2,
            "is_egrem": False,
            "label": "Merge",
            "cost": self.current_merge_cost,
            "line_color_outer": (90, 75, 0),
            "line_color_inner": (255, 230, 0),
            "line_width_outer": 8,
            "line_width_inner": 5,
            "label_bg_color": (255, 255, 200),
            "label_border_color": (255, 200, 0),
            "label_text_color": (255, 255, 255),
            "cost_color": (255, 255, 200),
        }

    def get_egrem_preview_info(self):
        """Return dict with egrem preview drawing info, or None if not active."""
        if not (self.egrem_preview and self.merge_tower_1 is not None and self.merge_tower_2 is not None):
            return None
        idx1, idx2 = min(self.merge_tower_1, self.merge_tower_2), max(self.merge_tower_1, self.merge_tower_2)
        return {
            "idx1": idx1,
            "idx2": idx2,
            "is_egrem": True,
            "label": "egrem",
            "cost": self.current_merge_cost,
            "line_color_outer": (0, 0, 0),
            "line_color_inner_1": (80, 255, 80),
            "line_color_inner_2": (255, 80, 80),
            "line_width_outer": 9,
            "line_width_inner": 5,
            "label_bg_color": (40, 40, 45),
            "label_border_color": (80, 255, 80),
            "label_text_color": (255, 255, 255),
            "cost_color": (200, 200, 200),
        }

    def reset_egrem_consecutive(self):
        """Call when user does anything other than another egrem attempt (click elsewhere, cancel, confirm merge, etc.)."""
        self.egrem_consecutive = 0

    def select_for_merge(self, bench_idx, frame=0):
        if bench_idx < 0 or bench_idx >= 10 or self.bench[bench_idx] is None:
            return False
        if self.merge_tower_1 is None:
            self.merge_tower_1 = bench_idx
            self.selected_tower = bench_idx  # Set for placement preview
            self.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        # Clicking an already-selected card deselects it
        if bench_idx == self.merge_tower_1:
            self.merge_tower_1 = None
            self.selected_tower = None
            self.merge_preview = None
            self.egrem_preview = False
            self.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        if self.merge_tower_2 is not None and bench_idx == self.merge_tower_2:
            self.merge_tower_2 = None
            self.merge_preview = None
            self.egrem_preview = False
            self.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        t1 = self.bench[self.merge_tower_1]
        t2 = self.bench[bench_idx]
        same_tier = t1.get_merge_tier() == t2.get_merge_tier()
        # Third card: replace second selection (keep first), then same-tier → preview, different → egrem
        self.merge_tower_2 = bench_idx
        tier1 = t1.get_merge_tier()
        tier2 = t2.get_merge_tier()
        self.current_merge_cost = (tier1 * 10) + (tier2 * 10)
        if same_tier:
            self.merge_preview = Tower.merge_towers(t1, t2)
            self.egrem_preview = False
            self.reset_egrem_consecutive()
            return True
        # Different tier: trigger egrem attempt (cost, flash, maybe create egrem tower)
        return self._try_egrem(frame)

    def _try_egrem(self, frame):
        """Attempt egrem (wrong-tier merge). Cost (tier1*10 + tier2*10) * 1.25; shows preview for confirmation."""
        if self.merge_tower_1 is None or self.merge_tower_2 is None:
            return False
        t1 = self.bench[self.merge_tower_1]
        t2 = self.bench[self.merge_tower_2]
        if t1 is None or t2 is None:
            return False
        combo = tuple(sorted([t1.base_type, t2.base_type]))
        if combo != self.egrem_combo:
            self.egrem_combo = combo
            self.egrem_total_spent = 0
        tier1 = t1.get_merge_tier()
        tier2 = t2.get_merge_tier()
        base_cost = (tier1 * 10) + (tier2 * 10)
        # Ensure minimum cost of 5 even for T0+T0
        base_cost = max(5, base_cost)
        cost = int(base_cost * 1.25)
        self.current_merge_cost = cost  # Display the egrem cost
        if self.gold < cost:
            self.merge_tower_2 = None
            self.egrem_preview = False
            self.current_merge_cost = 0
            return False
        self.gold -= cost
        self.egrem_consecutive += 1
        self.egrem_total_spent += cost
        self.egrem_preview = True
        self.egrem_flash_until = frame + 120  # 2 seconds
        self.egrem_flash_bench_idx = self.merge_tower_2
        self.merge_preview = None
        return True

    def _complete_egrem(self):
        """Create Egrem tower and put on bench; remove the two source towers."""
        idx1, idx2 = sorted([self.merge_tower_1, self.merge_tower_2])
        t1, t2 = self.bench[idx1], self.bench[idx2]
        egrem = Tower(0, 0, tower_type="Nanite Swarm")
        egrem.gold_invested = (t1.gold_invested if t1 else 0) + (t2.gold_invested if t2 else 0)
        
        # Configure egrem spawning based on source towers
        egrem.egrem_source_types = [t1.base_type, t2.base_type]
        egrem._configure_egrem_spawning()
        
        # Remove both source towers from bench
        self.bench[idx1] = None
        self.bench[idx2] = None
        
        # Place egrem tower in first unoccupied slot
        for i in range(10):
            if self.bench[i] is None:
                self.bench[i] = egrem
                break
        
        # Deselect all cards after egrem
        self.merge_tower_1 = None
        self.merge_tower_2 = None
        self.merge_preview = None
        self.egrem_preview = False
        self.selected_tower = None
        self.current_merge_cost = 0
        self.egrem_consecutive = 0
        self.egrem_combo = None
        self.egrem_total_spent = 0
        self.egrem_flash_until = 0
        self.egrem_flash_bench_idx = None

    def confirm_merge(self):
        if None in (self.merge_tower_1, self.merge_tower_2, self.merge_preview):
            return False
        idx1, idx2 = sorted([self.merge_tower_1, self.merge_tower_2])
        t1, t2 = self.bench[idx1], self.bench[idx2]
        tier1 = t1.get_merge_tier() if t1 else 0
        tier2 = t2.get_merge_tier() if t2 else 0
        cost = (tier1 * 10) + (tier2 * 10)
        if self.gold < cost:
            return False
        self.gold -= cost
        self.reset_egrem_consecutive()
        self.merge_preview.gold_invested = (t1.gold_invested if t1 else 0) + (t2.gold_invested if t2 else 0) + cost
        
        # Remove both source towers from bench
        self.bench[idx1] = None
        self.bench[idx2] = None
        
        # Place merged tower in first unoccupied slot
        for i in range(10):
            if self.bench[i] is None:
                self.bench[i] = self.merge_preview
                break
        
        # Deselect all cards after merge
        self.merge_tower_1 = None
        self.merge_tower_2 = None
        self.merge_preview = None
        self.selected_tower = None
        self.current_merge_cost = 0
        self.egrem_preview = False
        return True

    def cancel_merge(self):
        self.merge_tower_1 = self.merge_tower_2 = self.merge_preview = self.selected_tower = None
        self.current_merge_cost = 0
        self.egrem_preview = False
        self.reset_egrem_consecutive()

    def place_tower(self, gx, gy, bench_idx=None):
        if not (0 <= gx < self.width and 0 <= gy < self.height):
            return False
        if self.grid[gy][gx] != '.':
            return False
        if bench_idx is None or bench_idx >= 10 or self.bench[bench_idx] is None:
            return False
        tower = self.bench[bench_idx]
        tower.x = gx
        tower.y = gy
        self.towers.append(tower)
        self.grid[gy][gx] = tower.base_type[0]
        self.bench[bench_idx] = None
        self.selected_tower = None
        self.merge_tower_1 = self.merge_tower_2 = self.merge_preview = None
        self.egrem_preview = False
        self.reset_egrem_consecutive()
        return True

    def sell_from_bench(self, idx):
        if idx < 0 or idx >= 10 or self.bench[idx] is None:
            return
        t = self.bench.pop(idx)
        value = 2 + t.get_merge_tier() * 2   # simple value
        self.gold += value
        self.bench.insert(idx, None)  # keep order
        self.selected_tower = self.merge_tower_1 = self.merge_tower_2 = self.merge_preview = None
        self.egrem_preview = False
        self.reset_egrem_consecutive()

    def sell_tower_from_grid(self, gx, gy):
        """Remove tower at (gx, gy) and refund 60% of gold_invested."""
        for t in self.towers[:]:
            if t.x == gx and t.y == gy:
                refund = int(t.gold_invested * 0.6)
                self.gold += refund
                self.towers.remove(t)
                self.grid[gy][gx] = '.'
                if self.upgrade_dialog_tower is t:
                    self.upgrade_dialog_tower = None
                return True
        return False

    def get_upgrade_choices(self, tower):
        effective = tower.get_effective_traits()
        already = set(tower.upgrades)
        synergy = []
        for uid in [k for k in UPGRADE_DEFS if not k.startswith("wild")]:
            if uid in already: continue
            u = UPGRADE_DEFS[uid]
            if any(s in effective for s in u.get("synergizes_with", [])):
                synergy.append(uid)
        wildcard = [k for k in UPGRADE_DEFS if k.startswith("wild") and k not in already]

        chosen = []
        if len(synergy) >= 2:
            chosen = random.sample(synergy, 2)
        elif synergy:
            chosen = synergy[:]
        while len(chosen) < 2 and wildcard:
            pick = random.choice(wildcard)
            wildcard.remove(pick)
            chosen.append(pick)
        if wildcard and len(chosen) < 3:
            chosen.append(random.choice(wildcard))
        return chosen[:3]

    def apply_upgrade(self, tower, upgrade_id):
        if upgrade_id not in UPGRADE_DEFS or upgrade_id in tower.upgrades:
            return False
        u = UPGRADE_DEFS[upgrade_id]
        if self.gold < u["cost"]:
            return False
        self.gold -= u["cost"]
        tower.gold_invested += u["cost"]
        tower.upgrades.append(upgrade_id)
        tower._calculate_stats()
        return True

    def start_next_wave(self):
        if self.wave_active:
            return
        self.wave_active = True
        wave_size = 5 + self.round_num * 2
        types = ["Drone"]
        if self.round_num >= 3: types.append("Scout")
        if self.round_num >= 5: types.append("Harvester")
        if self.round_num >= 7: types.append("Adaptor")
        if self.round_num >= 9: types.append("Assimilator")
        self.spawn_queue = [Enemy(self.path, random.choice(types), self.round_num) for _ in range(wave_size)]
        # Egrem towers on grid spawn 1-2 mini-boss style enemies per wave (fewer, stronger)
        for t in self.towers:
            if t.base_type == "Nanite Swarm":
                for _ in range(random.randint(1, 2)):
                    self.spawn_queue.append(Enemy(self.path, "Assimilator", self.round_num + 2))
        self.spawn_timer = 0

    def update_wave(self, frame):
        if not self.wave_active or self.paused:
            return
        self.spawn_timer += 1
        if self.spawn_queue and self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self.enemies.append(self.spawn_queue.pop(0))
        
        # Update towers (including egrem spawning)
        for t in self.towers:
            t.update(self.enemies, frame, self)

        # Apply auras
        for t in self.towers:
            if "resist_2" in t.upgrades:
                for dy in range(-t.range, t.range + 1):
                    for dx in range(-t.range, t.range + 1):
                        if abs(dx) + abs(dy) > t.range:
                            continue
                        nx, ny = t.x + dx, t.y + dy
                        if 0 <= nx < len(game.enemy_grid[0]) and 0 <= ny < len(game.enemy_grid):
                            for e in game.enemy_grid[ny][nx]:
                                if e.alive and not e.leaked:
                                    e.apply_debuff('slow', 30, 60)
        
        # Update enemy grid
        for row in self.enemy_grid:
            for cell in row:
                cell.clear()
        for e in self.enemies:
            pos = e.get_position()
            if pos:
                self.enemy_grid[pos[1]][pos[0]].append(e)
        
        for e in self.enemies[:]:
            e.move()
            if e.leaked:
                self.lives -= 1
                self.enemies.remove(e)
        for e in self.enemies[:]:
            if not e.alive:
                gold = max(1, (3 + e.difficulty * 3) // 2)  # scaled back ~half
                self.gold += gold
                self.enemies.remove(e)
        if self.lives <= 0:
            self.game_over = True
            self.final_wave = self.round_num
            self.final_gold = self.gold
            self.wave_active = False
        if self.wave_active and not self.enemies and not self.spawn_queue:
            bonus = (len(self.towers) * 3 + self.round_num * 4) // 2   # scaled back ~half
            self.gold += bonus
            self.wave_bonus_text = f"+{bonus} bonus"
            self.wave_bonus_show_until = frame + 240
            self.round_num += 1
            self.wave_active = False
            # Auto-start next wave if auto mode is enabled
            if self.auto_mode:
                self.start_next_wave()

    def spawn_enemy_at_position(self, enemy_type, x, y, wave_num=1):
        """Spawn an enemy at a specific grid position (for egrem towers)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            # Find the closest path point to this position
            closest_pos = min(self.path, key=lambda p: abs(p[0]-x) + abs(p[1]-y))
            closest_idx = self.path.index(closest_pos)
            enemy = Enemy(self.path[closest_idx:], enemy_type, wave_num, is_egrem_spawned=True)
            self.enemies.append(enemy)
            # Add to enemy_grid immediately so towers can target it
            pos = enemy.get_position()
            if pos and 0 <= pos[0] < self.width and 0 <= pos[1] < self.height:
                self.enemy_grid[pos[1]][pos[0]].append(enemy)
            return enemy
        return None


# ==============================
# PYGAME MAIN
# ==============================
pygame.init()
game = Game()
TILE = 40
SHOP_H = 140
BENCH_H = 130
GRID_W = game.width * TILE
PANEL_RIGHT_W = 180
WIDTH = GRID_W + PANEL_RIGHT_W
HEIGHT = SHOP_H + BENCH_H + game.height * TILE
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Borg TD Prototype")
clock = pygame.time.Clock()

BLACK = (10,10,15)
GRID = (35,35,45)
PATH = (180,100,60)
ENEMY = (220,60,60)
HP_BG = (50,50,50)
HP_FILL = (60,220,80)
SHOP_BG = (20,20,30)
BENCH_BG = (25,25,35)
PANEL_BG = (22,22,32)
PANEL_BTN = (60,80,120)
PANEL_BTN_SEL = (90,120,180)
CARD_BG = (40,40,55)
CARD_SEL = (100,150,255)
CARD_EMP = (30,30,40)
TEXT = (220,220,220)

font = pygame.font.SysFont("consolas", 16)
font_s = pygame.font.SysFont("consolas", 12)
font_merge = pygame.font.SysFont("consolas", 20)  # Larger font for merge/egrem labels

tower_colors = {
    "Neural Processor": (70,130,255),
    "Plasma Capacitor":  (100,255,100),
    "Thermal Regulator":   (220,120,60),
    "Signal Router":      (200,100,255),
    "Quantum Field Gen":   (255,200,50),
    "Nanite Swarm":      (40, 40, 45),  # dark grey background; card drawn with green/red in bench
}

frame = 0
grid_y = SHOP_H + BENCH_H

running = True
while running:
    frame += 1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if event.button == 1:
                # Upgrade dialog (when open) — check first so dialog clicks in right panel are handled
                dialog_rect = pygame.Rect(GRID_W + 8, 162, 164, 268)
                if game.upgrade_dialog_tower is not None and dialog_rect.collidepoint(mx, my):
                    t = game.upgrade_dialog_tower
                    opts_y = [200, 234, 268]
                    choices = getattr(game, "upgrade_dialog_choices", [])
                    for i, uid in enumerate(choices):
                        if i >= 3:
                            break
                        r = pygame.Rect(GRID_W + 10, opts_y[i], 160, 32)
                        if r.collidepoint(mx, my):
                            if game.apply_upgrade(t, uid):
                                game.upgrade_dialog_choices = game.get_upgrade_choices(t)
                            break
                    else:
                        # Direction selector for Track towers
                        if t.fire_type == "Track":
                            for d in range(4):
                                dx = GRID_W + 14 + d * 35
                                dy = 318
                                r = pygame.Rect(dx, dy, 30, 20)
                                if r.collidepoint(mx, my):
                                    t.track_direction = d
                                    break
                        else:
                            sell_r = pygame.Rect(GRID_W + 10, 306, 75, 24)
                            close_r = pygame.Rect(GRID_W + 95, 306, 75, 24)
                            if sell_r.collidepoint(mx, my):
                                game.sell_tower_from_grid(t.x, t.y)
                                game.upgrade_dialog_tower = None
                            elif close_r.collidepoint(mx, my):
                                game.upgrade_dialog_tower = None
                # Right panel: Play/Pause, Next Wave, Auto (only when not in dialog area)
                elif mx >= GRID_W:
                    play_rect = pygame.Rect(GRID_W + 14, 96, 100, 26)
                    next_rect = pygame.Rect(GRID_W + 14, 128, 100, 26)
                    auto_rect = pygame.Rect(GRID_W + 14, 160, 100, 26)
                    if play_rect.collidepoint(mx, my):
                        game.paused = not game.paused
                    elif next_rect.collidepoint(mx, my):
                        game.start_next_wave()
                    elif auto_rect.collidepoint(mx, my):
                        game.auto_mode = not game.auto_mode
                # Shop
                elif my < SHOP_H:
                    for i in range(5):
                        x = 15 + i * 80
                        y = 15
                        if x <= mx <= x+70 and y <= my <= y+100:
                            game.move_to_bench(i)
                    # Reroll
                    rx = 15 + 5*80
                    if rx <= mx <= rx+35 and 65 <= my <= 100:
                        game.reroll_shop()
                # Bench
                elif SHOP_H <= my < SHOP_H + BENCH_H:
                    # Check for merge/egrem clicks FIRST (before bench card clicks)
                    handled_merge = False
                    if game.merge_preview or game.egrem_preview:
                        idx1, idx2 = game.merge_tower_1, game.merge_tower_2
                        if idx1 is not None and idx2 is not None:
                            cx1 = 45 + min(idx1, idx2) * 68
                            cx2 = 45 + max(idx1, idx2) * 68
                            mid_x = (cx1 + cx2) // 2
                            mid_y = SHOP_H + 60
                            
                            if game.merge_preview:
                                merge_txt = font_merge.render("Merge", True, (0, 0, 0))
                                merge_rect = merge_txt.get_rect(center=(mid_x, mid_y))
                                merge_rect.inflate_ip(18, 13)  # 25% larger clickable area
                                if merge_rect.collidepoint(mx, my):
                                    game.confirm_merge()
                                    handled_merge = True
                            elif game.egrem_preview:
                                egrem_txt = font_merge.render("egrem", True, (0, 0, 0))
                                egrem_rect = egrem_txt.get_rect(center=(mid_x, mid_y))
                                egrem_rect.inflate_ip(18, 13)  # 25% larger clickable area (matching merge)
                                if egrem_rect.collidepoint(mx, my):
                                    # Confirm egrem by completing it
                                    game._complete_egrem()
                                    handled_merge = True
                    
                    # Only check bench cards if merge/egrem wasn't handled
                    if not handled_merge:
                        clicked_on_bench_card = False
                        for i in range(10):
                            x = 15 + i * 68
                            y = SHOP_H + 15
                            if x <= mx <= x+60 and y <= my <= y+90:
                                if game.bench[i]:
                                    clicked_on_bench_card = True
                                    game.select_for_merge(i, frame)
                        
                        # Handle cancel if clicked outside merge/egrem area
                        if (game.merge_preview or game.egrem_preview) and not clicked_on_bench_card:
                            game.cancel_merge()
                # Grid: place from bench, or open upgrade dialog on placed tower
                elif my >= grid_y and mx < GRID_W:
                    gx = mx // TILE
                    gy = (my - grid_y) // TILE
                    if game.selected_tower is not None and game.merge_preview is None and not game.egrem_preview:
                        game.place_tower(gx, gy, bench_idx=game.selected_tower)
                    else:
                        if game.merge_preview or game.egrem_preview or game.merge_tower_1 is not None:
                            game.cancel_merge()
                        # Left-click on placed tower: open upgrade dialog
                        for t in game.towers:
                            if t.x == gx and t.y == gy:
                                game.upgrade_dialog_tower = t
                                game.upgrade_dialog_choices = game.get_upgrade_choices(t)
                                break
            elif event.button == 3:
                # Right-click: cancel merge/egrem if preview is open
                if game.merge_preview or game.egrem_preview or game.merge_tower_1 is not None:
                    game.cancel_merge()
                # Sell bench
                elif SHOP_H <= my < SHOP_H + BENCH_H:
                    for i in range(10):
                        x = 15 + i * 68
                        y = SHOP_H + 15
                        if x <= mx <= x+60 and y <= my <= y+90:
                            game.sell_from_bench(i)
                            break
                # Sell grid (60% of gold invested)
                elif my >= grid_y and mx < GRID_W:
                    gx = mx // TILE
                    gy = (my - grid_y) // TILE
                    game.sell_tower_from_grid(gx, gy)

    game.update_wave(frame)

    screen.fill(BLACK)

    # Shop (left of panel only)
    pygame.draw.rect(screen, SHOP_BG, (0,0,GRID_W,SHOP_H))
    pygame.draw.line(screen, GRID, (0,SHOP_H), (GRID_W,SHOP_H), 2)
    for i in range(5):
        x = 15 + i * 80
        y = 15
        card = game.shop[i]
        col = CARD_EMP if card is None else CARD_BG
        pygame.draw.rect(screen, col, (x,y,70,100))
        pygame.draw.rect(screen, TEXT, (x,y,70,100), 1 if card else 2)
        if card:
            screen.blit(font_s.render(card["type"][:8], True, TEXT), (x+5,y+10))
            screen.blit(font_s.render(f"${card['cost']}", True, TEXT), (x+5,y+75))

    # Reroll
    rx = 15 + 400
    pygame.draw.rect(screen, CARD_BG, (rx,65,35,35))
    pygame.draw.rect(screen, TEXT, (rx,65,35,35), 1)
    screen.blit(font_s.render("R", True, TEXT), (rx+10,70))

    # Bench (left of panel only)
    pygame.draw.rect(screen, BENCH_BG, (0,SHOP_H,GRID_W,BENCH_H))
    pygame.draw.line(screen, GRID, (0,SHOP_H+BENCH_H), (GRID_W,SHOP_H+BENCH_H), 2)
    screen.blit(font_s.render("BENCH", True, TEXT), (15, SHOP_H+5))
    for i in range(10):
        x = 15 + i * 68
        y = SHOP_H + 15
        col = CARD_EMP if game.bench[i] is None else CARD_BG
        if i in (game.merge_tower_1, game.merge_tower_2):
            col = CARD_SEL
        pygame.draw.rect(screen, col, (x,y,60,90))
        pygame.draw.rect(screen, TEXT, (x,y,60,90), 2)
        if game.bench[i]:
            t = game.bench[i]
            if t.base_type == "Nanite Swarm":
                pygame.draw.rect(screen, (28, 28, 35), (x, y, 60, 90))
                pygame.draw.rect(screen, (80, 255, 80), (x, y, 60, 90), 2)
                screen.blit(font_s.render("Egrem", True, (80, 255, 100)), (x+5, y+5))
                screen.blit(font_s.render("spawn", True, (255, 80, 80)), (x+5, y+28))
                screen.blit(font_s.render(f"T{t.get_merge_tier()}", True, TEXT), (x+5, y+50))
            else:
                display_name = t.BASE_TYPES[t.base_type]["display"]
                screen.blit(font_s.render(display_name[:6], True, TEXT), (x+5,y+5))
                screen.blit(font_s.render(f"D:{t.dmg}", True, TEXT), (x+5,y+30))
                screen.blit(font_s.render(f"T{t.get_merge_tier()}", True, TEXT), (x+5,y+50))
        # Flash overlay for egrem (wrong-tier) attempt on second selected card
        if game.egrem_flash_bench_idx is not None and frame < game.egrem_flash_until and i == game.egrem_flash_bench_idx:
            flash_alpha = 80 + 60 * (1 - (game.egrem_flash_until - frame) / 120)
            s = pygame.Surface((60, 90))
            s.set_alpha(min(140, int(flash_alpha)))
            s.fill((255, 80, 80))
            screen.blit(s, (x, y))

    # Merge/Egrem preview rendering
    for preview_info in [game.get_merge_preview_info(), game.get_egrem_preview_info()]:
        if preview_info is None:
            continue
        
        idx1, idx2 = preview_info["idx1"], preview_info["idx2"]
        cx1 = int(15 + idx1 * 68 + 30)
        cx2 = int(15 + idx2 * 68 + 30)
        cy = int(SHOP_H + 15 + 45)
        
        # Zig-zag points
        amp = 20
        dx = cx2 - cx1
        pts = [
            (cx1, cy),
            (cx1 + dx // 4, cy + amp),
            (cx1 + dx // 2, cy - amp),
            (cx1 + (3 * dx) // 4, cy + amp),
            (cx2, cy),
        ]
        
        # Draw outer line (glow/outline)
        for i in range(len(pts) - 1):
            pygame.draw.line(screen, preview_info["line_color_outer"], pts[i], pts[i + 1], preview_info["line_width_outer"])
        
        # Draw inner line (colored)
        for i in range(len(pts) - 1):
            if preview_info["is_egrem"] and "line_color_inner_1" in preview_info:
                # Egrem alternates colors
                c = preview_info["line_color_inner_1"] if i % 2 == 0 else preview_info["line_color_inner_2"]
            else:
                c = preview_info["line_color_inner"]
            pygame.draw.line(screen, c, pts[i], pts[i + 1], preview_info["line_width_inner"])
        
        # Draw label
        mid_x, mid_y = (cx1 + cx2) // 2, cy
        label_surf = font_merge.render(preview_info["label"], True, (0, 0, 0))
        label_rect = label_surf.get_rect(center=(mid_x, mid_y))
        label_rect.inflate_ip(13, 8)
        pygame.draw.rect(screen, preview_info["label_bg_color"], label_rect)
        pygame.draw.rect(screen, preview_info["label_border_color"], label_rect, 2)
        
        # Draw label outline
        for ox, oy in [(-1,-1),(-1,1),(1,-1),(1,1),(0,-1),(0,1),(-1,0),(1,0)]:
            screen.blit(font_merge.render(preview_info["label"], True, (255, 255, 255)), 
                       (label_rect.centerx - label_surf.get_width()//2 + ox, label_rect.centery - label_surf.get_height()//2 + oy))
        screen.blit(label_surf, (label_rect.centerx - label_surf.get_width()//2, label_rect.centery - label_surf.get_height()//2))
        
        # Draw cost below label
        cost_surf = font_s.render(f"${preview_info['cost']}", True, preview_info["cost_color"])
        screen.blit(cost_surf, (mid_x - cost_surf.get_width()//2, mid_y + 18))

    # Right panel: stats + controls
    pygame.draw.rect(screen, PANEL_BG, (GRID_W, 0, PANEL_RIGHT_W, SHOP_H + BENCH_H))
    pygame.draw.line(screen, GRID, (GRID_W, 0), (GRID_W, SHOP_H + BENCH_H), 2)
    px = GRID_W + 14
    screen.blit(font.render(f"Gold:  {game.gold}", True, TEXT), (px, 18))
    screen.blit(font.render(f"Lives: {game.lives}", True, TEXT), (px, 42))
    screen.blit(font.render(f"Wave:  {game.round_num}", True, TEXT), (px, 66))
    # Play/Pause button
    play_rect = pygame.Rect(px, 96, 100, 26)
    col_play = PANEL_BTN_SEL if game.paused else PANEL_BTN
    pygame.draw.rect(screen, col_play, play_rect)
    pygame.draw.rect(screen, TEXT, play_rect, 1)
    screen.blit(font_s.render("Play" if game.paused else "Pause", True, TEXT), (px + 28, 100))
    # Next Wave button
    next_rect = pygame.Rect(px, 128, 100, 26)
    pygame.draw.rect(screen, PANEL_BTN, next_rect)
    pygame.draw.rect(screen, TEXT, next_rect, 1)
    screen.blit(font_s.render("Next Wave", True, TEXT), (px + 14, 132))
    # Auto toggle button
    auto_rect = pygame.Rect(px, 160, 100, 26)
    col_auto = PANEL_BTN_SEL if game.auto_mode else PANEL_BTN
    pygame.draw.rect(screen, col_auto, auto_rect)
    pygame.draw.rect(screen, TEXT, auto_rect, 1)
    screen.blit(font_s.render("Auto " + ("ON" if game.auto_mode else "OFF"), True, TEXT), (px + 18, 164))

    # Upgrade dialog (when a placed tower is selected)
    if game.upgrade_dialog_tower is not None:
        t = game.upgrade_dialog_tower
        dialog_rect = pygame.Rect(GRID_W + 8, 162, 164, 268)
        pygame.draw.rect(screen, (35, 35, 50), dialog_rect)
        pygame.draw.rect(screen, TEXT, dialog_rect, 2)
        screen.blit(font.render("Upgrade", True, TEXT), (GRID_W + 14, 168))
        screen.blit(font_s.render(f"{t.base_type}  D:{t.dmg} R:{t.range}", True, TEXT), (GRID_W + 14, 184))
        opts_y = [200, 234, 268]
        for i, uid in enumerate(getattr(game, "upgrade_dialog_choices", [])):
            if i >= 3:
                break
            u = UPGRADE_DEFS.get(uid, {})
            name = u.get("name", uid)
            cost = u.get("cost", 0)
            desc = u.get("desc", "")
            r = pygame.Rect(GRID_W + 10, opts_y[i], 160, 32)
            pygame.draw.rect(screen, CARD_BG, r)
            pygame.draw.rect(screen, TEXT, r, 1)
            screen.blit(font_s.render(f"{name} ${cost}", True, TEXT), (GRID_W + 14, opts_y[i] + 4))
            screen.blit(font_s.render(desc[:28], True, (180, 180, 200)), (GRID_W + 14, opts_y[i] + 16))
        # Direction selector for Track and DirectionalBeam towers
        if t.fire_type in ("Track", "DirectionalBeam"):
            screen.blit(font_s.render("Direction:", True, TEXT), (GRID_W + 14, 302))
            directions = ["N", "E", "S", "W"]
            for d in range(4):
                dx = GRID_W + 14 + d * 35
                dy = 318
                col = PANEL_BTN_SEL if t.track_direction == d else PANEL_BTN
                pygame.draw.rect(screen, col, (dx, dy, 30, 20))
                pygame.draw.rect(screen, TEXT, (dx, dy, 30, 20), 1)
                screen.blit(font_s.render(directions[d], True, TEXT), (dx + 10, dy + 2))
        else:
            pygame.draw.rect(screen, (120, 80, 80), (GRID_W + 10, 306, 75, 24))
            pygame.draw.rect(screen, TEXT, (GRID_W + 10, 306, 75, 24), 1)
            screen.blit(font_s.render("Sell 60%", True, TEXT), (GRID_W + 18, 310))
            pygame.draw.rect(screen, PANEL_BTN, (GRID_W + 95, 306, 75, 24))
            pygame.draw.rect(screen, TEXT, (GRID_W + 95, 306, 75, 24), 1)
            screen.blit(font_s.render("Close", True, TEXT), (GRID_W + 118, 310))

    # Grid
    for x in range(game.width+1):
        pygame.draw.line(screen, GRID, (x*TILE, grid_y), (x*TILE, grid_y + game.height*TILE), 1)
    for y in range(game.height+1):
        pygame.draw.line(screen, GRID, (0, grid_y + y*TILE), (GRID_W, grid_y + y*TILE), 1)

    for i in range(len(game.path)-1):
        x1,y1 = game.path[i]
        x2,y2 = game.path[i+1]
        pygame.draw.line(screen, PATH,
                         (x1*TILE +20, grid_y + y1*TILE +20),
                         (x2*TILE +20, grid_y + y2*TILE +20), 12)

    # Range preview
    mx,my = pygame.mouse.get_pos()
    if game.selected_tower is not None and game.merge_preview is None and my >= grid_y:
        gx = mx // TILE
        gy = (my - grid_y) // TILE
        if 0 <= gx < game.width and 0 <= gy < game.height:
            t = game.bench[game.selected_tower]
            if t and t.fire_type != "Overwatch":
                r = min(t.range * TILE, 200)  # Limit size to prevent huge surfaces
                cx = gx * TILE + 20
                cy = grid_y + gy * TILE + 20
                s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
                pygame.draw.circle(s, (100,160,255,60), (r+2,r+2), r)
                pygame.draw.circle(s, (160,220,255,180), (r+2,r+2), r, 2)
                screen.blit(s, (cx-r-2, cy-r-2))

    # Attack beams
    for t in game.towers:
        if t.last_shot_target and frame - t.last_shot_frame < 18:
            tx = t.x * TILE + 20
            ty = grid_y + t.y * TILE + 20
            ex,ey = t.last_shot_target
            exx = ex * TILE + 20
            eyy = grid_y + ey * TILE + 20
            age = frame - t.last_shot_frame
            w = max(2, 6 - age//3)
            col = (*tower_colors.get(t.base_type, (180,180,255)), 255 - age*14)
            pygame.draw.line(screen, col, (tx,ty), (exx,eyy), w)

    # Towers
    for t in game.towers:
        col = tower_colors.get(t.base_type, (150,150,150))
        r = pygame.Rect(t.x*TILE +6, grid_y + t.y*TILE +6, TILE-12, TILE-12)
        pygame.draw.rect(screen, col, r)
        pygame.draw.rect(screen, (220,220,255), r, 2)
        # Permanent range display for Radius towers
        if t.fire_type == "Radius":
            cx = t.x * TILE + 20
            cy = grid_y + t.y * TILE + 20
            rad = t.range * TILE
            s = pygame.Surface((rad*2+4, rad*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (220,120,60,80), (rad+2, rad+2), rad)
            pygame.draw.circle(s, (255,150,80,150), (rad+2, rad+2), rad, 2)
            screen.blit(s, (cx-rad-2, cy-rad-2))

    # Enemies
    for e in game.enemies:
        pos = e.get_position()
        if pos:
            ex,ey = pos
            c = (ex*TILE +20, grid_y + ey*TILE +20)
            enemy_color = (60, 220, 60) if e.is_egrem_spawned else ENEMY
            pygame.draw.circle(screen, enemy_color, c, 13)
            ratio = max(0, e.health / e.max_health)
            pygame.draw.rect(screen, HP_BG, (c[0]-20, c[1]-30, 40, 6))
            pygame.draw.rect(screen, HP_FILL, (c[0]-20, c[1]-30, 40*ratio, 6))

    # Wave bonus
    if frame < game.wave_bonus_show_until:
        txt = font.render(game.wave_bonus_text, True, (100,255,140))
        tw,th = txt.get_size()
        pygame.draw.rect(screen, (0,0,0,180), (WIDTH//2 - tw//2 -20, 60, tw+40, th+20))
        screen.blit(txt, (WIDTH//2 - tw//2, 70))

    # Game over
    if game.game_over:
        o = pygame.Surface((WIDTH,HEIGHT))
        o.set_alpha(180)
        o.fill((0,0,0))
        screen.blit(o, (0,0))
        txt = pygame.font.SysFont("consolas",48,bold=True).render("GAME OVER", True, (255,80,80))
        screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2 -60)))
        s = font.render(f"Wave {game.final_wave}   Gold {game.final_gold}", True, TEXT)
        screen.blit(s, s.get_rect(center=(WIDTH//2, HEIGHT//2)))
        r = font.render("Click anywhere to restart", True, TEXT)
        screen.blit(r, r.get_rect(center=(WIDTH//2, HEIGHT//2 +60)))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()