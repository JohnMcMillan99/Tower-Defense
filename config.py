"""
Shared configuration for Tower Defense 3.
"""

# Set to True to enable debug logging to debug.log (useful for troubleshooting)
DEBUG = False

# In-run HUD readouts (Dev Tools + right-rail toggles write the same dict)
HUD_CONFIG = {
    "enemy_health_bars": True,
    "enemy_names": True,
    "damage_numbers": True,
}

# Persistent Collective (profile Dilithium ≠ run gold)
COLLECTIVE_CONFIG = {
    "currency_name": "Dilithium",
    "dilithium_on_defeat": 8,
    "dilithium_on_victory": 25,
}

# ---------------------------------------------------------------------------
# Tunable reward / economy loops (adjust freely for balance)
# ---------------------------------------------------------------------------
REWARD_CONFIG = {
    # Path tiles: starter + milestone grants + egrem drops into shared loot_bag
    "egrem_tile_drop_chance": 0.28,
    "starting_path_tiles": 1,       # Straight copies seeded on New Run
    "mini_boss_tile_count": 1,      # grant before upgrades so grow wins the last slot
    "boss_tile_count": 1,
    # Upgrade loot from milestone waves (shared loot_bag)
    "mini_boss_wave_interval": 5,
    "boss_wave_interval": 20,
    "mini_boss_upgrade_count": 1,
    "boss_upgrade_count": 1,  # was 2 — tighter bag pressure
    "boss_prefer_wildcard_chance": 0.55,
    # Combat scale on those same waves. Loot is separate. Event yaml may
    # replace the roster on 10/15/20; HP/speed on milestone numbers come from
    # these knobs only (not stacked with yaml hp_mult / speed_mult).
    "mini_boss_hp_mult": 1.45,
    "boss_hp_mult": 1.85,
    "mini_boss_speed_mult": 1.12,
    "boss_speed_mult": 1.2,
}

# Shared loot bag: path tiles + upgrades compete for the same slots
# Full bag refuses new drops (no displace UI) — miss is recorded on the run.
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
    "starting_lives": 20,
    "kill_gold_mult": 0.5,       # applied to base kill payout
    "kill_gold_base": 3,         # (base + difficulty * per) // 2
    "kill_gold_per_difficulty": 3,
    "wave_bonus_mult": 0.5,      # applied to clear bonus
    "wave_bonus_per_tower": 3,   # (towers * this + wave * per_wave) // 2
    "wave_bonus_per_wave": 4,
    "sell_bench_mult": 0.5,
    "sell_grid_refund": 0.45,    # was 0.60
    "reroll_cost": 3,
}

# Wave size / spawn cadence / HP curve (read live — Dev Tools mutates this)
# Timing at 60 FPS, Auto on, clear_beat 2s, last-enemy tail ~3s:
#   size = min(size_cap, base_size + wave * per_wave)
#   spawn_s ≈ (size-1) * spawn_interval/60
#   ~80 waves × ~15s ≈ 20 min success. Deaths around wave 45–50 ≈ 12 min.
WAVE_CONFIG = {
    "base_size": 5,              # enemies = min(cap, base_size + wave * per_wave)
    "per_wave": 1,
    "size_cap": 22,              # keeps late spawns from dominating the clock
    "web_min": 3,
    "web_base": 5,
    "web_divisor": 2,
    "hp_scale_per_wave": 3.5,    # HP *= 1 + (wave-1) * this * difficulty
    "spawn_interval": 30,        # frames between spawns (30/60 = 0.5s)
}

# Swarm reads the board each wave and resists whatever you stacked.
# Hybrid flag: resist hybrid shots + speed. Lineage tags: resist the
# types you actually placed (neural / plasma / …). Latch soak silences.
ADAPTATION_CONFIG = {
    "recompute_every_n_waves": 1,  # 1 = snapshot placed towers at every wave start
    "hybrid_exposure": {
        "factor_per_point": 0.05,
        "max_factor": 0.5,
        "speed_boost_per_point": 0.02,
        "max_speed_boost": 0.4,
        "applies_to_tags": [
            "hybrid",
            "neural_plasma",
            "thermal_signal",
            "quantum_plasma",
            "neural_quantum",
        ],
    },
    "lineage": {
        "factor_per_point": 0.06,
        "max_factor": 0.45,
        "min_score": 1.5,  # one unmerged tower is not enough to adapt
        "tags": {
            "Neural Processor": "neural",
            "Plasma Capacitor": "plasma",
            "Thermal Regulator": "thermal",
            "Signal Router": "signal",
            "Quantum Field Gen": "quantum",
        },
    },
    "tier": {
        "base_weight": 1.0,
        "per_generation": 1.0,   # gen-3 counts 4x a base; was 0.5
        "dominate_share": 0.65,  # one lineage this dominant gets extra resist
        "dominate_mult": 1.35,
    },
}

