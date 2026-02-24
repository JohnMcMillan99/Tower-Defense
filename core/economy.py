import random
from models.tower import Tower
from data.units import UNIT_TYPES
from data.tiles import TILE_TYPES
from data.upgrades import UPGRADE_DEFS


class EconomyManager:
    def __init__(self, game):
        self.game = game

    def generate_shop(self):
        for i in range(5):
            if self.game.shop[i] is None:
                if self.game.shop_mode == "towers":
                    typ = random.choice([u["name"] for u in UNIT_TYPES])
                    cost = next(u["base_cost"] for u in UNIT_TYPES if u["name"] == typ)
                    self.game.shop[i] = {"type": typ, "cost": cost}
                elif self.game.shop_mode == "tiles":
                    tile = random.choice(TILE_TYPES)
                    self.game.shop[i] = {"type": tile["name"], "cost": tile["base_cost"], "tile_data": tile}
                elif self.game.shop_mode == "upgrades":
                    upgrade_id = random.choice(list(UPGRADE_DEFS.keys()))
                    u = UPGRADE_DEFS[upgrade_id]
                    self.game.shop[i] = {"type": upgrade_id, "cost": u["cost"], "name": u["name"], "desc": u["desc"]}

    def move_to_bench(self, shop_idx):
        if shop_idx < 0 or shop_idx >= 5 or self.game.shop[shop_idx] is None:
            return False
        card = self.game.shop[shop_idx]
        if self.game.gold < card["cost"]:
            return False

        if self.game.shop_mode == "tiles":
            # Move tile to map tile bench
            tile_data = card["tile_data"]
            for i in range(3):  # Updated for larger bench
                if self.game.map_tile_bench[i] is None:
                    self.game.map_tile_bench[i] = tile_data.copy()
                    self.game.gold -= card["cost"]
                    self.game.shop[shop_idx] = None
                    return True
            return False
        elif self.game.shop_mode == "upgrades":
            # Move upgrade to upgrade bench
            upgrade_id = card["type"]
            for i in range(3):
                if self.game.upgrade_bench[i] is None:
                    self.game.upgrade_bench[i] = upgrade_id
                    self.game.gold -= card["cost"]
                    self.game.shop[shop_idx] = None
                    return True
            return False  # Bench full
        else:
            # Move tower to regular bench
            tower = Tower(0, 0, card["type"])
            tower.gold_invested = card["cost"]
            for i in range(10):
                if self.game.bench[i] is None:
                    self.game.bench[i] = tower
                    self.game.gold -= card["cost"]
                    self.game.shop[shop_idx] = None
                    self.game.selected_tower = None
                    self.game.merge_tower_1 = None
                    self.game.merge_tower_2 = None
                    self.game.merge_preview = None
                    self.game.egrem_preview = False
                    self.reset_egrem_consecutive()
                    return True
            return False

    def reroll_shop(self):
        if self.game.gold < self.game.reroll_cost:
            return False
        self.game.gold -= self.game.reroll_cost
        self.generate_shop()
        return True

    def get_merge_preview_info(self):
        """Return dict with merge preview drawing info, or None if not active."""
        if not (self.game.merge_preview and self.game.merge_tower_1 is not None and self.game.merge_tower_2 is not None):
            return None
        idx1, idx2 = min(self.game.merge_tower_1, self.game.merge_tower_2), max(self.game.merge_tower_1, self.game.merge_tower_2)
        return {
            "idx1": idx1,
            "idx2": idx2,
            "is_egrem": False,
            "label": "Merge",
            "cost": self.game.current_merge_cost,
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
        if not (self.game.egrem_preview and self.game.merge_tower_1 is not None and self.game.merge_tower_2 is not None):
            return None
        idx1, idx2 = min(self.game.merge_tower_1, self.game.merge_tower_2), max(self.game.merge_tower_1, self.game.merge_tower_2)
        return {
            "idx1": idx1,
            "idx2": idx2,
            "is_egrem": True,
            "label": "egrem",
            "cost": self.game.current_merge_cost,
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
        self.game.egrem_consecutive = 0

    def select_for_merge(self, bench_idx, frame=0):
        if bench_idx < 0 or bench_idx >= 10 or self.game.bench[bench_idx] is None:
            return False
        if self.game.merge_tower_1 is None:
            self.game.merge_tower_1 = bench_idx
            self.game.selected_tower = bench_idx  # Set for placement preview
            self.game.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        # Clicking an already-selected card deselects it
        if bench_idx == self.game.merge_tower_1:
            self.game.merge_tower_1 = None
            self.game.selected_tower = None
            self.game.merge_preview = None
            self.game.egrem_preview = False
            self.game.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        if self.game.merge_tower_2 is not None and bench_idx == self.game.merge_tower_2:
            self.game.merge_tower_2 = None
            self.game.merge_preview = None
            self.game.egrem_preview = False
            self.game.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        t1 = self.game.bench[self.game.merge_tower_1]
        t2 = self.game.bench[bench_idx]
        same_tier = t1.get_merge_tier() == t2.get_merge_tier()
        # Third card: replace second selection (keep first), then same-tier → preview, different → egrem
        self.game.merge_tower_2 = bench_idx
        tier1 = t1.get_merge_tier()
        tier2 = t2.get_merge_tier()
        self.game.current_merge_cost = (tier1 * 10) + (tier2 * 10)
        if same_tier:
            self.game.merge_preview = Tower.merge_towers(t1, t2)
            self.game.egrem_preview = False
            self.reset_egrem_consecutive()
            return True
        # Different tier: trigger egrem attempt (cost, flash, maybe create egrem tower)
        return self._try_egrem(frame)

    def _try_egrem(self, frame):
        """Attempt egrem (wrong-tier merge). Cost (tier1*10 + tier2*10) * 1.25; shows preview for confirmation."""
        if self.game.merge_tower_1 is None or self.game.merge_tower_2 is None:
            return False
        t1 = self.game.bench[self.game.merge_tower_1]
        t2 = self.game.bench[self.game.merge_tower_2]
        if t1 is None or t2 is None:
            return False
        combo = tuple(sorted([t1.base_type, t2.base_type]))
        if combo != self.game.egrem_combo:
            self.game.egrem_combo = combo
            self.game.egrem_total_spent = 0
        tier1 = t1.get_merge_tier()
        tier2 = t2.get_merge_tier()
        base_cost = (tier1 * 10) + (tier2 * 10)
        # Ensure minimum cost of 5 even for T0+T0
        base_cost = max(5, base_cost)
        cost = int(base_cost * 1.3)
        self.game.current_merge_cost = cost  # Display the egrem cost
        if self.game.gold < cost:
            self.game.merge_tower_2 = None
            self.game.egrem_preview = False
            self.game.current_merge_cost = 0
            return False
        self.game.gold -= cost
        self.game.egrem_consecutive += 1
        self.game.egrem_total_spent += cost
        self.game.egrem_preview = True
        self.game.egrem_flash_until = frame + 120  # 2 seconds
        self.game.egrem_flash_bench_idx = self.game.merge_tower_2
        self.game.merge_preview = None
        return True

    def _complete_egrem(self):
        """Create Egrem tower and put on bench; remove the two source towers."""
        idx1, idx2 = sorted([self.game.merge_tower_1, self.game.merge_tower_2])
        t1, t2 = self.game.bench[idx1], self.game.bench[idx2]
        egrem = Tower(0, 0, tower_type="Nanite Swarm")
        egrem.gold_invested = (t1.gold_invested if t1 else 0) + (t2.gold_invested if t2 else 0)

        # Configure egrem spawning based on source towers
        egrem.egrem_source_types = [t1.base_type, t2.base_type]
        egrem._configure_egrem_spawning()

        # Remove both source towers from bench
        self.game.bench[idx1] = None
        self.game.bench[idx2] = None

        # Place egrem tower in first unoccupied slot
        for i in range(10):
            if self.game.bench[i] is None:
                self.game.bench[i] = egrem
                break

        # Deselect all cards after egrem
        self.game.merge_tower_1 = None
        self.game.merge_tower_2 = None
        self.game.merge_preview = None
        self.game.egrem_preview = False
        self.game.selected_tower = None
        self.game.current_merge_cost = 0
        self.game.egrem_consecutive = 0
        self.game.egrem_combo = None
        self.game.egrem_total_spent = 0
        self.game.egrem_flash_until = 0
        self.game.egrem_flash_bench_idx = None

    def confirm_merge(self):
        if None in (self.game.merge_tower_1, self.game.merge_tower_2, self.game.merge_preview):
            return False
        idx1, idx2 = sorted([self.game.merge_tower_1, self.game.merge_tower_2])
        t1, t2 = self.game.bench[idx1], self.game.bench[idx2]
        tier1 = t1.get_merge_tier() if t1 else 0
        tier2 = t2.get_merge_tier() if t2 else 0
        cost = (tier1 * 10) + (tier2 * 10)
        if self.game.gold < cost:
            return False
        self.game.gold -= cost
        self.reset_egrem_consecutive()
        self.game.merge_preview.gold_invested = (t1.gold_invested if t1 else 0) + (t2.gold_invested if t2 else 0) + cost

        # Remove both source towers from bench
        self.game.bench[idx1] = None
        self.game.bench[idx2] = None

        # Place merged tower in first unoccupied slot
        for i in range(10):
            if self.game.bench[i] is None:
                self.game.bench[i] = self.game.merge_preview
                break

        # Deselect all cards after merge
        self.game.merge_tower_1 = None
        self.game.merge_tower_2 = None
        self.game.merge_preview = None
        self.game.selected_tower = None
        self.game.current_merge_cost = 0
        self.game.egrem_preview = False
        return True

    def cancel_merge(self):
        self.game.merge_tower_1 = self.game.merge_tower_2 = self.game.merge_preview = self.game.selected_tower = None
        self.game.current_merge_cost = 0
        self.game.egrem_preview = False
        self.reset_egrem_consecutive()

    def place_tower(self, gx, gy, bench_idx=None):
        if not (0 <= gx < self.game.width and 0 <= gy < self.game.height):
            return False
        if self.game.grid[gy][gx] != '.':
            return False
        if bench_idx is None or bench_idx >= 10 or self.game.bench[bench_idx] is None:
            return False
        tower = self.game.bench[bench_idx]
        tower.x = gx
        tower.y = gy
        self.game.towers.append(tower)
        self.game.grid[gy][gx] = tower.base_type[0]
        self.game.bench[bench_idx] = None
        self.game.selected_tower = None
        self.game.merge_tower_1 = self.game.merge_tower_2 = self.game.merge_preview = None
        self.game.egrem_preview = False
        self.reset_egrem_consecutive()
        return True

    def sell_from_bench(self, idx):
        if idx < 0 or idx >= 10 or self.game.bench[idx] is None:
            return
        t = self.game.bench.pop(idx)
        value = 2 + t.get_merge_tier() * 2   # simple value
        self.game.gold += value
        self.game.bench.insert(idx, None)  # keep order
        self.game.selected_tower = self.game.merge_tower_1 = self.game.merge_tower_2 = self.game.merge_preview = None
        self.game.egrem_preview = False
        self.reset_egrem_consecutive()

    def sell_tower_from_grid(self, gx, gy):
        """Remove tower at (gx, gy) and refund 60% of gold_invested."""
        for t in self.game.towers[:]:
            if t.x == gx and t.y == gy:
                refund = int(t.gold_invested * 0.6)
                self.game.gold += refund
                self.game.towers.remove(t)
                self.game.grid[gy][gx] = '.'
                if self.game.upgrade_dialog_tower is t:
                    self.game.upgrade_dialog_tower = None
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
        if self.game.gold < u["cost"]:
            return False
        self.game.gold -= u["cost"]
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
        if self.game.upgrade_bench[bench_idx] != upgrade_id:
            return False  # Upgrade not in bench slot

        # Apply upgrade to tower
        tower.upgrades.append(upgrade_id)
        tower._calculate_stats()

        # Remove from bench
        self.game.upgrade_bench[bench_idx] = None

        return True