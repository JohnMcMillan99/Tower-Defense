import random
from models.tower import Tower
from data.units import UNIT_TYPES
from data.tiles import get_tile_types
from data.upgrades import UPGRADE_DEFS
from config import REWARD_CONFIG, ECONOMY_CONFIG, BENCH_CONFIG, play_rules


def _is_tile_slot(item):
    return isinstance(item, dict) and "name" in item and "width" in item


def _is_upgrade_slot(item):
    return isinstance(item, str) and item in UPGRADE_DEFS


class EconomyManager:
    def __init__(self, game):
        self.game = game

    def _tower_bench_size(self):
        return len(self.game.bench)

    def _loot_bag(self):
        return getattr(self.game, "loot_bag", None) or []

    def _rules(self):
        pause = getattr(self.game, "paused", False) is True
        return play_rules(self.game, pause_open=pause)

    def _bind_tower(self, tower):
        if tower is not None:
            tower.game = self.game
        return tower

    def generate_shop(self, clear_existing=False):
        """Fill shop with tower offers. If clear_existing, replace all 5 slots."""
        if clear_existing:
            self.game.shop = [None] * 5
        for i in range(5):
            if self.game.shop[i] is None:
                typ = random.choice([u["name"] for u in UNIT_TYPES])
                cost = next(u["base_cost"] for u in UNIT_TYPES if u["name"] == typ)
                self.game.shop[i] = {"type": typ, "cost": cost}

    def move_to_bench(self, shop_idx):
        if not self._rules().shop:
            return False
        if shop_idx < 0 or shop_idx >= 5 or self.game.shop[shop_idx] is None:
            return False
        card = self.game.shop[shop_idx]
        if self.game.gold < card["cost"]:
            return False

        tower = self._bind_tower(Tower(0, 0, card["type"]))
        tower.gold_invested = card["cost"]
        for i in range(self._tower_bench_size()):
            if self.game.bench[i] is None:
                self.game.bench[i] = tower
                self.game.gold -= card["cost"]
                self.game.shop[shop_idx] = None
                self.game.selected_tower = None
                self.game.merge_tower_1 = None
                self.game.merge_tower_2 = None
                self.game.merge_preview = None
                self.game.egrem_preview = False
                self.game.incompatible_preview = False
                self.reset_egrem_consecutive()
                return True
        return False

    def reroll_shop(self):
        if not self._rules().shop:
            return False
        if self.game.gold < self.game.reroll_cost:
            return False
        self.game.gold -= self.game.reroll_cost
        self.generate_shop(clear_existing=True)
        return True

    def _pick_random_tile(self):
        """Pick a path tile for egrem drops, weighted by SPL when available."""
        minimal_mode = getattr(self.game, "minimal_mode", False)
        available = get_tile_types(minimal_mode)
        if not available:
            return None
        if not minimal_mode and hasattr(self.game, "shop_power_level"):
            unlocked = [t for t in available if t.get("unlock_level", 1) <= self.game.shop_power_level]
            pool = unlocked or [t for t in available if t.get("unlock_level", 1) == 1] or available
            weights = [1.0 + (t.get("unlock_level", 1) - 1) * 0.5 for t in pool]
            return random.choices(pool, weights=weights, k=1)[0].copy()
        return random.choice(available).copy()

    def try_add_loot(self, item):
        """Add tile dict or upgrade id to first empty loot_bag slot."""
        bag = self._loot_bag()
        if item is None or bag is None:
            return False
        for i in range(len(bag)):
            if bag[i] is None:
                bag[i] = item
                return True
        return False

    def try_add_tile_to_bench(self, tile_data=None):
        """Add a path tile to the shared loot bag. Returns True if placed."""
        tile = tile_data if tile_data is not None else self._pick_random_tile()
        if tile is None:
            return False
        return self.try_add_loot(tile)

    def try_grant_egrem_tile_drop(self):
        """Roll egrem kill → path tile drop into loot bag."""
        chance = REWARD_CONFIG.get("egrem_tile_drop_chance", 0.28)
        if random.random() >= chance:
            return False
        if self.try_add_tile_to_bench():
            self._set_reward_toast("Path tile → loot bag")
            return True
        self._set_reward_toast("Loot bag full — tile lost")
        return False

    def _pick_upgrade_reward(self, prefer_wildcard=False):
        synergy = [k for k in UPGRADE_DEFS if not k.startswith("wild")]
        wildcard = [k for k in UPGRADE_DEFS if k.startswith("wild")]
        if prefer_wildcard and wildcard and random.random() < REWARD_CONFIG.get("boss_prefer_wildcard_chance", 0.55):
            return random.choice(wildcard)
        pool = synergy + wildcard
        return random.choice(pool) if pool else None

    def try_add_upgrade_to_bench(self, upgrade_id):
        """Add an upgrade id to the shared loot bag."""
        if upgrade_id is None or upgrade_id not in UPGRADE_DEFS:
            return False
        return self.try_add_loot(upgrade_id)

    def grant_wave_upgrade_rewards(self, wave_num):
        """Grant upgrade loot for mini-boss / boss milestone waves into loot bag."""
        mini_iv = REWARD_CONFIG.get("mini_boss_wave_interval", 5)
        boss_iv = REWARD_CONFIG.get("boss_wave_interval", 20)
        if wave_num <= 0:
            return 0

        is_boss = wave_num % boss_iv == 0
        is_mini = (not is_boss) and wave_num % mini_iv == 0
        if not is_boss and not is_mini:
            return 0

        count = REWARD_CONFIG.get("boss_upgrade_count", 1) if is_boss else REWARD_CONFIG.get("mini_boss_upgrade_count", 1)
        granted = 0
        for _ in range(count):
            uid = self._pick_upgrade_reward(prefer_wildcard=is_boss)
            if self.try_add_upgrade_to_bench(uid):
                granted += 1

        if granted:
            label = "Boss" if is_boss else "Mini-boss"
            self._set_reward_toast(f"{label} loot: +{granted} upgrade{'s' if granted != 1 else ''}")
        elif count:
            self._set_reward_toast("Loot bag full — upgrade lost")
        return granted

    def _set_reward_toast(self, text, frames=240):
        """Show a short HUD toast (drawn preferentially over wave bonus)."""
        frame = getattr(self.game, "current_frame", 0)
        self.game.reward_toast_text = text
        self.game.reward_toast_until = frame + frames

    def clear_loot_selection(self):
        self.game.selected_loot = None

    def select_loot(self, idx):
        """Select a loot_bag slot (tile or upgrade)."""
        bag = self._loot_bag()
        if idx < 0 or idx >= len(bag) or bag[idx] is None:
            return False
        item = bag[idx]
        if self.game.selected_loot == idx:
            self.clear_loot_selection()
            return True
        if _is_tile_slot(item) or _is_upgrade_slot(item):
            self.game.selected_loot = idx
            if _is_tile_slot(item):
                self.game.selected_tile_rotation = 0
            return True
        self.clear_loot_selection()
        return False

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
        if not self._rules().merge:
            return False
        if bench_idx < 0 or bench_idx >= self._tower_bench_size() or self.game.bench[bench_idx] is None:
            return False

        # Clear stale selection: indices can point to empty slots after merge/egrem
        if self.game.merge_tower_1 is not None and self.game.bench[self.game.merge_tower_1] is None:
            self.game.merge_tower_1 = self.game.merge_tower_2 = None
            self.game.merge_preview = None
            self.game.egrem_preview = False
            self.game.incompatible_preview = False
            self.game.selected_tower = None
        if self.game.merge_tower_2 is not None and self.game.bench[self.game.merge_tower_2] is None:
            self.game.merge_tower_2 = None
            self.game.merge_preview = None
            self.game.egrem_preview = False

        if self.game.merge_tower_1 is None:
            self.game.merge_tower_1 = bench_idx
            self.game.selected_tower = bench_idx  # Set for placement preview
            self.game.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        # Clicking an already-selected card deselects it
        if bench_idx == self.game.merge_tower_1:
            self.game.merge_tower_1 = None
            self.game.merge_tower_2 = None
            self.game.selected_tower = None
            self.game.merge_preview = None
            self.game.egrem_preview = False
            self.game.incompatible_preview = False
            self.game.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        if self.game.merge_tower_2 is not None and bench_idx == self.game.merge_tower_2:
            self.game.merge_tower_2 = None
            self.game.merge_preview = None
            self.game.egrem_preview = False
            self.game.incompatible_preview = False
            self.game.current_merge_cost = 0
            self.reset_egrem_consecutive()
            return True
        t1 = self.game.bench[self.game.merge_tower_1]
        t2 = self.game.bench[bench_idx]
        self.game.merge_tower_2 = bench_idx
        tier1 = t1.get_merge_tier()
        tier2 = t2.get_merge_tier()
        self.game.current_merge_cost = (tier1 * 10) + (tier2 * 10)
        if Tower.can_merge(t1, t2):
            self.game.merge_preview = Tower.merge_towers(t1, t2)
            self.game.egrem_preview = False
            self.reset_egrem_consecutive()
            return True
        if tier1 != tier2:
            return self._try_egrem(frame)
        # Same tier but no hybrid match - show "Incompatible" for ~2 seconds
        self.game.incompatible_preview = True
        self.game.incompatible_show_until = frame + 120
        self.game.merge_preview = None
        self.game.egrem_preview = False
        return True

    def _try_egrem(self, frame):
        """Preview egrem (wrong-tier merge). Gold is charged only on confirm."""
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
        base_cost = max(5, base_cost)
        cost = int(base_cost * 1.3)
        self.game.current_merge_cost = cost
        if self.game.gold < cost:
            self.game.merge_tower_2 = None
            self.game.egrem_preview = False
            self.game.current_merge_cost = 0
            return False
        self.game.egrem_consecutive += 1
        self.game.egrem_preview = True
        self.game.egrem_flash_until = frame + 120
        self.game.egrem_flash_bench_idx = self.game.merge_tower_2
        self.game.merge_preview = None
        return True

    def _complete_egrem(self):
        """Create Egrem tower and put on bench; remove the two source towers."""
        if not self._rules().merge:
            return False
        if self.game.merge_tower_1 is None or self.game.merge_tower_2 is None:
            return False
        cost = self.game.current_merge_cost
        if self.game.gold < cost:
            return False
        self.game.gold -= cost
        self.game.egrem_total_spent += cost

        idx1, idx2 = sorted([self.game.merge_tower_1, self.game.merge_tower_2])
        t1, t2 = self.game.bench[idx1], self.game.bench[idx2]
        egrem = self._bind_tower(Tower(0, 0, tower_type="Nanite Swarm"))
        egrem.gold_invested = (t1.gold_invested if t1 else 0) + (t2.gold_invested if t2 else 0) + cost

        egrem.egrem_source_types = [t1.base_type, t2.base_type]
        egrem._configure_egrem_spawning()

        self.game.bench[idx1] = None
        self.game.bench[idx2] = None

        for i in range(self._tower_bench_size()):
            if self.game.bench[i] is None:
                self.game.bench[i] = egrem
                break

        self.game.merge_tower_1 = None
        self.game.merge_tower_2 = None
        self.game.merge_preview = None
        self.game.egrem_preview = False
        self.game.incompatible_preview = False
        self.game.selected_tower = None
        self.game.current_merge_cost = 0
        self.game.egrem_consecutive = 0
        self.game.egrem_combo = None
        self.game.egrem_total_spent = 0
        self.game.egrem_flash_until = 0
        self.game.egrem_flash_bench_idx = None
        return True

    def get_incompatible_preview_info(self, frame):
        """Return dict for drawing 'Incompatible' visual, or None. Auto-clears when expired."""
        if not self.game.incompatible_preview or self.game.merge_tower_1 is None or self.game.merge_tower_2 is None:
            return None
        if frame >= self.game.incompatible_show_until:
            self.game.incompatible_preview = False
            self.game.merge_tower_1 = self.game.merge_tower_2 = None
            self.game.selected_tower = None
            return None
        idx1, idx2 = min(self.game.merge_tower_1, self.game.merge_tower_2), max(self.game.merge_tower_1, self.game.merge_tower_2)
        return {
            "idx1": idx1,
            "idx2": idx2,
            "label": "Incompatible",
            "line_color_outer": (80, 0, 0),
            "line_color_inner": (200, 50, 50),
            "line_width_outer": 8,
            "line_width_inner": 5,
            "label_bg_color": (120, 30, 30),
            "label_border_color": (200, 60, 60),
        }

    def confirm_merge(self):
        if not self._rules().merge:
            return False
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
        self._bind_tower(self.game.merge_preview)
        self.game.merge_preview.gold_invested = (t1.gold_invested if t1 else 0) + (t2.gold_invested if t2 else 0) + cost

        self.game.bench[idx1] = None
        self.game.bench[idx2] = None

        for i in range(self._tower_bench_size()):
            if self.game.bench[i] is None:
                self.game.bench[i] = self.game.merge_preview
                break

        self.game.merge_tower_1 = None
        self.game.merge_tower_2 = None
        self.game.merge_preview = None
        self.game.selected_tower = None
        self.game.current_merge_cost = 0
        self.game.egrem_preview = False
        self.game.incompatible_preview = False
        return True

    def cancel_merge(self):
        self.game.merge_tower_1 = self.game.merge_tower_2 = self.game.merge_preview = self.game.selected_tower = None
        self.game.current_merge_cost = 0
        self.game.egrem_preview = False
        self.game.incompatible_preview = False
        self.reset_egrem_consecutive()

    def place_tower(self, gx, gy, bench_idx=None):
        if not self._rules().place_towers:
            return False
        if not (0 <= gx < self.game.width and 0 <= gy < self.game.height):
            return False
        if self.game.grid[gy][gx] != '.':
            return False
        if bench_idx is None or bench_idx >= self._tower_bench_size() or self.game.bench[bench_idx] is None:
            return False
        tower = self.game.bench[bench_idx]
        self._bind_tower(tower)
        tower.x = gx
        tower.y = gy
        self.game.towers.append(tower)
        self.game.grid[gy][gx] = tower.base_type[0]
        self.game.bench[bench_idx] = None
        self.game.selected_tower = None
        self.game.merge_tower_1 = self.game.merge_tower_2 = self.game.merge_preview = None
        self.game.egrem_preview = False
        self.game.incompatible_preview = False
        self.reset_egrem_consecutive()
        return True

    def sell_from_bench(self, idx):
        if idx < 0 or idx >= self._tower_bench_size() or self.game.bench[idx] is None:
            return
        t = self.game.bench.pop(idx)
        value = int((2 + t.get_merge_tier() * 2) * ECONOMY_CONFIG.get("sell_bench_mult", 0.5))
        self.game.gold += max(1, value)
        self.game.bench.insert(idx, None)
        self.game.selected_tower = self.game.merge_tower_1 = self.game.merge_tower_2 = self.game.merge_preview = None
        self.game.egrem_preview = False
        self.game.incompatible_preview = False
        self.reset_egrem_consecutive()

    def sell_tower_from_grid(self, gx, gy):
        """Remove tower at (gx, gy) and refund a fraction of gold_invested."""
        for t in self.game.towers[:]:
            if t.x == gx and t.y == gy:
                refund = int(t.gold_invested * ECONOMY_CONFIG.get("sell_grid_refund", 0.45))
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
            if uid in already:
                continue
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

    def can_apply_upgrade(self, tower, upgrade_id):
        """True if this firmware belongs on this tower (wildcard = any)."""
        if tower is None or upgrade_id not in UPGRADE_DEFS:
            return False
        if upgrade_id in tower.upgrades:
            return False
        if len(tower.upgrades) >= tower.UPGRADE_CAPACITY:
            return False
        u = UPGRADE_DEFS[upgrade_id]
        tags = set(u.get("traits") or [])
        if "wildcard" in tags:
            return True
        needed = (tags | set(u.get("synergizes_with") or [])) - {"wildcard"}
        tower_traits = set(tower.get_traits())
        return bool(needed and needed & tower_traits)

    def apply_upgrade(self, tower, upgrade_id):
        if not self.can_apply_upgrade(tower, upgrade_id):
            return False
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
        if not self.can_apply_upgrade(tower, upgrade_id):
            return False
        bag = self._loot_bag()
        if bench_idx < 0 or bench_idx >= len(bag) or bag[bench_idx] != upgrade_id:
            return False

        tower.upgrades.append(upgrade_id)
        tower._calculate_stats()
        bag[bench_idx] = None
        if getattr(self.game, "selected_loot", None) == bench_idx:
            self.clear_loot_selection()
        return True
