"""UILayout rect helpers — draw and click share one source of truth."""
import pygame

pygame.init()


def test_shop_and_reroll_rects():
    from ui.layout import UILayout
    from unittest.mock import MagicMock

    game = MagicMock()
    game.width = 18
    game.height = 14
    game.minimal_mode = True
    L = UILayout(game)
    assert L.shop_card_rect(0) == pygame.Rect(12, 18, 70, 100)
    assert L.shop_card_rect(4).x == 12 + 4 * 80
    rr = L.reroll_rect()
    assert rr.w == 35 and rr.h == 35
    assert rr.right <= L.shop_col_w


def test_top_row_shop_map_split_5_3():
    from ui.layout import UILayout
    from unittest.mock import MagicMock

    game = MagicMock()
    game.width = 18
    game.height = 14
    game.loot_bag = [None] * 4
    game.bench = [None] * 5
    L = UILayout(game)
    assert L.shop_col_w + L.map_col_w == L.GRID_W
    assert L.shop_col_w == (L.GRID_W * 5) // 8
    shop = L.shop_region()
    maps = L.map_column_region()
    assert shop.right == maps.left
    assert shop.top == maps.top == 0
    assert shop.h == maps.h == L.SHOP_H
    # Loot cards sit in the map column, above the tower bench
    card0 = L.loot_card_rect(0)
    assert maps.collidepoint(card0.center)
    assert card0.bottom < L.SHOP_H
    # Tower bench is 5 slots under both columns
    bench0 = L.bench_card_rect(0)
    assert bench0.y >= L.SHOP_H
    assert L.bench_card_rect(4).right <= L.GRID_W
    assert L.tower_slots == 5
    assert L.loot_slots == 4


def test_panel_buttons_stack():
    from ui.layout import UILayout
    from unittest.mock import MagicMock

    game = MagicMock()
    game.width = 18
    game.height = 14
    game.minimal_mode = True
    L = UILayout(game)
    play, nxt, auto = L.panel_control_rects(show_spl=False)
    assert play.y < nxt.y < auto.y
    play2, nxt2, auto2 = L.panel_control_rects(show_spl=True)
    assert play2.y > play.y


def test_inspector_tabs_cover_width():
    from ui.layout import UILayout
    from unittest.mock import MagicMock

    game = MagicMock()
    game.width = 18
    game.height = 14
    L = UILayout(game)
    tabs = L.inspector_tab_rects()
    outer = L.inspector_rect()
    assert set(tabs) == {"tower", "enemy", "stats"}
    assert tabs["tower"].x == outer.x
    assert tabs["stats"].right == outer.right


def test_game_inspector_aliases():
    from core.game import Game

    g = Game(minimal_mode=True)
    g.open_inspector("stats")
    assert g.tower_stats_open is True
    assert g.inspector_mode == "stats"
    g.tower_stats_open = False
    assert g.inspector_mode is None
    g.open_inspector("enemy", object())
    assert g.selected_enemy is not None
    g.selected_enemy = None
    assert g.inspector_mode is None
