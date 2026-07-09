"""Pre-run Sort Directive modifiers + directive pick (Slice E)."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence

from models.drone_data import DroneData
from core.sort_directives import list_directives, get_directive


# ---------------------------------------------------------------------------
# Modifier definitions (id → apply to pool / wave sizes)
# ---------------------------------------------------------------------------
MODIFIER_DEFS: Dict[str, Dict[str, Any]] = {
    "dense_swarm": {
        "name": "Dense Swarm",
        "desc": "+25% enemies per wave",
        "size_mult": 1.25,
    },
    "thin_signal": {
        "name": "Thin Signal",
        "desc": "-20% enemies per wave",
        "size_mult": 0.8,
    },
    "speed_skew": {
        "name": "Velocity Bias",
        "desc": "Bias pool toward Scouts",
        "type_weights": {"Scout": 2.5, "Drone": 1.0, "Harvester": 0.7, "Adaptor": 0.7, "Assimilator": 0.5},
    },
    "armor_skew": {
        "name": "Armor Bias",
        "desc": "Bias pool toward Harvesters / Assimilators",
        "type_weights": {"Harvester": 2.2, "Assimilator": 1.8, "Drone": 0.8, "Scout": 0.6, "Adaptor": 1.0},
    },
    "elite_injection": {
        "name": "Elite Injection",
        "desc": "More Assimilators in the pool",
        "type_weights": {"Assimilator": 2.5, "Adaptor": 1.4, "Drone": 0.9, "Scout": 0.9, "Harvester": 1.0},
        "assimilator_bonus": 0.15,
    },
    "early_unlock": {
        "name": "Early Contact",
        "desc": "Unlock types 2 waves earlier",
        "unlock_shift": -2,
    },
}

# Meta stubs — which directives / modifiers are unlocked (YAML can override later)
META_UNLOCK_STUBS = {
    "directives": [
        "PowerSort",
        "DescendingSpike",
        "DroneBubble",
        "AssimilationMerge",
        "PivotPartition",
        "PriorityExtract",
        "ResistanceBucket",
    ],
    "modifiers": list(MODIFIER_DEFS.keys()),
    "starting_intel_bonus": 0,
}


def unlocked_directives(meta: Optional[dict] = None) -> List[str]:
    meta = meta or META_UNLOCK_STUBS
    allowed = set(meta.get("directives") or list_directives())
    return [n for n in list_directives() if n in allowed]


def unlocked_modifiers(meta: Optional[dict] = None) -> List[str]:
    meta = meta or META_UNLOCK_STUBS
    allowed = set(meta.get("modifiers") or MODIFIER_DEFS.keys())
    return [m for m in MODIFIER_DEFS if m in allowed]


def pick_directive(seed: int, name: Optional[str] = None, hidden: bool = False, meta: Optional[dict] = None):
    """
    Choose a directive for the run.
    Returns (directive_name, hidden_flag, display_label).
    """
    options = unlocked_directives(meta)
    rng = random.Random(seed ^ 0xD1EC)
    if name and name in options:
        chosen = name
    else:
        chosen = rng.choice(options) if options else "PowerSort"
    label = "???" if hidden else get_directive(chosen).display_name
    return chosen, bool(hidden), label


def apply_modifiers_to_size(wave_num: int, base_size: int, modifier_ids: Sequence[str]) -> int:
    size = float(base_size)
    for mid in modifier_ids:
        defn = MODIFIER_DEFS.get(mid)
        if not defn:
            continue
        if "size_mult" in defn:
            size *= float(defn["size_mult"])
    return max(1, int(round(size)))


def unlock_types_with_modifiers(wave_num: int, base_fn, modifier_ids: Sequence[str]) -> List[str]:
    shift = 0
    for mid in modifier_ids:
        defn = MODIFIER_DEFS.get(mid)
        if defn and "unlock_shift" in defn:
            shift += int(defn["unlock_shift"])
    effective = max(1, wave_num + shift)
    return list(base_fn(effective))


def weighted_choice(rng: random.Random, types: Sequence[str], weights: Dict[str, float]) -> str:
    w = [max(0.05, float(weights.get(t, 1.0))) for t in types]
    return rng.choices(list(types), weights=w, k=1)[0]


def build_modified_pool(
    seed: int,
    planned_waves: int,
    wave_size_fn,
    unlocked_fn,
    modifier_ids: Optional[Sequence[str]] = None,
) -> List[DroneData]:
    """Seeded pool with modifier size / type / unlock bias applied."""
    mods = list(modifier_ids or [])
    rng = random.Random(seed)
    # Merge type weights from all modifiers
    type_weights: Dict[str, float] = {}
    for mid in mods:
        defn = MODIFIER_DEFS.get(mid) or {}
        for t, w in (defn.get("type_weights") or {}).items():
            type_weights[t] = type_weights.get(t, 1.0) * float(w)

    pool: List[DroneData] = []
    for w in range(1, planned_waves + 1):
        types = unlock_types_with_modifiers(w, unlocked_fn, mods) or ["Drone"]
        size = apply_modifiers_to_size(w, int(wave_size_fn(w)), mods)
        for _ in range(size):
            if type_weights:
                etype = weighted_choice(rng, types, type_weights)
            else:
                etype = rng.choice(types)
            # Elite injection: chance to upgrade to Assimilator if unlocked
            for mid in mods:
                bonus = (MODIFIER_DEFS.get(mid) or {}).get("assimilator_bonus")
                if bonus and "Assimilator" in types and rng.random() < float(bonus):
                    etype = "Assimilator"
                    break
            noise = rng.randint(-2, 2)
            pool.append(DroneData.from_type(etype, wave_num=w, noise=noise))
    return pool


class RunSetup:
    """Pre-run choices that feed SortOrchestrator.create."""

    def __init__(
        self,
        seed: Optional[int] = None,
        directive_name: Optional[str] = None,
        directive_hidden: bool = False,
        modifier_ids: Optional[Sequence[str]] = None,
        meta: Optional[dict] = None,
    ):
        self.meta = meta or META_UNLOCK_STUBS
        self.seed = int(seed if seed is not None else random.randint(0, 2**31 - 1))
        self.modifier_ids = [m for m in (modifier_ids or []) if m in MODIFIER_DEFS]
        self.directive_name, self.directive_hidden, self.directive_label = pick_directive(
            self.seed, name=directive_name, hidden=directive_hidden, meta=self.meta
        )
        self.starting_intel_bonus = int(self.meta.get("starting_intel_bonus", 0))

    def to_dict(self):
        return {
            "seed": self.seed,
            "directive": self.directive_name,
            "directive_hidden": self.directive_hidden,
            "directive_label": self.directive_label,
            "modifiers": list(self.modifier_ids),
            "starting_intel_bonus": self.starting_intel_bonus,
        }

    @classmethod
    def random_offer(cls, seed: Optional[int] = None, meta: Optional[dict] = None, hidden_chance: float = 0.35):
        """Build a random pre-run offer: 0–2 modifiers + maybe-hidden directive."""
        meta = meta or META_UNLOCK_STUBS
        seed = int(seed if seed is not None else random.randint(0, 2**31 - 1))
        rng = random.Random(seed ^ 0xA11D)
        mods_pool = unlocked_modifiers(meta)
        n = rng.randint(0, min(2, len(mods_pool))) if mods_pool else 0
        mods = rng.sample(mods_pool, n) if n else []
        hidden = rng.random() < hidden_chance
        return cls(seed=seed, directive_hidden=hidden, modifier_ids=mods, meta=meta)
