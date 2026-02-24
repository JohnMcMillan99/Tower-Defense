import os
import sys
import json
import random
import pygame
from enum import Enum

# Import modules
from models.enemy import Enemy
from models.tower import Tower
from map.path_graph import PathGraph
from data.tiles import TILE_TYPES
from data.units import UNIT_TYPES, TOWER_TRAITS
from data.upgrades import UPGRADE_DEFS, UPGRADE_SYNERGY, UPGRADE_WILDCARD, EGREM_SPAWN_CONFIG

# Keep using TD3 for now until imports are stable
from utils.path_generator import PathGenerator


# ==============================
# DIRECTIONS
# ==============================
class Direction(Enum):
    N = (0, -1)   # dy = -1 (up)
    S = (0, 1)    # dy = 1 (down)
    E = (1, 0)    # dx = 1 (right)
    W = (-1, 0)   # dx = -1 (left)


# ==============================
# SHOP UNIT TYPES (Hardware Components)
# ==============================
# UNIT_TYPES imported from data.units module above

# ==============================
# Constants imported from data modules above
# ==============================
# ==============================

# ==============================
# EGREM SPAWNING CONFIG
# ==============================
# EGREM_SPAWN_CONFIG imported from data.upgrades module above

















# ==============================
# GAME
# ==============================
class Game:
    def __init__(self, height=6, width=10, min_path_len=20):
        # Core playable area (center of expanded grid)
        self.core_height = height
        self.core_width = width
        # Expanded grid with border (add 4 nodes on each side)
        self.border_size = 4
        self.height = height + 2 * self.border_size
        self.width = width + 2 * self.border_size
        self.grid = [["." for _ in range(self.width)] for _ in range(self.height)]
        self.path_graph = PathGraph()
        self.path_gen = PathGenerator(self.core_height, self.core_width)
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
        self.map_tile_bench = [None] * 3  # Separate bench for map tiles (increased size)
        self.upgrade_bench = [None] * 3  # Upgrade bench - stores upgrade IDs
        self.selected_tower = None
        self.selected_map_tile = None  # Selected tile from map bench
        self.selected_upgrade = None  # Selected upgrade from upgrade bench
        self.selected_tile_rotation = 0  # 0, 90, 180, 270 degrees
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
        self.selected_enemy = None  # Enemy selected for inspection
        # Egrem (wrong-tier merge) state
        self.egrem_preview = False
        self.egrem_consecutive = 0
        self.egrem_combo = None       # (type1, type2) sorted, for tracking total spent
        self.egrem_total_spent = 0
        self.egrem_flash_until = 0    # frame when flash ends
        self.egrem_flash_bench_idx = None
        self.auto_mode = False  # Auto wave toggle
        self.shop_mode = "towers"  # "towers" or "tiles"
        self.generate_shop()

    def regenerate_map(self, min_len):
        while True:
            self.path_gen.generate_path()
            loops = 0
            while self.path_gen.generate_loop() and loops < 1:  # Limit to 1 loop for less cramping
                loops += 1
            if len(self.path_gen.path) >= min_len:
                break

        # Build PathGraph from generated path
        self.path_graph = PathGraph()
        # Offset path coordinates to full grid space (account for borders)
        path_coords = [(x + self.border_size, y + self.border_size) for x, y in self.path_gen.path]

        # Set start and end
        if path_coords:
            self.path_graph.set_start(path_coords[0])
            self.path_graph.set_end(path_coords[-1])

            # Add all nodes and edges
            for pos in path_coords:
                self.path_graph.add_node(pos)

            for i in range(len(path_coords) - 1):
                self.path_graph.add_edge(path_coords[i], path_coords[i+1])

        # Mark initial path cells on the grid
        for x, y in path_coords:
            if 0 <= x < self.width and 0 <= y < self.height:
                self.grid[y][x] = 'P'  # Mark as path cell

        # Keep backward compatibility - compute ordered path
        self.path = self.path_graph.get_ordered_path()

    def generate_shop(self):
        for i in range(5):
            if self.shop[i] is None:
                if self.shop_mode == "towers":
                    typ = random.choice([u["name"] for u in UNIT_TYPES])
                    cost = next(u["base_cost"] for u in UNIT_TYPES if u["name"] == typ)
                    self.shop[i] = {"type": typ, "cost": cost}
                elif self.shop_mode == "tiles":
                    tile = random.choice(TILE_TYPES)
                    self.shop[i] = {"type": tile["name"], "cost": tile["base_cost"], "tile_data": tile}
                elif self.shop_mode == "upgrades":
                    upgrade_id = random.choice(list(UPGRADE_DEFS.keys()))
                    u = UPGRADE_DEFS[upgrade_id]
                    self.shop[i] = {"type": upgrade_id, "cost": u["cost"], "name": u["name"], "desc": u["desc"]}

    def move_to_bench(self, shop_idx):
        if shop_idx < 0 or shop_idx >= 5 or self.shop[shop_idx] is None:
            return False
        card = self.shop[shop_idx]
        if self.gold < card["cost"]:
            return False

        if self.shop_mode == "tiles":
            # Move tile to map tile bench
            tile_data = card["tile_data"]
            for i in range(3):  # Updated for larger bench
                if self.map_tile_bench[i] is None:
                    self.map_tile_bench[i] = tile_data.copy()
                    self.gold -= card["cost"]
                    self.shop[shop_idx] = None
                    return True
            return False
        elif self.shop_mode == "upgrades":
            # Move upgrade to upgrade bench
            upgrade_id = card["type"]
            for i in range(3):
                if self.upgrade_bench[i] is None:
                    self.upgrade_bench[i] = upgrade_id
                    self.gold -= card["cost"]
                    self.shop[shop_idx] = None
                    return True
            return False  # Bench full
        else:
            # Move tower to regular bench
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
        cost = int(base_cost * 1.3)
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
        if len(tower.upgrades) >= tower.UPGRADE_CAPACITY:
            return False  # Tower at capacity
        u = UPGRADE_DEFS[upgrade_id]
        if self.gold < u["cost"]:
            return False
        self.gold -= u["cost"]
        tower.gold_invested += u["cost"]
        tower.upgrades.append(upgrade_id)
        tower._calculate_stats()
        return True

    def apply_upgrade_from_bench(self, tower, upgrade_id, bench_idx):
        """Apply upgrade from bench to tower (no additional gold cost)."""
        if upgrade_id not in UPGRADE_DEFS or upgrade_id in tower.upgrades:
            return False
        if len(tower.upgrades) >= tower.UPGRADE_CAPACITY:
            return False  # Tower at capacity
        if self.upgrade_bench[bench_idx] != upgrade_id:
            return False  # Upgrade not in bench slot

        # Apply upgrade to tower
        tower.upgrades.append(upgrade_id)
        tower._calculate_stats()

        # Remove from bench
        self.upgrade_bench[bench_idx] = None

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

    # ------------------------------------------------------------------
    # Tile placement helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rotate_grid(grid, times):
        """Rotate a 2-D list of booleans 90° clockwise `times` times."""
        result = [list(row) for row in grid]
        for _ in range(times % 4):
            result = [list(row) for row in zip(*result[::-1])]
        return result

    @staticmethod
    def _get_tile_path_cells(tile_data, gx, gy, rotation):
        """Return list of world-coord (wx, wy) cells that are path cells in the rotated tile."""
        rotated = Game._rotate_grid(tile_data["path_grid"], rotation)
        cells = []
        for dy, row in enumerate(rotated):
            for dx, val in enumerate(row):
                if val:
                    cells.append((gx + dx, gy + dy))
        return cells

    @staticmethod
    def _get_endpoints(cell_list):
        """Return cells that have exactly 1 neighbour within the cell list (path endpoints)."""
        cell_set = set(cell_list)
        endpoints = []
        for (x, y) in cell_list:
            neighbours = sum(1 for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)] if (nx,ny) in cell_set)
            if neighbours <= 1:
                endpoints.append((x, y))
        return endpoints

    def can_place_tile(self, tile_data, gx, gy, rotation):
        """Check if a tile can be placed at the given grid position with rotation.

        Rules:
          1. Tile must fit within grid bounds.
          2. No tile cell may overlap an existing tower or path cell.
          3. At least one tile path endpoint must be adjacent to the map path end.
        """
        # #region agent log
        def debug_log(msg, data=None):
            log_entry = {
                "sessionId": "03f8e0",
                "runId": "tile_placement_debug",
                "hypothesisId": "H1_visual_blocking_H2_no_valid_tiles",
                "location": "can_place_tile",
                "message": msg,
                "data": data or {},
                "timestamp": 0  # Will be set by logging system
            }
            with open("debug-03f8e0.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        # #endregion

        debug_log("can_place_tile called", {
            "tile": tile_data["name"],
            "position": (gx, gy),
            "rotation": rotation,
            "path_length": len(self.path),
            "path_end": self.path[-1] if self.path else None
        })

        rotated = self._rotate_grid(tile_data["path_grid"], rotation)
        tile_h = len(rotated)
        tile_w = len(rotated[0]) if rotated else 0

        # Rule 1 – bounds
        bounds_ok = not (gx < 0 or gy < 0 or gx + tile_w > self.width or gy + tile_h > self.height)
        debug_log("bounds check", {"bounds_ok": bounds_ok, "gx": gx, "gy": gy, "tile_w": tile_w, "tile_h": tile_h, "grid_size": (self.width, self.height)})
        if not bounds_ok:
            return False

        # Rule 2 – no overlap with towers or existing path
        overlap_found = False
        for dy in range(tile_h):
            for dx in range(tile_w):
                cell = self.grid[gy + dy][gx + dx]
                if cell != '.':
                    overlap_found = True
                    break
            if overlap_found:
                break

        debug_log("overlap check", {"overlap_found": overlap_found, "tile_area": [(gx+dx, gy+dy) for dy in range(tile_h) for dx in range(tile_w)]})
        if overlap_found:
            return False

        tile_cells = self._get_tile_path_cells(tile_data, gx, gy, rotation)
        debug_log("tile cells", {"tile_cells": tile_cells})
        if not tile_cells:
            return False

        # Rule 3 – at least one tile endpoint must be adjacent to the path end
        tile_endpoints = self._get_endpoints(tile_cells)
        map_end = self.path[-1] if self.path else None

        debug_log("adjacency check", {
            "tile_endpoints": tile_endpoints,
            "map_end": map_end,
            "tile_cells": tile_cells
        })

        def adjacent(a, b):
            return abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1

        connects = map_end and any(adjacent(te, map_end) for te in tile_endpoints)
        debug_log("connection result", {"connects": connects})

        if not connects:
            return False

        debug_log("placement VALID")
        return True

    def place_map_tile(self, tile_data, gx, gy, rotation):
        """Place a map tile at the given position, extending the map and path.

        The new path cells are inserted at the correct end of game.path so that
        the path remains a continuous ordered sequence. Updates path_graph.end
        so enemies and directional rendering follow the extended path.
        """
        tile_placement_log("place_map_tile_START", {"gx": gx, "gy": gy, "rotation": rotation, "tile": tile_data["name"]})
        rotated = self._rotate_grid(tile_data["path_grid"], rotation)
        tile_h = len(rotated)
        tile_w = len(rotated[0]) if rotated else 0

        tile_cells = self._get_tile_path_cells(tile_data, gx, gy, rotation)
        tile_cell_set = set(tile_cells)
        tile_endpoints = self._get_endpoints(tile_cells)
        tile_placement_log("place_map_tile_tile_cells", {"tile_cells": list(tile_cells), "tile_endpoints": tile_endpoints})

        def adjacent(a, b):
            return abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1

        map_end = self.path[-1] if self.path else None
        # Find entry (tile cell adjacent to path end) and exit (where path extends)
        entry = None
        exit_cell = None
        for ep in tile_endpoints:
            if map_end and adjacent(ep, map_end):
                entry = ep
                break
        if entry is None and map_end:
            # No endpoints (e.g. loop); find any tile cell adjacent to path end
            for c in tile_cells:
                if adjacent(c, map_end):
                    entry = c
                    break
        for ep in tile_endpoints:
            if ep != entry:
                exit_cell = ep
                break
        if exit_cell is None and entry is not None and len(tile_cells) > 1:
            # Loop or single-endpoint: exit is tile cell farthest from map_end (excluding entry)
            others = [c for c in tile_cells if c != entry]
            exit_cell = max(others, key=lambda c: abs(c[0]-map_end[0]) + abs(c[1]-map_end[1])) if map_end and others else (others[0] if others else entry)

        # Order tile cells from entry to exit via BFS within the tile
        from collections import deque
        ordered = []
        if entry is not None:
            queue = deque([entry])
            visited = {entry}
            came_from = {entry: None}
            while queue:
                cur = queue.popleft()
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    nb = (cur[0]+dx, cur[1]+dy)
                    if nb in tile_cell_set and nb not in visited:
                        visited.add(nb)
                        came_from[nb] = cur
                        queue.append(nb)
            if exit_cell and exit_cell in came_from:
                cur = exit_cell
                while cur is not None:
                    ordered.append(cur)
                    cur = came_from[cur]
                ordered.reverse()
            else:
                ordered = list(tile_cells)
        else:
            ordered = list(tile_cells)

        tile_placement_log("place_map_tile_ordered", {"ordered": ordered, "path_end": map_end, "new_end": exit_cell})

        # Update PathGraph with new tiles
        for pos in ordered:
            self.path_graph.add_node(pos)
        for i in range(len(ordered) - 1):
            self.path_graph.add_edge(ordered[i], ordered[i+1])
        if ordered and self.path:
            self.path_graph.add_edge(self.path[-1], ordered[0])

        # Update path end so BFS computes the full extended path
        new_end = ordered[-1] if ordered else (exit_cell or map_end)
        if new_end is not None:
            self.path_graph.set_end(new_end)

        # Recompute ordered path (start to new end)
        self.path = self.path_graph.get_ordered_path()
        tile_placement_log("place_map_tile_path_updated", {"new_path_length": len(self.path), "new_end": new_end})

        # Mark grid cells
        for dy in range(tile_h):
            for dx in range(tile_w):
                if rotated[dy][dx]:
                    self.grid[gy + dy][gx + dx] = 'P'  # path
                else:
                    self.grid[gy + dy][gx + dx] = 'X'  # expanded non-path
        tile_placement_log("place_map_tile_DONE")

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

    def should_expand_map(self, tile_cells):
        """Check if tile placement should trigger map expansion."""
        for tx, ty in tile_cells:
            # Check if any tile cell is within 2 units of any edge
            if tx <= 1 or tx >= self.width - 3 or ty <= 1 or ty >= self.height - 3:
                return True
        return False

    def expand_grid(self, tile_cells):
        """Expand grid by 2 rows/columns in directions needed."""
        expand_north = any(ty <= 1 for tx, ty in tile_cells)
        expand_south = any(ty >= self.height - 3 for tx, ty in tile_cells)
        expand_west = any(tx <= 1 for tx, ty in tile_cells)
        expand_east = any(tx >= self.width - 3 for tx, ty in tile_cells)

        # Calculate new dimensions
        new_width = self.width + (2 if expand_east else 0) + (2 if expand_west else 0)
        new_height = self.height + (2 if expand_south else 0) + (2 if expand_north else 0)

        # Create new grid and enemy_grid
        new_grid = [["." for _ in range(new_width)] for _ in range(new_height)]
        new_enemy_grid = [[[] for _ in range(new_width)] for _ in range(new_height)]

        # Copy existing data with offset
        offset_x = 2 if expand_west else 0
        offset_y = 2 if expand_north else 0

        for y in range(self.height):
            for x in range(self.width):
                new_grid[y + offset_y][x + offset_x] = self.grid[y][x]
                new_enemy_grid[y + offset_y][x + offset_x] = self.enemy_grid[y][x]

        # Update coordinates if expanding west/north
        if expand_west or expand_north:
            # Shift all path coordinates
            self.path = [(x + offset_x, y + offset_y) for x, y in self.path]

            # Update path graph
            self.path_graph = PathGraph()
            for pos in self.path:
                self.path_graph.add_node(pos)
            for i in range(len(self.path) - 1):
                self.path_graph.add_edge(self.path[i], self.path[i+1])
            if self.path:
                self.path_graph.set_end(self.path[-1])

            # Update towers
            for tower in self.towers:
                tower.x += offset_x
                tower.y += offset_y

        # Update grid references
        self.grid = new_grid
        self.enemy_grid = new_enemy_grid
        self.width = new_width
        self.height = new_height


# Camera transform functions
def world_to_screen(wx, wy):
    """Convert world coordinates to screen coordinates."""
    sx = (wx * TILE * zoom_level) + camera_x
    sy = grid_y + (wy * TILE * zoom_level) + camera_y
    return sx, sy

def screen_to_world(sx, sy):
    """Convert screen coordinates to world coordinates."""
    wx = ((sx - camera_x) / (TILE * zoom_level))
    wy = ((sy - grid_y - camera_y) / (TILE * zoom_level))
    return wx, wy


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

# Camera system
camera_x = 0
camera_y = 0
zoom_level = 1.0
dragging = False
last_mouse_x = 0
last_mouse_y = 0

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
map_bench_x = 15
map_bench_y = HEIGHT - 100

# Tile placement debug logging
def tile_placement_log(step, data=None):
    try:
        with open("tile_placement_debug.log", "a") as f:
            import time
            entry = {"step": step, "data": data or {}, "time": time.time()}
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

# Clear log at startup for fresh debug run
try:
    open("tile_placement_debug.log", "w").close()
except Exception:
    pass

running = True
while running:
    frame += 1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # Camera controls with arrow keys
            if event.key == pygame.K_LEFT:
                camera_x += 50
            elif event.key == pygame.K_RIGHT:
                camera_x -= 50
            elif event.key == pygame.K_UP:
                camera_y += 50
            elif event.key == pygame.K_DOWN:
                camera_y -= 50
            elif event.key == pygame.K_HOME:  # Reset camera
                camera_x = 0
                camera_y = 0
                zoom_level = 1.0
            elif pygame.K_1 <= event.key <= pygame.K_3:  # Upgrade bench shortcuts
                slot_idx = event.key - pygame.K_1
                if game.upgrade_bench[slot_idx] is not None:
                    game.selected_upgrade = slot_idx if game.selected_upgrade != slot_idx else None
        elif event.type == pygame.MOUSEWHEEL:
            # Zoom in/out with mouse wheel
            old_zoom = zoom_level
            zoom_level = max(0.5, min(2.0, zoom_level + event.y * 0.1))
            # Zoom towards mouse cursor
            mx, my = pygame.mouse.get_pos()
            if my >= grid_y and mx < GRID_W:
                wx, wy = screen_to_world(mx, my)
                camera_x = mx - (wx * TILE * zoom_level)
                camera_y = my - grid_y - (wy * TILE * zoom_level)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            upgrade_bench_x = GRID_W + 10
            upgrade_bench_y = HEIGHT - 100
            tile_placement_log("MOUSEBUTTONDOWN", {
                "button": event.button, "mx": mx, "my": my,
                "grid_y": grid_y, "map_bench_y": map_bench_y, "GRID_W": GRID_W,
                "upgrade_bench_x": upgrade_bench_x, "upgrade_bench_y": upgrade_bench_y,
                "selected_map_tile": game.selected_map_tile,
                "in_grid_region": my >= grid_y and mx < GRID_W,
                "in_map_bench_region": my >= map_bench_y and my < map_bench_y + 80
            })
            if event.button == 3:  # Right click - rotate selected tile
                if game.selected_map_tile is not None:
                    game.selected_tile_rotation = (game.selected_tile_rotation + 1) % 4
            elif event.button == 1:
                # Upgrade dialog (when open) — check first so dialog clicks in right panel are handled
                if game.upgrade_dialog_tower is not None:
                    t = game.upgrade_dialog_tower
                    base_height = 280  # Updated to match dialog height
                    upgrade_height = 20 + (len(t.upgrades) * 16) if t.upgrades else 0
                    dialog_height = base_height + upgrade_height
                    dialog_rect = pygame.Rect(GRID_W + 8, 162, 164, dialog_height)
                    if dialog_rect.collidepoint(mx, my):
                        t = game.upgrade_dialog_tower
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
                            sell_r = pygame.Rect(GRID_W + 10, 266, 75, 24)  # Updated position
                            close_r = pygame.Rect(GRID_W + 95, 266, 75, 24)  # Updated position
                            if sell_r.collidepoint(mx, my):
                                game.sell_tower_from_grid(t.x, t.y)
                                game.upgrade_dialog_tower = None
                            elif close_r.collidepoint(mx, my):
                                game.upgrade_dialog_tower = None
                    else:
                        # Clicked outside dialog - deselect tower
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
                    # Shop mode toggle (moved here to match its new position)
                    tx = map_bench_x + 3*80 + 20
                    ty = map_bench_y
                    if tx <= mx <= tx+35 and ty <= my <= ty+35:
                        # Cycle through modes: towers → tiles → upgrades → towers
                        if game.shop_mode == "towers":
                            game.shop_mode = "tiles"
                        elif game.shop_mode == "tiles":
                            game.shop_mode = "upgrades"
                        else:  # "upgrades"
                            game.shop_mode = "towers"
                        game.shop = [None] * 5  # Clear shop when switching modes
                        game.generate_shop()
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
                # Map Tile Bench
                elif my >= map_bench_y and my < map_bench_y + 80:
                    tile_placement_log("MAP_BENCH_BRANCH", {"reason": "my in map_bench_y range", "mx": mx, "my": my})
                    for i in range(3):  # Updated for larger bench
                        x = map_bench_x + i * 80
                        y = map_bench_y
                        if x <= mx <= x+70 and y <= my <= y+80:
                            if game.map_tile_bench[i] is not None:
                                game.selected_map_tile = i
                                game.selected_tile_rotation = 0
                                break
                # Rotate buttons: only handle when click is actually on the rotate button region
                rot_x = map_bench_x + 3*80 + 10
                rot_y = map_bench_y + 5
                in_rotate_region = rot_y <= my <= rot_y + 26 and (rot_x <= mx <= rot_x + 26 or rot_x + 34 <= mx <= rot_x + 60)
                if game.selected_map_tile is not None and in_rotate_region:
                    # Left rotate button (<)
                    if rot_x <= mx <= rot_x + 26:
                        game.selected_tile_rotation = (game.selected_tile_rotation - 1) % 4
                    # Right rotate button (>)
                    elif rot_x + 34 <= mx <= rot_x + 60:
                        game.selected_tile_rotation = (game.selected_tile_rotation + 1) % 4
                # Map tile bench and shop toggle (checked before grid to prevent overlap issues)
                elif my >= map_bench_y and my < map_bench_y + 80 and mx < GRID_W:
                    tx = map_bench_x + 3*80 + 20
                    ty = map_bench_y
                    if tx <= mx <= tx+35 and ty <= my <= ty+35:
                        # Cycle through modes: towers → tiles → upgrades → towers
                        if game.shop_mode == "towers":
                            game.shop_mode = "tiles"
                        elif game.shop_mode == "tiles":
                            game.shop_mode = "upgrades"
                        else:  # "upgrades"
                            game.shop_mode = "towers"
                        game.shop = [None] * 5  # Clear shop when switching modes
                        game.generate_shop()
                    # Map tile bench selection
                    for i in range(3):  # Updated for larger bench
                        x = map_bench_x + i * 80
                        y = map_bench_y
                        if x <= mx <= x+70 and y <= my <= y+80:
                            if game.map_tile_bench[i] is not None:
                                game.selected_map_tile = i
                                game.selected_tile_rotation = 0
                                break
                # Upgrade Bench (bottom right)
                elif mx >= GRID_W and my >= upgrade_bench_y and my < upgrade_bench_y + 80:
                    for i in range(3):
                        x = upgrade_bench_x + i * 55
                        y = upgrade_bench_y
                        if x <= mx <= x+50 and y <= my <= y+80:
                            if game.upgrade_bench[i] is not None:
                                # Toggle selection: if already selected, deselect; else select
                                game.selected_upgrade = i if game.selected_upgrade != i else None
                                break
                # Grid: place from bench, place map tile, select enemy, or open upgrade dialog on placed tower
                elif my >= grid_y and mx < GRID_W:
                        gx, gy = screen_to_world(mx, my)
                        gx, gy = int(gx), int(gy)
                        tile_placement_log("GRID_CLICK", {"gx": gx, "gy": gy, "selected_map_tile": game.selected_map_tile})
                        if game.selected_map_tile is not None:
                            # Place map tile to expand grid
                            tile_data = game.map_tile_bench[game.selected_map_tile]
                            tile_placement_log("BEFORE_CAN_PLACE", {
                                "tile_data": tile_data["name"] if tile_data else None,
                                "gx": gx, "gy": gy, "rotation": game.selected_tile_rotation
                            })
                            can_place = tile_data and game.can_place_tile(tile_data, gx, gy, game.selected_tile_rotation)
                            tile_placement_log("AFTER_CAN_PLACE", {"can_place": can_place})
                            if tile_data and can_place:
                                tile_placement_log("CALLING_PLACE_MAP_TILE", {"gx": gx, "gy": gy})
                                game.place_map_tile(tile_data, gx, gy, game.selected_tile_rotation)

                                # Check if expansion needed and expand
                                tile_cells = game._get_tile_path_cells(tile_data, gx, gy, game.selected_tile_rotation)
                                if game.should_expand_map(tile_cells):
                                    game.expand_grid(tile_cells)
                                    # Update global window dimensions
                                    GRID_W = game.width * TILE
                                    WIDTH = GRID_W + PANEL_RIGHT_W
                                    HEIGHT = SHOP_H + BENCH_H + game.height * TILE
                                    screen = pygame.display.set_mode((WIDTH, HEIGHT))

                                # Remove tile from bench after placement
                                game.map_tile_bench[game.selected_map_tile] = None
                                game.selected_map_tile = None
                                game.selected_tile_rotation = 0
                                tile_placement_log("PLACEMENT_COMPLETE")
                        elif game.selected_tower is not None and game.merge_preview is None and not game.egrem_preview:
                            game.place_tower(gx, gy, bench_idx=game.selected_tower)
                        else:
                            if game.merge_preview or game.egrem_preview or game.merge_tower_1 is not None:
                                game.cancel_merge()
                            # Check for enemy selection first
                            enemy_selected = False
                            if 0 <= gx < game.width and 0 <= gy < game.height:
                                for e in game.enemy_grid[gy][gx]:
                                    if e.alive:
                                        game.selected_enemy = e
                                        game.upgrade_dialog_tower = None  # Clear tower selection
                                        enemy_selected = True
                                        break
                            if not enemy_selected:
                                # Left-click on placed tower
                                for t in game.towers:
                                    if t.x == gx and t.y == gy:
                                        if game.selected_upgrade is not None:
                                            # Apply selected upgrade from bench to tower
                                            upgrade_id = game.upgrade_bench[game.selected_upgrade]
                                            if game.apply_upgrade_from_bench(t, upgrade_id, game.selected_upgrade):
                                                game.selected_upgrade = None  # Clear selection after successful apply
                                        else:
                                            # Open upgrade dialog
                                            game.upgrade_dialog_tower = t
                                            game.upgrade_dialog_choices = game.get_upgrade_choices(t)
                                        game.selected_enemy = None  # Clear enemy selection
                                        break
                                else:
                                    # Clicked on empty grid: clear selections
                                    game.selected_enemy = None
                                    game.upgrade_dialog_tower = None
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
                # Deselect upgrade from upgrade bench
                elif mx >= GRID_W and my >= upgrade_bench_y and my < upgrade_bench_y + 80:
                    game.selected_upgrade = None
                # Sell grid (60% of gold invested)
                elif my >= grid_y and mx < GRID_W:
                    gx, gy = screen_to_world(mx, my)
                    gx, gy = int(gx), int(gy)
                    game.sell_tower_from_grid(gx, gy)
            elif event.button == 2:  # Middle mouse button - start dragging
                dragging = True
                last_mouse_x, last_mouse_y = event.pos
        elif event.type == pygame.MOUSEMOTION:
            if dragging:
                dx = event.pos[0] - last_mouse_x
                dy = event.pos[1] - last_mouse_y
                camera_x += dx
                camera_y += dy
                last_mouse_x, last_mouse_y = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:  # Middle mouse button - stop dragging
                dragging = False

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
            # Display info differently for tiles vs towers vs upgrades
            if "tile_data" in card:
                tile = card["tile_data"]
                screen.blit(font_s.render(tile["name"][:10], True, TEXT), (x+5,y+5))
                screen.blit(font_s.render(f"{tile['width']}x{tile['height']}", True, TEXT), (x+5,y+20))
                # Draw mini path preview
                path_grid = tile["path_grid"]
                cell_size = 8
                start_x = x + 35 - (len(path_grid[0]) * cell_size) // 2
                start_y = y + 35
                for py in range(len(path_grid)):
                    for px in range(len(path_grid[py])):
                        if path_grid[py][px]:
                            pygame.draw.rect(screen, PATH, (start_x + px*cell_size, start_y + py*cell_size, cell_size, cell_size))
                screen.blit(font_s.render(f"${card['cost']}", True, TEXT), (x+5,y+75))
            elif "name" in card:
                # Upgrade card
                name = card["name"]
                desc = card["desc"]
                screen.blit(font_s.render(name[:10], True, TEXT), (x+5,y+5))
                # Show short description
                screen.blit(font_s.render(desc[:12], True, (180,180,200)), (x+5,y+20))
                screen.blit(font_s.render(desc[12:24] if len(desc) > 12 else "", True, (180,180,200)), (x+5,y+35))
                screen.blit(font_s.render(f"${card['cost']}", True, TEXT), (x+5,y+75))
            else:
                # Tower card
                screen.blit(font_s.render(card["type"][:8], True, TEXT), (x+5,y+10))
                screen.blit(font_s.render(f"${card['cost']}", True, TEXT), (x+5,y+75))

    # Shop mode toggle (next to map tile bench on right)
    tx = map_bench_x + 3*80 + 20  # Positioned right of the enlarged bench
    ty = map_bench_y
    pygame.draw.rect(screen, CARD_BG, (tx,ty,35,35))
    pygame.draw.rect(screen, TEXT, (tx,ty,35,35), 1)
    # Show T/M/U based on current shop mode
    mode_char = "T" if game.shop_mode == "towers" else ("M" if game.shop_mode == "tiles" else "U")
    screen.blit(font_s.render(mode_char, True, TEXT), (tx+10,ty+10))

    # Reroll
    rx = 15 + 400
    pygame.draw.rect(screen, CARD_BG, (rx,65,35,35))
    pygame.draw.rect(screen, TEXT, (rx,65,35,35), 1)
    screen.blit(font_s.render("R", True, TEXT), (rx+10,70))

    # Bench (left of panel only)
    pygame.draw.rect(screen, BENCH_BG, (0,SHOP_H,GRID_W,BENCH_H))
    pygame.draw.line(screen, GRID, (0,SHOP_H+BENCH_H), (GRID_W,SHOP_H+BENCH_H), 2)
    screen.blit(font_s.render("BENCH", True, TEXT), (15, SHOP_H+5))

    # Map Tile Bench (bottom left, enlarged)
    pygame.draw.rect(screen, SHOP_BG, (0, map_bench_y-10, 280, 100))  # Widened for 3 slots
    pygame.draw.line(screen, GRID, (0, map_bench_y-10), (280, map_bench_y-10), 2)
    screen.blit(font_s.render("MAP TILES", True, TEXT), (15, map_bench_y-5))
    for i in range(3):  # Updated for larger bench
        x = map_bench_x + i * 80
        y = map_bench_y
        col = CARD_EMP if game.map_tile_bench[i] is None else CARD_BG
        if i == game.selected_map_tile:
            col = CARD_SEL
        pygame.draw.rect(screen, col, (x,y,70,80))
        pygame.draw.rect(screen, TEXT, (x,y,70,80), 2)
        if game.map_tile_bench[i]:
            tile = game.map_tile_bench[i]
            screen.blit(font_s.render(tile["name"][:8], True, TEXT), (x+5,y+10))
            screen.blit(font_s.render(f"{tile['width']}x{tile['height']}", True, TEXT), (x+5,y+50))

    # Upgrade Bench (bottom right, in right panel)
    upgrade_bench_x = GRID_W + 10
    upgrade_bench_y = HEIGHT - 100
    pygame.draw.rect(screen, SHOP_BG, (GRID_W, upgrade_bench_y-10, PANEL_RIGHT_W, 100))
    pygame.draw.line(screen, GRID, (GRID_W, upgrade_bench_y-10), (WIDTH, upgrade_bench_y-10), 2)
    screen.blit(font_s.render("UPGRADES", True, TEXT), (GRID_W + 15, upgrade_bench_y-5))
    for i in range(3):
        x = upgrade_bench_x + i * 55  # 3 slots of ~55px each fit in 180px panel
        y = upgrade_bench_y
        col = CARD_EMP if game.upgrade_bench[i] is None else CARD_BG
        if i == game.selected_upgrade:
            col = CARD_SEL
        pygame.draw.rect(screen, col, (x, y, 50, 80))
        pygame.draw.rect(screen, TEXT, (x, y, 50, 80), 2)
        if game.upgrade_bench[i]:
            upgrade_id = game.upgrade_bench[i]
            u = UPGRADE_DEFS.get(upgrade_id, {})
            name = u.get("name", upgrade_id)
            # Abbreviate long names
            if len(name) > 8:
                name = name[:6] + ".."
            screen.blit(font_s.render(name, True, TEXT), (x+3, y+5))
            screen.blit(font_s.render(f"${u.get('cost', 0)}", True, TEXT), (x+3, y+60))

    # Hint text for upgrade bench
    hint_text = "Click or press 1-3 to select"
    screen.blit(font_s.render(hint_text, True, (160, 160, 180)), (GRID_W + 15, upgrade_bench_y + 85))

    # Rotate button next to map bench
    if game.selected_map_tile is not None:
        rot_x = map_bench_x + 2*80 + 10
        rot_y = map_bench_y + 5

        # Left rotate button  ◄
        pygame.draw.rect(screen, PANEL_BTN, (rot_x, rot_y, 26, 26))
        pygame.draw.rect(screen, TEXT, (rot_x, rot_y, 26, 26), 1)
        screen.blit(font_s.render("<", True, TEXT), (rot_x + 8, rot_y + 6))

        # Right rotate button  ►
        pygame.draw.rect(screen, PANEL_BTN, (rot_x + 34, rot_y, 26, 26))
        pygame.draw.rect(screen, TEXT, (rot_x + 34, rot_y, 26, 26), 1)
        screen.blit(font_s.render(">", True, TEXT), (rot_x + 42, rot_y + 6))

        # Degree label between buttons
        deg_lbl = font_s.render(f"{game.selected_tile_rotation * 90}\u00b0", True, TEXT)
        screen.blit(deg_lbl, (rot_x + 27 - deg_lbl.get_width() // 2, rot_y + 7))

        # Step indicator below  e.g. "2/4"
        step_lbl = font_s.render(f"{game.selected_tile_rotation + 1}/4", True, (160, 160, 180))
        screen.blit(step_lbl, (rot_x + 30 - step_lbl.get_width() // 2, rot_y + 30))

        # Hint text
        hint_lbl = font_s.render("A/D or </> rotate", True, (120, 120, 140))
        screen.blit(hint_lbl, (rot_x - 10, rot_y + 46))
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

        # Calculate dynamic dialog height based on upgrades
        base_height = 280  # Reduced since no upgrade options
        upgrade_height = 20 + (len(t.upgrades) * 16) if t.upgrades else 0
        dialog_height = base_height + upgrade_height

        dialog_rect = pygame.Rect(GRID_W + 8, 162, 164, dialog_height)
        pygame.draw.rect(screen, (35, 35, 50), dialog_rect)
        pygame.draw.rect(screen, TEXT, dialog_rect, 2)
        screen.blit(font.render("Upgrade", True, TEXT), (GRID_W + 14, 168))
        screen.blit(font_s.render(f"{t.base_type}  D:{t.dmg} R:{t.range}", True, TEXT), (GRID_W + 14, 184))

        # Upgrade capacity info
        capacity_text = f"Upgrades: {len(t.upgrades)}/{t.UPGRADE_CAPACITY}"
        capacity_color = (180, 180, 200) if len(t.upgrades) < t.UPGRADE_CAPACITY else (255, 150, 150)
        screen.blit(font_s.render(capacity_text, True, capacity_color), (GRID_W + 14, 200))

        # Hint text
        screen.blit(font_s.render("Select upgrade from bench,", True, (160, 160, 180)), (GRID_W + 14, 220))
        screen.blit(font_s.render("then click tower to apply", True, (160, 160, 180)), (GRID_W + 14, 235))

        # Sell and Close buttons - adjust position based on dialog height
        button_y = 266 + upgrade_height
        pygame.draw.rect(screen, (120, 80, 80), (GRID_W + 10, button_y, 75, 24))
        pygame.draw.rect(screen, TEXT, (GRID_W + 10, button_y, 75, 24), 1)
        screen.blit(font_s.render("Sell 60%", True, TEXT), (GRID_W + 18, button_y + 4))
        pygame.draw.rect(screen, PANEL_BTN, (GRID_W + 95, button_y, 75, 24))
        pygame.draw.rect(screen, TEXT, (GRID_W + 95, button_y, 75, 24), 1)
        screen.blit(font_s.render("Close", True, TEXT), (GRID_W + 118, button_y + 4))

        # Tower stats integrated into the dialog (below buttons)
        tower_stats_y = button_y + 34  # Start below the buttons
        screen.blit(font_s.render("Stats:", True, TEXT), (GRID_W + 14, tower_stats_y))
        tower_stats_y += 16
        screen.blit(font_s.render(f"Damage: {t.dmg}", True, TEXT), (GRID_W + 14, tower_stats_y))
        tower_stats_y += 16
        screen.blit(font_s.render(f"Range: {t.range}", True, TEXT), (GRID_W + 14, tower_stats_y))
        tower_stats_y += 16
        screen.blit(font_s.render(f"Fire Rate: {t.fire_rate}", True, TEXT), (GRID_W + 14, tower_stats_y))
        tower_stats_y += 16
        screen.blit(font_s.render(f"Heat: {t.heat:.1f}/{t.max_heat}", True, TEXT), (GRID_W + 14, tower_stats_y))
        tower_stats_y += 20
        if t.upgrades:
            screen.blit(font_s.render("Upgrades:", True, TEXT), (GRID_W + 14, tower_stats_y))
            for uid in t.upgrades:
                tower_stats_y += 16
                name = UPGRADE_DEFS.get(uid, {}).get("name", uid)
                screen.blit(font_s.render(f"- {name}", True, (180, 180, 200)), (GRID_W + 14, tower_stats_y))

        # Draw range visualization for selected tower
        if t.fire_type != "Overwatch":  # Overwatch has infinite range
            cx = t.x * TILE + 20
            cy = grid_y + t.y * TILE + 20
            rad = t.range * TILE
            s = pygame.Surface((rad*2+4, rad*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (100,160,255,80), (rad+2, rad+2), rad)
            pygame.draw.circle(s, (160,220,255,150), (rad+2, rad+2), rad, 2)
            screen.blit(s, (cx-rad-2, cy-rad-2))

    # Enemy stats card (below upgrade dialog area)
    if game.selected_enemy:
        e = game.selected_enemy
        enemy_stats_rect = pygame.Rect(GRID_W + 8, 162 + 320 + 10, 164, 120)  # Positioned below the expanded upgrade dialog
        pygame.draw.rect(screen, (35, 35, 50), enemy_stats_rect)
        pygame.draw.rect(screen, TEXT, enemy_stats_rect, 2)
        y_offset = enemy_stats_rect.y + 6
        screen.blit(font.render(f"{e.display_name}", True, TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 20
        screen.blit(font_s.render(f"HP: {e.health}/{e.max_health}", True, TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 16
        screen.blit(font_s.render(f"Speed: {e.move_speed}", True, TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 16
        screen.blit(font_s.render(f"Difficulty: {e.difficulty}", True, TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 16
        screen.blit(font_s.render(f"Wave: {e.wave_num}", True, TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 16
        screen.blit(font_s.render(f"Position: {e.position_index}", True, TEXT), (enemy_stats_rect.x + 6, y_offset))

    # Grid
    for x in range(game.width+1):
        sx1, sy1 = world_to_screen(x, 0)
        sx2, sy2 = world_to_screen(x, game.height)
        pygame.draw.line(screen, GRID, (sx1, sy1), (sx2, sy2), max(1, int(zoom_level)))
    for y in range(game.height+1):
        sx1, sy1 = world_to_screen(0, y)
        sx2, sy2 = world_to_screen(game.width, y)
        pygame.draw.line(screen, GRID, (sx1, sy1), (sx2, sy2), max(1, int(zoom_level)))

    # Render grid cells based on content
    for y in range(game.height):
        for x in range(game.width):
            cell_content = game.grid[y][x]
            if cell_content == 'P':  # Path cell - render directional path
                # First render a subtle background
                sx, sy = world_to_screen(x, y)
                cell_rect = pygame.Rect(sx + 1, sy + 1, TILE * zoom_level - 2, TILE * zoom_level - 2)
                pygame.draw.rect(screen, (120, 80, 40), cell_rect)  # Light brown background

                # Find this cell's position in the path
                cell_pos = (x, y)
                path_index = None
                for i, path_pos in enumerate(game.path):
                    if path_pos == cell_pos:
                        path_index = i
                        break

                if path_index is not None:
                    # Get previous and next positions in path
                    prev_pos = game.path[path_index - 1] if path_index > 0 else None
                    next_pos = game.path[path_index + 1] if path_index < len(game.path) - 1 else None

                    # Calculate directions
                    center_x = sx + (TILE * zoom_level) // 2
                    center_y = sy + (TILE * zoom_level) // 2
                    path_width = max(2, int(8 * zoom_level))  # Scale path width with zoom

                    # Draw path segments
                    if prev_pos:
                        # Calculate direction from current to previous
                        dx = prev_pos[0] - cell_pos[0]
                        dy = prev_pos[1] - cell_pos[1]
                        if dx > 0:  # Previous is right
                            start_x, start_y = center_x + (TILE * zoom_level) // 2, center_y
                        elif dx < 0:  # Previous is left
                            start_x, start_y = center_x - (TILE * zoom_level) // 2, center_y
                        elif dy > 0:  # Previous is down
                            start_x, start_y = center_x, center_y + (TILE * zoom_level) // 2
                        elif dy < 0:  # Previous is up
                            start_x, start_y = center_x, center_y - (TILE * zoom_level) // 2
                        else:
                            start_x, start_y = center_x, center_y
                        pygame.draw.line(screen, (160, 82, 45), (center_x, center_y), (start_x, start_y), path_width)

                    if next_pos:
                        # Calculate direction from current to next
                        dx = next_pos[0] - cell_pos[0]
                        dy = next_pos[1] - cell_pos[1]
                        if dx > 0:  # Next is right
                            end_x, end_y = center_x + (TILE * zoom_level) // 2, center_y
                        elif dx < 0:  # Next is left
                            end_x, end_y = center_x - (TILE * zoom_level) // 2, center_y
                        elif dy > 0:  # Next is down
                            end_x, end_y = center_x, center_y + (TILE * zoom_level) // 2
                        elif dy < 0:  # Next is up
                            end_x, end_y = center_x, center_y - (TILE * zoom_level) // 2
                        else:
                            end_x, end_y = center_x, center_y
                        pygame.draw.line(screen, (160, 82, 45), (center_x, center_y), (end_x, end_y), path_width)

            elif cell_content == 'X':  # Expanded non-path
                         cell_rect = pygame.Rect(sx + 1, sy + 1, TILE * zoom_level - 2, TILE * zoom_level - 2)
                         pygame.draw.rect(screen, (128, 128, 128), cell_rect)

    # Draw subtle connecting lines between path cells (now that we have directional rendering)
    for i in range(len(game.path)-1):
        x1,y1 = game.path[i]
        x2,y2 = game.path[i+1]
        sx1, sy1 = world_to_screen(x1, y1)
        sx2, sy2 = world_to_screen(x2, y2)
        pygame.draw.line(screen, (120, 60, 30),  # Darker brown for subtle connection
                         (sx1 + 20 * zoom_level, sy1 + 20 * zoom_level),
                         (sx2 + 20 * zoom_level, sy2 + 20 * zoom_level), max(2, int(6 * zoom_level)))


    # Range preview
    mx,my = pygame.mouse.get_pos()
    if my >= grid_y and mx < GRID_W:
        gx, gy = screen_to_world(mx, my)
        gx, gy = int(gx), int(gy)
        if 0 <= gx < game.width and 0 <= gy < game.height:
            t = None
            cx, cy = world_to_screen(gx, gy)
            cx += 20 * zoom_level
            cy += 20 * zoom_level
            if game.selected_tower is not None and game.merge_preview is None:
                # Tower selected from bench for placement - show range at mouse position
                t = game.bench[game.selected_tower]
            elif game.upgrade_dialog_tower is not None:
                # Placed tower selected - show range around the placed tower, not at mouse
                t = game.upgrade_dialog_tower
                cx = t.x * TILE + 20
                cy = grid_y + t.y * TILE + 20
            if t and t.fire_type != "Overwatch":
                r = min(t.range * TILE * zoom_level, 200)  # Limit size to prevent huge surfaces
                s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
                pygame.draw.circle(s, (100,160,255,60), (r+2,r+2), r)
                pygame.draw.circle(s, (160,220,255,180), (r+2,r+2), r, 2)
                screen.blit(s, (cx-r-2, cy-r-2))

    # Tile placement preview at mouse cursor
    if game.selected_map_tile is not None and game.map_tile_bench[game.selected_map_tile]:
        mx, my = pygame.mouse.get_pos()
        if my >= grid_y and mx < GRID_W:
            gx, gy = screen_to_world(mx, my)
            gx, gy = int(gx), int(gy)
            tile_data = game.map_tile_bench[game.selected_map_tile]

            # Use the helper to get the rotated grid
            rotated_grid = Game._rotate_grid(tile_data["path_grid"], game.selected_tile_rotation)

            # Check validity for color feedback
            placement_valid = game.can_place_tile(tile_data, gx, gy, game.selected_tile_rotation)

            # Color: green tint if valid, red tint if invalid
            if placement_valid:
                fill_color  = (60, 200, 80, 130)   # green, semi-transparent
                border_color = (80, 255, 100)
            else:
                fill_color  = (220, 60, 60, 130)   # red, semi-transparent
                border_color = (255, 80, 80)

            # Draw preview at mouse position
            preview_x, preview_y = world_to_screen(gx, gy)
            cell_size = TILE * zoom_level

            for py in range(len(rotated_grid)):
                for px in range(len(rotated_grid[py])):
                    if rotated_grid[py][px]:
                        rect = pygame.Rect(preview_x + px*cell_size, preview_y + py*cell_size, cell_size, cell_size)
                        s = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
                        s.fill(fill_color)
                        screen.blit(s, rect)
                        pygame.draw.rect(screen, border_color, rect, max(1, int(2 * zoom_level)))

            # Draw a small validity label near the cursor
            label_text = "OK" if placement_valid else "X"
            label_col  = (80, 255, 100) if placement_valid else (255, 80, 80)
            lbl = font_s.render(label_text, True, label_col)
            screen.blit(lbl, (mx + 14, my - 14))

    # Attack beams
    for t in game.towers:
        if t.last_shot_target and frame - t.last_shot_frame < 18:
            tx, ty = world_to_screen(t.x, t.y)
            tx += 20 * zoom_level
            ty += 20 * zoom_level
            ex,ey = t.last_shot_target
            exx, eyy = world_to_screen(ex, ey)
            exx += 20 * zoom_level
            eyy += 20 * zoom_level
            age = frame - t.last_shot_frame
            w = max(2, int((6 - age//3) * zoom_level))
            col = (*tower_colors.get(t.base_type, (180,180,255)), 255 - age*14)
            pygame.draw.line(screen, col, (tx,ty), (exx,eyy), w)

    # Towers
    for t in game.towers:
        col = tower_colors.get(t.base_type, (150,150,150))
        tx, ty = world_to_screen(t.x, t.y)
        r = pygame.Rect(tx + 6 * zoom_level, ty + 6 * zoom_level, (TILE * zoom_level) - 12, (TILE * zoom_level) - 12)
        pygame.draw.rect(screen, col, r)

        # Visual feedback when upgrade is selected for application
        if game.selected_upgrade is not None:
            upgrade_id = game.upgrade_bench[game.selected_upgrade]
            if upgrade_id and len(t.upgrades) < t.UPGRADE_CAPACITY and upgrade_id not in t.upgrades:
                # Tower can receive this upgrade - green border
                pygame.draw.rect(screen, (100,255,100), r, max(2, int(4 * zoom_level)))
            else:
                # Tower cannot receive this upgrade - red border
                pygame.draw.rect(screen, (255,100,100), r, max(2, int(4 * zoom_level)))
        else:
            pygame.draw.rect(screen, (220,220,255), r, max(1, int(2 * zoom_level)))
        # Permanent range display for Radius towers
        if t.fire_type == "Radius":
            cx = tx + 20 * zoom_level
            cy = ty + 20 * zoom_level
            rad = t.range * TILE * zoom_level
            s = pygame.Surface((rad*2+4, rad*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (220,120,60,80), (rad+2, rad+2), rad)
            pygame.draw.circle(s, (255,150,80,150), (rad+2, rad+2), rad, 2)
            screen.blit(s, (cx-rad-2, cy-rad-2))

    # Enemies
    for e in game.enemies:
        pos = e.get_position()
        if pos:
            ex,ey = pos
            exx, eyy = world_to_screen(ex, ey)
            c = (exx + 20 * zoom_level, eyy + 20 * zoom_level)
            enemy_color = (60, 220, 60) if e.is_egrem_spawned else ENEMY
            pygame.draw.circle(screen, enemy_color, c, max(5, int(13 * zoom_level)))
            ratio = max(0, e.health / e.max_health)
            bar_width = max(10, int(40 * zoom_level))
            bar_height = max(2, int(6 * zoom_level))
            pygame.draw.rect(screen, HP_BG, (c[0]-20*zoom_level, c[1]-30*zoom_level, bar_width, bar_height))
            pygame.draw.rect(screen, HP_FILL, (c[0]-20*zoom_level, c[1]-30*zoom_level, bar_width*ratio, bar_height))

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

    # Camera info display (top-right corner)
    if not game.game_over:
        camera_info = f"Zoom: {zoom_level:.1f}x | Camera: ({camera_x:.0f}, {camera_y:.0f})"
        info_surf = font_s.render(camera_info, True, TEXT)
        screen.blit(info_surf, (WIDTH - info_surf.get_width() - 10, 10))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()