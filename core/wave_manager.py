import random
from models.enemy import Enemy
from models.assimilator import Assimilator


class WaveManager:
    def __init__(self, game):
        self.game = game

    def start_next_wave(self):
        if self.game.wave_active:
            return
        self.game.wave_active = True
        if self.game.web_mode:
            wave_size = max(3, (5 + self.game.round_num) // 2)
        else:
            wave_size = 5 + self.game.round_num * 2
        types = ["Drone"]
        if self.game.round_num >= 3: types.append("Scout")
        if self.game.round_num >= 5: types.append("Harvester")
        if self.game.round_num >= 7: types.append("Adaptor")
        if self.game.round_num >= 9: types.append("Assimilator")
        self.game.spawn_queue = []
        for _ in range(wave_size):
            enemy_type = random.choice(types)
            if enemy_type == "Assimilator":
                enemy = Assimilator(self.game.path, self.game.round_num, web_mode=self.game.web_mode)
                enemy.set_game_reference(self.game)
            else:
                enemy = Enemy(self.game.path, enemy_type, self.game.round_num, web_mode=self.game.web_mode)
            self.game.spawn_queue.append(enemy)
        # Egrem towers on grid spawn 1-2 mini-boss style enemies per wave (fewer, stronger)
        for t in self.game.towers:
            if t.base_type == "Nanite Swarm":
                if self.game.web_mode:
                    spawn_count = random.randint(0, 1)
                else:
                    spawn_count = random.randint(1, 2)
                for _ in range(spawn_count):
                    self.game.spawn_queue.append(Enemy(self.game.path, "Assimilator", self.game.round_num + 2, web_mode=self.game.web_mode))
        self.game.spawn_timer = 0

    def update_wave(self, frame):
        if not self.game.wave_active or self.game.paused:
            return
        self.game.spawn_timer += 1
        if self.game.spawn_queue and self.game.spawn_timer >= self.game.spawn_interval:
            self.game.spawn_timer = 0
            self.game.enemies.append(self.game.spawn_queue.pop(0))

        # Update towers (including egrem spawning)
        for t in self.game.towers:
            t.update(self.game.enemies, frame, self.game)

        # Apply auras
        for t in self.game.towers:
            if "resist_2" in t.upgrades:
                for dy in range(-t.range, t.range + 1):
                    for dx in range(-t.range, t.range + 1):
                        if abs(dx) + abs(dy) > t.range:
                            continue
                        nx, ny = t.x + dx, t.y + dy
                        if 0 <= nx < len(self.game.enemy_grid[0]) and 0 <= ny < len(self.game.enemy_grid):
                            for e in self.game.enemy_grid[ny][nx]:
                                if e.alive and not e.leaked:
                                    e.apply_debuff('slow', 30, 60)

        # Update enemy grid
        for row in self.game.enemy_grid:
            for cell in row:
                cell.clear()
        for e in self.game.enemies:
            pos = e.get_position()
            if pos:
                self.game.enemy_grid[pos[1]][pos[0]].append(e)

        # Assimilator latch logic (Circuit Stronghold)
        if hasattr(self.game, 'board') and self.game.board:
            assim_data = self.game.data_loader.get_assimilator_data() or {}
            base_chance = assim_data.get('chance_base', 0.4)

            for e in self.game.enemies[:]:
                if getattr(e, 'enemy_type', None) == 'Assimilator' and not getattr(e, 'is_latched', False):
                    pos = e.get_position()
                    if pos:
                        ax, ay = pos
                        tx, ty, ttype = self.game.board.scan_latch_targets(ax, ay)
                        if tx is not None:
                            # Check for repel AoE from pure towers
                            repel_active = False
                            for t in self.game.towers:
                                if t.camouflage_repels():
                                    # Check if assimilator is within tower's repel range
                                    distance = abs(t.x - ax) + abs(t.y - ay)
                                    if distance <= t.range:
                                        repel_active = True
                                        break

                            if not repel_active:
                                # Roll assimilate chance
                                if random.random() < base_chance:
                                    if e.latch_to(tx, ty, ttype, self.game.board.wall_manager):
                                        # Update stack_count from target
                                        if ttype == 'wall':
                                            wall = self.game.board.wall_manager.get_wall(tx, ty)
                                            if wall:
                                                e.stack_count = wall.get_latch_count()
                                        # Set game reference for tower access
                                        e.set_game_reference(self.game)

        # Update latched assimilators
        for e in self.game.enemies[:]:
            if getattr(e, 'is_latched', False):
                e.update_latch(self.game.board.wall_manager)

        # Integrity drain (0.02/stack)
        self.game.integrity_tick()

        for e in self.game.enemies[:]:
            e.move()
            if e.leaked:
                self.game.lives -= 1
                self.game.enemies.remove(e)
        for e in self.game.enemies[:]:
            if not e.alive:
                gold = max(1, (3 + e.difficulty * 3) // 2)  # scaled back ~half
                self.game.gold += gold
                self.game.enemies.remove(e)
        if self.game.lives <= 0:
            self.game.game_over = True
            self.game.final_wave = self.game.round_num
            self.game.final_gold = self.game.gold
            self.game.wave_active = False
        if self.game.wave_active and not self.game.enemies and not self.game.spawn_queue:
            bonus = (len(self.game.towers) * 3 + self.game.round_num * 4) // 2   # scaled back ~half
            self.game.gold += bonus
            self.game.wave_bonus_text = f"+{bonus} bonus"
            self.game.wave_bonus_show_until = frame + 240
            self.game.round_num += 1
            self.game.wave_active = False
            # Auto-start next wave if auto mode is enabled
            if self.game.auto_mode:
                self.start_next_wave()

    def spawn_enemy_at_position(self, enemy_type, x, y, wave_num=1):
        """Spawn an enemy at a specific grid position (for egrem towers)."""
        if 0 <= x < self.game.width and 0 <= y < self.game.height:
            # Find the closest path point to this position
            closest_pos = min(self.game.path, key=lambda p: abs(p[0]-x) + abs(p[1]-y))
            closest_idx = self.game.path.index(closest_pos)
            if enemy_type == "Assimilator":
                enemy = Assimilator(self.game.path[closest_idx:], wave_num, is_egrem_spawned=True, web_mode=self.game.web_mode)
                enemy.set_game_reference(self.game)
            else:
                enemy = Enemy(self.game.path[closest_idx:], enemy_type, wave_num, is_egrem_spawned=True, web_mode=self.game.web_mode)
            self.game.enemies.append(enemy)
            # Add to enemy_grid immediately so towers can target it
            pos = enemy.get_position()
            if pos and 0 <= pos[0] < self.game.width and 0 <= pos[1] < self.game.height:
                self.game.enemy_grid[pos[1]][pos[0]].append(enemy)
            return enemy
        return None