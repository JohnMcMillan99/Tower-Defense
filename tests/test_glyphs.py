"""Circuit Relics vs virus glyphs — distinct silhouettes, shared PNG override path."""
import pygame

pygame.init()


def test_enemy_glyphs_are_distinct():
    from ui.glyphs import get_glyph

    drone = pygame.image.tostring(get_glyph("Drone"), "RGBA")
    scout = pygame.image.tostring(get_glyph("Scout"), "RGBA")
    harv = pygame.image.tostring(get_glyph("Harvester"), "RGBA")
    assert drone != scout
    assert scout != harv
    assert drone != harv


def test_tower_glyphs_still_chip_shaped():
    from ui.glyphs import get_glyph

    neural = get_glyph("Neural Processor")
    drone = get_glyph("Drone")
    assert neural.get_size() == (32, 32)
    assert drone.get_size() == (32, 32)
    assert pygame.image.tostring(neural, "RGBA") != pygame.image.tostring(drone, "RGBA")


def test_all_enemy_types_have_glyphs():
    from ui.glyphs import get_glyph
    from models.enemy import Enemy

    for name in Enemy.TYPES:
        g = get_glyph(name)
        assert g.get_width() == 32
        # Virus glyphs are transparent outside the silhouette (towers are opaque chips)
        assert g.get_at((0, 0))[3] < 255


def test_composition_names_follow_virus_order():
    from ui.glyphs import ordered_composition_names

    names = ordered_composition_names({"Assimilator": 10, "Drone": 80, "Scout": 10})
    assert names == ["Drone", "Scout", "Assimilator"]
    assert ordered_composition_names({}) == []
