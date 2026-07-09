import pygame
from config import log_debug


class EventHandler:
    def __init__(self, game, renderer):
        self.game = game
        self.renderer = renderer
        self.running = True

    @property
    def layout(self):
        return self.renderer.layout

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
        elif pygame.K_1 <= event.key <= pygame.K_4:
            slot_idx = event.key - pygame.K_1
            bag = getattr(self.game, "loot_bag", self.game.upgrade_bench)
            if slot_idx < len(bag) and bag[slot_idx] is not None:
                self.game.economy.select_loot(slot_idx)

    def _handle_mousewheel(self, event):
        """Handle mouse wheel zoom (or inspector stats scroll)."""
        mx, my = pygame.mouse.get_pos()
        L = self.layout
        if self.game.inspector_mode == "stats" and L.inspector_rect().collidepoint(mx, my):
            max_s = self.renderer.tower_stats_max_scroll()
            self.game.inspector_scroll = max(
                0, min(max_s, self.game.inspector_scroll - event.y * 18)
            )
            return

        self.renderer.zoom_level = max(0.5, min(2.0, self.renderer.zoom_level + event.y * 0.1))
        if my >= L.grid_y and mx < L.GRID_W:
            wx, wy = self.renderer.screen_to_world(mx, my)
            self.renderer.camera_x = mx - (wx * self.renderer.TILE * self.renderer.zoom_level)
            self.renderer.camera_y = my - L.grid_y - (wy * self.renderer.TILE * self.renderer.zoom_level)

    def _handle_mousebuttondown(self, event, frame):
        mx, my = event.pos
        if event.button == 3:
            if self.game.selected_map_tile is not None:
                self.game.selected_tile_rotation = (self.game.selected_tile_rotation + 1) % 4
            return
        if event.button == 1:
            self._handle_left_click(mx, my, frame)

    def restart_game(self):
        """Rebuild Game and rebind renderer after game over."""
        from core.game import Game
        web_mode = getattr(self.game, "web_mode", False)
        minimal_mode = getattr(self.game, "minimal_mode", False)
        new_game = Game(web_mode=web_mode, minimal_mode=minimal_mode)
        self.game = new_game
        self.renderer.game = new_game
        if hasattr(self.renderer, "update_dimensions"):
            self.renderer.update_dimensions()
        self.renderer.camera_x = 0
        self.renderer.camera_y = 0
        self.renderer.zoom_level = 1.0

    def _handle_left_click(self, mx, my, frame):
        log_debug("Left click detected", {"mouse_x": mx, "mouse_y": my}, location="events.py:_handle_left_click")
        L = self.layout

        if self.game.game_over:
            self.restart_game()
            return

        # Inspector panel (tabs / content / close) before other right-column handlers
        if self.game.inspector_mode and L.inspector_rect().collidepoint(mx, my):
            self._handle_inspector_click(mx, my)
            return

        if L.upgrade_bench_region().collidepoint(mx, my):
            return

        if mx >= L.GRID_W:
            self._handle_right_panel_click(mx, my, frame)
            return

        # Top row: shop (left 5/8) | map tiles (right 3/8)
        if my < L.SHOP_H:
            if L.map_column_region().collidepoint(mx, my):
                self._handle_map_bench_click(mx, my)
            else:
                self._handle_shop_click(mx, my)
            return

        if L.SHOP_H <= my < L.SHOP_H + L.BENCH_H:
            self._handle_bench_click(mx, my, frame)
            return

        if my >= L.grid_y and mx < L.GRID_W:
            self._handle_grid_click(mx, my, frame)

    def _handle_inspector_click(self, mx, my):
        L = self.layout
        tabs = L.inspector_tab_rects()
        for name, tab in tabs.items():
            if tab.collidepoint(mx, my):
                if name == "stats":
                    self.game.open_inspector("stats")
                elif name == "tower":
                    self.game.open_inspector("tower", self.game.inspector_tower)
                elif name == "enemy":
                    self.game.open_inspector("enemy", self.game.inspector_enemy)
                return

        if L.inspector_close_rect().collidepoint(mx, my):
            self.game.close_inspector()
            return

        if self.game.inspector_mode == "tower" and self.game.inspector_tower is not None:
            t = self.game.inspector_tower
            if t.fire_type in ("Track", "DirectionalBeam"):
                for d, r in enumerate(L.inspector_direction_rects()):
                    if r.collidepoint(mx, my):
                        t.track_direction = d
                        return
            sell_r, _ = L.inspector_sell_close_rects()
            if sell_r.collidepoint(mx, my):
                self.game.economy.sell_tower_from_grid(t.x, t.y)
                self.game.close_inspector()
                return

    def _handle_right_panel_click(self, mx, my, frame):
        L = self.layout
        if L.stats_toggle_rect().collidepoint(mx, my):
            if self.game.inspector_mode == "stats":
                self.game.close_inspector()
            else:
                self.game.open_inspector("stats")
            return

        play, next_wave, auto = L.panel_control_rects(show_spl=L.show_spl(self.game))
        if play.collidepoint(mx, my):
            self.game.paused = not self.game.paused
        elif next_wave.collidepoint(mx, my):
            self.game.wave_manager.start_next_wave(frame)
        elif auto.collidepoint(mx, my):
            self.game.auto_mode = not self.game.auto_mode

    def _handle_shop_click(self, mx, my):
        L = self.layout
        for i in range(5):
            if L.shop_card_rect(i).collidepoint(mx, my):
                self.game.economy.move_to_bench(i)
                return
        if L.reroll_rect().collidepoint(mx, my):
            self.game.economy.reroll_shop()

    def _handle_bench_click(self, mx, my, frame):
        L = self.layout
        if self.game.merge_preview or self.game.egrem_preview:
            idx1, idx2 = self.game.merge_tower_1, self.game.merge_tower_2
            if idx1 is not None and idx2 is not None:
                cx1, mid_y = L.bench_card_center(min(idx1, idx2))
                cx2, _ = L.bench_card_center(max(idx1, idx2))
                mid_x = (cx1 + cx2) // 2
                if self.game.merge_preview:
                    merge_txt = self.renderer.font_merge.render("Merge", True, (0, 0, 0))
                    merge_rect = merge_txt.get_rect(center=(mid_x, mid_y))
                    merge_rect.inflate_ip(18, 13)
                    if merge_rect.collidepoint(mx, my):
                        self.game.economy.confirm_merge()
                        return
                elif self.game.egrem_preview:
                    egrem_txt = self.renderer.font_merge.render("egrem", True, (0, 0, 0))
                    egrem_rect = egrem_txt.get_rect(center=(mid_x, mid_y))
                    egrem_rect.inflate_ip(18, 13)
                    if egrem_rect.collidepoint(mx, my):
                        self.game.economy._complete_egrem()
                        return

        clicked_on_bench_card = False
        for i in range(len(self.game.bench)):
            if L.bench_card_rect(i).collidepoint(mx, my):
                if self.game.bench[i] is not None:
                    clicked_on_bench_card = True
                    self.game.economy.select_for_merge(i, frame)
                break

        if not clicked_on_bench_card and (
            self.game.merge_preview or self.game.egrem_preview
            or self.game.incompatible_preview or self.game.merge_tower_1 is not None
        ):
            self.game.economy.cancel_merge()

    def _handle_map_bench_click(self, mx, my):
        L = self.layout
        bag = getattr(self.game, "loot_bag", self.game.map_tile_bench)
        for i in range(len(bag)):
            if L.loot_card_rect(i).collidepoint(mx, my):
                if bag[i] is not None:
                    self.game.economy.select_loot(i)
                return

        left_r, right_r = L.rotate_button_rects()
        if self.game.selected_map_tile is not None:
            if left_r.collidepoint(mx, my):
                self.game.selected_tile_rotation = (self.game.selected_tile_rotation - 1) % 4
            elif right_r.collidepoint(mx, my):
                self.game.selected_tile_rotation = (self.game.selected_tile_rotation + 1) % 4

    def _handle_upgrade_bench_click(self, mx, my):
        return

    def _handle_grid_click(self, mx, my, frame):
        L = self.layout
        gx, gy = self.renderer.screen_to_world(mx, my)
        gx, gy = int(gx), int(gy)

        if self.game.selected_map_tile is not None:
            tile_data = self.game.loot_bag[self.game.selected_map_tile]
            if tile_data and isinstance(tile_data, dict) and self.game.can_place_tile(tile_data, gx, gy, self.game.selected_tile_rotation):
                self.game.place_map_tile(tile_data, gx, gy, self.game.selected_tile_rotation)
                tile_cells = self.game._get_tile_path_cells(tile_data, gx, gy, self.game.selected_tile_rotation)
                if self.game.should_expand_map(tile_cells):
                    self.game.expand_grid(tile_cells)
                    self.renderer.update_dimensions()
                self.game.loot_bag[self.game.selected_map_tile] = None
                self.game.economy.clear_loot_selection()
                self.game.selected_tile_rotation = 0
            return

        if (self.game.selected_tower is not None and
            self.game.merge_preview is None and
            not self.game.egrem_preview and
            not self.game.incompatible_preview):
            self.game.economy.place_tower(gx, gy, self.game.selected_tower)
            return

        if self.game.merge_preview or self.game.egrem_preview or self.game.incompatible_preview or self.game.merge_tower_1 is not None:
            self.game.economy.cancel_merge()

        enemy_selected = False
        if 0 <= gx < self.game.width and 0 <= gy < self.game.height:
            for e in self.game.enemy_grid[gy][gx]:
                if e.alive:
                    self.game.open_inspector("enemy", e)
                    enemy_selected = True
                    break

        if not enemy_selected:
            for t in self.game.towers:
                if t.x == gx and t.y == gy:
                    if self.game.selected_upgrade is not None:
                        upgrade_id = self.game.loot_bag[self.game.selected_upgrade]
                        if self.game.economy.apply_upgrade_from_bench(t, upgrade_id, self.game.selected_upgrade):
                            self.game.economy.clear_loot_selection()
                    else:
                        self.game.open_inspector("tower", t)
                    return
            # Empty grid — leave inspector alone unless clicking away from panel intent
            if self.game.inspector_mode in ("tower", "enemy"):
                self.game.close_inspector()

    def _handle_mousebuttonup(self, event):
        L = self.layout
        if event.button == 2:
            self.renderer.dragging = False
        elif event.button == 3:
            if self.game.merge_preview or self.game.egrem_preview or self.game.incompatible_preview or self.game.merge_tower_1 is not None:
                self.game.economy.cancel_merge()
                return

            my = event.pos[1]
            if L.SHOP_H <= my < L.SHOP_H + L.BENCH_H:
                mx = event.pos[0]
                for i in range(len(self.game.bench)):
                    if L.bench_card_rect(i).collidepoint(mx, my):
                        self.game.economy.sell_from_bench(i)
                        return

            mx, my = event.pos
            if L.map_column_region().collidepoint(mx, my):
                self.game.economy.clear_loot_selection()
                return

            if my >= L.grid_y and mx < L.GRID_W:
                gx, gy = self.renderer.screen_to_world(mx, my)
                gx, gy = int(gx), int(gy)
                self.game.economy.sell_tower_from_grid(gx, gy)

    def _handle_mousemotion(self, event):
        if self.renderer.dragging:
            dx = event.pos[0] - self.renderer.last_mouse_x
            dy = event.pos[1] - self.renderer.last_mouse_y
            self.renderer.camera_x += dx
            self.renderer.camera_y += dy
            self.renderer.last_mouse_x, self.renderer.last_mouse_y = event.pos
