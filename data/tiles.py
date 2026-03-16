# ==============================
# SHOP TILE TYPES (Map Expansion)
# ==============================

def get_tile_types(minimal_mode=False):
    """Get tile types. minimal_mode=True returns only basic tiles; False returns all variants."""
    base_tiles = [
        {
            "name": "Straight",
            "width": 2, "height": 1,
            "base_cost": 5,
            "path_grid": [[True, True]],
            "entry_side": "W",
            "exit_side": "E",
            "unlock_level": 1,
            "traits": ["path_short"],
        },
        {
            "name": "Left Turn",
            "width": 2, "height": 2,
            "base_cost": 8,
            "path_grid": [[True, False], [True, True]],
            "entry_side": "S",
            "exit_side": "E",
            "unlock_level": 1,
            "traits": ["path_turn"],
        },
        {
            "name": "Right Turn",
            "width": 2, "height": 2,
            "base_cost": 8,
            "path_grid": [[False, True], [True, True]],
            "entry_side": "S",
            "exit_side": "W",
            "unlock_level": 1,
            "traits": ["path_turn"],
        },
        {
            "name": "Loop",
            "width": 2, "height": 2,
            "base_cost": 12,
            "path_grid": [[True, True], [True, True]],
            "entry_side": "S",
            "exit_side": "N",
            "unlock_level": 1,
            "traits": ["path_loop", "risk_medium"],
        },
    ]

    if not minimal_mode:
        base_tiles.extend([
            {
                "name": "Long Straight",
                "width": 1, "height": 3,
                "base_cost": 15,
                "path_grid": [[True], [True], [True]],
                "entry_side": "N",
                "exit_side": "S",
                "unlock_level": 2,
                "traits": ["path_long", "risk_low"],
            },
            {
                "name": "S-Curve",
                "width": 2, "height": 3,
                "base_cost": 18,
                "path_grid": [[True, False], [True, True], [False, True]],
                "entry_side": "S",
                "exit_side": "E",
                "unlock_level": 2,
                "traits": ["path_complex", "risk_high"],
            },
        ])

    return base_tiles

# Default TILE_TYPES for backward compatibility (full mode)
TILE_TYPES = get_tile_types(minimal_mode=False)