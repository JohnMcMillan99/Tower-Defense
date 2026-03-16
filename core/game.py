import random
from enum import Enum
from models.enemy import Enemy
from models.tower import Tower
from map.path_graph import PathGraph
from data.tiles import TILE_TYPES
from data.units import UNIT_TYPES, TOWER_TRAITS
from data.upgrades import UPGRADE_DEFS, EGREM_SPAWN_CONFIG
from data.loader import DataLoader
from utils.path_generator import PathGenerator
from .economy import EconomyManager
from .wave_manager import WaveManager
from .board import BoardManager


class Direction(Enum):
    N = (0, -1)   # dy = -1 (up)
    S = (0, 1)    # dy = 1 (down)
    E = (1, 0)    # dx = 1 (right)
    W = (-1, 0)   # dx = -1 (left)


class Game:
    def __init__(self, height=6, width=10, min_path_len=20, web_mode=False, feature_level=10):
        def log_debug(msg, data=None):
            import json
            import time
            log_entry = {
                "sessionId": "b53f80",
                "id": f"log_{int(time.time()*1000)}_game_init",
                "timestamp": int(time.time() * 1000),
                "location": "game.py:__init__",
                "message": msg,
                "data": data or {},
                "runId": "init_debug",
                "hypothesisId": "init_failure"
            }
            try:
                with open("debug-b53f80.log", "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except:
                pass

        log_debug("Game.__init__ start", {"height": height, "width": width, "web_mode": web_mode, "feature_level": feature_level})

        # Core playable area (center of expanded grid)
        self.core_height = height
        self.core_width = width
        # Expanded grid with border (add 4 nodes on each side)
        self.border_size = 4
        self.height = height + 2 * self.border_size
        self.width = width + 2 * self.border_size
        log_debug("Grid dimensions set", {"core_height": self.core_height, "core_width": self.core_width, "height": self.height, "width": self.width})

        self.grid = [["." for _ in range(self.width)] for _ in range(self.height)]
        log_debug("Grid initialized")

        self.path_graph = PathGraph()
        log_debug("PathGraph initialized")

        self.path_gen = PathGenerator(self.core_height, self.core_width)
        log_debug("PathGenerator initialized")

        self.regenerate_map(min_path_len)
        log_debug("Map regenerated")
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
        log_debug("Shop and bench initialized")
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
        self.web_mode = web_mode  # Flag for reduced load in browser
        self.feature_level = feature_level  # Feature toggle level (1-10)
        log_debug("Feature level set", {"feature_level": feature_level})

        # Shop Power Level and XP system (enabled at level 2+)
        if feature_level >= 2:
            self.shop_power_level = 1
            self.xp = 0
            self.xp_to_next = 100
            self.spl_max = 10
            log_debug("SPL/XP system initialized")

        # Load YAML data
        log_debug("Loading YAML data")
        self.data_loader = DataLoader()
        log_debug("YAML data loaded")

        # Initialize enemy base_xp if feature level allows
        log_debug("Initializing enemy base_xp")
        from models.enemy import Enemy
        Enemy.init_for_feature_level(feature_level)
        log_debug("Enemy base_xp initialized")

        # Check for pygame availability (pygbag compatibility)
        log_debug("Checking pygame availability")
        try:
            import pygame
            self.pygame_available = True
            log_debug("Pygame available")
        except ImportError:
            self.pygame_available = False
            log_debug("Pygame not available")
            print("Warning: Pygame not available, visual effects will be disabled")

        # Initialize managers
        log_debug("Initializing managers")
        self.economy = EconomyManager(self)
        log_debug("EconomyManager initialized")

        self.wave_manager = WaveManager(self)
        log_debug("WaveManager initialized")

        self.board = BoardManager(self)
        log_debug("BoardManager initialized")

        log_debug("Generating initial shop")
        self.economy.generate_shop()
        log_debug("Initial shop generated")

        log_debug("Game.__init__ complete")

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

        rotated = self._rotate_grid(tile_data["path_grid"], rotation)
        tile_h = len(rotated)
        tile_w = len(rotated[0]) if rotated else 0

        # Rule 1 – bounds
        bounds_ok = not (gx < 0 or gy < 0 or gx + tile_w > self.width or gy + tile_h > self.height)
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

        if overlap_found:
            return False

        tile_cells = self._get_tile_path_cells(tile_data, gx, gy, rotation)
        if not tile_cells:
            return False

        # Rule 3 – at least one tile cell must be adjacent to the path end
        tile_endpoints = self._get_endpoints(tile_cells)
        map_end = self.path[-1] if self.path else None

        def adjacent(a, b):
            return abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1

        # For tiles with endpoints (straight, turn), check if any endpoint is adjacent
        # For loops (no endpoints), check if any tile cell is adjacent
        if tile_endpoints:
            connects = map_end and any(adjacent(te, map_end) for te in tile_endpoints)
        else:
            # Loop tile - check if any tile cell is adjacent to map end
            connects = map_end and any(adjacent(tc, map_end) for tc in tile_cells)

        if not connects:
            return False

        return True

    def place_map_tile(self, tile_data, gx, gy, rotation):
        """Place a map tile at the given position, extending the map and path.

        The new path cells are inserted at the correct end of game.path so that
        the path remains a continuous ordered sequence. Updates path_graph.end
        so enemies and directional rendering follow the extended path.
        """
        import json
        tile_placement_log = lambda step, data=None: None  # Disable logging for now
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

    def check_spl_level_up(self):
        """Check for SPL level up based on current XP."""
        while self.xp >= self.xp_to_next and self.shop_power_level < self.spl_max:
            self.xp -= self.xp_to_next
            self.shop_power_level += 1
            self.xp_to_next = int(100 * (1.5 ** (self.shop_power_level - 1)))

    def integrity_tick(self):
        """
        Update board integrity by applying drain from latched assimilators.
        Called each frame in wave update loop.
        """
        if hasattr(self, 'board') and self.board:
            self.board.update_walls()