"""Programmatic latch probe — wave tick sticks an Assimilator to a hybrid."""
from config import LATCH_CONFIG
from core.game import Game
from core.run_setup import RunSetup
from models.assimilator import Assimilator
from models.tower import Tower
from data.loader import DataLoader


def test_wave_tick_latch_sticks_to_adjacent_hybrid(monkeypatch):
    Tower.set_data_loader(DataLoader())
    monkeypatch.setitem(LATCH_CONFIG, "enabled", True)
    monkeypatch.setitem(LATCH_CONFIG, "chance_base", 1.0)
    monkeypatch.setitem(LATCH_CONFIG, "debug", False)

    g = Game(minimal_mode=True, run_setup=RunSetup(seed=2, directive_name="PowerSort"))
    hybrid = Tower.merge_towers(
        Tower(0, 0, "Neural Processor"),
        Tower(0, 0, "Plasma Capacitor"),
    )
    hybrid.dmg = 0
    # Sit beside path[0]
    px, py = g.path[0]
    placed = False
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        tx, ty = px + dx, py + dy
        if 0 <= tx < g.width and 0 <= ty < g.height and g.grid[ty][tx] == ".":
            hybrid.x, hybrid.y = tx, ty
            hybrid.game = g
            g.towers.append(hybrid)
            placed = True
            break
    assert placed

    assim = Assimilator(g.path, wave_num=9)
    assim.set_game_reference(g)
    assim.position_index = 0
    g.enemies = [assim]
    g.wave_active = True
    g.spawn_queue = []

    for frame in range(5):
        g.wave_manager.update_wave(frame)
        if assim.is_latched:
            break

    assert assim.is_latched is True
    assert assim.latch_target == (hybrid.x, hybrid.y)
    assert g.latch_stats["sticks"] >= 1
    assert g.latch_stats["targets"] >= 1
