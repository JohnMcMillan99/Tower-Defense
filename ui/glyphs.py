"""Circuit Relics — 32×32 pixel glyphs. PNG in assets/glyphs/ overrides the fallback."""
from __future__ import annotations

import os
import pygame

_CACHE = {}
_SIZE = 32

# Identity accents (lineage white/brown stay out of these)
_TOWER_PALETTE = {
    "Neural Processor": ((40, 70, 140), (90, 160, 255)),
    "Plasma Capacitor": ((30, 90, 40), (80, 220, 120)),
    "Thermal Regulator": ((120, 50, 20), (230, 130, 50)),
    "Signal Router": ((70, 30, 110), (190, 110, 255)),
    "Quantum Field Gen": ((90, 80, 20), (255, 210, 60)),
    "Nanite Swarm": ((20, 20, 24), (70, 70, 80)),
}

# Virus silhouettes — match renderer enemy_accents, not tower chip greens
_ENEMY_PALETTE = {
    "Drone": ((0, 80, 40), (0, 210, 90)),
    "Scout": ((20, 90, 70), (90, 255, 170)),
    "Harvester": ((80, 90, 10), (190, 220, 50)),
    "Adaptor": ((10, 80, 90), (40, 190, 210)),
    "Assimilator": ((80, 20, 100), (210, 80, 255)),
}

ENEMY_STAMP_ORDER = ("Drone", "Scout", "Harvester", "Adaptor", "Assimilator")


def ordered_composition_names(composition, limit=5):
    """Stable type order for Round Guide stamps. Unknown keys append."""
    if not composition:
        return []
    known = [n for n in ENEMY_STAMP_ORDER if n in composition]
    extra = [k for k in composition if k not in ENEMY_STAMP_ORDER]
    return (known + extra)[: max(0, int(limit))]


def _assets_dir():
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "glyphs"))


def _slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def _fallback_tower(name: str, size: int) -> pygame.Surface:
    dark, light = _TOWER_PALETTE.get(name, ((50, 50, 60), (180, 180, 190)))
    surf = pygame.Surface((size, size))
    surf.fill((8, 8, 12))
    pygame.draw.rect(surf, dark, (2, 2, size - 4, size - 4))
    pygame.draw.rect(surf, light, (2, 2, size - 4, size - 4), 2)
    mid = size // 2
    pygame.draw.rect(surf, light, (0, mid - 3, 4, 6))
    pygame.draw.rect(surf, light, (size - 4, mid - 3, 4, 6))
    if name == "Neural Processor":
        pygame.draw.line(surf, light, (8, 10), (size - 8, 10), 2)
        pygame.draw.line(surf, light, (mid, 10), (mid, size - 8), 2)
        pygame.draw.rect(surf, light, (mid - 3, size - 12, 6, 6))
    elif name == "Plasma Capacitor":
        pygame.draw.circle(surf, light, (mid, mid), size // 4, 2)
        pygame.draw.circle(surf, light, (mid, mid), 3)
    elif name == "Thermal Regulator":
        pygame.draw.polygon(surf, light, [(mid, 7), (size - 8, size - 8), (8, size - 8)], 2)
    elif name == "Signal Router":
        pygame.draw.lines(surf, light, False, [(8, 8), (mid, mid), (size - 8, 8)], 2)
        pygame.draw.lines(surf, light, False, [(8, size - 8), (mid, mid), (size - 8, size - 8)], 2)
    elif name == "Quantum Field Gen":
        pygame.draw.rect(surf, light, (8, 8, size - 16, size - 16), 2)
        pygame.draw.line(surf, light, (8, 8), (size - 8, size - 8), 1)
        pygame.draw.line(surf, light, (size - 8, 8), (8, size - 8), 1)
    else:
        pygame.draw.lines(surf, light, True, [(mid, 6), (size - 8, 12), (size - 10, size - 8), (10, size - 8), (8, 12)], 2)
    return surf


def _fallback_enemy(name: str, size: int) -> pygame.Surface:
    """Filled virus silhouettes — no chip pins, so they do not read as towers."""
    dark, light = _ENEMY_PALETTE.get(name, ((50, 50, 60), (180, 180, 190)))
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    mid = size // 2
    if name == "Drone":
        pts = [(mid, 4), (size - 6, 12), (size - 8, size - 6), (8, size - 6), (6, 12)]
        pygame.draw.polygon(surf, dark, pts)
        pygame.draw.polygon(surf, light, pts, 2)
    elif name == "Scout":
        pts = [(mid, 3), (size - 5, size - 6), (mid, size - 12), (5, size - 6)]
        pygame.draw.polygon(surf, dark, pts)
        pygame.draw.polygon(surf, light, pts, 2)
    elif name == "Harvester":
        pts = [(8, 8), (size - 8, 8), (size - 4, size - 6), (4, size - 6)]
        pygame.draw.polygon(surf, dark, pts)
        pygame.draw.polygon(surf, light, pts, 2)
        pygame.draw.line(surf, light, (10, mid), (size - 10, mid), 2)
    elif name == "Adaptor":
        pts = [(mid, 4), (size - 5, mid), (mid, size - 4), (5, mid)]
        pygame.draw.polygon(surf, dark, pts)
        pygame.draw.polygon(surf, light, pts, 2)
        pygame.draw.circle(surf, light, (mid, mid), 3)
    else:
        # Assimilator / unknown: nested hex
        outer = [(mid, 3), (size - 5, 11), (size - 5, size - 11), (mid, size - 3), (5, size - 11), (5, 11)]
        inner = [(mid, 10), (size - 11, 15), (size - 11, size - 15), (mid, size - 10), (11, size - 15), (11, 15)]
        pygame.draw.polygon(surf, dark, outer)
        pygame.draw.polygon(surf, light, outer, 2)
        pygame.draw.polygon(surf, light, inner, 1)
    return surf


def _fallback(name: str, size: int) -> pygame.Surface:
    if name in _ENEMY_PALETTE:
        return _fallback_enemy(name, size)
    return _fallback_tower(name, size)


def get_glyph(name: str, size: int = _SIZE) -> pygame.Surface:
    key = (name, size)
    if key in _CACHE:
        return _CACHE[key]
    path = os.path.join(_assets_dir(), f"{_slug(name)}.png")
    if os.path.isfile(path):
        img = pygame.image.load(path)
        if img.get_size() != (size, size):
            img = pygame.transform.scale(img, (size, size))
        _CACHE[key] = img
        return img
    surf = _fallback(name, size)
    _CACHE[key] = surf
    return surf


def blit_glyph(screen, name, dest_rect, pad=4, valign="top"):
    """Draw a glyph in dest_rect. Shop/bench use top pad; map units use center."""
    inner = max(12, min(dest_rect.w, dest_rect.h) - pad * 2)
    glyph = get_glyph(name, 32)
    scaled = pygame.transform.scale(glyph, (inner, inner))
    x = dest_rect.x + (dest_rect.w - inner) // 2
    if valign == "center":
        y = dest_rect.y + (dest_rect.h - inner) // 2
    else:
        y = dest_rect.y + pad
    screen.blit(scaled, (x, y))
