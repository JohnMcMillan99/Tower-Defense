"""
Shared UI layout — single source of truth for draw + click hitboxes.

Top row (over grid width): Shop (5/8) | Map tiles (3/8)
Second row: Tower bench full width
"""
import pygame


class UILayout:
    """Compute screen rects from game grid size. Recreate/refresh after expand."""

    TILE = 40
    SHOP_H = 140
    BENCH_H = 130
    PANEL_RIGHT_W = 180

    # Top-row column split (shop : map tiles)
    TOP_SHOP_RATIO = 5
    TOP_MAP_RATIO = 3

    SHOP_CARD_W = 70
    SHOP_CARD_H = 100
    SHOP_CARD_GAP = 80
    SHOP_PAD_X = 12
    SHOP_PAD_Y = 18

    TOWER_BENCH_SLOTS = 5
    BENCH_CARD_W = 70
    BENCH_CARD_H = 90
    BENCH_CARD_GAP = 80
    BENCH_ORIGIN_X = 15
    BENCH_ORIGIN_Y_OFFSET = 15  # below SHOP_H

    MAP_BENCH_SLOTS = 4  # shared loot bag (tiles + upgrades)
    MAP_CARD_W = 52
    MAP_CARD_H = 72
    MAP_CARD_GAP = 56
    MAP_PAD_X = 8
    MAP_PAD_Y = 18

    UPGRADE_SLOTS = 0  # upgrades live in loot bag now
    UPGRADE_CARD_W = 50
    UPGRADE_CARD_H = 80
    UPGRADE_CARD_GAP = 55

    REROLL_SIZE = 35
    BTN_W = 100
    BTN_H = 26

    def __init__(self, game):
        self.refresh(game)

    def refresh(self, game):
        self.game = game
        self.GRID_W = game.width * self.TILE
        self.WIDTH = self.GRID_W + self.PANEL_RIGHT_W
        self.HEIGHT = self.SHOP_H + self.BENCH_H + game.height * self.TILE
        self.grid_y = self.SHOP_H + self.BENCH_H

        total = self.TOP_SHOP_RATIO + self.TOP_MAP_RATIO
        self.shop_col_w = (self.GRID_W * self.TOP_SHOP_RATIO) // total
        self.map_col_w = self.GRID_W - self.shop_col_w
        self.map_col_x = self.shop_col_w

        # Loot bag (tiles + upgrades) in top-right HUD column
        self.map_bench_x = self.map_col_x + self.MAP_PAD_X
        self.map_bench_y = self.MAP_PAD_Y
        self.MAP_BENCH_X = self.map_bench_x
        self.loot_slots = len(getattr(game, "loot_bag", None) or [None] * self.MAP_BENCH_SLOTS)
        self.tower_slots = len(getattr(game, "bench", None) or [None] * self.TOWER_BENCH_SLOTS)

        # No separate upgrade strip — reclaim bottom-right for inspector
        self.upgrade_bench_y = self.HEIGHT + 200  # off-screen / unused
        self.upgrade_bench_x = self.GRID_W + 10

    # --- Top row regions ---
    def shop_region(self):
        return pygame.Rect(0, 0, self.shop_col_w, self.SHOP_H)

    def map_column_region(self):
        return pygame.Rect(self.map_col_x, 0, self.map_col_w, self.SHOP_H)

    # --- Shop ---
    def shop_card_rect(self, i):
        x = self.SHOP_PAD_X + i * self.SHOP_CARD_GAP
        y = self.SHOP_PAD_Y
        return pygame.Rect(x, y, self.SHOP_CARD_W, self.SHOP_CARD_H)

    def reroll_rect(self):
        # Sit after the 5th shop card, still inside the shop column
        x = self.SHOP_PAD_X + 5 * self.SHOP_CARD_GAP - 10
        # Clamp into shop column if grid is narrow
        max_x = self.shop_col_w - self.REROLL_SIZE - 8
        x = min(x, max_x)
        return pygame.Rect(x, 40, self.REROLL_SIZE, self.REROLL_SIZE)

    # --- Tower bench ---
    def bench_card_rect(self, i):
        x = self.BENCH_ORIGIN_X + i * self.BENCH_CARD_GAP
        y = self.SHOP_H + self.BENCH_ORIGIN_Y_OFFSET
        return pygame.Rect(x, y, self.BENCH_CARD_W, self.BENCH_CARD_H)

    def bench_card_center(self, i):
        r = self.bench_card_rect(i)
        return r.centerx, r.centery

    # --- Loot bag (top-right column; tiles + upgrades) ---
    def loot_card_rect(self, i):
        # 2x2 grid in the map column
        col = i % 2
        row = i // 2
        x = self.map_bench_x + col * self.MAP_CARD_GAP
        y = self.map_bench_y + row * (self.MAP_CARD_H + 6)
        return pygame.Rect(x, y, self.MAP_CARD_W, self.MAP_CARD_H)

    def map_tile_card_rect(self, i):
        """Compat alias — loot bag cards."""
        return self.loot_card_rect(i)

    def map_bench_region(self):
        """Hitbox covering loot cards + rotate controls in the map column."""
        return self.map_column_region()

    def rotate_button_rects(self):
        """Left / right rotate buttons under loot cards."""
        base_y = self.map_bench_y + 2 * (self.MAP_CARD_H + 6) + 2
        # Keep inside SHOP_H
        base_y = min(base_y, self.SHOP_H - 26)
        rot_x = self.map_bench_x
        left = pygame.Rect(rot_x, base_y, 26, 22)
        right = pygame.Rect(rot_x + 34, base_y, 26, 22)
        return left, right

    # --- Upgrade bench (deprecated — empty region so clicks fall through) ---
    def upgrade_card_rect(self, i):
        return pygame.Rect(-100, -100, 1, 1)

    def upgrade_bench_region(self):
        return pygame.Rect(-100, -100, 1, 1)

    # --- Right panel controls ---
    def stats_toggle_rect(self):
        return pygame.Rect(self.GRID_W + 116, 16, 58, 20)

    def panel_control_rects(self, show_spl=False):
        """Play / Next Wave / Auto — must match _draw_right_panel stacking."""
        px = self.GRID_W + 14
        py = 18
        py += 24  # Gold
        py += 24  # Lives
        py += 24  # Wave
        if show_spl:
            py += 24  # SPL
            py += 12 + 4 + 20  # XP bar + text
        py += 8
        play = pygame.Rect(px, py, self.BTN_W, self.BTN_H)
        py += 32
        next_wave = pygame.Rect(px, py, self.BTN_W, self.BTN_H)
        py += 32
        auto = pygame.Rect(px, py, self.BTN_W, self.BTN_H)
        return play, next_wave, auto

    def show_spl(self, game=None):
        g = game or self.game
        return (not getattr(g, "minimal_mode", True)) and hasattr(g, "shop_power_level")

    def round_guide_rect(self, show_spl=None):
        """Scout Round Guide strip below Play/Next/Auto."""
        if show_spl is None:
            show_spl = self.show_spl()
        _, _, auto = self.panel_control_rects(show_spl=show_spl)
        top = auto.bottom + 10
        return pygame.Rect(self.GRID_W + 8, top, 164, 132)

    # --- Inspector (single panel for tower / enemy / stats) ---
    def inspector_rect(self):
        bottom_margin = 16  # upgrade strip removed
        guide = self.round_guide_rect()
        top = guide.bottom + 6
        return pygame.Rect(
            self.GRID_W + 8,
            top,
            164,
            max(80, self.HEIGHT - top - bottom_margin),
        )

    def inspector_tab_rects(self):
        """Tower / Enemy / Stats tab hitboxes along the top of the inspector."""
        outer = self.inspector_rect()
        tab_w = outer.w // 3
        names = ("tower", "enemy", "stats")
        tabs = {}
        for i, name in enumerate(names):
            x = outer.x + i * tab_w
            w = outer.right - x if i == len(names) - 1 else tab_w
            tabs[name] = pygame.Rect(x, outer.y, w, 22)
        return tabs

    def inspector_content_rect(self):
        outer = self.inspector_rect()
        return pygame.Rect(outer.x + 4, outer.y + 26, outer.w - 8, outer.h - 56)

    def inspector_close_rect(self):
        outer = self.inspector_rect()
        return pygame.Rect(outer.x + 24, outer.bottom - 28, outer.w - 48, 24)

    def inspector_sell_close_rects(self):
        """Sell / Close for tower tab (bottom of content area)."""
        content = self.inspector_content_rect()
        y = content.bottom - 28
        sell = pygame.Rect(content.x, y, 72, 24)
        close = pygame.Rect(content.right - 72, y, 72, 24)
        return sell, close

    def inspector_direction_rects(self):
        """N/E/S/W aim buttons for line towers in tower inspector."""
        content = self.inspector_content_rect()
        y = content.y + 118
        rects = []
        for d in range(4):
            rects.append(pygame.Rect(content.x + d * 38, y, 32, 20))
        return rects
