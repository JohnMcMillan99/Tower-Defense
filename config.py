"""
Shared configuration for Tower Defense 3.
"""

# Set to True to enable debug logging to debug.log (useful for troubleshooting)
DEBUG = False

# ---------------------------------------------------------------------------
# Tunable reward / economy loops (adjust freely for balance)
# ---------------------------------------------------------------------------
REWARD_CONFIG = {
    # Path tiles drop from defeated egrem-spawned enemies into shared loot_bag
    "egrem_tile_drop_chance": 0.28,
    # Upgrade loot from milestone waves (shared loot_bag)
    "mini_boss_wave_interval": 5,
    "boss_wave_interval": 20,
    "mini_boss_upgrade_count": 1,
    "boss_upgrade_count": 1,  # was 2 — tighter bag pressure
    "boss_prefer_wildcard_chance": 0.55,
}

# Shared loot bag: path tiles + upgrades compete for the same slots
LOOT_CONFIG = {
    "bag_slots": 4,
}

# Tower holding bench size (shop still 5; merge/place from here)
BENCH_CONFIG = {
    "tower_slots": 5,
}

# Gold income / starting purse — ~50% of prior rates (strong nerf)
ECONOMY_CONFIG = {
    "starting_gold": 25,
    "kill_gold_mult": 0.5,       # applied to base kill payout
    "wave_bonus_mult": 0.5,      # applied to clear bonus
    "sell_bench_mult": 0.5,
    "sell_grid_refund": 0.45,    # was 0.60
    "reroll_cost": 3,
}

# ---------------------------------------------------------------------------
# Scout / Sort Directive intel (Round Guide fog-of-war)
# ---------------------------------------------------------------------------
INTEL_CONFIG = {
    "max_intel": 100,
    "egrem_intel_gain": 8,
    "starting_intel": 0,
    # Egrem kills inject noise into remaining sort pool (Slice D)
    "egrem_noise_chance": 0.45,
    "egrem_noise_min": 1,
    "egrem_noise_max": 2,
    # Confidence = f(intel, waves_observed, noise). Shown on Round Guide.
    "confidence_intel_weight": 0.7,
    "confidence_noise_penalty": 0.08,  # per recent noise injection
    "confidence_floor": 0.15,
    # Higher min = more scout detail. First matching tier from the bottom wins.
    "tiers": [
        {"min": 0, "horizon": 1, "show_types": False, "show_percents": False, "label": "Contact"},
        {"min": 25, "horizon": 1, "show_types": True, "show_percents": True, "label": "Scan"},
        {"min": 50, "horizon": 2, "show_types": True, "show_percents": True, "label": "Tap"},
        {"min": 75, "horizon": 3, "show_types": True, "show_percents": True, "label": "Matrix"},
    ],
}

# ---------------------------------------------------------------------------
# Sort Directive orchestration (pool → directive → wave chunks)
# ---------------------------------------------------------------------------
SORT_CONFIG = {
    "enabled": True,
    "default_directive": "PowerSort",
    "planned_waves": 40,
    # None = random seed each run; set an int for reproducible harnesses
    "seed": None,
    # Pre-run: chance the directive name is hidden until Matrix intel
    "directive_hidden_chance": 0.35,
    # Optional forced picks for tests / harness (None = random offer)
    "force_directive": None,
    "force_modifiers": None,
    "force_hidden": None,
}


def log_debug(msg, data=None, location="main"):
    """Write debug log entry only when DEBUG is True."""
    if not DEBUG:
        return
    import json
    import time
    log_entry = {
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": msg,
        "data": data or {},
    }
    try:
        with open("debug.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
