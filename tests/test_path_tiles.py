"""Path tiles as the grow verb: seed, milestone grant, place, leak delay."""
from data.tiles import get_tile_types
from config import REWARD_CONFIG
from core.game import Game
from core.economy import EconomyManager
from models.enemy import Enemy


def _straight():
    for t in get_tile_types(minimal_mode=True):
        if t["name"] == "Straight":
            return t.copy()
    raise AssertionError("Straight tile missing")


def _u_bend():
    for t in get_tile_types(minimal_mode=True):
        if t["name"] == "U-Bend":
            return t.copy()
    raise AssertionError("U-Bend tile missing")


def _find_straight_placement(game, tile):
    """Return (gx, gy, rotation) that appends Straight at path end, or None."""
    ex, ey = game.path[-1]
    # Try neighbor origins for rot 0 (2x1) and rot 1 (1x2 after one clockwise)
    candidates = []
    for rot in range(4):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (0, 0), (-1, -1), (1, -1), (-1, 1)):
            gx, gy = ex + dx, ey + dy
            if game.can_place_tile(tile, gx, gy, rot):
                candidates.append((gx, gy, rot))
    return candidates[0] if candidates else None


def test_new_run_seeds_straight():
    g = Game(minimal_mode=True)
    tiles = [s for s in g.loot_bag if isinstance(s, dict) and s.get("name") == "Straight"]
    assert len(tiles) == int(REWARD_CONFIG.get("starting_path_tiles", 1))


def test_mini_boss_grants_tile_before_upgrade(monkeypatch):
    from unittest.mock import MagicMock
    from config import LOOT_CONFIG, BENCH_CONFIG, ECONOMY_CONFIG

    game = MagicMock()
    game.loot_bag = [None] * int(LOOT_CONFIG.get("bag_slots", 4))
    game.bench = [None] * int(BENCH_CONFIG.get("tower_slots", 5))
    game.minimal_mode = True
    game.current_frame = 0
    game.reward_toast_text = ""
    game.reward_toast_until = 0
    game.paused = False
    eco = EconomyManager(game)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_wave_interval", 5)
    monkeypatch.setitem(REWARD_CONFIG, "boss_wave_interval", 99)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_tile_count", 1)
    monkeypatch.setitem(REWARD_CONFIG, "mini_boss_upgrade_count", 1)
    eco.grant_wave_upgrade_rewards(5)
    kinds = []
    for s in game.loot_bag:
        if isinstance(s, dict) and "width" in s:
            kinds.append("tile")
        elif isinstance(s, str):
            kinds.append("upgrade")
    assert kinds.count("tile") >= 1
    assert kinds.count("upgrade") >= 1
    # Tile wins the earlier slot
    first_filled = next(i for i, s in enumerate(game.loot_bag) if s is not None)
    assert isinstance(game.loot_bag[first_filled], dict)


def test_straight_extends_path():
    g = Game(minimal_mode=True)
    tile = _straight()
    before = len(g.path)
    place = _find_straight_placement(g, tile)
    assert place is not None, "no legal Straight attach at path end"
    gx, gy, rot = place
    g.place_map_tile(tile, gx, gy, rot)
    assert len(g.path) == before + 2


def test_disconnected_tile_rejected():
    g = Game(minimal_mode=True)
    tile = _straight()
    ex, ey = g.path[-1]
    far_x = min(g.width - 2, ex + 6)
    far_y = min(g.height - 1, ey + 6)
    if abs(far_x - ex) + abs(far_y - ey) < 3:
        far_x, far_y = 0, 0
    assert g.can_place_tile(tile, far_x, far_y, 0) is False


def test_place_delays_leak_for_live_enemy():
    g = Game(minimal_mode=True)
    tile = _straight()
    place = _find_straight_placement(g, tile)
    assert place is not None
    old_len = len(g.path)

    e = Enemy(g.path, "Drone", 1)
    e.position_index = old_len - 1
    e.move_speed = 1
    e.move_counter = 0.0
    e.speed_mult = 1.0
    gx, gy, rot = place
    g.place_map_tile(tile, gx, gy, rot)
    assert len(g.path) == old_len + 2
    # Shared list grew: one step from the old end is no longer a leak
    e.move()
    assert e.leaked is False
    assert e.position_index == old_len
    e.move_counter = 0.0
    e.move()
    assert e.leaked is False
    e.move_counter = 0.0
    e.move()
    assert e.leaked is True


def test_u_bend_has_two_endpoints():
    tile = _u_bend()
    cells = Game._get_tile_path_cells(tile, 0, 0, 0)
    ends = Game._get_endpoints(cells)
    assert len(ends) == 2
    assert sum(1 for row in tile["path_grid"] for c in row if c) == 3
