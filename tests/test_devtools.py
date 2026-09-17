"""Dev Tools catalog mutates live tables; New Run reads them."""
from core.app import App, SCREEN_RUN_SELECT
from core.devtools import catalog, reset_catalog_for_tests
from core.sort_orchestrator import default_wave_size
from config import ECONOMY_CONFIG, RUN_FLOW_CONFIG
from models.tower import Tower
from models.enemy import Enemy


def setup_function():
    reset_catalog_for_tests()
    catalog().ensure()
    catalog().reset_all()


def teardown_function():
    catalog().reset_all()
    reset_catalog_for_tests()


def test_catalog_walks_flow_and_economy():
    cat = catalog()
    ids = [t.id for t in cat.tables]
    assert "flow" in ids
    assert "economy" in ids
    assert "towers" in ids
    assert "enemies" in ids
    assert "directive_combat" in ids
    keys = {lf.path[-1] for lf in cat.leaves("directive_combat")}
    assert "latch_chance_mult" in keys
    assert "lineage_factor_mult" in keys
    keys = {lf.path[-1] for lf in cat.leaves("economy")}
    assert "starting_gold" in keys
    assert "starting_lives" in keys


def test_set_mutates_live_config():
    cat = catalog()
    cat.set("economy", ("starting_gold",), 99)
    assert ECONOMY_CONFIG["starting_gold"] == 99
    cat.set("flow", ("victory_waves",), 4)
    assert RUN_FLOW_CONFIG["victory_waves"] == 4
    cat.reset_all()
    assert ECONOMY_CONFIG["starting_gold"] == 25
    assert RUN_FLOW_CONFIG["victory_waves"] == 80


def test_wave_size_reads_wave_config():
    catalog().set("waves", ("base_size",), 10)
    catalog().set("waves", ("per_wave",), 1)
    assert default_wave_size(3) == 13
    catalog().reset_all()
    assert default_wave_size(1) == 6


def test_new_run_picks_up_slider_values():
    catalog().set("economy", ("starting_gold",), 77)
    catalog().set("economy", ("starting_lives",), 9)
    catalog().set("flow", ("victory_waves",), 3)
    catalog().set("waves", ("spawn_interval",), 12)
    catalog().set("towers", ("Neural Processor", "dmg"), 15)
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    assert app.game.gold == 77
    assert app.game.lives == 9
    assert app.game.spawn_interval == 12
    assert RUN_FLOW_CONFIG["victory_waves"] == 3
    t = Tower(0, 0, "Neural Processor")
    assert t.dmg == 15
    catalog().reset_all()


def test_enemy_hp_scale_uses_wave_config():
    catalog().set("waves", ("hp_scale_per_wave",), 0.0)
    catalog().set("enemies", ("Drone", "health"), 10)
    e = Enemy([(0, 0)], "Drone", wave_num=5)
    assert e.max_health == 10
    catalog().reset_all()


def test_easy_preset_is_current_defaults():
    cat = catalog()
    cat.set("economy", ("starting_gold",), 99)
    cat.apply_preset("easy")
    assert ECONOMY_CONFIG["starting_gold"] == 25
    assert RUN_FLOW_CONFIG["victory_waves"] == 80
    assert cat.active_preset == "easy"


def test_medium_and_hard_scale_the_fight():
    cat = catalog()
    cat.apply_preset("medium")
    assert RUN_FLOW_CONFIG["victory_waves"] == 15
    assert ECONOMY_CONFIG["starting_lives"] == 15
    assert default_wave_size(1) == 9  # 6 + 1*3
    assert Enemy.TYPES["Drone"]["health"] == 13
    cat.apply_preset("hard")
    assert RUN_FLOW_CONFIG["victory_waves"] == 20
    assert ECONOMY_CONFIG["starting_lives"] == 10
    assert default_wave_size(1) == 12  # 8 + 1*4
    assert Enemy.TYPES["Drone"]["health"] == 16
    cat.apply_preset("easy")
    assert default_wave_size(1) == 6
    assert Enemy.TYPES["Drone"]["health"] == 10


def test_save_and_reload_user_loadout(tmp_path):
    from core.dev_presets import PresetStore
    from core.devtools import reset_catalog_for_tests

    store = PresetStore(path=str(tmp_path / "dev_presets.json"))
    reset_catalog_for_tests(store)
    cat = catalog()
    cat.ensure()
    cat.reset_all()
    cat.set("economy", ("starting_gold",), 88)
    cat.set("flow", ("victory_waves",), 6)
    slot = cat.save_loadout("user_2")
    assert slot == "user_2"
    assert (tmp_path / "dev_presets.json").is_file()
    cat.apply_preset("easy")
    assert ECONOMY_CONFIG["starting_gold"] == 25
    cat.apply_preset("user_2")
    assert ECONOMY_CONFIG["starting_gold"] == 88
    assert RUN_FLOW_CONFIG["victory_waves"] == 6
    # Fresh catalog, same file
    reset_catalog_for_tests(PresetStore(path=str(tmp_path / "dev_presets.json")))
    catalog().ensure()
    catalog().apply_preset("user_2")
    assert ECONOMY_CONFIG["starting_gold"] == 88


def test_empty_user_slot_does_not_apply(tmp_path):
    from core.dev_presets import PresetStore
    from core.devtools import reset_catalog_for_tests

    reset_catalog_for_tests(PresetStore(path=str(tmp_path / "empty.json")))
    cat = catalog()
    cat.ensure()
    cat.reset_all()
    assert cat.apply_preset("user_1") is False
    assert cat.active_preset == "easy"


def test_devtools_button_opens_overlay_without_selecting_slot():
    app = App(headless=True, minimal_mode=True)
    assert app.screen != SCREEN_RUN_SELECT
    app.devtools.open_panel()
    assert app.devtools.open is True
    # Slot click is ignored while overlay owns events
    import pygame
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (480, 220)})
    app.process_event(event)
    assert app.screen != SCREEN_RUN_SELECT
    app.devtools.close()
    assert app.devtools.open is False
