"""Collective — persistent firmware bought with Dilithium (not run gold)."""
from __future__ import annotations

from typing import List, Optional, Sequence

from config import COLLECTIVE_CONFIG

CURRENCY = COLLECTIVE_CONFIG.get("currency_name", "Dilithium")

# Three L4 unlocks. apply_to_run() installs them on New Run only.
COLLECTIVE_STUBS = [
    {
        "id": "bench_slot_1",
        "name": "Aux Rack",
        "cost": 100,
        "blurb": "Extra bench bay. Isolation hardware.",
        "effect": "bench_slots +1",
    },
    {
        "id": "reroll_cheap",
        "name": "Cache Flush",
        "cost": 150,
        "blurb": "Shop reroll costs 1. Purge noise.",
        "effect": "reroll_cost 1",
    },
    {
        "id": "start_gold_1",
        "name": "Seed Capacitor",
        "cost": 120,
        "blurb": "+5 starting gold. Boot reserve.",
        "effect": "start_gold +5",
    },
]


def stubs() -> List[dict]:
    return list(COLLECTIVE_STUBS)


def owned(profile, unlock_id: str) -> bool:
    return unlock_id in (getattr(profile, "unlock_ids", None) or [])


def try_buy(profile, unlock_id: str) -> Optional[str]:
    """Spend Dilithium and mark an unlock. Applies on the next New Run."""
    card = next((c for c in COLLECTIVE_STUBS if c["id"] == unlock_id), None)
    if card is None:
        return "Unknown patch"
    if owned(profile, unlock_id):
        return f"{card['name']} already installed"
    cost = int(card["cost"])
    purse = int(getattr(profile, "dilithium", 0) or 0)
    if purse < cost:
        return f"Insufficient {CURRENCY}"
    profile.dilithium = purse - cost
    profile.unlock_ids.append(unlock_id)
    return f"{card['name']} installed — applies on next New Run"


def apply_to_run(game, unlock_ids: Optional[Sequence[str]] = None) -> None:
    """Mutate this Game only. Never writes back into ECONOMY/BENCH config."""
    ids = set(unlock_ids or [])
    if "bench_slot_1" in ids:
        slots = getattr(game, "bench", None)
        if isinstance(slots, list):
            game.bench.append(None)
    if "reroll_cheap" in ids:
        game.reroll_cost = 1
    if "start_gold_1" in ids:
        game.gold = int(getattr(game, "gold", 0) or 0) + 5
