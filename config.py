"""
Shared configuration for Tower Defense 3.
"""

# Set to True to enable debug logging to debug.log (useful for troubleshooting)
DEBUG = False

# ---------------------------------------------------------------------------
# Tunable reward / economy loops (adjust freely for balance)
# ---------------------------------------------------------------------------
REWARD_CONFIG = {
    # Path tiles drop from defeated egrem-spawned enemies into map_tile_bench
    "egrem_tile_drop_chance": 0.35,
    # Upgrade loot from milestone waves (auto-fills upgrade_bench)
    "mini_boss_wave_interval": 5,
    "boss_wave_interval": 20,
    "mini_boss_upgrade_count": 1,
    "boss_upgrade_count": 2,
    "boss_prefer_wildcard_chance": 0.55,
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
