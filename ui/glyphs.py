"""Circuit Relics — 32×32 pixel glyphs. PNG in assets/glyphs/ overrides the fallback."""
from __future__ import annotations

import os
import pygame

_CACHE = {}
_SIZE = 32

# Identity accents (lineage white/brown and egrem green stay out of these)
_PALETTE = {
    "Neural Processor": ((40, 70, 140), (90, 160, 255)),
    "Plasma Capacitor": ((30, 90, 40), (80, 220, 120)),
    "Thermal Regulator": ((120, 50, 20), (230, 130, 50)),
    "Signal Router": ((70, 30, 110), (190, 110, 255)),
    "Quantum Field Gen": ((90, 80, 20), (255, 210, 60)),
    "Nanite Swarm": ((20, 20, 24), (70, 70, 80)),
}


def _assets_dir():
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "glyphs"))


def _slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def _fallback(name: str, size: int) -> pygame.Surface:
    dark, light = _PALETTE.get(name, ((50, 50, 60), (180, 180, 190)))
    surf = pygame.Surface((size, size))
    surf.fill((8, 8, 12))
    pygame.draw.rect(surf, dark, (2, 2, size - 4, size - 4))
    pygame.draw.rect(surf, light, (2, 2, size - 4, size - 4), 2)
    # Chip pins
    mid = size // 2
    pygame.draw.rect(surf, light, (0, mid - 3, 4, 6))
    pygame.draw.rect(surf, light, (size - 4, mid - 3, 4, 6))
    # Per-type stamp
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
        # Broken-hex swarm (egrem / unknown) — not green
        pygame.draw.lines(surf, light, True, [(mid, 6), (size - 8, 12), (size - 10, size - 8), (10, size - 8), (8, 12)], 2)
    return surf


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


def blit_glyph(screen, name, dest_rect, pad=4):
    """Draw a glyph centered in dest_rect, leaving room for labels."""
    inner = max(12, min(dest_rect.w, dest_rect.h) - pad * 2)
    glyph = get_glyph(name, 32)
    scaled = pygame.transform.scale(glyph, (inner, inner))
    x = dest_rect.x + (dest_rect.w - inner) // 2
    y = dest_rect.y + pad
    screen.blit(scaled, (x, y))