# Assimilator stick + soak. Walls are still not placed in play.
LATCH_CONFIG = {
    "enabled": True,           # scan adjacent towers / (future) walls
    "chance_base": 0.4,        # roll per assimilator per frame when a target exists
    "scan_range": 5,
    "fill_per_frame": 0.01,    # corruption per frame before stack mult
    "silence_frames": 90,      # tower skip-fire after a completed soak (~1.5s)
    "heat_on_corrupt": 3.0,    # extra heat applied with the silence
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
    # Type-swap this many slots in the *next* planned wave toward injected types
    "egrem_reshape_swaps": 2,
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
# Run flow — state machine owns time; these flags own verbs
# ---------------------------------------------------------------------------
RUN_FLOW_CONFIG = {
    "mode": "live_always",  # live_always | tft_timer | auto_chain
    "prep_seconds": 12,     # unused until tft_timer
    "clear_beat_seconds": 2,  # Auto gap after a clear; 0 = instant chain
    "shop_during_combat": True,
    "place_towers_during_combat": True,
    "place_tiles_during_combat": True,
    "merge_during_combat": True,
    "allow_next_wave_button": True,
    # Success length. Sort planned_waves should be >= this.
    "victory_waves": 80,
    "endless_after_victory": False,
}


class PlayRules:
    """Which verbs are legal right now. PauseMenu forces all False."""

    __slots__ = ("sim_tick", "shop", "place_towers", "place_tiles", "merge", "next_wave")

    def __init__(self, sim_tick=True, shop=True, place_towers=True, place_tiles=True, merge=True, next_wave=True):
        self.sim_tick = sim_tick
        self.shop = shop
        self.place_towers = place_towers
        self.place_tiles = place_tiles
        self.merge = merge
        self.next_wave = next_wave


def wave_is_live(game) -> bool:
    """True when enemies or the spawn queue exist. Ignores MagicMock test doubles."""
    if game is None:
        return False
    enemies = getattr(game, "enemies", None)
    queue = getattr(game, "spawn_queue", None)
    if not isinstance(enemies, (list, tuple)):
        enemies = ()
    if not isinstance(queue, (list, tuple)):
        queue = ()
    return bool(enemies or queue)


def play_rules(game=None, pause_open=False) -> PlayRules:
    """Resolve verbs from RUN_FLOW_CONFIG. Pause overlay short-circuits everything."""
    if pause_open:
        return PlayRules(
            sim_tick=False, shop=False, place_towers=False,
            place_tiles=False, merge=False, next_wave=False,
        )
    cfg = RUN_FLOW_CONFIG
    live = wave_is_live(game)
    next_wave = bool(cfg.get("allow_next_wave_button", True))
    if cfg.get("mode") == "auto_chain":
        next_wave = False
    shop = place_towers = place_tiles = merge = True
    if live:
        shop = bool(cfg.get("shop_during_combat", True))
        place_towers = bool(cfg.get("place_towers_during_combat", True))
        place_tiles = bool(cfg.get("place_tiles_during_combat", True))
        merge = bool(cfg.get("merge_during_combat", True))
    return PlayRules(
        sim_tick=True, shop=shop, place_towers=place_towers,
        place_tiles=place_tiles, merge=merge, next_wave=next_wave,
    )


# ---------------------------------------------------------------------------
# Sort Directive orchestration (pool → directive → wave chunks)
# ---------------------------------------------------------------------------
SORT_CONFIG = {
    "enabled": True,
    "default_directive": "PowerSort",
    "planned_waves": 80,
    # None = random seed each run; set an int for reproducible harnesses
    "seed": None,
    # Pre-run: chance the directive name is hidden until Matrix intel
    "directive_hidden_chance": 0.35,
    # Optional forced picks for tests / harness (None = random offer)
    "force_directive": None,
    "force_modifiers": None,
    "force_hidden": None,
}

# One combat hook per Compile pick. Empty / missing keys = 1.0 / no override.
# Does not change wave order — that stays on the directive's restructure().
DIRECTIVE_COMBAT = {
    "PowerSort": {
        "lineage_factor_mult": 0.9,
    },
    "DescendingSpike": {
        "lineage_min_score": 1.0,
    },
    "DroneBubble": {
        "latch_chance_mult": 0.85,
    },
    "AssimilationMerge": {
        "latch_chance_mult": 1.5,
    },
    "PivotPartition": {
        "fill_per_frame_mult": 1.25,
    },
    "PriorityExtract": {
        "hybrid_speed_mult": 1.25,
    },
    "ResistanceBucket": {
        "lineage_factor_mult": 1.25,
    },
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
