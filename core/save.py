"""Profile / run-checkpoint store. Dilithium and WaveClear snapshots persist to disk."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def default_profiles_path() -> str:
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "saves", "profiles.json")
    )


@dataclass
class ProfileSave:
    slot: int = 0
    dilithium: int = 0
    unlock_ids: List[str] = field(default_factory=list)
    runs_played: int = 0
    runs_won: int = 0


@dataclass
class RunCheckpoint:
    slot: int = 0
    seed: int = 0
    directive_name: str = ""
    modifier_ids: List[str] = field(default_factory=list)
    wave_number: int = 1
    gold: int = 0
    lives: int = 0
    intel: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)
    snapshot: Dict[str, Any] = field(default_factory=dict)


class MemorySaveStore:
    """One profile + optional checkpoint per slot. Optional JSON path for Dilithium/unlocks."""

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.profiles: Dict[int, ProfileSave] = {i: ProfileSave(slot=i) for i in range(3)}
        self.checkpoints: Dict[int, Optional[RunCheckpoint]] = {i: None for i in range(3)}
        if path:
            self.load()

    def profile(self, slot: int) -> ProfileSave:
        return self.profiles.setdefault(slot, ProfileSave(slot=slot))

    def has_checkpoint(self, slot: int) -> bool:
        return self.checkpoints.get(slot) is not None

    def save_checkpoint(self, slot: int, ckpt: RunCheckpoint) -> None:
        ckpt.slot = slot
        self.checkpoints[slot] = ckpt
        self.persist()

    def clear_checkpoint(self, slot: int) -> None:
        self.checkpoints[slot] = None
        self.persist()

    def record_run_over(self, slot: int, victory: bool) -> None:
        from config import COLLECTIVE_CONFIG
        p = self.profile(slot)
        p.runs_played += 1
        if victory:
            p.runs_won += 1
        key = "dilithium_on_victory" if victory else "dilithium_on_defeat"
        grant = COLLECTIVE_CONFIG.get(key, 0)
        p.dilithium = int(getattr(p, "dilithium", 0) or 0) + int(grant)
        self.clear_checkpoint(slot)
        self.persist()

    def load(self) -> None:
        if not self.path or not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        slots = raw.get("slots") if isinstance(raw, dict) else None
        if not isinstance(slots, dict):
            return
        for key, blob in slots.items():
            try:
                idx = int(key)
            except (TypeError, ValueError):
                continue
            if not isinstance(blob, dict):
                continue
            unlocks = blob.get("unlock_ids") or []
            if not isinstance(unlocks, list):
                unlocks = []
            self.profiles[idx] = ProfileSave(
                slot=idx,
                dilithium=int(blob.get("dilithium", 0) or 0),
                unlock_ids=[str(u) for u in unlocks],
                runs_played=int(blob.get("runs_played", 0) or 0),
                runs_won=int(blob.get("runs_won", 0) or 0),
            )
            ck = blob.get("checkpoint")
            if isinstance(ck, dict):
                self.checkpoints[idx] = _checkpoint_from_dict(idx, ck)
            else:
                self.checkpoints[idx] = None

    def persist(self) -> None:
        if not self.path:
            return
        payload = {
            "slots": {
                str(i): {
                    "dilithium": int(p.dilithium),
                    "unlock_ids": list(p.unlock_ids),
                    "runs_played": int(p.runs_played),
                    "runs_won": int(p.runs_won),
                    "checkpoint": _checkpoint_to_dict(self.checkpoints.get(i)),
                }
                for i, p in self.profiles.items()
            }
        }
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self.path)


def _checkpoint_to_dict(ckpt: Optional[RunCheckpoint]) -> Optional[dict]:
    if ckpt is None:
        return None
    return {
        "seed": int(ckpt.seed),
        "directive_name": ckpt.directive_name,
        "modifier_ids": list(ckpt.modifier_ids),
        "wave_number": int(ckpt.wave_number),
        "gold": int(ckpt.gold),
        "lives": int(ckpt.lives),
        "intel": int(ckpt.intel),
        "extra": dict(ckpt.extra or {}),
        "snapshot": dict(ckpt.snapshot or {}),
    }


def _checkpoint_from_dict(slot: int, blob: dict) -> RunCheckpoint:
    return RunCheckpoint(
        slot=slot,
        seed=int(blob.get("seed", 0) or 0),
        directive_name=str(blob.get("directive_name", "") or ""),
        modifier_ids=list(blob.get("modifier_ids") or []),
        wave_number=int(blob.get("wave_number", 1) or 1),
        gold=int(blob.get("gold", 0) or 0),
        lives=int(blob.get("lives", 0) or 0),
        intel=int(blob.get("intel", 0) or 0),
        extra=dict(blob.get("extra") or {}),
        snapshot=dict(blob.get("snapshot") or {}),
    )
