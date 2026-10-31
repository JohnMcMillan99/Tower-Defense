"""Dev Tools loadouts: built-in Easy/Medium/Hard plus three user slots on disk."""
from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, Optional

BUILTIN_IDS = ("easy", "medium", "hard")
USER_SLOTS = ("user_1", "user_2", "user_3")

BUILTIN_LABELS = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
    "user_1": "1",
    "user_2": "2",
    "user_3": "3",
}

# Easy is the live catalog defaults (current shipped balance).
# Medium / Hard are patches merged onto that snapshot.
MEDIUM_PATCH = {
    "flow": {"victory_waves": 15},
    "waves": {
        "base_size": 6,
        "per_wave": 3,
        "hp_scale_per_wave": 4.5,
        "spawn_interval": 22,
        "web_min": 4,
        "web_base": 6,
    },
    "economy": {
        "starting_gold": 20,
        "starting_lives": 15,
        "kill_gold_mult": 0.4,
        "wave_bonus_mult": 0.4,
        "reroll_cost": 4,
    },
    "rewards": {"egrem_tile_drop_chance": 0.22},
    "enemies": {
        "Drone": {"health": 13, "speed": 8},
        "Scout": {"health": 10, "speed": 5},
        "Harvester": {"health": 20, "speed": 10},
        "Adaptor": {"health": 26, "speed": 7},
        "Assimilator": {"health": 33, "speed": 8},
    },
}

HARD_PATCH = {
    "flow": {"victory_waves": 20},
    "waves": {
        "base_size": 8,
        "per_wave": 4,
        "hp_scale_per_wave": 5.5,
        "spawn_interval": 16,
        "web_min": 5,
        "web_base": 7,
    },
    "economy": {
        "starting_gold": 15,
        "starting_lives": 10,
        "kill_gold_mult": 0.3,
        "wave_bonus_mult": 0.3,
        "sell_bench_mult": 0.4,
        "sell_grid_refund": 0.35,
        "reroll_cost": 5,
    },
    "rewards": {"egrem_tile_drop_chance": 0.16},
    "enemies": {
        "Drone": {"health": 16, "speed": 7},
        "Scout": {"health": 13, "speed": 4},
        "Harvester": {"health": 24, "speed": 9},
        "Adaptor": {"health": 32, "speed": 6},
        "Assimilator": {"health": 40, "speed": 7},
    },
}

PATCHES = {"medium": MEDIUM_PATCH, "hard": HARD_PATCH}


def default_presets_path() -> str:
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "dev_presets.json")
    )


def deep_merge(base: dict, patch: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def merge_tables(defaults: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = {tid: copy.deepcopy(root) for tid, root in defaults.items()}
    for tid, table_patch in patch.items():
        if tid not in merged or not isinstance(merged[tid], dict) or not isinstance(table_patch, dict):
            continue
        merged[tid] = deep_merge(merged[tid], table_patch)
    return merged


class PresetStore:
    """User slots persist as JSON. Built-ins are computed from catalog defaults."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or default_presets_path()
        self.user: Dict[str, Optional[dict]] = {slot: None for slot in USER_SLOTS}
        self.load()

    def load(self) -> None:
        self.user = {slot: None for slot in USER_SLOTS}
        if not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        slots = raw.get("slots") if isinstance(raw, dict) else None
        if not isinstance(slots, dict):
            return
        for slot in USER_SLOTS:
            blob = slots.get(slot)
            if isinstance(blob, dict) and isinstance(blob.get("tables"), dict):
                self.user[slot] = blob

    def write(self) -> None:
        payload = {"slots": {slot: self.user.get(slot) for slot in USER_SLOTS}}
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self.path)

    def get_user_tables(self, slot: str) -> Optional[dict]:
        blob = self.user.get(slot)
        if not blob:
            return None
        tables = blob.get("tables")
        return tables if isinstance(tables, dict) else None

    def has_user(self, slot: str) -> bool:
        return self.get_user_tables(slot) is not None

    def save_user(self, slot: str, tables: dict, name: Optional[str] = None) -> None:
        if slot not in USER_SLOTS:
            raise KeyError(slot)
        self.user[slot] = {
            "name": name or BUILTIN_LABELS[slot],
            "tables": copy.deepcopy(tables),
        }
        self.write()

    def first_empty_user(self) -> str:
        for slot in USER_SLOTS:
            if not self.has_user(slot):
                return slot
        return USER_SLOTS[0]
