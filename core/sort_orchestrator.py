"""
SortOrchestrator — seeded drone pool + Sort Directive → wave chunks.

WaveManager consumes next_wave() / forecast(); event waves stay outside this path.
"""
from __future__ import annotations

import random
from typing import Callable, Dict, List, Optional, Sequence

from models.drone_data import DroneData
from core.sort_directives import SortDirective, get_directive
from config import SORT_CONFIG


_TYPE_ORDER = ("Drone", "Scout", "Harvester", "Adaptor", "Assimilator")


def unlocked_types_for_wave(wave_num: int) -> List[str]:
    """Enemy types eligible for a normal wave (shared by pool build + legacy spawn)."""
    from models.enemy import Enemy
    types = []
    for name in _TYPE_ORDER:
        stats = Enemy.TYPES.get(name) or {}
        first = int(stats.get("first_wave", 1))
        if int(wave_num) >= first:
            types.append(name)
    return types or ["Drone"]


def default_wave_size(wave_num: int, web_mode: bool = False) -> int:
    from config import WAVE_CONFIG
    if web_mode:
        web_min = int(WAVE_CONFIG.get("web_min", 3))
        web_base = int(WAVE_CONFIG.get("web_base", 5))
        div = max(1, int(WAVE_CONFIG.get("web_divisor", 2)))
        return max(web_min, (web_base + wave_num) // div)
    base = int(WAVE_CONFIG.get("base_size", 5))
    per = int(WAVE_CONFIG.get("per_wave", 1))
    size = base + int(wave_num) * per
    cap = WAVE_CONFIG.get("size_cap")
    if cap is not None:
        size = min(size, int(cap))
    return max(1, size)


def estimate_auto_run_seconds(
    victory_waves: int | None = None,
    clear_beat_seconds: float | None = None,
    tail_seconds: float = 3.0,
    fps: float = 60.0,
) -> dict:
    """Wall-clock envelope for Auto success using WAVE_CONFIG + clear_beat only.

    Per wave: spawn cadence for (size-1) gaps + last-enemy tail + clear beat.
    Does not model HP, path length, or player skill — clock tuning only.
    """
    from config import WAVE_CONFIG, RUN_FLOW_CONFIG, SORT_CONFIG

    waves = int(victory_waves if victory_waves is not None else RUN_FLOW_CONFIG.get("victory_waves", 80))
    beat = float(
        clear_beat_seconds if clear_beat_seconds is not None
        else RUN_FLOW_CONFIG.get("clear_beat_seconds", 2) or 0
    )
    interval = float(WAVE_CONFIG.get("spawn_interval", 30))
    planned = int(SORT_CONFIG.get("planned_waves", waves))
    total = 0.0
    for w in range(1, waves + 1):
        size = default_wave_size(w)
        spawn_s = max(0, size - 1) * (interval / max(1.0, fps))
        total += spawn_s + float(tail_seconds) + beat
    return {
        "victory_waves": waves,
        "planned_waves": planned,
        "seconds": total,
        "minutes": total / 60.0,
    }


class SortOrchestrator:
    def __init__(
        self,
        seed: int,
        waves: List[List[DroneData]],
        directive: SortDirective,
        raw_pool: Optional[Sequence[DroneData]] = None,
    ):
        self.seed = int(seed)
        self.directive = directive
        self.directive_name = getattr(directive, "name", "PowerSort")
        self.directive_display = getattr(directive, "display_name", self.directive_name)
        self.raw_pool = list(raw_pool) if raw_pool is not None else []
        # Remaining planned waves (index 0 = next normal wave to spawn)
        self.remaining: List[List[DroneData]] = [list(w) for w in waves]
        self.waves_emitted = 0

    @classmethod
    def create(
        cls,
        seed: Optional[int] = None,
        directive_name: Optional[str] = None,
        planned_waves: Optional[int] = None,
        web_mode: bool = False,
        wave_size_fn: Optional[Callable[[int], int]] = None,
        unlocked_fn: Optional[Callable[[int], List[str]]] = None,
        modifier_ids: Optional[Sequence[str]] = None,
        run_setup=None,
    ):
        """Build pool from unlock/size rules (+ optional modifiers), apply directive."""
        from core.run_setup import (
            apply_modifiers_to_size,
            build_modified_pool,
        )

        cfg = SORT_CONFIG
        mods = list(modifier_ids or [])
        if run_setup is not None:
            seed = getattr(run_setup, "seed", seed)
            directive_name = getattr(run_setup, "directive_name", directive_name)
            mods = list(getattr(run_setup, "modifier_ids", mods) or mods)

        if seed is None:
            seed = cfg.get("seed")
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        seed = int(seed)

        dname = directive_name or cfg.get("default_directive", "PowerSort")
        directive = get_directive(dname)
        plan = int(planned_waves if planned_waves is not None else cfg.get("planned_waves", 40))

        size_fn = wave_size_fn or (lambda w: default_wave_size(w, web_mode))
        types_fn = unlocked_fn or unlocked_types_for_wave

        if mods:
            raw = build_modified_pool(
                seed=seed,
                planned_waves=plan,
                wave_size_fn=size_fn,
                unlocked_fn=types_fn,
                modifier_ids=mods,
            )
            wave_sizes = [apply_modifiers_to_size(w, size_fn(w), mods) for w in range(1, plan + 1)]
        else:
            raw = build_run_pool(
                seed=seed,
                planned_waves=plan,
                wave_size_fn=size_fn,
                unlocked_fn=types_fn,
            )
            wave_sizes = [size_fn(w) for w in range(1, plan + 1)]

        waves = directive.restructure(raw, wave_sizes, seed)
        orch = cls(seed=seed, waves=waves, directive=directive, raw_pool=raw)
        orch.modifier_ids = list(mods)
        return orch

    @property
    def remaining_count(self):
        return sum(len(w) for w in self.remaining)

    def peek_wave(self, offset: int = 0) -> List[DroneData]:
        """Look ahead without consuming. Empty list if past end of plan."""
        if offset < 0 or offset >= len(self.remaining):
            return []
        return list(self.remaining[offset])

    def next_wave(self) -> List[DroneData]:
        """Consume and return the next planned wave chunk."""
        if not self.remaining:
            return []
        chunk = self.remaining.pop(0)
        self.waves_emitted += 1
        return list(chunk)

    def skip_wave_slot(self):
        """
        Advance the plan without spawning (e.g. event wave replaced this slot).
        Drops the next chunk so later forecasts stay aligned with round_num.
        """
        if self.remaining:
            self.remaining.pop(0)
            self.waves_emitted += 1

    def forecast(self, horizon: int = 1) -> List[Dict]:
        """
        Non-destructive preview of the next `horizon` chunks.
        Each entry: {count, composition: {type: count}, drones: [...]}
        """
        out = []
        for i in range(max(0, int(horizon))):
            chunk = self.peek_wave(i)
            composition: Dict[str, int] = {}
            for d in chunk:
                composition[d.enemy_type] = composition.get(d.enemy_type, 0) + 1
            out.append({
                "count": len(chunk),
                "composition": composition,
                "is_exact": True,
                "drones": chunk,
            })
        return out

    def inject(self, drones: Sequence[DroneData], at_front: bool = False, swaps: int = 0):
        """Egrem noise: reshape the next planned wave (count + composition).

        Extras prepend into remaining[0]. Optional type-swaps rewrite existing
        slots toward the injected types so the Round Guide forecast moves even
        when inject count is small. `at_front` is kept for callers; reshape
        always targets the next wave (not the plan tail).
        """
        _ = at_front
        extra = list(drones)
        if not self.remaining:
            self.remaining = [extra] if extra else []
            return

        nxt = list(self.remaining[0])
        swap_n = max(0, int(swaps or 0))
        if nxt and extra and swap_n > 0:
            types = [d.enemy_type for d in extra]
            idxs = list(range(len(nxt)))
            rng = random.Random((self.seed + self.waves_emitted * 17 + len(extra)) & 0xFFFFFFFF)
            rng.shuffle(idxs)
            for i in idxs[: min(swap_n, len(nxt))]:
                et = rng.choice(types)
                origin = getattr(nxt[i], "origin_wave", 1)
                nxt[i] = DroneData.from_type(et, wave_num=origin, noise=rng.randint(-1, 2))

        # Grow next wave at the front so scout composition stamps update now
        self.remaining[0] = list(extra) + nxt


def build_run_pool(seed: int, planned_waves: int, wave_size_fn, unlocked_fn) -> List[DroneData]:
    """Seeded raw pool: per-wave unlock types, before directive reordering."""
    rng = random.Random(seed)
    pool: List[DroneData] = []
    for w in range(1, planned_waves + 1):
        types = list(unlocked_fn(w)) or ["Drone"]
        size = int(wave_size_fn(w))
        for _ in range(size):
            etype = rng.choice(types)
            noise = rng.randint(-2, 2)
            pool.append(DroneData.from_type(etype, wave_num=w, noise=noise))
    return pool
