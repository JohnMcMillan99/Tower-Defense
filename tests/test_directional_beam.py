"""Thermal Regulator DirectionalBeam pierce + flame FX."""
from models.tower import Tower
from models.enemy import Enemy


class _FakeEnemy:
    def __init__(self, x, y, hp=100):
        self.path = [(x, y)] * 5
        self.position_index = 0
        self.enemy_type = "Drone"
        self.wave_num = 1
        self.alive = True
        self.leaked = False
        self.health = hp
        self.max_health = hp
        self.resistances = {}
        self.debuffs = {}
        self.is_egrem_spawned = False
        self.speed_mult = 1.0
        self.web_mode = False
        self.difficulty = 1

    def get_position(self):
        return self.path[self.position_index]

    def take_damage(self, dmg, attacker_tags=None):
        self.health -= dmg
        if self.health <= 0:
            self.alive = False
            return True
        return False


class _FakeGame:
    def __init__(self, w=10, h=10):
        self.width = w
        self.height = h
        self.enemy_grid = [[[] for _ in range(w)] for _ in range(h)]
        self.enemies = []


def test_directional_beam_hits_all_in_line():
    game = _FakeGame()
    tower = Tower(2, 5, "Thermal Regulator")
    tower.track_direction = 1  # E
    tower.cooldown = 0
    tower.heat = 0
    # Three enemies east of tower within range 3
    e1 = _FakeEnemy(3, 5, hp=50)
    e2 = _FakeEnemy(4, 5, hp=50)
    e3 = _FakeEnemy(5, 5, hp=50)
    # One off-line (should not be hit)
    e4 = _FakeEnemy(4, 6, hp=50)
    for e in (e1, e2, e3, e4):
        game.enemy_grid[e.path[0][1]][e.path[0][0]].append(e)

    tower.update([], current_frame=10, game=game)

    assert e1.health < 50
    assert e2.health < 50
    assert e3.health < 50
    assert e4.health == 50  # off the beam line


def test_directional_beam_sets_flame_fx_to_max_range():
    game = _FakeGame()
    tower = Tower(2, 5, "Thermal Regulator")
    tower.track_direction = 1  # E
    tower.cooldown = 0
    tower.range = 3
    tower.update([], current_frame=42, game=game)
    assert tower.last_shot_style == "flame_beam"
    assert tower.last_shot_frame == 42
    assert tower.last_shot_target == (2 + 3, 5)  # max range tip


def test_directional_beam_west():
    game = _FakeGame()
    tower = Tower(5, 5, "Thermal Regulator")
    tower.track_direction = 0  # W
    tower.cooldown = 0
    tower.range = 2
    e1 = _FakeEnemy(4, 5, hp=40)
    e2 = _FakeEnemy(3, 5, hp=40)
    game.enemy_grid[5][4].append(e1)
    game.enemy_grid[5][3].append(e2)
    tower.update([], 1, game)
    assert e1.health < 40 and e2.health < 40
    assert tower.last_shot_target == (5 - 2, 5)
