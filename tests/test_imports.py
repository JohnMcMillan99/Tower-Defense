#!/usr/bin/env python3
"""Test script to check if our tile placement logic works"""

# Test the tile placement logic
from utils.path_generator import PathGenerator

# Create a simple path
pg = PathGenerator(6, 10)
path = pg.generate_path()
print(f"Generated initial path: {path}")

# Test tile placement - simulate placing a straight tile
# Assume the path ends at some position
if path:
    path_end = path[-1]
    print(f"Path end: {path_end}")

    # Simulate a straight tile at position (path_end[0]+1, path_end[1])
    # This should connect to the path end
    tile_gx = path_end[0] + 1
    tile_gy = path_end[1]
    tile_cells = [(tile_gx, tile_gy), (tile_gx + 1, tile_gy)]  # Straight tile
    print(f"Tile cells: {tile_cells}")

    # Check adjacency
    def adjacent(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1

    tile_endpoints = [tile_cells[0], tile_cells[-1]]  # First and last cells as endpoints
    print(f"Tile endpoints: {tile_endpoints}")

    connects = any(adjacent(te, path_end) for te in tile_endpoints)
    print(f"Tile connects to path end: {connects}")

    if connects:
        # Simulate placement
        extended_path = path + tile_cells
        print(f"Extended path: {extended_path}")
        print("✓ Tile placement simulation successful!")
    else:
        print("❌ Tile placement would fail - no connection to path end")