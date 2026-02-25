import pygame
import json
from datetime import datetime
from models.tower import Tower


class Renderer:
    def __init__(self, game):
        self.game = game

        # Layout constants
        self.TILE = 40
        self.SHOP_H = 140
        self.BENCH_H = 130
        self.GRID_W = game.width * self.TILE
        self.PANEL_RIGHT_W = 180
        self.WIDTH = self.GRID_W + self.PANEL_RIGHT_W
        self.HEIGHT = self.SHOP_H + self.BENCH_H + game.height * self.TILE

        # Camera system
        self.camera_x = 0
        self.camera_y = 0
        self.zoom_level = 1.0
        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        # Colors
        self.BLACK = (10, 10, 15)
        self.GRID = (35, 35, 45)
        self.PATH = (180, 100, 60)
        self.ENEMY = (220, 60, 60)
        self.HP_BG = (50, 50, 50)
        self.HP_FILL = (60, 220, 80)
        self.SHOP_BG = (20, 20, 30)
        self.BENCH_BG = (25, 25, 35)
        self.PANEL_BG = (22, 22, 32)
        self.PANEL_BTN = (60, 80, 120)
        self.PANEL_BTN_SEL = (90, 120, 180)
        self.CARD_BG = (40, 40, 55)
        self.CARD_SEL = (100, 150, 255)
        self.CARD_EMP = (30, 30, 40)
        self.TEXT = (220, 220, 220)

        # Fonts
        self.font = pygame.font.SysFont("consolas", 16)
        self.font_s = pygame.font.SysFont("consolas", 12)
        self.font_merge = pygame.font.SysFont("consolas", 20)

        # Tower colors
        self.tower_colors = {
            "Neural Processor": (70, 130, 255),
            "Plasma Capacitor": (100, 255, 100),
            "Thermal Regulator": (220, 120, 60),
            "Signal Router": (200, 100, 255),
            "Quantum Field Gen": (255, 200, 50),
            "Nanite Swarm": (40, 40, 45),
        }

        # Layout positions
        self.grid_y = self.SHOP_H + self.BENCH_H
        self.map_bench_x = 15
        self.map_bench_y = self.HEIGHT - 100

        # Initialize screen
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Borg TD Prototype")

    def world_to_screen(self, wx, wy):
        """Convert world coordinates to screen coordinates."""
        sx = (wx * self.TILE * self.zoom_level) + self.camera_x
        sy = self.grid_y + (wy * self.TILE * self.zoom_level) + self.camera_y
        return sx, sy

    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates."""
        wx = ((sx - self.camera_x) / (self.TILE * self.zoom_level))
        wy = ((sy - self.grid_y - self.camera_y) / (self.TILE * self.zoom_level))
        return wx, wy

    def update_dimensions(self):
        """Update dimensions when grid expands."""
        self.GRID_W = self.game.width * self.TILE
        self.WIDTH = self.GRID_W + self.PANEL_RIGHT_W
        self.HEIGHT = self.SHOP_H + self.BENCH_H + self.game.height * self.TILE
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        self.map_bench_y = self.HEIGHT - 100

    def draw(self, frame):
        """Main drawing function."""
        self.screen.fill(self.BLACK)

        self._draw_shop()
        self._draw_bench(frame)
        self._draw_map_tile_bench()
        self._draw_upgrade_bench()
        self._draw_rotate_button()
        self._draw_merge_preview()
        self._draw_right_panel()
        self._draw_upgrade_dialog()
        self._draw_enemy_stats()
        self._draw_grid()
        self._draw_range_preview()
        self._draw_tile_preview()
        self._draw_attack_beams(frame)
        self._draw_towers()
        self._draw_enemies()
        self._draw_wave_bonus(frame)
        self._draw_game_over()
        self._draw_camera_info()
        self._draw_version_info()

    def _draw_version_info(self):
        """Draw version/timestamp info in top right corner."""
        # Get current timestamp
        now = datetime.now()
        version_text = now.strftime("v%Y-%m-%d %H:%M")

        # Render text
        text_surface = self.font_s.render(version_text, True, self.TEXT)
        text_rect = text_surface.get_rect()

        # Position in top right corner
        text_rect.topright = (self.WIDTH - 5, 5)

        # Draw text
        self.screen.blit(text_surface, text_rect)

    def _draw_shop(self):
        """Draw the shop section."""
        pygame.draw.rect(self.screen, self.SHOP_BG, (0, 0, self.GRID_W, self.SHOP_H))
        pygame.draw.line(self.screen, self.GRID, (0, self.SHOP_H), (self.GRID_W, self.SHOP_H), 2)

        for i in range(5):
            x = 15 + i * 80
            y = 15
            card = self.game.shop[i]
            col = self.CARD_EMP if card is None else self.CARD_BG
            pygame.draw.rect(self.screen, col, (x, y, 70, 100))
            pygame.draw.rect(self.screen, self.TEXT, (x, y, 70, 100), 1 if card else 2)
            if card:
                if "tile_data" in card:
                    tile = card["tile_data"]
                    self.screen.blit(self.font_s.render(tile["name"][:10], True, self.TEXT), (x+5, y+5))
                    self.screen.blit(self.font_s.render(f"{tile['width']}x{tile['height']}", True, self.TEXT), (x+5, y+20))
                    # Draw mini path preview
                    path_grid = tile["path_grid"]
                    cell_size = 8
                    start_x = x + 35 - (len(path_grid[0]) * cell_size) // 2
                    start_y = y + 35
                    for py in range(len(path_grid)):
                        for px in range(len(path_grid[py])):
                            if path_grid[py][px]:
                                pygame.draw.rect(self.screen, self.PATH, (start_x + px*cell_size, start_y + py*cell_size, cell_size, cell_size))
                    self.screen.blit(self.font_s.render(f"${card['cost']}", True, self.TEXT), (x+5, y+75))
                elif "name" in card:
                    # Upgrade card
                    name = card["name"]
                    desc = card["desc"]
                    self.screen.blit(self.font_s.render(name[:10], True, self.TEXT), (x+5, y+5))
                    # Show short description
                    self.screen.blit(self.font_s.render(desc[:12], True, (180, 180, 200)), (x+5, y+20))
                    self.screen.blit(self.font_s.render(desc[12:24] if len(desc) > 12 else "", True, (180, 180, 200)), (x+5, y+35))
                    self.screen.blit(self.font_s.render(f"${card['cost']}", True, self.TEXT), (x+5, y+75))
                else:
                    # Tower card
                    self.screen.blit(self.font_s.render(card["type"][:8], True, self.TEXT), (x+5, y+10))
                    self.screen.blit(self.font_s.render(f"${card['cost']}", True, self.TEXT), (x+5, y+75))

        # Shop mode toggle
        tx = self.map_bench_x + 3*80 + 20
        ty = self.map_bench_y
        pygame.draw.rect(self.screen, self.CARD_BG, (tx, ty, 35, 35))
        pygame.draw.rect(self.screen, self.TEXT, (tx, ty, 35, 35), 1)
        mode_char = "T" if self.game.shop_mode == "towers" else ("M" if self.game.shop_mode == "tiles" else "U")
        self.screen.blit(self.font_s.render(mode_char, True, self.TEXT), (tx+10, ty+10))

        # Reroll
        rx = 15 + 400
        pygame.draw.rect(self.screen, self.CARD_BG, (rx, 65, 35, 35))
        pygame.draw.rect(self.screen, self.TEXT, (rx, 65, 35, 35), 1)
        self.screen.blit(self.font_s.render("R", True, self.TEXT), (rx+10, 70))

    def _draw_bench(self, frame):
        """Draw the bench section."""
        pygame.draw.rect(self.screen, self.BENCH_BG, (0, self.SHOP_H, self.GRID_W, self.BENCH_H))
        pygame.draw.line(self.screen, self.GRID, (0, self.SHOP_H + self.BENCH_H), (self.GRID_W, self.SHOP_H + self.BENCH_H), 2)
        self.screen.blit(self.font_s.render("BENCH", True, self.TEXT), (15, self.SHOP_H + 5))

        for i in range(10):
            x = 15 + i * 68
            y = self.SHOP_H + 15
            col = self.CARD_EMP if self.game.bench[i] is None else self.CARD_BG
            if i in (self.game.merge_tower_1, self.game.merge_tower_2):
                col = self.CARD_SEL
            pygame.draw.rect(self.screen, col, (x, y, 60, 90))
            pygame.draw.rect(self.screen, self.TEXT, (x, y, 60, 90), 2)
            if self.game.bench[i]:
                t = self.game.bench[i]
                if t.base_type == "Nanite Swarm":
                    pygame.draw.rect(self.screen, (28, 28, 35), (x, y, 60, 90))
                    pygame.draw.rect(self.screen, (80, 255, 80), (x, y, 60, 90), 2)
                    self.screen.blit(self.font_s.render("Egrem", True, (80, 255, 100)), (x+5, y+5))
                    self.screen.blit(self.font_s.render("spawn", True, (255, 80, 80)), (x+5, y+28))
                    self.screen.blit(self.font_s.render(f"T{t.get_merge_tier()}", True, self.TEXT), (x+5, y+50))
                else:
                    display_name = t.BASE_TYPES[t.base_type]["display"]
                    self.screen.blit(self.font_s.render(display_name[:6], True, self.TEXT), (x+5, y+5))
                    self.screen.blit(self.font_s.render(f"D:{t.dmg}", True, self.TEXT), (x+5, y+30))
                    self.screen.blit(self.font_s.render(f"T{t.get_merge_tier()}", True, self.TEXT), (x+5, y+50))

        # Flash overlay for egrem
        if self.game.egrem_flash_bench_idx is not None and frame < self.game.egrem_flash_until:
            flash_alpha = 80 + 60 * (1 - (self.game.egrem_flash_until - frame) / 120)
            i = self.game.egrem_flash_bench_idx
            x = 15 + i * 68
            y = self.SHOP_H + 15
            s = pygame.Surface((60, 90))
            s.set_alpha(min(140, int(flash_alpha)))
            s.fill((255, 80, 80))
            self.screen.blit(s, (x, y))

    def _draw_map_tile_bench(self):
        """Draw the map tile bench."""
        pygame.draw.rect(self.screen, self.SHOP_BG, (0, self.map_bench_y - 10, 280, 100))
        pygame.draw.line(self.screen, self.GRID, (0, self.map_bench_y - 10), (280, self.map_bench_y - 10), 2)
        self.screen.blit(self.font_s.render("MAP TILES", True, self.TEXT), (15, self.map_bench_y - 5))

        for i in range(3):
            x = self.map_bench_x + i * 80
            y = self.map_bench_y
            col = self.CARD_EMP if self.game.map_tile_bench[i] is None else self.CARD_BG
            if i == self.game.selected_map_tile:
                col = self.CARD_SEL
            pygame.draw.rect(self.screen, col, (x, y, 70, 80))
            pygame.draw.rect(self.screen, self.TEXT, (x, y, 70, 80), 2)
            if self.game.map_tile_bench[i]:
                tile = self.game.map_tile_bench[i]
                self.screen.blit(self.font_s.render(tile["name"][:8], True, self.TEXT), (x+5, y+10))
                self.screen.blit(self.font_s.render(f"{tile['width']}x{tile['height']}", True, self.TEXT), (x+5, y+50))

    def _draw_upgrade_bench(self):
        """Draw the upgrade bench."""
        upgrade_bench_x = self.GRID_W + 10
        upgrade_bench_y = self.HEIGHT - 100
        pygame.draw.rect(self.screen, self.SHOP_BG, (self.GRID_W, upgrade_bench_y - 10, self.PANEL_RIGHT_W, 100))
        pygame.draw.line(self.screen, self.GRID, (self.GRID_W, upgrade_bench_y - 10), (self.WIDTH, upgrade_bench_y - 10), 2)
        self.screen.blit(self.font_s.render("UPGRADES", True, self.TEXT), (self.GRID_W + 15, upgrade_bench_y - 5))

        for i in range(3):
            x = upgrade_bench_x + i * 55
            y = upgrade_bench_y
            col = self.CARD_EMP if self.game.upgrade_bench[i] is None else self.CARD_BG
            if i == self.game.selected_upgrade:
                col = self.CARD_SEL
            pygame.draw.rect(self.screen, col, (x, y, 50, 80))
            pygame.draw.rect(self.screen, self.TEXT, (x, y, 50, 80), 2)
            if self.game.upgrade_bench[i]:
                upgrade_id = self.game.upgrade_bench[i]
                from data.upgrades import UPGRADE_DEFS
                u = UPGRADE_DEFS.get(upgrade_id, {})
                name = u.get("name", upgrade_id)
                if len(name) > 8:
                    name = name[:6] + ".."
                self.screen.blit(self.font_s.render(name, True, self.TEXT), (x+3, y+5))
                self.screen.blit(self.font_s.render(f"${u.get('cost', 0)}", True, self.TEXT), (x+3, y+60))

        hint_text = "Click or press 1-3 to select"
        self.screen.blit(self.font_s.render(hint_text, True, (160, 160, 180)), (self.GRID_W + 15, upgrade_bench_y + 85))

    def _draw_rotate_button(self):
        """Draw the rotate button for selected map tiles."""
        if self.game.selected_map_tile is not None:
            rot_x = self.map_bench_x + 2*80 + 10
            rot_y = self.map_bench_y + 5

            # Left rotate button
            pygame.draw.rect(self.screen, self.PANEL_BTN, (rot_x, rot_y, 26, 26))
            pygame.draw.rect(self.screen, self.TEXT, (rot_x, rot_y, 26, 26), 1)
            self.screen.blit(self.font_s.render("<", True, self.TEXT), (rot_x + 8, rot_y + 6))

            # Right rotate button
            pygame.draw.rect(self.screen, self.PANEL_BTN, (rot_x + 34, rot_y, 26, 26))
            pygame.draw.rect(self.screen, self.TEXT, (rot_x + 34, rot_y, 26, 26), 1)
            self.screen.blit(self.font_s.render(">", True, self.TEXT), (rot_x + 42, rot_y + 6))

            # Degree label
            deg_lbl = self.font_s.render(f"{self.game.selected_tile_rotation * 90}\u00b0", True, self.TEXT)
            self.screen.blit(deg_lbl, (rot_x + 27 - deg_lbl.get_width() // 2, rot_y + 7))

            # Step indicator
            step_lbl = self.font_s.render(f"{self.game.selected_tile_rotation + 1}/4", True, (160, 160, 180))
            self.screen.blit(step_lbl, (rot_x + 30 - step_lbl.get_width() // 2, rot_y + 30))

            # Hint text
            hint_lbl = self.font_s.render("A/D or </> rotate", True, (120, 120, 140))
            self.screen.blit(hint_lbl, (rot_x - 10, rot_y + 46))

    def _draw_merge_preview(self):
        """Draw merge/egrem preview lines and labels."""
        for preview_info in [self.game.economy.get_merge_preview_info(), self.game.economy.get_egrem_preview_info()]:
            if preview_info is None:
                continue

            idx1, idx2 = preview_info["idx1"], preview_info["idx2"]
            cx1 = int(15 + idx1 * 68 + 30)
            cx2 = int(15 + idx2 * 68 + 30)
            cy = int(self.SHOP_H + 15 + 45)

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

            # Draw lines
            for i in range(len(pts) - 1):
                pygame.draw.line(self.screen, preview_info["line_color_outer"], pts[i], pts[i + 1], preview_info["line_width_outer"])
                c = preview_info["line_color_inner_1"] if preview_info["is_egrem"] and "line_color_inner_1" in preview_info and i % 2 == 0 else preview_info["line_color_inner"]
                pygame.draw.line(self.screen, c, pts[i], pts[i + 1], preview_info["line_width_inner"])

            # Draw label
            mid_x, mid_y = (cx1 + cx2) // 2, cy
            label_surf = self.font_merge.render(preview_info["label"], True, (0, 0, 0))
            label_rect = label_surf.get_rect(center=(mid_x, mid_y))
            label_rect.inflate_ip(13, 8)
            pygame.draw.rect(self.screen, preview_info["label_bg_color"], label_rect)
            pygame.draw.rect(self.screen, preview_info["label_border_color"], label_rect, 2)

            # Draw label outline
            for ox, oy in [(-1,-1),(-1,1),(1,-1),(1,1),(0,-1),(0,1),(-1,0),(1,0)]:
                self.screen.blit(self.font_merge.render(preview_info["label"], True, (255, 255, 255)),
                               (label_rect.centerx - label_surf.get_width()//2 + ox, label_rect.centery - label_surf.get_height()//2 + oy))
            self.screen.blit(label_surf, (label_rect.centerx - label_surf.get_width()//2, label_rect.centery - label_surf.get_height()//2))

            # Draw cost
            cost_surf = self.font_s.render(f"${preview_info['cost']}", True, preview_info["cost_color"])
            self.screen.blit(cost_surf, (mid_x - cost_surf.get_width()//2, mid_y + 18))

    def _draw_right_panel(self):
        """Draw the right panel with game stats and controls."""
        pygame.draw.rect(self.screen, self.PANEL_BG, (self.GRID_W, 0, self.PANEL_RIGHT_W, self.SHOP_H + self.BENCH_H))
        pygame.draw.line(self.screen, self.GRID, (self.GRID_W, 0), (self.GRID_W, self.SHOP_H + self.BENCH_H), 2)

        px = self.GRID_W + 14
        self.screen.blit(self.font.render(f"Gold:  {self.game.gold}", True, self.TEXT), (px, 18))
        self.screen.blit(self.font.render(f"Lives: {self.game.lives}", True, self.TEXT), (px, 42))
        self.screen.blit(self.font.render(f"Wave:  {self.game.round_num}", True, self.TEXT), (px, 66))

        # Play/Pause button
        play_rect = pygame.Rect(px, 96, 100, 26)
        col_play = self.PANEL_BTN_SEL if self.game.paused else self.PANEL_BTN
        pygame.draw.rect(self.screen, col_play, play_rect)
        pygame.draw.rect(self.screen, self.TEXT, play_rect, 1)
        self.screen.blit(self.font_s.render("Play" if self.game.paused else "Pause", True, self.TEXT), (px + 28, 100))

        # Next Wave button
        next_rect = pygame.Rect(px, 128, 100, 26)
        pygame.draw.rect(self.screen, self.PANEL_BTN, next_rect)
        pygame.draw.rect(self.screen, self.TEXT, next_rect, 1)
        self.screen.blit(self.font_s.render("Next Wave", True, self.TEXT), (px + 14, 132))

        # Auto toggle button
        auto_rect = pygame.Rect(px, 160, 100, 26)
        col_auto = self.PANEL_BTN_SEL if self.game.auto_mode else self.PANEL_BTN
        pygame.draw.rect(self.screen, col_auto, auto_rect)
        pygame.draw.rect(self.screen, self.TEXT, auto_rect, 1)
        self.screen.blit(self.font_s.render("Auto " + ("ON" if self.game.auto_mode else "OFF"), True, self.TEXT), (px + 18, 164))

    def _draw_upgrade_dialog(self):
        """Draw the upgrade dialog when a tower is selected."""
        if self.game.upgrade_dialog_tower is None:
            return

        t = self.game.upgrade_dialog_tower
        base_height = 280
        upgrade_height = 20 + (len(t.upgrades) * 16) if t.upgrades else 0
        dialog_height = base_height + upgrade_height

        dialog_rect = pygame.Rect(self.GRID_W + 8, 162, 164, dialog_height)
        pygame.draw.rect(self.screen, (35, 35, 50), dialog_rect)
        pygame.draw.rect(self.screen, self.TEXT, dialog_rect, 2)
        self.screen.blit(self.font.render("Upgrade", True, self.TEXT), (self.GRID_W + 14, 168))
        self.screen.blit(self.font_s.render(f"{t.base_type}  D:{t.dmg} R:{t.range}", True, self.TEXT), (self.GRID_W + 14, 184))

        capacity_text = f"Upgrades: {len(t.upgrades)}/{t.UPGRADE_CAPACITY}"
        capacity_color = (180, 180, 200) if len(t.upgrades) < t.UPGRADE_CAPACITY else (255, 150, 150)
        self.screen.blit(self.font_s.render(capacity_text, True, capacity_color), (self.GRID_W + 14, 200))

        self.screen.blit(self.font_s.render("Select upgrade from bench,", True, (160, 160, 180)), (self.GRID_W + 14, 220))
        self.screen.blit(self.font_s.render("then click tower to apply", True, (160, 160, 180)), (self.GRID_W + 14, 235))

        button_y = 266 + upgrade_height
        pygame.draw.rect(self.screen, (120, 80, 80), (self.GRID_W + 10, button_y, 75, 24))
        pygame.draw.rect(self.screen, self.TEXT, (self.GRID_W + 10, button_y, 75, 24), 1)
        self.screen.blit(self.font_s.render("Sell 60%", True, self.TEXT), (self.GRID_W + 18, button_y + 4))
        pygame.draw.rect(self.screen, self.PANEL_BTN, (self.GRID_W + 95, button_y, 75, 24))
        pygame.draw.rect(self.screen, self.TEXT, (self.GRID_W + 95, button_y, 75, 24), 1)
        self.screen.blit(self.font_s.render("Close", True, self.TEXT), (self.GRID_W + 118, button_y + 4))

        tower_stats_y = button_y + 34
        self.screen.blit(self.font_s.render("Stats:", True, self.TEXT), (self.GRID_W + 14, tower_stats_y))
        tower_stats_y += 16
        self.screen.blit(self.font_s.render(f"Damage: {t.dmg}", True, self.TEXT), (self.GRID_W + 14, tower_stats_y))
        tower_stats_y += 16
        self.screen.blit(self.font_s.render(f"Range: {t.range}", True, self.TEXT), (self.GRID_W + 14, tower_stats_y))
        tower_stats_y += 16
        self.screen.blit(self.font_s.render(f"Fire Rate: {t.fire_rate}", True, self.TEXT), (self.GRID_W + 14, tower_stats_y))
        tower_stats_y += 16
        self.screen.blit(self.font_s.render(f"Heat: {t.heat:.1f}/{t.max_heat}", True, self.TEXT), (self.GRID_W + 14, tower_stats_y))
        tower_stats_y += 20
        if t.upgrades:
            self.screen.blit(self.font_s.render("Upgrades:", True, self.TEXT), (self.GRID_W + 14, tower_stats_y))
            for uid in t.upgrades:
                tower_stats_y += 16
                from data.upgrades import UPGRADE_DEFS
                name = UPGRADE_DEFS.get(uid, {}).get("name", uid)
                self.screen.blit(self.font_s.render(f"- {name}", True, (180, 180, 200)), (self.GRID_W + 14, tower_stats_y))

        # Range visualization
        if t.fire_type != "Overwatch":
            cx = t.x * self.TILE + 20
            cy = self.grid_y + t.y * self.TILE + 20
            rad = t.range * self.TILE
            s = pygame.Surface((rad*2+4, rad*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (100, 160, 255, 80), (rad+2, rad+2), rad)
            pygame.draw.circle(s, (160, 220, 255, 150), (rad+2, rad+2), rad, 2)
            self.screen.blit(s, (cx-rad-2, cy-rad-2))

    def _draw_enemy_stats(self):
        """Draw enemy stats when an enemy is selected."""
        if self.game.selected_enemy is None:
            return

        e = self.game.selected_enemy
        enemy_stats_rect = pygame.Rect(self.GRID_W + 8, 162 + 320 + 10, 164, 120)
        pygame.draw.rect(self.screen, (35, 35, 50), enemy_stats_rect)
        pygame.draw.rect(self.screen, self.TEXT, enemy_stats_rect, 2)
        y_offset = enemy_stats_rect.y + 6
        self.screen.blit(self.font.render(f"{e.display_name}", True, self.TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 20
        self.screen.blit(self.font_s.render(f"HP: {e.health}/{e.max_health}", True, self.TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 16
        self.screen.blit(self.font_s.render(f"Speed: {e.move_speed}", True, self.TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 16
        self.screen.blit(self.font_s.render(f"Difficulty: {e.difficulty}", True, self.TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 16
        self.screen.blit(self.font_s.render(f"Wave: {e.wave_num}", True, self.TEXT), (enemy_stats_rect.x + 6, y_offset))
        y_offset += 16
        self.screen.blit(self.font_s.render(f"Position: {e.position_index}", True, self.TEXT), (enemy_stats_rect.x + 6, y_offset))

    def _draw_grid(self):
        """Draw the game grid."""
        for x in range(self.game.width + 1):
            sx1, sy1 = self.world_to_screen(x, 0)
            sx2, sy2 = self.world_to_screen(x, self.game.height)
            pygame.draw.line(self.screen, self.GRID, (sx1, sy1), (sx2, sy2), max(1, int(self.zoom_level)))
        for y in range(self.game.height + 1):
            sx1, sy1 = self.world_to_screen(0, y)
            sx2, sy2 = self.world_to_screen(self.game.width, y)
            pygame.draw.line(self.screen, self.GRID, (sx1, sy1), (sx2, sy2), max(1, int(self.zoom_level)))

        # Render grid cells
        for y in range(self.game.height):
            for x in range(self.game.width):
                cell_content = self.game.grid[y][x]
                if cell_content == 'P':
                    sx, sy = self.world_to_screen(x, y)
                    cell_rect = pygame.Rect(sx + 1, sy + 1, self.TILE * self.zoom_level - 2, self.TILE * self.zoom_level - 2)
                    pygame.draw.rect(self.screen, (120, 80, 40), cell_rect)

                    cell_pos = (x, y)
                    path_index = None
                    for i, path_pos in enumerate(self.game.path):
                        if path_pos == cell_pos:
                            path_index = i
                            break

                    if path_index is not None:
                        prev_pos = self.game.path[path_index - 1] if path_index > 0 else None
                        next_pos = self.game.path[path_index + 1] if path_index < len(self.game.path) - 1 else None

                        center_x = sx + (self.TILE * self.zoom_level) // 2
                        center_y = sy + (self.TILE * self.zoom_level) // 2
                        path_width = max(2, int(8 * self.zoom_level))

                        if prev_pos:
                            dx = prev_pos[0] - cell_pos[0]
                            dy = prev_pos[1] - cell_pos[1]
                            if dx > 0:
                                start_x, start_y = center_x + (self.TILE * self.zoom_level) // 2, center_y
                            elif dx < 0:
                                start_x, start_y = center_x - (self.TILE * self.zoom_level) // 2, center_y
                            elif dy > 0:
                                start_x, start_y = center_x, center_y + (self.TILE * self.zoom_level) // 2
                            elif dy < 0:
                                start_x, start_y = center_x, center_y - (self.TILE * self.zoom_level) // 2
                            else:
                                start_x, start_y = center_x, center_y
                            pygame.draw.line(self.screen, (160, 82, 45), (center_x, center_y), (start_x, start_y), path_width)

                        if next_pos:
                            dx = next_pos[0] - cell_pos[0]
                            dy = next_pos[1] - cell_pos[1]
                            if dx > 0:
                                end_x, end_y = center_x + (self.TILE * self.zoom_level) // 2, center_y
                            elif dx < 0:
                                end_x, end_y = center_x - (self.TILE * self.zoom_level) // 2, center_y
                            elif dy > 0:
                                end_x, end_y = center_x, center_y + (self.TILE * self.zoom_level) // 2
                            elif dy < 0:
                                end_x, end_y = center_x, center_y - (self.TILE * self.zoom_level) // 2
                            else:
                                end_x, end_y = center_x, center_y
                            pygame.draw.line(self.screen, (160, 82, 45), (center_x, center_y), (end_x, end_y), path_width)

                elif cell_content == 'X':
                    sx, sy = self.world_to_screen(x, y)
                    cell_rect = pygame.Rect(sx + 1, sy + 1, self.TILE * self.zoom_level - 2, self.TILE * self.zoom_level - 2)
                    pygame.draw.rect(self.screen, (128, 128, 128), cell_rect)

        # Connecting lines
        for i in range(len(self.game.path) - 1):
            x1, y1 = self.game.path[i]
            x2, y2 = self.game.path[i+1]
            sx1, sy1 = self.world_to_screen(x1, y1)
            sx2, sy2 = self.world_to_screen(x2, y2)
            pygame.draw.line(self.screen, (120, 60, 30),
                           (sx1 + 20 * self.zoom_level, sy1 + 20 * self.zoom_level),
                           (sx2 + 20 * self.zoom_level, sy2 + 20 * self.zoom_level),
                           max(2, int(6 * self.zoom_level)))

    def _draw_range_preview(self):
        """Draw range preview when placing towers."""
        mx, my = pygame.mouse.get_pos()
        if my >= self.grid_y and mx < self.GRID_W:
            gx, gy = self.screen_to_world(mx, my)
            gx, gy = int(gx), int(gy)
            if 0 <= gx < self.game.width and 0 <= gy < self.game.height:
                t = None
                cx, cy = self.world_to_screen(gx, gy)
                cx += 20 * self.zoom_level
                cy += 20 * self.zoom_level
                if self.game.selected_tower is not None and self.game.merge_preview is None:
                    t = self.game.bench[self.game.selected_tower]
                elif self.game.upgrade_dialog_tower is not None:
                    t = self.game.upgrade_dialog_tower
                    cx = t.x * self.TILE + 20
                    cy = self.grid_y + t.y * self.TILE + 20
                if t and t.fire_type != "Overwatch":
                    r = min(t.range * self.TILE * self.zoom_level, 200)
                    s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
                    pygame.draw.circle(s, (100, 160, 255, 60), (r+2, r+2), r)
                    pygame.draw.circle(s, (160, 220, 255, 180), (r+2, r+2), r, 2)
                    self.screen.blit(s, (cx-r-2, cy-r-2))

    def _draw_tile_preview(self):
        """Draw tile placement preview."""
        if self.game.selected_map_tile is not None and self.game.map_tile_bench[self.game.selected_map_tile]:
            mx, my = pygame.mouse.get_pos()
            if my >= self.grid_y and mx < self.GRID_W:
                gx, gy = self.screen_to_world(mx, my)
                gx, gy = int(gx), int(gy)
                tile_data = self.game.map_tile_bench[self.game.selected_map_tile]

                rotated_grid = self.game._rotate_grid(tile_data["path_grid"], self.game.selected_tile_rotation)
                placement_valid = self.game.can_place_tile(tile_data, gx, gy, self.game.selected_tile_rotation)

                fill_color = (60, 200, 80, 130) if placement_valid else (220, 60, 60, 130)
                border_color = (80, 255, 100) if placement_valid else (255, 80, 80)

                preview_x, preview_y = self.world_to_screen(gx, gy)
                cell_size = self.TILE * self.zoom_level

                for py in range(len(rotated_grid)):
                    for px in range(len(rotated_grid[py])):
                        if rotated_grid[py][px]:
                            rect = pygame.Rect(preview_x + px*cell_size, preview_y + py*cell_size, cell_size, cell_size)
                            s = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
                            s.fill(fill_color)
                            self.screen.blit(s, rect)
                            pygame.draw.rect(self.screen, border_color, rect, max(1, int(2 * self.zoom_level)))

                label_text = "OK" if placement_valid else "X"
                label_col = (80, 255, 100) if placement_valid else (255, 80, 80)
                lbl = self.font_s.render(label_text, True, label_col)
                self.screen.blit(lbl, (mx + 14, my - 14))

    def _draw_attack_beams(self, frame):
        """Draw attack beams."""
        for t in self.game.towers:
            if t.last_shot_target and frame - t.last_shot_frame < 18:
                tx, ty = self.world_to_screen(t.x, t.y)
                tx += 20 * self.zoom_level
                ty += 20 * self.zoom_level
                ex, ey = t.last_shot_target
                exx, eyy = self.world_to_screen(ex, ey)
                exx += 20 * self.zoom_level
                eyy += 20 * self.zoom_level
                age = frame - t.last_shot_frame
                w = max(2, int((6 - age//3) * self.zoom_level))
                col = (*self.tower_colors.get(t.base_type, (180, 180, 255)), 255 - age*14)
                pygame.draw.line(self.screen, col, (tx, ty), (exx, eyy), w)

    def _draw_towers(self):
        """Draw towers on the grid."""
        for t in self.game.towers:
            col = self.tower_colors.get(t.base_type, (150, 150, 150))
            tx, ty = self.world_to_screen(t.x, t.y)
            r = pygame.Rect(tx + 6 * self.zoom_level, ty + 6 * self.zoom_level,
                          (self.TILE * self.zoom_level) - 12, (self.TILE * self.zoom_level) - 12)
            pygame.draw.rect(self.screen, col, r)

            if self.game.selected_upgrade is not None:
                from data.upgrades import UPGRADE_DEFS
                upgrade_id = self.game.upgrade_bench[self.game.selected_upgrade]
                if upgrade_id and len(t.upgrades) < t.UPGRADE_CAPACITY and upgrade_id not in t.upgrades:
                    pygame.draw.rect(self.screen, (100, 255, 100), r, max(2, int(4 * self.zoom_level)))
                else:
                    pygame.draw.rect(self.screen, (255, 100, 100), r, max(2, int(4 * self.zoom_level)))
            else:
                pygame.draw.rect(self.screen, (220, 220, 255), r, max(1, int(2 * self.zoom_level)))

            if t.fire_type == "Radius":
                cx = tx + 20 * self.zoom_level
                cy = ty + 20 * self.zoom_level
                rad = t.range * self.TILE * self.zoom_level
                s = pygame.Surface((rad*2+4, rad*2+4), pygame.SRCALPHA)
                pygame.draw.circle(s, (220, 120, 60, 80), (rad+2, rad+2), rad)
                pygame.draw.circle(s, (255, 150, 80, 150), (rad+2, rad+2), rad, 2)
                self.screen.blit(s, (cx-rad-2, cy-rad-2))

    def _draw_enemies(self):
        """Draw enemies."""
        for e in self.game.enemies:
            pos = e.get_position()
            if pos:
                ex, ey = pos
                exx, eyy = self.world_to_screen(ex, ey)
                c = (exx + 20 * self.zoom_level, eyy + 20 * self.zoom_level)
                enemy_color = (60, 220, 60) if e.is_egrem_spawned else self.ENEMY
                pygame.draw.circle(self.screen, enemy_color, c, max(5, int(13 * self.zoom_level)))
                ratio = max(0, e.health / e.max_health)
                bar_width = max(10, int(40 * self.zoom_level))
                bar_height = max(2, int(6 * self.zoom_level))
                pygame.draw.rect(self.screen, self.HP_BG, (c[0]-20*self.zoom_level, c[1]-30*self.zoom_level, bar_width, bar_height))
                pygame.draw.rect(self.screen, self.HP_FILL, (c[0]-20*self.zoom_level, c[1]-30*self.zoom_level, bar_width*ratio, bar_height))

    def _draw_wave_bonus(self, frame):
        """Draw wave bonus text."""
        if frame < self.game.wave_bonus_show_until:
            txt = self.font.render(self.game.wave_bonus_text, True, (100, 255, 140))
            tw, th = txt.get_size()
            pygame.draw.rect(self.screen, (0, 0, 0, 180), (self.WIDTH//2 - tw//2 - 20, 60, tw+40, th+20))
            self.screen.blit(txt, (self.WIDTH//2 - tw//2, 70))

    def _draw_game_over(self):
        """Draw game over screen."""
        if not self.game.game_over:
            return

        o = pygame.Surface((self.WIDTH, self.HEIGHT))
        o.set_alpha(180)
        o.fill((0, 0, 0))
        self.screen.blit(o, (0, 0))
        txt = pygame.font.SysFont("consolas", 48, bold=True).render("GAME OVER", True, (255, 80, 80))
        self.screen.blit(txt, txt.get_rect(center=(self.WIDTH//2, self.HEIGHT//2 - 60)))
        s = self.font.render(f"Wave {self.game.final_wave}   Gold {self.game.final_gold}", True, self.TEXT)
        self.screen.blit(s, s.get_rect(center=(self.WIDTH//2, self.HEIGHT//2)))
        r = self.font.render("Click anywhere to restart", True, self.TEXT)
        self.screen.blit(r, r.get_rect(center=(self.WIDTH//2, self.HEIGHT//2 + 60)))

    def _draw_camera_info(self):
        """Draw camera info in top-right."""
        if not self.game.game_over:
            camera_info = f"Zoom: {self.zoom_level:.1f}x | Camera: ({self.camera_x:.0f}, {self.camera_y:.0f})"
            info_surf = self.font_s.render(camera_info, True, self.TEXT)
            self.screen.blit(info_surf, (self.WIDTH - info_surf.get_width() - 10, 10))