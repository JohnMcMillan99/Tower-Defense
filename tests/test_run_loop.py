"""Headless golden path: menu → run select → play → pause blocks shop → checkpoint → run over."""
from core.app import App, SCREEN_MAIN, SCREEN_RUN_SELECT, SCREEN_IN_RUN
from config import play_rules, RUN_FLOW_CONFIG, ECONOMY_CONFIG


def test_play_rules_pause_blocks_all_verbs():
    rules = play_rules(None, pause_open=True)
    assert rules.sim_tick is False
    assert rules.shop is False
    assert rules.place_towers is False
    assert rules.place_tiles is False
    assert rules.merge is False
    assert rules.next_wave is False


def test_play_rules_live_always_allows_shop_without_enemies():
    rules = play_rules(None, pause_open=False)
    assert rules.shop is True
    assert rules.sim_tick is True


def test_app_boot_is_main_menu():
    app = App(headless=True, minimal_mode=True)
    assert app.screen == SCREEN_MAIN
    assert app.game is None


def test_app_new_run_creates_game_only_then():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    assert app.screen == SCREEN_RUN_SELECT
    assert app.game is None
    app.new_run()
    assert app.screen == SCREEN_IN_RUN
    assert app.game is not None
    assert app.game.gold == int(ECONOMY_CONFIG.get("starting_gold", 25))


def test_new_run_toasts_sort_identity():
    from core.run_setup import RunSetup, DIRECTIVE_BLURBS

    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    setup = RunSetup(seed=9, directive_name="DescendingSpike", directive_hidden=False)
    app.new_run(run_setup=setup)
    assert "Descending Spike" in app.game.reward_toast_text
    assert DIRECTIVE_BLURBS["DescendingSpike"] in app.game.reward_toast_text
    assert app.game.reward_toast_until > 0


def test_pause_menu_blocks_shop():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.game.economy.generate_shop()
    app.open_pause()
    gold = app.game.gold
    assert play_rules(app.game, pause_open=True).shop is False
    assert app.game.economy.move_to_bench(0) is False
    assert app.game.gold == gold
    app.close_pause()
    # Unpaused: buying is allowed if gold and bench space exist
    assert play_rules(app.game, pause_open=False).shop is True


def test_pause_blocks_loot_and_sell():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.game.loot_bag[0] = {"name": "Straight", "width": 1, "height": 1}
    app.game.economy.generate_shop()
    app.game.economy.move_to_bench(0)
    app.open_pause()
    gold = app.game.gold
    assert app.game.economy.select_loot(0) is False
    assert app.game.selected_loot is None
    app.game.economy.sell_from_bench(0)
    assert app.game.gold == gold
    assert app.game.bench[0] is not None
    app.close_pause()
    assert app.game.economy.select_loot(0) is True


def test_wave_clear_writes_checkpoint():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    assert app.save_store.has_checkpoint(0) is False
    app.on_wave_cleared(1)
    assert app.save_store.has_checkpoint(0) is True
    ckpt = app.save_store.checkpoints[0]
    assert ckpt.wave_number == 2
    assert ckpt.gold == app.game.gold


def test_defeat_clears_checkpoint_and_records_run():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.on_wave_cleared(1)
    app.on_run_over("defeat")
    assert app.save_store.has_checkpoint(0) is False
    assert app.save_store.profile(0).runs_played == 1
    assert app.save_store.profile(0).runs_won == 0
    assert app.save_store.profile(0).dilithium >= 8


def test_victory_after_configured_waves(monkeypatch):
    monkeypatch.setitem(RUN_FLOW_CONFIG, "victory_waves", 1)
    monkeypatch.setitem(RUN_FLOW_CONFIG, "endless_after_victory", False)
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.game.wave_active = True
    app.game.enemies = []
    app.game.spawn_queue = []
    app.game.wave_manager.update_wave(30)
    assert app.game.game_over is True
    assert app.game.run_over_reason == "victory"


def test_wave_clear_toast_names_the_wave():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.game.wave_active = True
    app.game.enemies = []
    app.game.spawn_queue = []
    app.game.round_num = 3
    app.game.wave_manager.update_wave(30)
    assert "Wave 3 cleared" in app.game.wave_bonus_text
    assert "gold" in app.game.wave_bonus_text.lower()


