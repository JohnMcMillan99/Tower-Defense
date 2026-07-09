import os
import pygame
import json
from datetime import datetime
from models.tower import Tower
from data.upgrades import UPGRADE_DEFS
from ui.swarm_fx import SwarmFXManager
from ui.layout import UILayout
from config import log_debug


class Renderer:
    def __init__(self, game):
        log_debug("Renderer.__init__ start", location="renderer.py")
        self.game = game
        self.layout = UILayout(game)

        # Layout constants (mirrored from UILayout for existing call sites)
        self.TILE = self.layout.TILE
        self.SHOP_H = self.layout.SHOP_H
        self.BENCH_H = self.layout.BENCH_H
        self.GRID_W = self.layout.GRID_W
        self.PANEL_RIGHT_W = self.layout.PANEL_RIGHT_W
        self.WIDTH = self.layout.WIDTH
        self.HEIGHT = self.layout.HEIGHT
        self.grid_y = self.layout.grid_y
        self.map_bench_x = self.layout.map_bench_x
        self.map_bench_y = self.layout.map_bench_y

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
        self.CARD_PURE = (245, 245, 250)  # off-white for pure merged towers
        self.CARD_HYBRID = (120, 80, 50)  # brown for hybrid merged towers
        self.TEXT = (220, 220, 220)

        # Fonts (use bundled TTF in web - Font(None) can fail in wasm)
        log_debug("Font initialization start", {"web_mode": getattr(game, "web_mode", False)}, location="renderer.py")
        if getattr(game, "web_mode", False):
            log_debug("Web mode font loading", location="renderer.py")
            font_path = None
            for candidate in [
                os.path.join(os.path.dirname(__file__), "..", "freesansbold.ttf"),
                os.path.join(os.path.dirname(__file__), "..", "assets", "freesansbold.ttf"),
                "freesansbold.ttf",
                "assets/freesansbold.ttf",
            ]:
                if os.path.exists(candidate):
                    font_path = candidate
                    break
            try:
                if font_path:
                    log_debug("Loading fonts from file", {"font_path": font_path}, location="renderer.py")
                    self.font = pygame.font.Font(font_path, 16)
                    self.font_s = pygame.font.Font(font_path, 12)
                    self.font_merge = pygame.font.Font(font_path, 20)
                    self.font_over = pygame.font.Font(font_path, 48)
                    log_debug("File fonts loaded successfully", location="renderer.py")
                else:
                    raise FileNotFoundError("freesansbold.ttf")
            except Exception as e:
                log_debug("File font loading failed, using default fonts", {"error": str(e)}, location="renderer.py")
                self.font = pygame.font.Font(None, 16)
                self.font_s = pygame.font.Font(None, 12)
                self.font_merge = pygame.font.Font(None, 20)
                self.font_over = pygame.font.Font(None, 48)
        else:
            log_debug("System font loading", location="renderer.py")
            try:
                self.font = pygame.font.SysFont("consolas", 16)
                self.font_s = pygame.font.SysFont("consolas", 12)
                self.font_merge = pygame.font.SysFont("consolas", 20)
                self.font_over = pygame.font.SysFont("consolas", 48, bold=True)
                log_debug("System fonts loaded successfully", location="renderer.py")
            except Exception as e:
                log_debug("System font loading failed", {"error": str(e)}, location="renderer.py")

        log_debug("Renderer initialization complete", location="renderer.py")

        self.swarm_fx = SwarmFXManager()
        self._fps_clock = pygame.time.Clock()
        self._show_fps = getattr(game, 'show_fps', False)

        # Tower colors
        self.tower_colors = {
            "Neural Processor": (70, 130, 255),
            "Plasma Capacitor": (100, 255, 100),
            "Thermal Regulator": (220, 120, 60),
            "Signal Router": (200, 100, 255),
            "Quantum Field Gen": (255, 200, 50),
            "Nanite Swarm": (40, 40, 45),
            "Thermal Plasma Core": (255, 140, 80),
            "Cortex Assimilator": (120, 180, 255),
            "Thermal Router": (230, 140, 200),
            "Quantum Burst Engine": (200, 230, 80),
            "Neural Field Generator": (100, 180, 200),
        }

        # Layout positions (owned by UILayout)
        self.grid_y = self.layout.grid_y
        self.map_bench_x = self.layout.map_bench_x
        self.map_bench_y = self.layout.map_bench_y

        log_debug("Initializing pygame display", {"width": self.WIDTH, "height": self.HEIGHT}, location="renderer.py")

        # Initialize screen
        log_debug("Creating pygame display", {"width": self.WIDTH, "height": self.HEIGHT}, location="renderer.py")
        try:
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
            pygame.display.set_caption("Borg TD Prototype")
            log_debug("Display created successfully", {"surface_size": self.screen.get_size()}, location="renderer.py")
        except Exception as e:
            log_debug("Display creation failed", {"error": str(e)}, location="renderer.py")

        # Initialize fonts
        log_debug("Initializing fonts", location="renderer.py")
        if getattr(game, "web_mode", False):
            log_debug("Web mode detected, loading fonts", location="renderer.py")
            # ... existing font loading code ...
        else:
            log_debug("Native mode, loading system fonts", location="renderer.py")
            try:
                self.font = pygame.font.SysFont("consolas", 16)
                self.font_s = pygame.font.SysFont("consolas", 12)
                self.font_merge = pygame.font.SysFont("consolas", 20)
                self.font_over = pygame.font.SysFont("consolas", 48, bold=True)
                log_debug("System fonts loaded successfully", location="renderer.py")
            except Exception as e:
                log_debug("System font loading failed", {"error": str(e)}, location="renderer.py")

        log_debug("Renderer initialization complete", location="renderer.py")

    def _draw_tier_effects(self, rect, tier):
        """Draw tier-based visual effects on a card/tower."""
        if tier <= 0:
            return  # No effects for tier 0

        center_x, center_y = rect.center
        width, height = rect.size

        # Tier 1: Subtle glow
        if tier >= 1:
            glow_radius = 10 + tier * 5
            glow_surface = pygame.Surface((width + glow_radius*2, height + glow_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (255, 255, 255, 50), (width//2 + glow_radius, height//2 + glow_radius), glow_radius)
            self.screen.blit(glow_surface, (rect.x - glow_radius, rect.y - glow_radius))

        # Tier 2: Gradient fill overlay
        if tier >= 2:
            gradient_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            for y in range(height):
                alpha = int(100 * (1 - y / height))  # Fade from top to bottom
                color = (255, 255, 255, alpha)
                pygame.draw.line(gradient_surface, color, (0, y), (width, y))
            self.screen.blit(gradient_surface, rect.topleft)

        # Tier 3: Thick border
        if tier >= 3:
            border_width = 2 + (tier - 3)  # 2px for tier 3, thicker for higher
            pygame.draw.rect(self.screen, (255, 215, 0), rect, border_width)  # Gold border

        # Tier 4: Aura particles
        if tier >= 4:
            import random
            for _ in range(5 + tier):  # More particles for higher tiers
                px = center_x + random.randint(-width//2, width//2)
                py = center_y + random.randint(-height//2, height//2)
                pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 1)

    def _draw_egrem_swirls(self, x, y, width, height):
        """Draw chaotic swirl effects for Egrem towers."""
        import math
        import random

        # Create a surface for the swirl overlay
        swirl_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        center_x, center_y = width // 2, height // 2
        num_swirls = 3

        for i in range(num_swirls):
            # Random swirl parameters
            radius = random.randint(10, 25)
            angle_offset = random.random() * 2 * math.pi
            swirl_color = (random.randint(60, 100), random.randint(200, 255), random.randint(60, 100), 100)

            # Draw swirl as connected arcs
            points = []
            for angle in range(0, 360, 15):
                rad_angle = math.radians(angle) + angle_offset
                px = center_x + int(radius * math.cos(rad_angle) * (0.5 + 0.5 * math.sin(rad_angle * 2)))
                py = center_y + int(radius * math.sin(rad_angle) * (0.5 + 0.5 * math.sin(rad_angle * 2)))
                points.append((px, py))

            if len(points) > 2:
                pygame.draw.lines(swirl_surface, swirl_color, False, points, 2)

        self.screen.blit(swirl_surface, (x, y))

    def _render_text(self, font, text, color, bgcolor=None):
        """Render text with web compatibility - convert surface for proper blitting."""
        try:
            surf = font.render(text, True, color, bgcolor) if bgcolor else font.render(text, True, color)
            if surf.get_width() > 0 and surf.get_height() > 0:
                return surf.convert_alpha() if getattr(self.game, "web_mode", False) else surf
        except Exception:
            pass
        return None

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
        self.layout.refresh(self.game)
        self.GRID_W = self.layout.GRID_W
        self.WIDTH = self.layout.WIDTH
        self.HEIGHT = self.layout.HEIGHT
        self.grid_y = self.layout.grid_y
        self.map_bench_x = self.layout.map_bench_x
        self.map_bench_y = self.layout.map_bench_y
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))

    def draw(self, frame):
        """Main drawing function."""
        if frame <= 3:
            log_debug(f"Draw method called for frame {frame}", location="renderer.py:draw")
        try:
            self.screen.fill(self.BLACK)
            if frame <= 3:
                log_debug("Screen filled with black", location="renderer.py:draw")
        except Exception as e:
            log_debug("Screen fill failed", {"error": str(e)}, location="renderer.py:draw")

        self._draw_shop()
        self._draw_bench(frame)
        self._draw_loot_bag()
        self._draw_rotate_button()
        self._draw_merge_preview(frame)
        self._draw_right_panel()
        self._draw_inspector()
        self._draw_grid()
        self._draw_range_preview()
        self._draw_tile_preview()
        self._draw_attack_beams(frame)
        self._draw_towers()
        self._draw_enemies()
        self._draw_latch_effects()
        self._draw_wave_bonus(frame)
        self._draw_game_over()
        self._draw_camera_info()
        self._draw_version_info()
        self._draw_fps()

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

    def _draw_fps(self):
        """Draw FPS counter when DEBUG or show_fps is enabled."""
        from config import DEBUG
        if not (DEBUG or self._show_fps):
            return
        fps = self._fps_clock.get_fps()
        self._fps_clock.tick()
        fps_text = f"FPS: {fps:.0f}"
        text_surface = self.font_s.render(fps_text, True, (0, 255, 0))
        self.screen.blit(text_surface, (5, self.HEIGHT - 18))

    def _draw_latch_effects(self):
        """Draw assimilator latch effects."""
        # Update swarm effects
        self.swarm_fx.update(1.0)  # Assuming 1 frame per update

        # Draw latch effects for latched assimilators
        for enemy in self.game.enemies:
            if hasattr(enemy, 'is_latched') and enemy.is_latched:
                # Get assimilator position (use current position or stored latch position)
                assim_pos = enemy.get_position()
                if assim_pos:
                    target_pos = getattr(enemy, 'latch_target', None)
                    if target_pos:
                        stack_count = getattr(enemy, 'stack_count', 1)
                        self.swarm_fx.draw_latch(
                            self.screen,
                            assim_pos,
                            target_pos,
                            stack_count,
                            self.world_to_screen
                        )

        # Draw all swarm effects
        self.swarm_fx.draw(self.screen)

    def _draw_shop(self):
        """Draw the towers-only shop section (left 5/8 of top HUD)."""
        L = self.layout
        shop = L.shop_region()
        pygame.draw.rect(self.screen, self.SHOP_BG, shop)
        pygame.draw.line(self.screen, self.GRID, (shop.right, 0), (shop.right, self.SHOP_H), 2)
        pygame.draw.line(self.screen, self.GRID, (0, self.SHOP_H), (self.GRID_W, self.SHOP_H), 2)
        self.screen.blit(self.font_s.render("SHOP", True, self.TEXT), (shop.x + 12, 2))

        for i in range(5):
            r = L.shop_card_rect(i)
            card = self.game.shop[i]
            col = self.CARD_EMP if card is None else self.CARD_BG
            pygame.draw.rect(self.screen, col, r)
            pygame.draw.rect(self.screen, self.TEXT, r, 1 if card else 2)
            if card:
                self.screen.blit(self.font_s.render(card["type"][:8], True, self.TEXT), (r.x + 5, r.y + 10))
                self.screen.blit(self.font_s.render(f"${card['cost']}", True, self.TEXT), (r.x + 5, r.y + 75))

        rr = L.reroll_rect()
        pygame.draw.rect(self.screen, self.CARD_BG, rr)
        pygame.draw.rect(self.screen, self.TEXT, rr, 1)
        self.screen.blit(self.font_s.render("R", True, self.TEXT), (rr.x + 10, rr.y + 10))

    def _draw_bench(self, frame):
        """Draw the tower bench (full width under shop + map tiles)."""
        L = self.layout
        pygame.draw.rect(self.screen, self.BENCH_BG, (0, self.SHOP_H, self.GRID_W, self.BENCH_H))
        pygame.draw.line(self.screen, self.GRID, (0, self.SHOP_H + self.BENCH_H), (self.GRID_W, self.SHOP_H + self.BENCH_H), 2)
        self.screen.blit(self.font_s.render("BENCH", True, self.TEXT), (15, self.SHOP_H + 5))

        for i in range(len(self.game.bench)):
            r = L.bench_card_rect(i)
            x, y = r.x, r.y
            col = self.CARD_EMP if self.game.bench[i] is None else self.CARD_BG
            if self.game.bench[i]:
                merge_type = self.game.bench[i].get_merge_type()
                if merge_type == "pure":
                    col = self.CARD_PURE
                elif merge_type == "hybrid":
                    col = self.CARD_HYBRID
                # egrem and base keep CARD_BG
            if i in (self.game.merge_tower_1, self.game.merge_tower_2) and self.game.bench[i] is not None:
                col = self.CARD_SEL
            pygame.draw.rect(self.screen, col, r)
            pygame.draw.rect(self.screen, self.TEXT, r, 2)
            if self.game.bench[i]:
                t = self.game.bench[i]
                # Apply tier visual effects (full mode only)
                if not getattr(self.game, 'minimal_mode', True):
                    self._draw_tier_effects(r, t.get_merge_tier())

                if t.base_type == "Nanite Swarm":
                    pygame.draw.rect(self.screen, (28, 28, 35), r)
                    pygame.draw.rect(self.screen, (80, 255, 80), r, 2)
                    # Add chaotic swirl effects
                    self._draw_egrem_swirls(x, y, r.w, r.h)
                    self.screen.blit(self.font_s.render("Egrem", True, (80, 255, 100)), (x+5, y+5))
                    self.screen.blit(self.font_s.render("spawn", True, (255, 80, 80)), (x+5, y+28))
                    self.screen.blit(self.font_s.render(f"T{t.get_merge_tier()}", True, self.TEXT), (x+5, y+50))
                else:
                    display_name = t.get_display_name() if hasattr(t, 'get_display_name') else t.base_type
                    self.screen.blit(self.font_s.render(display_name[:8], True, self.TEXT), (x+5, y+5))
                    self.screen.blit(self.font_s.render(f"D:{t.dmg}", True, self.TEXT), (x+5, y+30))
                    tier_label = f"T{t.get_merge_tier()}"
                    mtype = t.get_merge_type()
                    if mtype == "pure" and t.merge_generation >= 1:
                        tier_label += " Pure"
                    elif mtype == "hybrid":
                        tier_label += " Hyb"
                    self.screen.blit(self.font_s.render(tier_label, True, self.TEXT), (x+5, y+50))
                    if t.merge_generation >= 1 and hasattr(t, 'calculate_purity'):
                        purity = t.calculate_purity()
                        p_col = (100, 255, 100) if purity == 100 else (255, 180, 60)
                        self.screen.blit(self.font_s.render(f"P:{purity}%", True, p_col), (x+5, y+70))

        # Flash overlay for egrem
        if self.game.egrem_flash_bench_idx is not None and frame < self.game.egrem_flash_until:
            flash_alpha = 80 + 60 * (1 - (self.game.egrem_flash_until - frame) / 120)
            i = self.game.egrem_flash_bench_idx
            r = L.bench_card_rect(i)
            s = pygame.Surface((r.w, r.h))
            s.set_alpha(min(140, int(flash_alpha)))
            s.fill((255, 80, 80))
            self.screen.blit(s, (r.x, r.y))

    def _draw_loot_bag(self):
        """Draw shared loot bag (path tiles + upgrades) in the top-right HUD column."""
        L = self.layout
        col = L.map_column_region()
        pygame.draw.rect(self.screen, self.SHOP_BG, col)
        bag = getattr(self.game, "loot_bag", self.game.map_tile_bench)
        filled = sum(1 for s in bag if s is not None)
        self.screen.blit(
            self.font_s.render(f"LOOT {filled}/{len(bag)}", True, self.TEXT),
            (col.x + 8, 2),
        )

        selected = getattr(self.game, "selected_loot", None)
        if selected is None:
            selected = self.game.selected_map_tile if self.game.selected_map_tile is not None else self.game.selected_upgrade

        for i, item in enumerate(bag):
            r = L.loot_card_rect(i)
            card_col = self.CARD_EMP if item is None else self.CARD_BG
            if i == selected:
                card_col = self.CARD_SEL
            pygame.draw.rect(self.screen, card_col, r)
            pygame.draw.rect(self.screen, self.TEXT, r, 2)
            if item is None:
                continue
            if isinstance(item, dict) and "name" in item:
                pygame.draw.rect(self.screen, (40, 70, 90), (r.x + 2, r.y + 2, r.w - 4, 14))
                self.screen.blit(self.font_s.render("TILE", True, (180, 220, 255)), (r.x + 4, r.y + 2))
                self.screen.blit(self.font_s.render(item["name"][:6], True, self.TEXT), (r.x + 4, r.y + 20))
                self.screen.blit(self.font_s.render(f"{item['width']}x{item['height']}", True, self.TEXT), (r.x + 4, r.y + 48))
            else:
                u = UPGRADE_DEFS.get(item, {})
                name = u.get("name", str(item))
                if len(name) > 6:
                    name = name[:5] + "."
                pygame.draw.rect(self.screen, (70, 50, 90), (r.x + 2, r.y + 2, r.w - 4, 14))
                self.screen.blit(self.font_s.render("UPG", True, (220, 180, 255)), (r.x + 4, r.y + 2))
                self.screen.blit(self.font_s.render(name, True, self.TEXT), (r.x + 4, r.y + 20))
                self.screen.blit(self.font_s.render(f"${u.get('cost', 0)}", True, self.TEXT), (r.x + 4, r.y + 48))

    def _draw_map_tile_bench(self):
        self._draw_loot_bag()

    def _draw_upgrade_bench(self):
        return

    def _draw_rotate_button(self):
        """Draw the rotate button for selected map tiles."""
        if self.game.selected_map_tile is None:
            return
        left, right = self.layout.rotate_button_rects()
        rot_x, rot_y = left.x, left.y

        pygame.draw.rect(self.screen, self.PANEL_BTN, left)
        pygame.draw.rect(self.screen, self.TEXT, left, 1)
        self.screen.blit(self.font_s.render("<", True, self.TEXT), (rot_x + 8, rot_y + 4))

        pygame.draw.rect(self.screen, self.PANEL_BTN, right)
        pygame.draw.rect(self.screen, self.TEXT, right, 1)
        self.screen.blit(self.font_s.render(">", True, self.TEXT), (right.x + 8, rot_y + 4))

        deg_lbl = self.font_s.render(f"{self.game.selected_tile_rotation * 90}\u00b0", True, self.TEXT)
        self.screen.blit(deg_lbl, (right.right + 8, rot_y + 4))

        hint_lbl = self.font_s.render("A/D", True, (120, 120, 140))
        self.screen.blit(hint_lbl, (rot_x, rot_y + 24))

    def _draw_merge_preview(self, frame=0):
        """Draw merge/egrem/incompatible preview lines and labels."""
        preview_sources = [
            self.game.economy.get_merge_preview_info(),
            self.game.economy.get_egrem_preview_info(),
            self.game.economy.get_incompatible_preview_info(frame),
        ]
        for preview_info in preview_sources:
            if preview_info is None:
                continue

            idx1, idx2 = preview_info["idx1"], preview_info["idx2"]
            cx1, cy = self.layout.bench_card_center(min(idx1, idx2))
            cx2, _ = self.layout.bench_card_center(max(idx1, idx2))
            cx1, cy, cx2 = int(cx1), int(cy), int(cx2)

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
                if preview_info.get("is_egrem") and "line_color_inner_1" in preview_info:
                    c = preview_info["line_color_inner_1"] if i % 2 == 0 else preview_info["line_color_inner_2"]
                else:
                    c = preview_info.get("line_color_inner", preview_info["line_color_outer"])
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

            # Draw cost (merge/egrem only; incompatible has no cost)
            if "cost" in preview_info:
                cost_surf = self.font_s.render(f"${preview_info['cost']}", True, preview_info.get("cost_color", self.TEXT))
                self.screen.blit(cost_surf, (mid_x - cost_surf.get_width()//2, mid_y + 18))

    def stats_toggle_rect(self):
        return self.layout.stats_toggle_rect()

    def tower_stats_close_rect(self):
        return self.layout.inspector_close_rect()

    def _tower_stats_lines_for_tower(self, t, total_last_damage, dur_frames):
        lines = []
        dname = t.get_display_name() if hasattr(t, "get_display_name") else t.base_type
        lines.append(f"{dname} @({t.x},{t.y})")
        lines.append(f"{t.base_type} | {t.fire_type}")
        rng = "Glbl" if (t.fire_type == "Overwatch" or t.range >= 90) else str(t.range)
        lines.append(f"D:{t.dmg} R:{rng} FR:{t.fire_rate}")
        lines.append(f"Heat {t.heat:.1f}/{t.max_heat:.0f}  CD:{t.cooldown}")
        purity_s = f"{t.calculate_purity()}%" if t.merge_generation >= 1 else "-"
        lines.append(f"T{t.merge_generation} Purity:{purity_s} ${t.gold_invested}")
        if dur_frames > 0:
            dps = t.damage_dealt_last_wave * 60.0 / max(1, dur_frames)
            lines.append(f"LastW: {t.damage_dealt_last_wave} dmg  DPS~{dps:.1f}")
        else:
            lines.append("LastW: -  DPS: -")
        lines.append(f"Kills L/W:{t.kills_last_wave}  Now:{t.damage_dealt_this_wave}d/{t.kills_this_wave}k")
        if total_last_damage > 0:
            pct = 100.0 * t.damage_dealt_last_wave / total_last_damage
            lines.append(f"Share last W: {pct:.0f}%")
        if t.fire_rate > 0 and t.fire_type not in ("Radius", "Spawner", "Beam", "TargetBeam"):
            paper = t.dmg * 60.0 / t.fire_rate
            lines.append(f"Paper DPS~{paper:.1f} (60fps)")
        for uid in t.upgrades[:4]:
            nm = UPGRADE_DEFS.get(uid, {}).get("name", uid)
            lines.append(f"+ {nm}"[:24])
        if len(t.upgrades) > 4:
            lines.append(f"+ {len(t.upgrades) - 4} more")
        return lines

    def _tower_stats_content_height(self):
        towers = sorted(self.game.towers, key=lambda t: (t.y, t.x))
        dur = getattr(self.game, "last_wave_duration_frames", 0)
        total_ld = sum(t.damage_dealt_last_wave for t in towers)
        h = 14 * 2 + 4
        for t in towers:
            h += len(self._tower_stats_lines_for_tower(t, total_ld, dur)) * 14 + 6
        return h

    def tower_stats_max_scroll(self):
        if self.game.inspector_mode != "stats":
            return 0
        inner = self.layout.inspector_content_rect()
        return max(0, self._tower_stats_content_height() - inner.height)

    def _draw_right_panel(self):
        """Draw the right panel with game stats and controls."""
        L = self.layout
        pygame.draw.rect(self.screen, self.PANEL_BG, (self.GRID_W, 0, self.PANEL_RIGHT_W, self.SHOP_H + self.BENCH_H))
        pygame.draw.line(self.screen, self.GRID, (self.GRID_W, 0), (self.GRID_W, self.SHOP_H + self.BENCH_H), 2)

        st = L.stats_toggle_rect()
        col_st = self.PANEL_BTN_SEL if self.game.inspector_mode == "stats" else self.PANEL_BTN
        pygame.draw.rect(self.screen, col_st, st)
        pygame.draw.rect(self.screen, self.TEXT, st, 1)
        st_lbl = self.font_s.render("Stats", True, self.TEXT)
        self.screen.blit(st_lbl, (st.centerx - st_lbl.get_width() // 2, st.centery - 6))

        px = self.GRID_W + 14
        py = 18
        self.screen.blit(self.font.render(f"Gold:  {self.game.gold}", True, self.TEXT), (px, py))
        py += 24
        self.screen.blit(self.font.render(f"Lives: {self.game.lives}", True, self.TEXT), (px, py))
        py += 24
        self.screen.blit(self.font.render(f"Wave:  {self.game.round_num}", True, self.TEXT), (px, py))
        py += 24

        if L.show_spl(self.game):
            self.screen.blit(self.font.render(f"SPL:   {self.game.shop_power_level}", True, self.TEXT), (px, py))
            py += 24
            xp_ratio = self.game.xp / self.game.xp_to_next if self.game.xp_to_next > 0 else 0
            bar_width, bar_height = 120, 12
            pygame.draw.rect(self.screen, self.HP_BG, (px, py, bar_width, bar_height))
            pygame.draw.rect(self.screen, (100, 255, 100), (px, py, int(bar_width * xp_ratio), bar_height))
            pygame.draw.rect(self.screen, self.TEXT, (px, py, bar_width, bar_height), 1)
            py += bar_height + 4
            self.screen.blit(self.font_s.render(f"XP: {self.game.xp}/{self.game.xp_to_next}", True, self.TEXT), (px, py))
            py += 20

        play_rect, next_rect, auto_rect = L.panel_control_rects(show_spl=L.show_spl(self.game))
        col_play = self.PANEL_BTN_SEL if self.game.paused else self.PANEL_BTN
        pygame.draw.rect(self.screen, col_play, play_rect)
        pygame.draw.rect(self.screen, self.TEXT, play_rect, 1)
        self.screen.blit(self.font_s.render("Play" if self.game.paused else "Pause", True, self.TEXT), (play_rect.x + 28, play_rect.y + 4))

        pygame.draw.rect(self.screen, self.PANEL_BTN, next_rect)
        pygame.draw.rect(self.screen, self.TEXT, next_rect, 1)
        self.screen.blit(self.font_s.render("Next Wave", True, self.TEXT), (next_rect.x + 14, next_rect.y + 4))

        col_auto = self.PANEL_BTN_SEL if self.game.auto_mode else self.PANEL_BTN
        pygame.draw.rect(self.screen, col_auto, auto_rect)
        pygame.draw.rect(self.screen, self.TEXT, auto_rect, 1)
        self.screen.blit(self.font_s.render("Auto " + ("ON" if self.game.auto_mode else "OFF"), True, self.TEXT), (auto_rect.x + 18, auto_rect.y + 4))

        self._draw_round_guide()

    def _draw_round_guide(self):
        """Tetris-like upcoming-wave scout strip (intel-gated)."""
        L = self.layout
        rect = L.round_guide_rect(show_spl=L.show_spl(self.game))
        pygame.draw.rect(self.screen, (22, 24, 32), rect)
        pygame.draw.rect(self.screen, self.GRID, rect, 1)

        preview = None
        if hasattr(self.game, "wave_manager") and self.game.wave_manager:
            preview = self.game.wave_manager.preview_upcoming()
        if not preview:
            return

        x, y = rect.x + 6, rect.y + 4
        tier_label = preview.get("tier_label", "Contact")
        intel = preview.get("intel", 0)
        intel_max = max(1, preview.get("intel_max", 100))
        self.screen.blit(self.font_s.render(f"Scout [{tier_label}]", True, self.TEXT), (x, y))
        y += 14

        bar_w, bar_h = rect.w - 12, 6
        pygame.draw.rect(self.screen, self.HP_BG, (x, y, bar_w, bar_h))
        fill = int(bar_w * min(1.0, intel / intel_max))
        pygame.draw.rect(self.screen, (80, 180, 220), (x, y, fill, bar_h))
        pygame.draw.rect(self.screen, self.TEXT, (x, y, bar_w, bar_h), 1)
        y += bar_h + 4
        self.screen.blit(self.font_s.render(f"Intel {intel}/{intel_max}", True, (160, 170, 190)), (x, y))
        y += 14

        conf = preview.get("confidence", 0)
        conf_pct = int(round(100 * conf))
        noise = preview.get("noise_injections", 0)
        conf_col = (100, 220, 140) if conf_pct >= 60 else (220, 190, 100) if conf_pct >= 35 else (200, 120, 100)
        noise_bit = f"  n{noise}" if noise else ""
        self.screen.blit(self.font_s.render(f"Conf {conf_pct}%{noise_bit}"[:26], True, conf_col), (x, y))
        y += 14

        loot = preview.get("loot") or {}
        loot_waves = loot.get("waves", 0)
        loot_kind = loot.get("kind", "mini_boss")
        loot_name = "Boss" if loot_kind == "boss" else "Mini"
        if loot_waves == 0:
            loot_txt = f"Loot: {loot_name} this wave"
        else:
            loot_txt = f"Loot: {loot_name} in {loot_waves}"
        self.screen.blit(self.font_s.render(loot_txt[:26], True, (220, 190, 100)), (x, y))
        y += 14

        hint = preview.get("directive_hint")
        if hint and y <= rect.bottom - 12:
            self.screen.blit(self.font_s.render(f"Dir: {hint}"[:26], True, (140, 200, 160)), (x, y))
            y += 12

        mods = preview.get("modifier_labels") or []
        if mods and y <= rect.bottom - 12:
            mod_txt = "+" + ",".join(m.split()[0] for m in mods)[:20]
            self.screen.blit(self.font_s.render(mod_txt, True, (180, 160, 220)), (x, y))
            y += 12

        for entry in preview.get("waves", [])[:3]:
            if y > rect.bottom - 12:
                break
            wnum = entry.get("wave", "?")
            count = entry.get("count", 0)
            kind = entry.get("kind", "normal")
            prefix = "E" if kind == "event" else "W"
            line = f"{prefix}{wnum}: {count}"
            if entry.get("show_types") and entry.get("composition"):
                comps = entry["composition"]
                if entry.get("is_exact") and entry.get("show_percents"):
                    bits = [f"{int(p)}%{t[:3]}" for t, p in list(comps.items())[:2]]
                elif entry.get("is_exact"):
                    bits = [f"{int(n)}×{t[:3]}" for t, n in list(comps.items())[:2]]
                elif entry.get("show_percents"):
                    bits = [f"{int(p)}%{t[:3]}" for t, p in list(comps.items())[:2]]
                else:
                    bits = [t[:4] for t in list(comps.keys())[:2]]
                if bits:
                    line = f"{line} {' '.join(bits)}"
            else:
                line = f"{line} ???"
            if entry.get("loot"):
                line += " *"
            conf = entry.get("confidence")
            if conf is not None and entry.get("show_types"):
                line += f" ~{int(100 * conf)}%"
            self.screen.blit(self.font_s.render(line[:28], True, self.TEXT), (x, y))
            y += 12

    def _draw_inspector(self):
        """Single inspector panel: tower | enemy | stats tabs."""
        mode = self.game.inspector_mode
        if mode is None:
            return

        L = self.layout
        outer = L.inspector_rect()
        tabs = L.inspector_tab_rects()
        content = L.inspector_content_rect()
        close_r = L.inspector_close_rect()

        pygame.draw.rect(self.screen, (35, 35, 50), outer)
        pygame.draw.rect(self.screen, self.TEXT, outer, 2)

        for name, tab in tabs.items():
            active = mode == name
            pygame.draw.rect(self.screen, self.PANEL_BTN_SEL if active else self.PANEL_BTN, tab)
            pygame.draw.rect(self.screen, self.TEXT, tab, 1)
            label = {"tower": "Tower", "enemy": "Enemy", "stats": "Stats"}[name]
            lbl = self.font_s.render(label, True, self.TEXT)
            self.screen.blit(lbl, (tab.centerx - lbl.get_width() // 2, tab.centery - 6))

        if mode == "tower":
            self._draw_inspector_tower(content)
        elif mode == "enemy":
            self._draw_inspector_enemy(content)
        else:
            self._draw_inspector_stats(content)

        pygame.draw.rect(self.screen, self.PANEL_BTN, close_r)
        pygame.draw.rect(self.screen, self.TEXT, close_r, 1)
        cl = self.font_s.render("Close", True, self.TEXT)
        self.screen.blit(cl, (close_r.centerx - cl.get_width() // 2, close_r.centery - 6))

    def _draw_inspector_tower(self, content):
        t = self.game.inspector_tower
        if t is None:
            self.screen.blit(self.font_s.render("Select a tower", True, (160, 160, 180)), (content.x, content.y))
            return

        dname = t.get_display_name() if hasattr(t, "get_display_name") else t.base_type
        y = content.y
        self.screen.blit(self.font_s.render(f"{dname}", True, self.TEXT), (content.x, y))
        y += 16
        self.screen.blit(self.font_s.render(f"D:{t.dmg} R:{t.range} FR:{t.fire_rate}", True, self.TEXT), (content.x, y))
        y += 16
        cap_col = (180, 180, 200) if len(t.upgrades) < t.UPGRADE_CAPACITY else (255, 150, 150)
        self.screen.blit(self.font_s.render(f"Upgrades {len(t.upgrades)}/{t.UPGRADE_CAPACITY}", True, cap_col), (content.x, y))
        y += 16
        self.screen.blit(self.font_s.render(f"Heat {t.heat:.1f}/{t.max_heat}", True, self.TEXT), (content.x, y))
        y += 16
        self.screen.blit(self.font_s.render("Bench upgrade then click tower", True, (160, 160, 180)), (content.x, y))

        if t.fire_type in ("Track", "DirectionalBeam"):
            labels = ["W", "E", "N", "S"]
            for d, r in enumerate(self.layout.inspector_direction_rects()):
                col = self.PANEL_BTN_SEL if t.track_direction == d else self.PANEL_BTN
                pygame.draw.rect(self.screen, col, r)
                pygame.draw.rect(self.screen, self.TEXT, r, 1)
                lbl = self.font_s.render(labels[d], True, self.TEXT)
                self.screen.blit(lbl, (r.centerx - lbl.get_width() // 2, r.centery - 6))

        sell_r, _ = self.layout.inspector_sell_close_rects()
        pygame.draw.rect(self.screen, (120, 80, 80), sell_r)
        pygame.draw.rect(self.screen, self.TEXT, sell_r, 1)
        self.screen.blit(self.font_s.render("Sell", True, self.TEXT), (sell_r.x + 20, sell_r.y + 4))

        if t.fire_type != "Overwatch":
            cx = t.x * self.TILE + 20
            cy = self.grid_y + t.y * self.TILE + 20
            rad = t.range * self.TILE
            s = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (100, 160, 255, 80), (rad + 2, rad + 2), rad)
            pygame.draw.circle(s, (160, 220, 255, 150), (rad + 2, rad + 2), rad, 2)
            self.screen.blit(s, (cx - rad - 2, cy - rad - 2))

    def _draw_inspector_enemy(self, content):
        e = self.game.inspector_enemy
        if e is None or not getattr(e, "alive", False):
            self.screen.blit(self.font_s.render("Select an enemy", True, (160, 160, 180)), (content.x, content.y))
            return
        y = content.y
        self.screen.blit(self.font.render(f"{e.display_name}", True, self.TEXT), (content.x, y))
        y += 22
        for line in (
            f"HP: {e.health}/{e.max_health}",
            f"Speed: {e.move_speed}",
            f"Difficulty: {e.difficulty}",
            f"Wave: {e.wave_num}",
            f"Pos idx: {e.position_index}",
        ):
            self.screen.blit(self.font_s.render(line, True, self.TEXT), (content.x, y))
            y += 16

    def _draw_inspector_stats(self, content):
        max_s = self.tower_stats_max_scroll()
        self.game.inspector_scroll = max(0, min(max_s, self.game.inspector_scroll))

        towers = sorted(self.game.towers, key=lambda t: (t.y, t.x))
        dur = self.game.last_wave_duration_frames
        total_ld = sum(t.damage_dealt_last_wave for t in towers)

        prev_clip = self.screen.get_clip()
        self.screen.set_clip(content)
        y = content.y - self.game.inspector_scroll
        x = content.x + 2

        self.screen.blit(self.font_s.render(f"Count: {len(towers)}", True, self.TEXT), (x, y))
        y += 14
        self.screen.blit(self.font_s.render(f"Total last wave dmg: {total_ld}", True, self.TEXT), (x, y))
        y += 18

        if not towers:
            self.screen.blit(self.font_s.render("No towers on map.", True, (160, 160, 180)), (x, y))

        for t in towers:
            for line in self._tower_stats_lines_for_tower(t, total_ld, dur):
                if y + 14 > content.y and y < content.bottom:
                    self.screen.blit(self.font_s.render(line, True, self.TEXT), (x, y))
                y += 14
            y += 6

        self.screen.set_clip(prev_clip)

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
        """Draw attack beams (TargetBeam/Ball lines + DirectionalBeam flame)."""
        for t in self.game.towers:
            if not t.last_shot_target or frame - t.last_shot_frame >= 18:
                continue
            tx, ty = self.world_to_screen(t.x, t.y)
            tx += 20 * self.zoom_level
            ty += 20 * self.zoom_level
            ex, ey = t.last_shot_target
            exx, eyy = self.world_to_screen(ex, ey)
            exx += 20 * self.zoom_level
            eyy += 20 * self.zoom_level
            age = frame - t.last_shot_frame
            style = getattr(t, "last_shot_style", None) or "beam"

            if style == "flame_beam" or t.fire_type == "DirectionalBeam":
                self._draw_flame_beam(tx, ty, exx, eyy, age, frame)
            else:
                w = max(2, int((6 - age // 3) * self.zoom_level))
                col = (*self.tower_colors.get(t.base_type, (180, 180, 255)), 255 - age * 14)
                pygame.draw.line(self.screen, col, (tx, ty), (exx, eyy), w)

    def _draw_flame_beam(self, x0, y0, x1, y1, age, frame):
        """Layered orange/yellow/red beam from tower to max-range tip."""
        # Draw on a temp surface so we can fade the whole beam
        min_x = int(min(x0, x1)) - 12
        min_y = int(min(y0, y1)) - 12
        max_x = int(max(x0, x1)) + 12
        max_y = int(max(y0, y1)) + 12
        w = max(1, max_x - min_x)
        h = max(1, max_y - min_y)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        lx0, ly0 = x0 - min_x, y0 - min_y
        lx1, ly1 = x1 - min_x, y1 - min_y
        alpha = max(0, 220 - age * 12)
        pygame.draw.line(surf, (180, 40, 10, alpha), (lx0, ly0), (lx1, ly1), max(8, int(10 * self.zoom_level)))
        pygame.draw.line(surf, (255, 120, 20, alpha), (lx0, ly0), (lx1, ly1), max(5, int(6 * self.zoom_level)))
        pygame.draw.line(surf, (255, 230, 80, min(255, alpha + 20)), (lx0, ly0), (lx1, ly1), max(2, int(3 * self.zoom_level)))
        steps = max(3, int(6 * self.zoom_level))
        for i in range(1, steps):
            t = i / steps
            sx = lx0 + (lx1 - lx0) * t
            sy = ly0 + (ly1 - ly0) * t
            jitter = ((frame * 3 + i * 17) % 7) - 3
            r = max(2, int(3 * self.zoom_level))
            pygame.draw.circle(
                surf,
                (255, max(40, 200 - i * 10), 40, max(40, alpha - 40)),
                (int(sx + jitter), int(sy - abs(jitter))),
                r,
            )
        self.screen.blit(surf, (min_x, min_y))

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
                # Use merge type to determine border color
                merge_type = t.get_merge_type()
                if merge_type == "pure":
                    border_color = (255, 255, 255)  # white for pure
                elif merge_type == "hybrid":
                    border_color = (160, 110, 60)  # brown for hybrid
                elif merge_type == "egrem":
                    border_color = (80, 255, 80)  # green for egrem
                else:
                    border_color = (220, 220, 255)  # light blue for base
                pygame.draw.rect(self.screen, border_color, r, max(1, int(2 * self.zoom_level)))

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
                # Enemy visuals (full mode: black base with green accents)
                if not getattr(self.game, 'minimal_mode', True):
                    # Black base for all enemies
                    base_color = (0, 0, 0)
                    pygame.draw.circle(self.screen, base_color, c, max(5, int(13 * self.zoom_level)))

                    # Green accents (veins/eyes)
                    accent_color = (0, 255, 0) if e.is_egrem_spawned else (0, 180, 0)
                    radius = max(5, int(13 * self.zoom_level))

                    # Draw accent details - small circles at cardinal points for "veins"
                    accent_positions = [
                        (c[0], c[1] - radius//2),  # Top (like eyes)
                        (c[0], c[1] + radius//2),  # Bottom
                        (c[0] - radius//2, c[1]),  # Left
                        (c[0] + radius//2, c[1]),  # Right
                    ]
                    accent_radius = max(1, int(3 * self.zoom_level))
                    for ax, ay in accent_positions:
                        pygame.draw.circle(self.screen, accent_color, (ax, ay), accent_radius)
                else:
                    # Original enemy visuals
                    enemy_color = (60, 220, 60) if e.is_egrem_spawned else self.ENEMY
                    pygame.draw.circle(self.screen, enemy_color, c, max(5, int(13 * self.zoom_level)))
                ratio = max(0, e.health / e.max_health)
                bar_width = max(10, int(40 * self.zoom_level))
                bar_height = max(2, int(6 * self.zoom_level))
                pygame.draw.rect(self.screen, self.HP_BG, (c[0]-20*self.zoom_level, c[1]-30*self.zoom_level, bar_width, bar_height))
                pygame.draw.rect(self.screen, self.HP_FILL, (c[0]-20*self.zoom_level, c[1]-30*self.zoom_level, bar_width*ratio, bar_height))

    def _draw_wave_bonus(self, frame):
        """Draw wave bonus / reward toast text."""
        text = None
        if getattr(self.game, "reward_toast_until", 0) > frame and getattr(self.game, "reward_toast_text", ""):
            text = self.game.reward_toast_text
        elif frame < self.game.wave_bonus_show_until:
            text = self.game.wave_bonus_text
        if not text:
            return
        txt = self.font.render(text, True, (100, 255, 140))
        tw, th = txt.get_size()
        pygame.draw.rect(self.screen, (0, 0, 0, 180), (self.WIDTH // 2 - tw // 2 - 20, 60, tw + 40, th + 20))
        self.screen.blit(txt, (self.WIDTH // 2 - tw // 2, 70))

    def _draw_game_over(self):
        """Draw game over screen."""
        if not self.game.game_over:
            return

        o = pygame.Surface((self.WIDTH, self.HEIGHT))
        o.set_alpha(180)
        o.fill((0, 0, 0))
        self.screen.blit(o, (0, 0))
        txt = self.font_over.render("GAME OVER", True, (255, 80, 80))
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