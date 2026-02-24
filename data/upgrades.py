# ==============================
# SOFTWARE UPGRADES (firmware patches)
# id → {name, desc, cost, traits, synergizes_with, dmg_mult, range_bonus, fire_rate_mult, heat_delta}
# heat_delta >0 = generates heat, <0 = cools / clears heat
# ==============================
UPGRADE_DEFS = {
    # Synergistic upgrades
    "switch_1": {"name": "Overclock Driver",     "desc": "+25% dmg, +heat",         "cost": 4,  "traits": ["switch"],   "synergizes_with": ["switch", "logic"],   "dmg_mult": 0.25, "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 1.5},
    "switch_2": {"name": "Burst Gate Firmware",  "desc": "+40% fire rate",          "cost": 6,  "traits": ["switch"],   "synergizes_with": ["switch"],             "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0.40, "heat_delta": 2.0},
    "charge_1": {"name": "Supercap Patch",       "desc": "+1 range, faster charge", "cost": 4,  "traits": ["charge"],   "synergizes_with": ["charge", "burst"],   "dmg_mult": 0,    "range_bonus": 1, "fire_rate_mult": 0,    "heat_delta": -0.5},
    "charge_2": {"name": "EMP Discharge",        "desc": "AoE stun on burst",       "cost": 7,  "traits": ["charge"],   "synergizes_with": ["charge"],             "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 1.0},  # stun logic added later
    "resist_1": {"name": "Cooling Heatsink",     "desc": "Aura: -heat nearby",      "cost": 5,  "traits": ["resist"],   "synergizes_with": ["resist", "heat"],     "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0.15, "heat_delta": -1.2},
    "resist_2": {"name": "Thermal Throttle",     "desc": "Slow enemies 30%",        "cost": 6,  "traits": ["resist"],   "synergizes_with": ["resist"],             "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 0},    # slow aura added later
    "block_1":  {"name": "Rectifier Shield",     "desc": "Block 20% debuffs",       "cost": 4,  "traits": ["block"],    "synergizes_with": ["block", "flow"],      "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": -0.8},
    "block_2":  {"name": "Laser Diode Focus",    "desc": "Piercing beam (2 hits)",  "cost": 6,  "traits": ["block"],    "synergizes_with": ["block"],              "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 0.5},
    "filter_1": {"name": "Inductive Trap",       "desc": "Pull enemies closer",     "cost": 5,  "traits": ["filter"],   "synergizes_with": ["filter", "magnetic"], "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 0},
    "filter_2": {"name": "EMI Filter",           "desc": "Stun fast enemies",       "cost": 7,  "traits": ["filter"],   "synergizes_with": ["filter"],             "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": 1.0},

    # Wildcard / general upgrades
    "wild_1":   {"name": "Quantum Patch",        "desc": "+15% all stats",          "cost": 5,  "traits": ["wildcard"], "synergizes_with": [],                     "dmg_mult": 0.15, "range_bonus": 0, "fire_rate_mult": 0.15, "heat_delta": 0.5},
    "wild_2":   {"name": "Nanite Antivirus",     "desc": "Kill gives +1 gold",      "cost": 4,  "traits": ["wildcard"], "synergizes_with": [],                     "dmg_mult": 0,    "range_bonus": 0, "fire_rate_mult": 0,    "heat_delta": -0.3},
}

# Separate lists for choice logic
UPGRADE_SYNERGY = [k for k in UPGRADE_DEFS if not k.startswith("wild")]
UPGRADE_WILDCARD = [k for k in UPGRADE_DEFS if k.startswith("wild")]

# ==============================
# EGREM SPAWNING CONFIG
# ==============================
# Maps tower types to spawn parameters: {enemy_type, spawn_count, spawn_interval_frames}
EGREM_SPAWN_CONFIG = {
    "Neural Processor": {"enemy_type": "Drone",       "base_spawn": 2, "spawn_interval": 90, "wave_scale": 1.0},
    "Plasma Capacitor":  {"enemy_type": "Harvester",   "base_spawn": 1, "spawn_interval": 120, "wave_scale": 1.2},
    "Thermal Regulator":   {"enemy_type": "Drone",       "base_spawn": 3, "spawn_interval": 60, "wave_scale": 0.8},
    "Signal Router":      {"enemy_type": "Scout",       "base_spawn": 2, "spawn_interval": 75, "wave_scale": 1.1},
    "Quantum Field Gen":   {"enemy_type": "Adaptor",     "base_spawn": 1, "spawn_interval": 100, "wave_scale": 1.3},
}