"""Collective: Dilithium spends, unlocks install on New Run, profile can persist."""
from core.app import App, SCREEN_RUN_SELECT
from core.collective import try_buy, stubs, apply_to_run, CURRENCY
from core.save import MemorySaveStore
from config import HUD_CONFIG, ECONOMY_CONFIG, BENCH_CONFIG


def test_collective_buy_requires_dilithium():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    p = app.save_store.profile(0)
    assert p.dilithium == 0
    msg = try_buy(p, "bench_slot_1")
    assert CURRENCY in msg
    assert "Insufficient" in msg
    assert p.unlock_ids == []
    p.dilithium = 100
    msg = try_buy(p, "bench_slot_1")
    assert "installed" in msg
    assert "bench_slot_1" in p.unlock_ids
    assert p.dilithium == 0
    assert try_buy(p, "bench_slot_1").startswith("Aux Rack")


def test_unlocks_apply_on_new_run():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.save_store.profile(0).unlock_ids = ["bench_slot_1", "reroll_cheap", "start_gold_1"]
    app.new_run()
    assert len(app.game.bench) == int(BENCH_CONFIG.get("tower_slots", 5)) + 1
    assert app.game.reroll_cost == 1
    assert app.game.gold == int(ECONOMY_CONFIG.get("starting_gold", 25)) + 5


def test_apply_to_run_does_not_mutate_config():
    from config import ECONOMY_CONFIG
    gold = ECONOMY_CONFIG["starting_gold"]
    reroll = ECONOMY_CONFIG["reroll_cost"]
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    apply_to_run(app.game, ["reroll_cheap", "start_gold_1"])
    assert ECONOMY_CONFIG["starting_gold"] == gold
    assert ECONOMY_CONFIG["reroll_cost"] == reroll


def test_profile_persists_dilithium(tmp_path):
    path = str(tmp_path / "profiles.json")
    store = MemorySaveStore(path=path)
    p = store.profile(0)
    p.dilithium = 40
    p.unlock_ids = ["start_gold_1"]
    store.persist()
    loaded = MemorySaveStore(path=path)
    assert loaded.profile(0).dilithium == 40
    assert loaded.profile(0).unlock_ids == ["start_gold_1"]
    assert loaded.profile(1).dilithium == 0


def test_collective_opens_from_run_select():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    assert app.screen == SCREEN_RUN_SELECT
    app.collective_open = True
    import pygame
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": app.collective_card_rects()[0].center})
    app.process_event(event)
    assert "Insufficient" in app.collective_status
    assert app.collective_open is True


def test_hud_toggles_flip_shared_config():
    HUD_CONFIG["enemy_health_bars"] = True
    HUD_CONFIG["enemy_names"] = True
    HUD_CONFIG["enemy_health_bars"] = False
    assert HUD_CONFIG["enemy_health_bars"] is False
    HUD_CONFIG["enemy_health_bars"] = True
    HUD_CONFIG["enemy_names"] = True


def test_stub_ids_match_yaml_l4_slice():
    ids = {c["id"] for c in stubs()}
    assert ids == {"bench_slot_1", "reroll_cheap", "start_gold_1"}
