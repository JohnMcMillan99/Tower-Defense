# ==============================
# ENEMY
# ==============================
class Enemy:
    TYPES = {
        "Drone":    {"health": 10, "speed": 10, "difficulty": 1, "display": "Drone", "symbol": "D"},
        "Scout":    {"health": 8,  "speed": 6,  "difficulty": 1, "display": "Scout", "symbol": "S"},
        "Harvester": {"health": 15, "speed": 12, "difficulty": 2, "display": "Harvester", "symbol": "H"},
        "Adaptor":  {"health": 20, "speed": 8,  "difficulty": 2, "display": "Adaptor", "symbol": "A"},
        "Assimilator": {"health": 25, "speed": 10, "difficulty": 3, "display": "Assimilator", "symbol": "X"},
    }

    def __init__(self, path, enemy_type="Drone", wave_num=1, is_egrem_spawned=False, web_mode=False):
        self.path = path
        self.position_index = 0
        self.enemy_type = enemy_type if enemy_type in self.TYPES else "Drone"
        self.wave_num = wave_num
        self.alive = True
        self.leaked = False
        self.move_counter = 0.0
        self.is_egrem_spawned = is_egrem_spawned
        self.debuffs = {}  # debuff_type: {'amount': val, 'frames_left': int}
        self.web_mode = web_mode
        self._calculate_stats()

    def _calculate_stats(self):
        from data.units import WEB_MODE_CONFIG
        base_stats = self.TYPES.get(self.enemy_type, self.TYPES["Drone"])
        difficulty = base_stats["difficulty"]
        wave_scale = 1.0 + (self.wave_num - 1) * 3.5 * difficulty

        # Apply web mode scaling if enabled
        web_scale = WEB_MODE_CONFIG["enemy_scale"] if self.web_mode else 1.0

        self.max_health = int(base_stats["health"] * wave_scale * web_scale)
        self.health = self.max_health
        self.move_speed = int(base_stats["speed"] * web_scale)
        self.difficulty = difficulty
        self.display_name = base_stats["display"]
        self.symbol = base_stats["symbol"]

    def move(self):
        if not self.alive or self.leaked:
            return
        increment = 1.0
        if 'slow' in self.debuffs:
            slow_pct = self.debuffs['slow']['amount'] / 100.0
            increment = 1.0 * (1 - slow_pct)
            self.debuffs['slow']['frames_left'] -= 1
            if self.debuffs['slow']['frames_left'] <= 0:
                del self.debuffs['slow']
        self.move_counter += increment
        if self.move_counter >= self.move_speed:
            self.move_counter -= self.move_speed
            self.position_index += 1
            if self.position_index >= len(self.path):
                self.leaked = True
                self.alive = False

    def get_position(self):
        if 0 <= self.position_index < len(self.path):
            return self.path[self.position_index]
        return None

    def take_damage(self, dmg):
        self.health -= dmg
        if self.health <= 0:
            self.alive = False
            return True
        return False

    def apply_debuff(self, debuff_type, amount, duration):
        if debuff_type not in self.debuffs:
            self.debuffs[debuff_type] = {'amount': amount, 'frames_left': duration}
        else:
            if duration > self.debuffs[debuff_type]['frames_left']:
                self.debuffs[debuff_type]['frames_left'] = duration
            self.debuffs[debuff_type]['amount'] = max(self.debuffs[debuff_type]['amount'], amount)