def test_hit_queues_combat_pop():
    from models.tower import Tower
    from models.enemy import Enemy

    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    enemy = Enemy(app.game.path, "Drone", wave_num=1)
    tower = Tower(0, 0, "Neural Processor")
    tower.game = app.game
    tower._damage_enemy(enemy, 5)
    assert app.game.combat_pops
    assert app.game.combat_pops[0]["dmg"] >= 1


def test_forfeit_from_pause():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.open_pause()
    app.forfeit_run()
    assert app.game.game_over is True
    assert app.game.run_over_reason == "forfeit"
    assert app.save_store.has_checkpoint(0) is False
    assert app.pause_open is False


def test_place_tower_sets_game_ref():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    from models.tower import Tower
    t = Tower(0, 0, "Neural Processor")
    app.game.bench[0] = t
    gx, gy = 2, 2
    # Find an empty non-path cell
    placed = False
    for y in range(app.game.height):
        for x in range(app.game.width):
            if app.game.grid[y][x] == ".":
                placed = app.game.economy.place_tower(x, y, 0)
                if placed:
                    assert app.game.towers[-1].game is app.game
                    return
    assert placed


def test_continue_restores_wave_clear_snapshot():
    from models.tower import Tower

    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.game.gold = 41
    app.game.lives = 17
    app.game.round_num = 4
    app.game.intel = 12
    t = Tower(3, 3, "Plasma Capacitor")
    t.upgrades = ["wild_1"]
    t.game = app.game
    app.game.towers.append(t)
    app.game.grid[3][3] = "P"
    path_before = list(app.game.path)
    app.on_wave_cleared(3)
    assert app.save_store.has_checkpoint(0)
    assert app.save_store.checkpoints[0].snapshot.get("gold") == 41

    app.continue_run()
    assert app.screen == SCREEN_IN_RUN
    assert app.game.gold == 41
    assert app.game.lives == 17
    assert app.game.round_num == 4
    assert app.game.intel == 12
    assert app.game.wave_active is False
    assert app.game.enemies == []
    assert len(app.game.towers) == 1
    assert app.game.towers[0].base_type == "Plasma Capacitor"
    assert app.game.towers[0].upgrades == ["wild_1"]
    assert list(app.game.path) == path_before
    # Continue does not re-apply Collective start-gold
    app.save_store.profile(0).unlock_ids = ["start_gold_1"]
    gold = app.game.gold
    app.continue_run()
    assert app.game.gold == gold


def test_checkpoint_survives_disk_reload(tmp_path):
    from core.save import MemorySaveStore

    path = str(tmp_path / "profiles.json")
    app = App(headless=True, minimal_mode=True)
    app.save_store = MemorySaveStore(path=path)
    app.select_slot(0)
    app.new_run()
    app.game.gold = 33
    app.on_wave_cleared(1)
    other = MemorySaveStore(path=path)
    assert other.has_checkpoint(0)
    assert other.checkpoints[0].gold == 33
    assert other.checkpoints[0].snapshot.get("gold") == 33


def test_quit_while_wave_live_forfeits():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.on_wave_cleared(1)
    app.game.enemies = [object()]
    app._quit_cleanup()
    assert app.game.run_over_reason == "forfeit"
    assert app.save_store.has_checkpoint(0) is False


def test_return_to_run_select_drops_game():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.return_to_run_select()
    assert app.screen == SCREEN_RUN_SELECT
    assert app.game is None


def test_run_over_click_returns_to_select_without_crash():
    """Clicking the end-of-run prompt must not read handler.running after teardown."""
    import pygame

    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    app.game.game_over = True
    app.game.run_over_reason = "victory"

    class FakeHandler:
        running = True

        def process_event(self, event, frame=0):
            raise AssertionError("run-over clicks belong to App, not EventHandler")

    app.handler = FakeHandler()
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (100, 100)})
    app.process_event(event)
    assert app.screen == SCREEN_RUN_SELECT
    assert app.handler is None
    assert app.running is True


def test_handler_teardown_during_event_does_not_crash():
    """If a handler pops the run mid-dispatch, App must not deref a dead handler."""
    import pygame

    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()

    class FakeHandler:
        running = True

        def process_event(self, event, frame=0):
            app.return_to_run_select()

    app.handler = FakeHandler()
    event = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (10, 10), "rel": (0, 0), "buttons": (0, 0, 0)})
    app.process_event(event)
    assert app.screen == SCREEN_RUN_SELECT
    assert app.running is True


