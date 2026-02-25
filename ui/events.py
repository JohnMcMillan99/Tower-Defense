import pygame
import json


class EventHandler:
    def __init__(self, game, renderer):
        self.game = game
        self.renderer = renderer
        self.running = True

    def handle_events(self, frame):
        """Handle all Pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)
            elif event.type == pygame.MOUSEWHEEL:
                self._handle_mousewheel(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mousebuttondown(event, frame)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mousebuttonup(event)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mousemotion(event)

    def _handle_keydown(self, event):
        """Handle key press events."""
        # Camera controls
        if event.key == pygame.K_LEFT:
            self.renderer.camera_x += 50
        elif event.key == pygame.K_RIGHT:
            self.renderer.camera_x -= 50
        elif event.key == pygame.K_UP:
            self.renderer.camera_y += 50
        elif event.key == pygame.K_DOWN:
            self.renderer.camera_y -= 50
        elif event.key == pygame.K_HOME:
            self.renderer.camera_x = 0
            self.renderer.camera_y = 0
            self.renderer.zoom_level = 1.0
        elif pygame.K_1 <= event.key <= pygame.K_3:
            # Upgrade bench shortcuts
            slot_idx = event.key - pygame.K_1
            if self.game.upgrade_bench[slot_idx] is not None:
                self.game.selected_upgrade = slot_idx if self.game.selected_upgrade != slot_idx else None

    def _handle_mousewheel(self, event):
        """Handle mouse wheel zoom."""
        old_zoom = self.renderer.zoom_level
        self.renderer.zoom_level = max(0.5, min(2.0, self.renderer.zoom_level + event.y * 0.1))

        # Zoom towards mouse cursor
        mx, my = pygame.mouse.get_pos()
        if my >= self.renderer.grid_y and mx < self.renderer.GRID_W:
            wx, wy = self.renderer.screen_to_world(mx, my)
            self.renderer.camera_x = mx - (wx * self.renderer.TILE * self.renderer.zoom_level)
            self.renderer.camera_y = my - self.renderer.grid_y - (wy * self.renderer.TILE * self.renderer.zoom_level)

    def _handle_mousebuttondown(self, event, frame):
        """Handle mouse button down events."""
        mx, my = event.pos

        # Right click - rotate selected tile
        if event.button == 3:
            if self.game.selected_map_tile is not None:
                self.game.selected_tile_rotation = (self.game.selected_tile_rotation + 1) % 4
            return

        # Left click
        if event.button == 1:
            self._handle_left_click(mx, my, frame)

    def _handle_left_click(self, mx, my, frame):
        """Handle left mouse button clicks."""
        # Upgrade dialog (when open)
        if self.game.upgrade_dialog_tower is not None:
            self._handle_upgrade_dialog_click(mx, my)
            return

        # Right panel: Play/Pause, Next Wave, Auto
        if mx >= self.renderer.GRID_W:
            self._handle_right_panel_click(mx, my)
            return

        # Shop
        if my < self.renderer.SHOP_H:
            self._handle_shop_click(mx, my)
            return

        # Bench
        if self.renderer.SHOP_H <= my < self.renderer.SHOP_H + self.renderer.BENCH_H:
            self._handle_bench_click(mx, my, frame)
            return

        # Map Tile Bench (includes shop mode toggle) - only when in bench x-range
        map_bench_right = self.renderer.map_bench_x + 3 * 80 + 20 + 35  # includes T/M/U toggle
        if (my >= self.renderer.map_bench_y and my < self.renderer.map_bench_y + 80
                and mx < map_bench_right):
            self._handle_map_bench_click(mx, my)
            return

        # Upgrade Bench
        upgrade_bench_y = self.renderer.HEIGHT - 100
        if mx >= self.renderer.GRID_W and my >= upgrade_bench_y and my < upgrade_bench_y + 80:
            self._handle_upgrade_bench_click(mx, my)

        # Grid
        if my >= self.renderer.grid_y and mx < self.renderer.GRID_W:
            self._handle_grid_click(mx, my, frame)

    def _handle_upgrade_dialog_click(self, mx, my):
        """Handle clicks in the upgrade dialog."""
        t = self.game.upgrade_dialog_tower
        base_height = 280
        upgrade_height = 20 + (len(t.upgrades) * 16) if t.upgrades else 0
        dialog_height = base_height + upgrade_height
        dialog_rect = pygame.Rect(self.renderer.GRID_W + 8, 162, 164, dialog_height)

        if dialog_rect.collidepoint(mx, my):
            # Direction selector for Track towers
            if t.fire_type == "Track":
                for d in range(4):
                    dx = self.renderer.GRID_W + 14 + d * 35
                    dy = 318
                    r = pygame.Rect(dx, dy, 30, 20)
                    if r.collidepoint(mx, my):
                        t.track_direction = d
                        return

            # Sell and Close buttons
            button_y = 266 + upgrade_height
            sell_r = pygame.Rect(self.renderer.GRID_W + 10, button_y, 75, 24)
            close_r = pygame.Rect(self.renderer.GRID_W + 95, button_y, 75, 24)
            if sell_r.collidepoint(mx, my):
                self.game.economy.sell_tower_from_grid(t.x, t.y)
                self.game.upgrade_dialog_tower = None
            elif close_r.collidepoint(mx, my):
                self.game.upgrade_dialog_tower = None
        else:
            # Clicked outside dialog
            self.game.upgrade_dialog_tower = None

    def _handle_right_panel_click(self, mx, my):
        """Handle clicks in the right panel."""
        play_rect = pygame.Rect(self.renderer.GRID_W + 14, 96, 100, 26)
        next_rect = pygame.Rect(self.renderer.GRID_W + 14, 128, 100, 26)
        auto_rect = pygame.Rect(self.renderer.GRID_W + 14, 160, 100, 26)

        if play_rect.collidepoint(mx, my):
            self.game.paused = not self.game.paused
        elif next_rect.collidepoint(mx, my):
            self.game.wave_manager.start_next_wave()
        elif auto_rect.collidepoint(mx, my):
            self.game.auto_mode = not self.game.auto_mode

    def _handle_shop_click(self, mx, my):
        """Handle clicks in the shop."""
        for i in range(5):
            x = 15 + i * 80
            y = 15
            if x <= mx <= x+70 and y <= my <= y+100:
                self.game.economy.move_to_bench(i)
                return

        # Reroll
        rx = 15 + 5*80
        if rx <= mx <= rx+35 and 65 <= my <= 100:
            self.game.economy.reroll_shop()

    def _handle_bench_click(self, mx, my, frame):
        """Handle clicks in the bench."""
        # Check for merge/egrem clicks first
        handled_merge = False
        if self.game.merge_preview or self.game.egrem_preview:
            idx1, idx2 = self.game.merge_tower_1, self.game.merge_tower_2
            if idx1 is not None and idx2 is not None:
                cx1 = 45 + min(idx1, idx2) * 68
                cx2 = 45 + max(idx1, idx2) * 68
                mid_x = (cx1 + cx2) // 2
                mid_y = self.renderer.SHOP_H + 60

                if self.game.merge_preview:
                    merge_txt = self.renderer.font_merge.render("Merge", True, (0, 0, 0))
                    merge_rect = merge_txt.get_rect(center=(mid_x, mid_y))
                    merge_rect.inflate_ip(18, 13)
                    if merge_rect.collidepoint(mx, my):
                        self.game.economy.confirm_merge()
                        handled_merge = True
                elif self.game.egrem_preview:
                    egrem_txt = self.renderer.font_merge.render("egrem", True, (0, 0, 0))
                    egrem_rect = egrem_txt.get_rect(center=(mid_x, mid_y))
                    egrem_rect.inflate_ip(18, 13)
                    if egrem_rect.collidepoint(mx, my):
                        self.game.economy._complete_egrem()
                        handled_merge = True

        # Handle bench card clicks if merge not handled
        if not handled_merge:
            clicked_on_bench_card = False
            for i in range(10):
                x = 15 + i * 68
                y = self.renderer.SHOP_H + 15
                if x <= mx <= x+60 and y <= my <= y+90:
                    if self.game.bench[i]:
                        clicked_on_bench_card = True
                        self.game.economy.select_for_merge(i, frame)

            # Handle cancel if clicked outside merge/egrem area
            if (self.game.merge_preview or self.game.egrem_preview) and not clicked_on_bench_card:
                self.game.economy.cancel_merge()

    def _handle_map_bench_click(self, mx, my):
        """Handle clicks in the map tile bench and shop mode toggle."""
        # Shop mode toggle (drawn next to map tile bench)
        tx = self.renderer.map_bench_x + 3 * 80 + 20
        ty = self.renderer.map_bench_y
        if tx <= mx <= tx + 35 and ty <= my <= ty + 35:
            if self.game.shop_mode == "towers":
                self.game.shop_mode = "tiles"
            elif self.game.shop_mode == "tiles":
                self.game.shop_mode = "upgrades"
            else:
                self.game.shop_mode = "towers"
            self.game.shop = [None] * 5
            self.game.economy.generate_shop()
            return

        for i in range(3):
            x = self.renderer.map_bench_x + i * 80
            y = self.renderer.map_bench_y
            if x <= mx <= x+70 and y <= my <= y+80:
                if self.game.map_tile_bench[i] is not None:
                    self.game.selected_map_tile = i
                    self.game.selected_tile_rotation = 0
                    return

        # Rotate buttons
        rot_x = self.renderer.map_bench_x + 3*80 + 10
        rot_y = self.renderer.map_bench_y + 5
        in_rotate_region = rot_y <= my <= rot_y + 26 and (rot_x <= mx <= rot_x + 26 or rot_x + 34 <= mx <= rot_x + 60)
        if self.game.selected_map_tile is not None and in_rotate_region:
            if rot_x <= mx <= rot_x + 26:
                self.game.selected_tile_rotation = (self.game.selected_tile_rotation - 1) % 4
            elif rot_x + 34 <= mx <= rot_x + 60:
                self.game.selected_tile_rotation = (self.game.selected_tile_rotation + 1) % 4

    def _handle_upgrade_bench_click(self, mx, my):
        """Handle clicks in the upgrade bench."""
        upgrade_bench_x = self.renderer.GRID_W + 10
        upgrade_bench_y = self.renderer.HEIGHT - 100

        for i in range(3):
            x = upgrade_bench_x + i * 55
            y = upgrade_bench_y
            if x <= mx <= x+50 and y <= my <= y+80:
                self.game.selected_upgrade = i if self.game.selected_upgrade != i else None
                return

    def _handle_grid_click(self, mx, my, frame):
        """Handle clicks on the game grid."""
        gx, gy = self.renderer.screen_to_world(mx, my)
        gx, gy = int(gx), int(gy)

        # Place map tile
        if self.game.selected_map_tile is not None:
            tile_data = self.game.map_tile_bench[self.game.selected_map_tile]
            if tile_data and self.game.can_place_tile(tile_data, gx, gy, self.game.selected_tile_rotation):
                self.game.place_map_tile(tile_data, gx, gy, self.game.selected_tile_rotation)

                # Check if expansion needed
                tile_cells = self.game._get_tile_path_cells(tile_data, gx, gy, self.game.selected_tile_rotation)
                if self.game.should_expand_map(tile_cells):
                    self.game.expand_grid(tile_cells)
                    self.renderer.update_dimensions()

                # Remove tile from bench
                self.game.map_tile_bench[self.game.selected_map_tile] = None
                self.game.selected_map_tile = None
                self.game.selected_tile_rotation = 0
            return

        # Place tower from bench
        if (self.game.selected_tower is not None and
            self.game.merge_preview is None and
            not self.game.egrem_preview):
            self.game.economy.place_tower(gx, gy, self.game.selected_tower)
            return

        # Clear merge/egrem selections
        if self.game.merge_preview or self.game.egrem_preview or self.game.merge_tower_1 is not None:
            self.game.economy.cancel_merge()

        # Check for enemy selection
        enemy_selected = False
        if 0 <= gx < self.game.width and 0 <= gy < self.game.height:
            for e in self.game.enemy_grid[gy][gx]:
                if e.alive:
                    self.game.selected_enemy = e
                    self.game.upgrade_dialog_tower = None
                    enemy_selected = True
                    break

        if not enemy_selected:
            # Check for tower selection
            for t in self.game.towers:
                if t.x == gx and t.y == gy:
                    if self.game.selected_upgrade is not None:
                        upgrade_id = self.game.upgrade_bench[self.game.selected_upgrade]
                        if self.game.economy.apply_upgrade_from_bench(t, upgrade_id, self.game.selected_upgrade):
                            self.game.selected_upgrade = None
                    else:
                        self.game.upgrade_dialog_tower = t
                        self.game.upgrade_dialog_choices = self.game.economy.get_upgrade_choices(t)
                    self.game.selected_enemy = None
                    return

            # Empty grid click
            self.game.selected_enemy = None
            self.game.upgrade_dialog_tower = None

    def _handle_mousebuttonup(self, event):
        """Handle mouse button up events."""
        if event.button == 2:  # Middle mouse button
            self.renderer.dragging = False

        elif event.button == 3:  # Right click
            # Cancel merge/egrem
            if self.game.merge_preview or self.game.egrem_preview or self.game.merge_tower_1 is not None:
                self.game.economy.cancel_merge()
                return

            # Sell from bench
            my = event.pos[1]
            if self.renderer.SHOP_H <= my < self.renderer.SHOP_H + self.renderer.BENCH_H:
                mx = event.pos[0]
                for i in range(10):
                    x = 15 + i * 68
                    y = self.renderer.SHOP_H + 15
                    if x <= mx <= x+60 and y <= my <= y+90:
                        self.game.economy.sell_from_bench(i)
                        return

            # Deselect upgrade
            mx, my = event.pos
            upgrade_bench_y = self.renderer.HEIGHT - 100
            if mx >= self.renderer.GRID_W and my >= upgrade_bench_y and my < upgrade_bench_y + 80:
                self.game.selected_upgrade = None
                return

            # Sell tower from grid
            if my >= self.renderer.grid_y and mx < self.renderer.GRID_W:
                gx, gy = self.renderer.screen_to_world(mx, my)
                gx, gy = int(gx), int(gy)
                self.game.economy.sell_tower_from_grid(gx, gy)

    def _handle_mousemotion(self, event):
        """Handle mouse motion events."""
        if self.renderer.dragging:
            dx = event.pos[0] - self.renderer.last_mouse_x
            dy = event.pos[1] - self.renderer.last_mouse_y
            self.renderer.camera_x += dx
            self.renderer.camera_y += dy
            self.renderer.last_mouse_x, self.renderer.last_mouse_y = event.pos