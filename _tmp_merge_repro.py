from core.game import Game
from models.tower import Tower
from data.loader import DataLoader
from config import play_rules

Tower.set_data_loader(DataLoader())
g = Game(minimal_mode=True)
g.gold = 100
g.bench[0] = Tower(0, 0, "Neural Processor")
g.bench[0].game = g
g.bench[1] = Tower(0, 0, "Neural Processor")
g.bench[1].game = g
print("can_merge same", Tower.can_merge(g.bench[0], g.bench[1]))
print("select1", g.economy.select_for_merge(0, 1))
print("m1", g.merge_tower_1, "preview", g.merge_preview, "egrem", g.egrem_preview)
print("select2", g.economy.select_for_merge(1, 1))
print(
    "m1/m2",
    g.merge_tower_1,
    g.merge_tower_2,
    "preview",
    bool(g.merge_preview),
    "egrem",
    g.egrem_preview,
    "incompat",
    g.incompatible_preview,
)
print("confirm", g.economy.confirm_merge())
print(
    "bench0",
    g.bench[0].base_type if g.bench[0] else None,
    "gen",
    getattr(g.bench[0], "merge_generation", None),
)

g2 = Game(minimal_mode=True)
g2.gold = 100
a = Tower(0, 0, "Neural Processor")
a.game = g2
b = Tower(0, 0, "Neural Processor")
b.game = g2
b.merge_generation = 1
b._calculate_stats()
g2.bench[0] = a
g2.bench[1] = b
print("can_merge tiers", Tower.can_merge(a, b), "tiers", a.get_merge_tier(), b.get_merge_tier())
g2.economy.select_for_merge(0, 10)
r = g2.economy.select_for_merge(1, 10)
print("egrem select", r, "egrem_preview", g2.egrem_preview, "cost", g2.current_merge_cost, "gold", g2.gold)
print("complete", g2.economy._complete_egrem())
print("bench", [(t.base_type if t else None) for t in g2.bench])
print("rules merge", play_rules(g2).merge)

# Simulate click path with layout rects
import pygame

pygame.init()
from ui.layout import UILayout
from ui.renderer import Renderer

g3 = Game(minimal_mode=True)
g3.gold = 100
g3.bench[0] = Tower(0, 0, "Neural Processor")
g3.bench[0].game = g3
g3.bench[1] = Tower(0, 0, "Neural Processor")
g3.bench[1].game = g3
r = Renderer(g3)
# force offscreen surface
r.screen = pygame.Surface((r.WIDTH, r.HEIGHT))
from ui.events import EventHandler

h = EventHandler(g3, r)
L = r.layout
c0 = L.bench_card_rect(0).center
c1 = L.bench_card_rect(1).center
h._handle_bench_click(c0[0], c0[1], 1)
h._handle_bench_click(c1[0], c1[1], 1)
print("after clicks preview", bool(g3.merge_preview), "egrem", g3.egrem_preview)
info = g3.economy.get_merge_preview_info()
print("preview info", info is not None, info and info.get("label"))
if g3.merge_preview:
    mrect = L.merge_action_rect(0, 1, "Merge", r.font_merge)
    print("merge_rect", mrect, "center click")
    h._handle_bench_click(mrect.centerx, mrect.centery, 2)
    print("after confirm", [(t.base_type if t else None, getattr(t, "merge_generation", None) if t else None) for t in g3.bench[:3]])
