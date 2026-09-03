"""
Live balance catalog for Dev Tools.

Mutates the same module-level dicts / class tables the run already reads.
A New Run (or the next spawned enemy/tower) sees the current values.
Session-only: Reset All restores the snapshot taken at first catalog build.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from core.dev_presets import (
    BUILTIN_IDS,
    PATCHES,
    PresetStore,
    USER_SLOTS,
    merge_tables,
)

Path = Tuple[str, ...]


SKIP_KEYS = frozenset({
    "display", "symbol", "name", "desc", "traits", "synergizes_with",
    "label", "fire_type", "seed", "force_directive", "force_modifiers",
    "force_hidden",
})


@dataclass
class Table:
    id: str
    title: str
    blurb: str
    root: Any
    skip_keys: frozenset = field(default_factory=lambda: SKIP_KEYS)
    enums: dict = field(default_factory=dict)  # path tuple -> choices


@dataclass
class Leaf:
    table_id: str
    path: Path
    kind: str  # bool | int | float | enum
    value: Any
    default: Any
    choices: Optional[Sequence[str]] = None
    lo: float = 0
    hi: float = 1
    step: float = 1

    @property
    def label(self) -> str:
        parts = [p.replace("_", " ") for p in self.path]
        if len(parts) >= 2:
            return f"{parts[-2]}  ·  {parts[-1]}"
        return parts[-1] if parts else self.table_id

    @property
    def dirty(self) -> bool:
        return self.value != self.default


def _resolve(root, path: Path):
    cur = root
    for p in path[:-1]:
        if isinstance(cur, dict):
            cur = cur[p]
        elif isinstance(cur, list):
            cur = cur[int(p)]
        else:
            raise KeyError(path)
    return cur, path[-1]


def get_at(root, path: Path):
    parent, key = _resolve(root, path)
    if isinstance(parent, list):
        return parent[int(key)]
    return parent[key]


def set_at(root, path: Path, value):
    parent, key = _resolve(root, path)
    if isinstance(parent, list):
        parent[int(key)] = value
    else:
        parent[key] = value


def restore_inplace(live, saved):
    if isinstance(live, dict) and isinstance(saved, dict):
        for k in list(live.keys()):
            if k not in saved:
                del live[k]
        for k, v in saved.items():
            if k in live and isinstance(live[k], (dict, list)) and isinstance(v, type(live[k])):
                restore_inplace(live[k], v)
            else:
                live[k] = copy.deepcopy(v) if isinstance(v, (dict, list)) else v
    elif isinstance(live, list) and isinstance(saved, list):
        live[:] = copy.deepcopy(saved)


def infer_bounds(path: Path, value) -> Tuple[float, float, float]:
    key = path[-1].lower() if path else ""
    if isinstance(value, float):
        if any(s in key for s in ("chance", "weight", "penalty", "floor")):
            return 0.0, 1.0, 0.01
        if any(s in key for s in ("mult", "scale", "delta")):
            return -4.0 if "delta" in key else 0.0, 8.0, 0.05
        return 0.0, max(8.0, abs(float(value)) * 4.0), 0.1
    if any(s in key for s in ("wave", "interval", "planned")):
        return 1, 80, 1
    if "slot" in key:
        return 1, 12, 1
    if any(s in key for s in ("gold", "cost", "lives", "intel")):
        return 0, 200, 1
    if "range" in key:
        return 0, max(20, int(value) if isinstance(value, int) else 20), 1
    if any(s in key for s in ("dmg", "health", "damage", "bonus")):
        return 0, 80, 1
    if any(s in key for s in ("fire_rate", "speed", "horizon")):
        return 0, 40, 1
    if isinstance(value, int) and abs(value) >= 40:
        return 0, max(120, abs(value)), 1
    return 0, max(20, abs(int(value)) * 5 if isinstance(value, int) else 20), 1


def walk_leaves(root, skip_keys, enums, prefix: Path = ()) -> Iterable[Tuple[Path, str, Any, Optional[Sequence[str]]]]:
    if isinstance(root, dict):
        for k, v in root.items():
            if k in skip_keys:
                continue
            yield from walk_leaves(v, skip_keys, enums, prefix + (str(k),))
        return
    if isinstance(root, list):
        if root and all(isinstance(x, dict) for x in root):
            for i, item in enumerate(root):
                yield from walk_leaves(item, skip_keys, enums, prefix + (str(i),))
        return
    path = prefix
    if path in enums:
        yield path, "enum", root, enums[path]
        return
    if isinstance(root, bool):
        yield path, "bool", root, None
    elif isinstance(root, int):
        yield path, "int", root, None
    elif isinstance(root, float):
        yield path, "float", root, None


class DevCatalog:
    def __init__(self, preset_store: Optional[PresetStore] = None):
        self.tables: List[Table] = []
        self._defaults: dict = {}
        self._built = False
        self.store = preset_store if preset_store is not None else PresetStore()
        self.active_preset: Optional[str] = None

    def ensure(self):
        if self._built:
            return
        self.tables = _build_tables()
        self._defaults = {t.id: copy.deepcopy(t.root) for t in self.tables}
        self._built = True

    def table(self, table_id: str) -> Table:
        self.ensure()
        for t in self.tables:
            if t.id == table_id:
                return t
        raise KeyError(table_id)

    def leaves(self, table_id: str) -> List[Leaf]:
        t = self.table(table_id)
        saved = self._defaults[t.id]
        out = []
        for path, kind, value, choices in walk_leaves(t.root, t.skip_keys, t.enums):
            try:
                default = get_at(saved, path)
            except (KeyError, IndexError, TypeError):
                default = value
            lo, hi, step = (0, 1, 1)
            if kind in ("int", "float"):
                lo, hi, step = infer_bounds(path, default if default is not None else value)
            out.append(Leaf(t.id, path, kind, value, default, choices, lo, hi, step))
        return out

    def get(self, table_id: str, path: Path):
        return get_at(self.table(table_id).root, path)

    def set(self, table_id: str, path: Path, value):
        t = self.table(table_id)
        leaf_kind = None
        for lf in self.leaves(table_id):
            if lf.path == path:
                leaf_kind = lf.kind
                break
        if leaf_kind == "int":
            value = int(round(float(value)))
        elif leaf_kind == "float":
            value = float(value)
        elif leaf_kind == "bool":
            value = bool(value)
        set_at(t.root, path, value)
        if table_id == "system" and path == ("debug_log",):
            import config as cfg
            cfg.DEBUG = bool(value)
        self.active_preset = None
        return self.get(table_id, path)

    def nudge(self, table_id: str, path: Path, direction: int):
        for lf in self.leaves(table_id):
            if lf.path != path:
                continue
            if lf.kind == "bool":
                return self.set(table_id, path, not lf.value)
            if lf.kind == "enum" and lf.choices:
                idx = list(lf.choices).index(lf.value) if lf.value in lf.choices else 0
                nxt = lf.choices[(idx + direction) % len(lf.choices)]
                return self.set(table_id, path, nxt)
            nxt = lf.value + lf.step * direction
            nxt = max(lf.lo, min(lf.hi, nxt))
            return self.set(table_id, path, nxt)
        return None

    def set_from_ratio(self, table_id: str, path: Path, ratio: float):
        ratio = max(0.0, min(1.0, float(ratio)))
        for lf in self.leaves(table_id):
            if lf.path != path:
                continue
            if lf.kind not in ("int", "float"):
                return lf.value
            raw = lf.lo + (lf.hi - lf.lo) * ratio
            return self.set(table_id, path, raw)
        return None

    def reset_table(self, table_id: str):
        self.ensure()
        t = self.table(table_id)
        restore_inplace(t.root, self._defaults[table_id])
        if table_id == "system":
            import config as cfg
            cfg.DEBUG = bool(t.root.get("debug_log", False))

    def reset_all(self):
        self.ensure()
        for t in self.tables:
            self.reset_table(t.id)
        self.active_preset = "easy"

    def export_state(self) -> dict:
        self.ensure()
        return {t.id: copy.deepcopy(t.root) for t in self.tables}

    def apply_state(self, state: dict) -> None:
        self.ensure()
        if not isinstance(state, dict):
            return
        for t in self.tables:
            blob = state.get(t.id)
            if isinstance(blob, dict):
                restore_inplace(t.root, blob)
            if t.id == "system":
                import config as cfg
                cfg.DEBUG = bool(t.root.get("debug_log", False))

    def builtin_state(self, preset_id: str) -> dict:
        self.ensure()
        easy = {tid: copy.deepcopy(root) for tid, root in self._defaults.items()}
        if preset_id == "easy":
            return easy
        patch = PATCHES.get(preset_id)
        if not patch:
            raise KeyError(preset_id)
        return merge_tables(easy, patch)

    def apply_preset(self, preset_id: str) -> bool:
        """Load a built-in or user slot. Returns False if the user slot is empty."""
        if preset_id in BUILTIN_IDS:
            self.apply_state(self.builtin_state(preset_id))
            self.active_preset = preset_id
            return True
        if preset_id in USER_SLOTS:
            tables = self.store.get_user_tables(preset_id)
            if tables is None:
                return False
            self.apply_state(tables)
            self.active_preset = preset_id
            return True
        raise KeyError(preset_id)

    def save_loadout(self, slot: Optional[str] = None) -> str:
        """Write current tables into a user slot. Defaults to selected/empty slot."""
        if slot is None:
            if self.active_preset in USER_SLOTS:
                slot = self.active_preset
            else:
                slot = self.store.first_empty_user()
        self.store.save_user(slot, self.export_state())
        self.active_preset = slot
        return slot

    def dirty_count(self) -> int:
        self.ensure()
        n = 0
        for t in self.tables:
            n += sum(1 for lf in self.leaves(t.id) if lf.dirty)
        return n


_CATALOG: Optional[DevCatalog] = None


def catalog() -> DevCatalog:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = DevCatalog()
    return _CATALOG


def reset_catalog_for_tests(preset_store: Optional[PresetStore] = None):
    """Rebuild after tests mutate module state."""
    global _CATALOG
    _CATALOG = DevCatalog(preset_store=preset_store) if preset_store is not None else None


def _build_tables() -> List[Table]:
    import config as cfg
    from models.tower import Tower
    from models.enemy import Enemy
    from data.units import UNIT_TYPES, WEB_MODE_CONFIG
    from data.upgrades import UPGRADE_DEFS, EGREM_SPAWN_CONFIG
    from core.sort_directives import list_directives

    core_towers = (
        "Neural Processor", "Plasma Capacitor", "Thermal Regulator",
        "Signal Router", "Quantum Field Gen", "Nanite Swarm",
    )
    tower_root = {k: Tower.BASE_TYPES[k] for k in core_towers if k in Tower.BASE_TYPES}
    unit_root = {u["name"]: u for u in UNIT_TYPES}

    # Keep DEBUG in a tiny live dict the walker can see
    system = {"debug_log": bool(cfg.DEBUG)}

    return [
        Table("flow", "Run flow", "Win length and live-play verbs. Applies on the next New Run.", cfg.RUN_FLOW_CONFIG, enums={
            ("mode",): ("live_always", "tft_timer", "auto_chain"),
        }),
        Table("waves", "Waves", "How many enemies spawn and how fast HP grows.", cfg.WAVE_CONFIG),
        Table("sort", "Sort", "Directive pool and planned wave count.", cfg.SORT_CONFIG, enums={
            ("default_directive",): tuple(list_directives()),
        }),
        Table("economy", "Economy", "Gold, lives, sell, reroll. starting_* apply on New Run.", cfg.ECONOMY_CONFIG),
        Table("rewards", "Rewards", "Loot drops from waves and egrem kills.", cfg.REWARD_CONFIG),
        Table("loot", "Loot bag", "Shared bag size (tiles + upgrades).", cfg.LOOT_CONFIG),
        Table("bench", "Bench", "Tower holding slots.", cfg.BENCH_CONFIG),
        Table("intel", "Intel", "Scout fog-of-war. Nested tiers stay editable.", cfg.INTEL_CONFIG),
        Table("towers", "Towers", "Base dmg / range / fire rate. New towers only.", tower_root),
        Table("shop", "Shop costs", "Buy prices in the shop.", unit_root),
        Table("enemies", "Enemies", "Base health / speed / difficulty. New spawns only.", Enemy.TYPES),
        Table("upgrades", "Firmware", "Upgrade numeric bonuses.", UPGRADE_DEFS),
        Table("egrem", "Egrem spawn", "Wrong-merge spawn cadence.", EGREM_SPAWN_CONFIG, enums={
            (name, "enemy_type"): ("Drone", "Scout", "Harvester", "Adaptor", "Assimilator")
            for name in EGREM_SPAWN_CONFIG
        }),
        Table("hud", "HUD", "Enemy nameplates and health bars.", cfg.HUD_CONFIG),
        Table("web", "Web scale", "Browser-mode enemy shrink.", WEB_MODE_CONFIG),
        Table("system", "System", "Session debug logging.", system),
    ]