def test_new_run_button_opens_sort_offer():
    import pygame

    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": app.run_select_rects()["new"].center})
    app.process_event(event)
    assert app.sort_offer_open is True
    assert app.game is None
    assert app.screen == SCREEN_RUN_SELECT
    assert app.sort_offer is not None
    assert len(app.sort_offer.directives) == 3


def test_compile_sort_offer_starts_run_with_selected_directive():
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.open_sort_offer()
    app.sort_offer.selected = 1
    name = app.sort_offer.directives[1]
    app.confirm_sort_offer()
    assert app.screen == SCREEN_IN_RUN
    assert app.game is not None
    assert app.game.run_setup.directive_name == name
    assert app.sort_offer_open is False


def test_sort_offer_card_click_selects_without_starting():
    import pygame

    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.open_sort_offer()
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": app.sort_offer_card_rects()[2].center})
    app.process_event(event)
    assert app.sort_offer.selected == 2
    assert app.game is None
    assert app.sort_offer_open is True


def test_sort_offer_back_cancels():
    import pygame

    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.open_sort_offer()
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": app.sort_offer_action_rects()["back"].center})
    app.process_event(event)
    assert app.sort_offer_open is False
    assert app.game is None
    assert app.screen == SCREEN_RUN_SELECT


def test_force_directive_skips_sort_offer(monkeypatch):
    from config import SORT_CONFIG

    monkeypatch.setitem(SORT_CONFIG, "force_directive", "PowerSort")
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.open_sort_offer()
    assert app.sort_offer_open is False
    assert app.screen == SCREEN_IN_RUN
    assert app.game.run_setup.directive_name == "PowerSort"


def test_wave_size_caps_late_waves():
    from core.sort_orchestrator import default_wave_size
    from config import WAVE_CONFIG

    cap = int(WAVE_CONFIG["size_cap"])
    assert default_wave_size(1) == 6
    assert default_wave_size(17) == cap
    assert default_wave_size(80) == cap


def test_auto_waits_clear_beat(monkeypatch):
    monkeypatch.setitem(RUN_FLOW_CONFIG, "clear_beat_seconds", 2)
    monkeypatch.setitem(RUN_FLOW_CONFIG, "victory_waves", 99)
    app = App(headless=True, minimal_mode=True)
    app.select_slot(0)
    app.new_run()
    g = app.game
    g.auto_mode = True
    g.wave_active = True
    g.enemies = []
    g.spawn_queue = []
    g.wave_manager.update_wave(10)
    assert g.game_over is False
    assert g.wave_active is False
    assert g.round_num == 2
    assert g.clear_beat_until == 130
    g.wave_manager.update_wave(129)
    assert g.wave_active is False
    g.wave_manager.update_wave(130)
    assert g.wave_active is True


def test_auto_run_clock_targets_twenty_minutes(monkeypatch):
    """f10: spawn_interval / size_cap / clear_beat only → ~20 min Auto success."""
    from core.sort_orchestrator import estimate_auto_run_seconds
    from config import SORT_CONFIG, WAVE_CONFIG, RUN_FLOW_CONFIG

    monkeypatch.setitem(RUN_FLOW_CONFIG, "victory_waves", 80)
    monkeypatch.setitem(RUN_FLOW_CONFIG, "clear_beat_seconds", 2)
    monkeypatch.setitem(WAVE_CONFIG, "base_size", 5)
    monkeypatch.setitem(WAVE_CONFIG, "per_wave", 1)
    monkeypatch.setitem(WAVE_CONFIG, "size_cap", 22)
    monkeypatch.setitem(WAVE_CONFIG, "spawn_interval", 30)
    monkeypatch.setitem(SORT_CONFIG, "planned_waves", 80)

    est = estimate_auto_run_seconds()
    assert est["victory_waves"] == 80
    assert SORT_CONFIG["planned_waves"] >= 80
    # Envelope: ~18–22 minutes with default tail assumption
    assert 18.0 <= est["minutes"] <= 22.0
    # Mid-run death proxy (~wave 45–50) lands near ~12 min
    mid = estimate_auto_run_seconds(victory_waves=48)
    assert 10.0 <= mid["minutes"] <= 14.0
