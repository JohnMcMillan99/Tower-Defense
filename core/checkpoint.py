"""WaveClear snapshot — run state only, never combat."""
from __future__ import annotations

from typing import Any, Dict, Optional


def dump_tower(tower) -> Optional[dict]:
    if tower is None:
        return None
    return {
        "x": int(tower.x),
        "y": int(tower.y),
        "base_type": getattr(tower, "base_type", "Neural Processor"),
        "parents": list(getattr(tower, "parents", None) or []),
        "merge_generation": int(getattr(tower, "merge_generation", 0) or 0),
        "upgrades": list(getattr(tower, "upgrades", None) or []),
        "gold_invested": int(getattr(tower, "gold_invested", 0) or 0),
        "heat": float(getattr(tower, "heat", 0) or 0),
        "track_direction": int(getattr(tower, "track_direction", 0) or 0),
        "egrem_source_types": list(getattr(tower, "egrem_source_types", None) or []),
    }


def load_tower(blob, game):
    if not blob:
        return None
    from models.tower import Tower
    tower = Tower(
        int(blob.get("x", 0)),
        int(blob.get("y", 0)),
        blob.get("base_type", "Neural Processor"),
        parents=list(blob.get("parents") or []),
    )
    tower.merge_generation = int(blob.get("merge_generation", 0) or 0)
    tower.upgrades = list(blob.get("upgrades") or [])
    tower.gold_invested = int(blob.get("gold_invested", 0) or 0)
    tower.heat = float(blob.get("heat", 0) or 0)
    tower.track_direction = int(blob.get("track_direction", 0) or 0)
    tower.egrem_source_types = list(blob.get("egrem_source_types") or [])
    tower.game = game
    tower._calculate_stats()
    if tower.base_type == "Nanite Swarm":
        tower._configure_egrem_spawning()
    return tower


def snapshot_run(game) -> Dict[str, Any]:
    setup = getattr(game, "run_setup", None)
    orch = getattr(game, "sort_orchestrator", None)
    return {
        "gold": int(game.gold),
        "lives": int(game.lives),
        "intel": int(getattr(game, "intel", 0) or 0),
        "round_num": int(game.round_num),
        "reroll_cost": int(getattr(game, "reroll_cost", 3) or 3),
        "noise_injections": int(getattr(game, "noise_injections", 0) or 0),
        "shop_power_level": int(getattr(game, "shop_power_level", 1) or 1),
        "xp": int(getattr(game, "xp", 0) or 0),
        "xp_to_next": int(getattr(game, "xp_to_next", 100) or 100),
        "seed": int(getattr(game, "run_seed", 0) or 0),
        "directive_name": getattr(setup, "directive_name", "") if setup else "",
        "directive_hidden": bool(getattr(setup, "directive_hidden", False)) if setup else False,
        "modifier_ids": list(getattr(setup, "modifier_ids", []) or []) if setup else [],
        "waves_emitted": int(getattr(orch, "waves_emitted", 0) or 0),
        "path": [list(p) for p in (getattr(game, "path", None) or [])],
        "grid": [list(row) for row in game.grid],
        "towers": [dump_tower(t) for t in game.towers],
        "bench": [dump_tower(t) for t in game.bench],
        "shop": [dict(card) if card else None for card in (game.shop or [])],
        "loot_bag": list(getattr(game, "loot_bag", None) or []),
    }


def restore_run(game, snap: Dict[str, Any]) -> None:
    from config import SORT_CONFIG
    from core.run_setup import RunSetup
    from core.sort_orchestrator import SortOrchestrator
    from map.path_graph import PathGraph

    game.gold = int(snap.get("gold", game.gold))
    game.lives = int(snap.get("lives", game.lives))
    game.intel = int(snap.get("intel", 0) or 0)
    game.round_num = int(snap.get("round_num", 1) or 1)
    game.reroll_cost = int(snap.get("reroll_cost", game.reroll_cost))
    game.noise_injections = int(snap.get("noise_injections", 0) or 0)
    if hasattr(game, "shop_power_level"):
        game.shop_power_level = int(snap.get("shop_power_level", 1) or 1)
        game.xp = int(snap.get("xp", 0) or 0)
        game.xp_to_next = int(snap.get("xp_to_next", 100) or 100)

    game.wave_active = False
    game.paused = False
    game.game_over = False
    game.run_over_reason = None
    game.enemies = []
    game.spawn_queue = []
    game.spawn_timer = 0
    game.selected_loot = None
    game.selected_tower = None
    game.merge_tower_1 = None
    game.merge_tower_2 = None
    game.merge_preview = None
    game.egrem_preview = False
    game.incompatible_preview = False
    game.close_inspector()

    if snap.get("grid"):
        game.grid = [list(row) for row in snap["grid"]]
    if snap.get("path") is not None:
        game.path = [tuple(p) for p in snap["path"]]
        graph = PathGraph()
        for pos in game.path:
            graph.add_node(pos)
        for i in range(max(0, len(game.path) - 1)):
            graph.add_edge(game.path[i], game.path[i + 1])
        if game.path:
            graph.set_start(game.path[0])
            graph.set_end(game.path[-1])
        game.path_graph = graph

    game.towers = [t for t in (load_tower(b, game) for b in snap.get("towers") or []) if t]
    bench = [load_tower(b, game) for b in snap.get("bench") or []]
    if bench:
        game.bench = bench
    shop = snap.get("shop")
    if shop is not None:
        game.shop = [dict(card) if card else None for card in shop]
    if "loot_bag" in snap:
        game.loot_bag = list(snap.get("loot_bag") or [])

    game.enemy_grid = [[[] for _ in range(game.width)] for _ in range(game.height)]

    game.run_seed = int(snap.get("seed", getattr(game, "run_seed", 0)) or 0)
    game.run_setup = RunSetup(
        seed=game.run_seed,
        directive_name=snap.get("directive_name") or None,
        directive_hidden=bool(snap.get("directive_hidden", False)),
        modifier_ids=list(snap.get("modifier_ids") or []),
    )
    if SORT_CONFIG.get("enabled", True):
        game.sort_orchestrator = SortOrchestrator.create(
            run_setup=game.run_setup,
            web_mode=getattr(game, "web_mode", False),
        )
        for _ in range(int(snap.get("waves_emitted", 0) or 0)):
            game.sort_orchestrator.next_wave()
