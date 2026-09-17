#!/usr/bin/env python3
"""Headless latch probe — force an Assimilator past a path-adjacent hybrid.

Usage:
  .venv\\Scripts\\python.exe tools/latch_probe.py
  .venv\\Scripts\\python.exe tools/latch_probe.py --frames 600 --chance 1.0

Prints latch_stats and whether a stick/soak happened. Writes debug.log when
LATCH_CONFIG.debug is on (this script enables it).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import LATCH_CONFIG, DEBUG
import config as cfg
from core.game import Game
from core.run_setup import RunSetup
from models.assimilator import Assimilator
from models.tower import Tower
from data.loader import DataLoader


def _place_hybrid_on_path(game: Game) -> Tower:
    """Put a latchable hybrid beside the first path cell that has a free neighbor."""
    Tower.set_data_loader(DataLoader())
    hybrid = Tower.merge_towers(
        Tower(0, 0, "Neural Processor"),
        Tower(0, 0, "Plasma Capacitor"),
    )
    assert hybrid.can_be_latched()
    for px, py in game.path:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tx, ty = px + dx, py + dy
            if not (0 <= tx < game.width and 0 <= ty < game.height):
                continue
            if game.grid[ty][tx] != ".":
                continue
            hybrid.x, hybrid.y = tx, ty
            hybrid.game = game
            hybrid.dmg = 0  # don't shoot the probe assimilator
            game.towers.append(hybrid)
            game.grid[ty][tx] = "T"
            return hybrid
    raise RuntimeError("no free cell adjacent to path")


def main(argv=None):
    p = argparse.ArgumentParser(description="Probe assimilator latch against a hybrid tower")
    p.add_argument("--frames", type=int, default=400)
    p.add_argument("--chance", type=float, default=1.0, help="Override LATCH_CONFIG.chance_base")
    p.add_argument("--log", action="store_true", help="Also set config.DEBUG")
    args = p.parse_args(argv)

    LATCH_CONFIG["enabled"] = True
    LATCH_CONFIG["debug"] = True
    LATCH_CONFIG["chance_base"] = float(args.chance)
    if args.log:
        cfg.DEBUG = True

    g = Game(minimal_mode=True, run_setup=RunSetup(seed=1, directive_name="PowerSort"))
    hybrid = _place_hybrid_on_path(g)
    print(f"hybrid at ({hybrid.x},{hybrid.y}) type={hybrid.get_merge_type()}")

    # Drop assimilator at path start; walk until adjacent / latched
    assim = Assimilator(g.path, wave_num=9, web_mode=False)
    assim.set_game_reference(g)
    g.enemies = [assim]
    g.wave_active = True
    g.spawn_queue = []

    for frame in range(args.frames):
        g.current_frame = frame
        # Rebuild enemy grid like a wave tick subset
        for row in g.enemy_grid:
            for cell in row:
                cell.clear()
        for e in g.enemies:
            pos = e.get_position()
            if pos:
                g.enemy_grid[pos[1]][pos[0]].append(e)
        g.wave_manager.update_wave(frame)
        if assim.is_latched:
            break
        if not assim.alive or assim.leaked:
            break

    stats = dict(g.latch_stats)
    report = {
        "stuck": bool(assim.is_latched),
        "progress": round(float(assim.assimilate_progress), 3),
        "target": list(assim.latch_target) if assim.latch_target else None,
        "tower_silence": int(getattr(hybrid, "silence_frames", 0) or 0),
        "pos": list(assim.get_position() or ()),
        "alive": assim.alive,
        "leaked": assim.leaked,
        "stats": stats,
        "debug_log": "debug.log" if (LATCH_CONFIG.get("debug") or DEBUG) else None,
    }
    print(json.dumps(report, indent=2))
    return 0 if stats.get("sticks", 0) > 0 or assim.is_latched else 1


if __name__ == "__main__":
    sys.exit(main())
