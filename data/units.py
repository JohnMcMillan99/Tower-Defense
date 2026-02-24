# ==============================
# SHOP UNIT TYPES (Hardware Components)
# ==============================
UNIT_TYPES = [
    {"name": "Neural Processor", "base_cost": 3},
    {"name": "Plasma Capacitor",  "base_cost": 4},
    {"name": "Thermal Regulator",   "base_cost": 3},
    {"name": "Signal Router",      "base_cost": 4},
    {"name": "Quantum Field Gen",   "base_cost": 5},
]

# ==============================
# HARDWARE TRAITS (for software synergy)
# ==============================
TOWER_TRAITS = {
    "Neural Processor": ["switch", "logic"],
    "Plasma Capacitor":  ["charge", "burst"],
    "Thermal Regulator":   ["resist", "heat"],
    "Signal Router":      ["block", "flow"],
    "Quantum Field Gen":   ["filter", "magnetic"],
    "Nanite Swarm":      ["egrem", "spawner"],
}

# ==============================
# WEB MODE CONFIGURATION
# ==============================
WEB_MODE_CONFIG = {
    "enemy_scale": 0.75,  # Reduce enemy health/speed by 25% in browser mode
}