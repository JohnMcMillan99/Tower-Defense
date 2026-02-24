# ==============================
# SHOP TILE TYPES (Map Expansion)
# ==============================
TILE_TYPES = [
    {
        "name": "Straight",
        "width": 2, "height": 1,
        "base_cost": 5,
        "path_grid": [[True, True]],
        "entry_side": "W",
        "exit_side": "E",
    },
    {
        "name": "Left Turn",
        "width": 2, "height": 2,
        "base_cost": 8,
        "path_grid": [[True, False], [True, True]],
        "entry_side": "S",
        "exit_side": "E",
    },
    {
        "name": "Right Turn",
        "width": 2, "height": 2,
        "base_cost": 8,
        "path_grid": [[False, True], [True, True]],
        "entry_side": "S",
        "exit_side": "W",
    },
    {
        "name": "Loop",
        "width": 2, "height": 2,
        "base_cost": 12,
        "path_grid": [[True, True], [True, True]],
        "entry_side": "S",
        "exit_side": "N",
    },
]