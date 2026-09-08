"""
App screen stack: MainMenu → RunSelect → InRun, plus Esc PauseMenu overlay.

Game is constructed only on New Run. Menus work without a Game instance.
"""
from __future__ import annotations

import pygame

from config import play_rules, wave_is_live
from core.checkpoint import restore_run, snapshot_run
from core.collective import apply_to_run, stubs as collective_stubs, try_buy as collective_buy, CURRENCY
from core.save import MemorySaveStore, RunCheckpoint, default_profiles_path
from ui.devtools import DevToolsPanel

SCREEN_MAIN = "main_menu"
SCREEN_RUN_SELECT = "run_select"
SCREEN_IN_RUN = "in_run"

MENU_W, MENU_H = 960, 600
BG = (10, 10, 15)
PANEL = (28, 28, 40)
TEXT = (220, 220, 220)
ACCENT = (90, 120, 180)
DISABLED = (70, 70, 80)


class App:
    def __init__(self, web_mode=False, minimal_mode=False, headless=False):
        self.web_mode = web_mode
        self.minimal_mode = minimal_mode
        self.headless = headless
        self.screen_id = SCREEN_MAIN
        self.slot = 0
        self.game = None
        self.renderer = None
        self.handler = None
        self.pause_open = False
        self.running = True
        self.devtools = DevToolsPanel()
        self.collective_open = False
        self.collective_status = ""
        self.sort_offer_open = False
        self.sort_offer = None
        self.save_store = MemorySaveStore(path=None if headless else default_profiles_path())
        self._menu_font = None
        self._menu_font_s = None
        self._menu_surface = None
        if not headless:
            self._ensure_menu_display()

    @property
    def screen(self):
        """Alias used by tests / call sites."""
        return self.screen_id

    def _ensure_menu_display(self):
        self._menu_surface = pygame.display.set_mode((MENU_W, MENU_H))
        pygame.display.set_caption("Tower Defense 3: Borg Assimilation")
        try:
            self._menu_font = pygame.font.SysFont("consolas", 28)
            self._menu_font_s = pygame.font.SysFont("consolas", 16)
        except Exception:
            self._menu_font = pygame.font.Font(None, 28)
            self._menu_font_s = pygame.font.Font(None, 16)

    def _fonts(self):
        if self._menu_font is None:
            self._menu_font = pygame.font.Font(None, 28)
            self._menu_font_s = pygame.font.Font(None, 16)
        return self._menu_font, self._menu_font_s

    # --- transitions ---
    def select_slot(self, slot: int):
        if slot < 0 or slot > 2:
            return
        self.slot = slot
        self.screen_id = SCREEN_RUN_SELECT
        self.pause_open = False

    def back_to_main(self):
        self.screen_id = SCREEN_MAIN
        self.pause_open = False
        self.collective_open = False
        self.sort_offer_open = False
        self.sort_offer = None
        self.game = None
        self.renderer = None
        self.handler = None
        if not self.headless:
            self._ensure_menu_display()

    def new_run(self, run_setup=None):
        from core.game import Game
        from ui.renderer import Renderer
        from ui.events import EventHandler

        self.game = Game(web_mode=self.web_mode, minimal_mode=self.minimal_mode, run_setup=run_setup)
        apply_to_run(self.game, self.save_store.profile(self.slot).unlock_ids)
        self.game.run_over_reason = None
        self.game.on_wave_cleared = self.on_wave_cleared
        self.game.on_run_over = self.on_run_over
        self.save_store.clear_checkpoint(self.slot)
        self.pause_open = False
        self.collective_open = False
        self.sort_offer_open = False
        self.sort_offer = None
        self.screen_id = SCREEN_IN_RUN
        self._sort_identity_toast()
        if self.headless:
            self.renderer = None
            self.handler = None
            return
        self.renderer = Renderer(self.game)
        self.handler = EventHandler(self.game, self.renderer, app=self)

    def _sort_identity_toast(self):
        """Compile identity toast. Continue does not call this."""
        from core.run_setup import DIRECTIVE_BLURBS

        game = self.game
        setup = getattr(game, "run_setup", None)
        if game is None or setup is None or setup.directive_hidden:
            return
        blurb = DIRECTIVE_BLURBS.get(setup.directive_name, "")
        label = getattr(setup, "directive_label", None) or setup.directive_name
        game.reward_toast_text = f"{label}  ·  {blurb}" if blurb else str(label)
        game.reward_toast_until = 360

    def open_sort_offer(self):
        from config import SORT_CONFIG
        from core.run_setup import SortOffer

        # Dev Tools force skips the pick so harnesses still one-click into a run.
        if SORT_CONFIG.get("force_directive") is not None:
            self.new_run()
            return
        seed = SORT_CONFIG.get("seed")
        self.sort_offer = SortOffer.roll(seed)
        self.sort_offer_open = True
        self.collective_open = False
        self.devtools.close()

    def confirm_sort_offer(self):
        if self.sort_offer is None:
            return
        setup = self.sort_offer.to_run_setup()
        self.new_run(run_setup=setup)

    def reroll_sort_offer(self):
        from core.run_setup import SortOffer
        if self.sort_offer is None:
            self.open_sort_offer()
            return
        self.sort_offer = SortOffer.roll()

    def continue_run(self):
        ckpt = self.save_store.checkpoints.get(self.slot)
        if ckpt is None:
            return
        from core.game import Game
        from ui.renderer import Renderer
        from ui.events import EventHandler

        self.game = Game(web_mode=self.web_mode, minimal_mode=self.minimal_mode)
        if ckpt.snapshot:
            restore_run(self.game, ckpt.snapshot)
        else:
            self.game.gold = ckpt.gold
            self.game.lives = ckpt.lives
            self.game.intel = ckpt.intel
            self.game.round_num = ckpt.wave_number
        self.game.run_over_reason = None
        self.game.on_wave_cleared = self.on_wave_cleared
        self.game.on_run_over = self.on_run_over
        self.pause_open = False
        self.collective_open = False
        self.sort_offer_open = False
        self.sort_offer = None
        self.screen_id = SCREEN_IN_RUN
        if self.headless:
            self.renderer = None
            self.handler = None
            return
        self.renderer = Renderer(self.game)
        self.handler = EventHandler(self.game, self.renderer, app=self)

    def return_to_run_select(self):
        self.pause_open = False
        self.game = None
        self.renderer = None
        self.handler = None
        self.sort_offer_open = False
        self.sort_offer = None
        self.screen_id = SCREEN_RUN_SELECT
        if not self.headless:
            self._ensure_menu_display()

    def open_pause(self):
        if self.screen_id != SCREEN_IN_RUN or self.game is None:
            return
        if getattr(self.game, "game_over", False):
            return
        self.pause_open = True
        self.game.paused = True

    def close_pause(self):
        self.pause_open = False
        if self.game is not None:
            self.game.paused = False

    def toggle_pause(self):
        if self.pause_open:
            self.close_pause()
        else:
            self.open_pause()

    def forfeit_run(self):
        if self.game is None:
            return
        self.game.run_over_reason = "forfeit"
        self.game.game_over = True
        self.game.final_wave = self.game.round_num
        self.game.final_gold = self.game.gold
        self.pause_open = False
        self.game.paused = True
        self.on_run_over("forfeit")

    def _quit_cleanup(self):
        """Mid-wave quit is a forfeit. Between waves, keep the last WaveClear snapshot."""
        if self.screen_id != SCREEN_IN_RUN or self.game is None or self.game.game_over:
            return
        if wave_is_live(self.game):
            self.forfeit_run()

    def on_wave_cleared(self, cleared_wave: int):
        if self.game is None:
            return
        setup = getattr(self.game, "run_setup", None)
        ckpt = RunCheckpoint(
            slot=self.slot,
            seed=int(getattr(self.game, "run_seed", 0) or 0),
            directive_name=getattr(setup, "directive_name", "") if setup else "",
            modifier_ids=list(getattr(setup, "modifier_ids", []) or []) if setup else [],
            wave_number=cleared_wave + 1,
            gold=self.game.gold,
            lives=self.game.lives,
            intel=int(getattr(self.game, "intel", 0) or 0),
            snapshot=snapshot_run(self.game),
        )
        self.save_store.save_checkpoint(self.slot, ckpt)

    def on_run_over(self, reason: str):
        victory = reason == "victory"
        self.save_store.record_run_over(self.slot, victory=victory)
        if self.game is not None:
            self.game.run_over_reason = reason

    def rules(self):
        return play_rules(self.game, pause_open=self.pause_open)

    # --- loop ---
    def handle_events(self, frame=0):
        if self.headless:
            return
        for event in pygame.event.get():
            self.process_event(event, frame)

    def process_event(self, event, frame=0):
        if event.type == pygame.QUIT:
            self._quit_cleanup()
            self.running = False
            if self.handler:
                self.handler.running = False
            return
        if self.sort_offer_open and self.screen_id == SCREEN_RUN_SELECT:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.sort_offer_open = False
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._click_sort_offer(event.pos)
            return
        if self.collective_open and self.screen_id == SCREEN_RUN_SELECT:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.collective_open = False
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._click_collective(event.pos)
            return
        if self.devtools.open and self.screen_id != SCREEN_IN_RUN:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.devtools.close()
                return
            self.devtools.handle_event(event, self._menu_size())
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.screen_id == SCREEN_IN_RUN and self.game and not self.game.game_over:
                self.toggle_pause()
                return
            if self.screen_id == SCREEN_RUN_SELECT:
                self.back_to_main()
                return
        if self.screen_id == SCREEN_IN_RUN and self.pause_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._click_pause_menu(event.pos)
            return
        if self.screen_id != SCREEN_IN_RUN:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.screen_id == SCREEN_MAIN:
                    self._click_main_menu(event.pos)
                elif self.screen_id == SCREEN_RUN_SELECT:
                    self._click_run_select(event.pos)
            return
        # Run-over overlay: App owns the pop back to Run Select. EventHandler
        # must not tear the handler down mid-dispatch (that crashed on .running).
        if self.game and self.game.game_over:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.return_to_run_select()
            return
        if self.handler:
            self.handler.process_event(event, frame)
            if self.handler is not None:
                self.running = self.handler.running

    def update(self, frame=0):
        if self.screen_id != SCREEN_IN_RUN or self.game is None:
            return
        rules = self.rules()
        if rules.sim_tick and not self.game.game_over:
            self.game.current_frame = frame
            self.game.wave_manager.update_wave(frame)

    def draw(self, frame=0):
        if self.headless:
            return
        if self.screen_id == SCREEN_MAIN:
            self._draw_main_menu()
        elif self.screen_id == SCREEN_RUN_SELECT:
            self._draw_run_select()
        elif self.screen_id == SCREEN_IN_RUN and self.renderer:
            self.renderer.draw(frame)
            if self.pause_open:
                self._draw_pause_overlay()
        if self.devtools.open and self.screen_id != SCREEN_IN_RUN:
            self.devtools.draw(self._menu_surface or pygame.display.get_surface())
        elif self.sort_offer_open and self.screen_id == SCREEN_RUN_SELECT:
            self._draw_sort_offer()
        elif self.collective_open and self.screen_id == SCREEN_RUN_SELECT:
            self._draw_collective()

    # --- hitboxes ---
    def _menu_size(self):
        surf = self._menu_surface or pygame.display.get_surface()
        if surf is not None:
            return surf.get_size()
        return (MENU_W, MENU_H)

    def devtools_button_rect(self):
        return pygame.Rect(MENU_W - 200, MENU_H - 56, 180, 40)

    def collective_button_rect(self):
        return pygame.Rect(MENU_W // 2 - 160, 428, 320, 48)

    def collective_card_rects(self):
        cards = []
        cx = MENU_W // 2 - 150
        for i in range(3):
            cards.append(pygame.Rect(cx, 168 + i * 100, 300, 88))
        return cards

    def collective_close_rect(self):
        return pygame.Rect(MENU_W // 2 + 110, 88, 72, 28)

    def sort_offer_card_rects(self):
        cards = []
        w, h, gap = 236, 210, 16
        total = 3 * w + 2 * gap
        x0 = MENU_W // 2 - total // 2
        y = 148
        for i in range(3):
            cards.append(pygame.Rect(x0 + i * (w + gap), y, w, h))
        return cards

    def sort_offer_action_rects(self):
        y = 430
        return {
            "compile": pygame.Rect(MENU_W // 2 - 250, y, 150, 44),
            "reroll": pygame.Rect(MENU_W // 2 - 75, y, 150, 44),
            "back": pygame.Rect(MENU_W // 2 + 100, y, 150, 44),
        }

    def slot_rects(self):
        rects = []
        cx, cy = MENU_W // 2, 220
        for i in range(3):
            rects.append(pygame.Rect(cx - 160, cy + i * 70, 320, 56))
        return rects

    def run_select_rects(self):
        cx = MENU_W // 2
        return {
            "new": pygame.Rect(cx - 160, 220, 320, 52),
            "continue": pygame.Rect(cx - 160, 286, 320, 52),
            "back": pygame.Rect(cx - 160, 352, 320, 52),
        }

    def pause_rects(self, size=None):
        w, h = size or (MENU_W, MENU_H)
        if self.renderer:
            w, h = self.renderer.WIDTH, self.renderer.HEIGHT
        cx, cy = w // 2, h // 2
        return {
            "resume": pygame.Rect(cx - 140, cy - 40, 280, 44),
            "forfeit": pygame.Rect(cx - 140, cy + 16, 280, 44),
            "settings": pygame.Rect(cx - 140, cy + 72, 280, 44),
        }

    def _click_main_menu(self, pos):
        if self.devtools_button_rect().collidepoint(pos):
            self.devtools.open_panel()
            return
        for i, r in enumerate(self.slot_rects()):
            if r.collidepoint(pos):
                self.select_slot(i)
                return

    def _click_run_select(self, pos):
        if self.devtools_button_rect().collidepoint(pos):
            self.collective_open = False
            self.devtools.open_panel()
            return
        if self.collective_button_rect().collidepoint(pos):
            self.devtools.close()
            self.sort_offer_open = False
            self.collective_open = True
            self.collective_status = ""
            return
        rs = self.run_select_rects()
        if rs["new"].collidepoint(pos):
            self.open_sort_offer()
        elif rs["continue"].collidepoint(pos):
            self.continue_run()
        elif rs["back"].collidepoint(pos):
            self.back_to_main()

    def _click_pause_menu(self, pos):
        size = None
        if self.renderer:
            size = (self.renderer.WIDTH, self.renderer.HEIGHT)
        rs = self.pause_rects(size)
        if rs["resume"].collidepoint(pos):
            self.close_pause()
        elif rs["forfeit"].collidepoint(pos):
            self.forfeit_run()
        elif rs["settings"].collidepoint(pos):
            return

    def _click_sort_offer(self, pos):
        if self.sort_offer is None:
            self.sort_offer_open = False
            return
        actions = self.sort_offer_action_rects()
        if actions["back"].collidepoint(pos):
            self.sort_offer_open = False
            return
        if actions["reroll"].collidepoint(pos):
            self.reroll_sort_offer()
            return
        if actions["compile"].collidepoint(pos):
            self.confirm_sort_offer()
            return
        for i, rect in enumerate(self.sort_offer_card_rects()):
            if i < len(self.sort_offer.directives) and rect.collidepoint(pos):
                self.sort_offer.selected = i
                return

    def _draw_sort_offer(self):
        from core.run_setup import DIRECTIVE_BLURBS, MODIFIER_DEFS
        from core.sort_directives import get_directive

        surf = self._menu_surface or pygame.display.get_surface()
        if surf is None or self.sort_offer is None:
            return
        font, font_s = self._fonts()
        dim = pygame.Surface((MENU_W, MENU_H))
        dim.set_alpha(210)
        dim.fill((0, 0, 0))
        surf.blit(dim, (0, 0))
        panel = pygame.Rect(48, 36, MENU_W - 96, MENU_H - 72)
        pygame.draw.rect(surf, PANEL, panel)
        pygame.draw.rect(surf, ACCENT, panel, 2)
        title = font.render("SORT DIRECTIVE", True, TEXT)
        surf.blit(title, title.get_rect(center=(MENU_W // 2, 68)))
        mods = [MODIFIER_DEFS[m]["name"] for m in self.sort_offer.modifier_ids if m in MODIFIER_DEFS]
        mod_line = "Modifiers: " + (" · ".join(mods) if mods else "none")
        sub = font_s.render(mod_line, True, ACCENT)
        surf.blit(sub, sub.get_rect(center=(MENU_W // 2, 104)))
        hint = font_s.render("Pick one  ·  Compile starts the run", True, DISABLED)
        surf.blit(hint, hint.get_rect(center=(MENU_W // 2, 128)))
        for i, (name, rect) in enumerate(zip(self.sort_offer.directives, self.sort_offer_card_rects())):
            selected = i == self.sort_offer.selected
            pygame.draw.rect(surf, (36, 40, 56) if selected else PANEL, rect)
            pygame.draw.rect(surf, ACCENT if selected else DISABLED, rect, 2 if selected else 1)
            label = get_directive(name).display_name
            title_s = font_s.render(label, True, TEXT)
            surf.blit(title_s, title_s.get_rect(center=(rect.centerx, rect.y + 28)))
            blurb = DIRECTIVE_BLURBS.get(name, "")
            self._blit_wrapped(surf, blurb, font_s, (160, 165, 180), rect.x + 14, rect.y + 56, rect.width - 28)
            if selected:
                mark = font_s.render("SELECTED", True, ACCENT)
                surf.blit(mark, mark.get_rect(center=(rect.centerx, rect.bottom - 22)))
        actions = self.sort_offer_action_rects()
        self._button(surf, actions["compile"], "Compile", font_s, True)
        self._button(surf, actions["reroll"], "Reroll", font_s, True)
        self._button(surf, actions["back"], "Back", font_s, True)

    @staticmethod
    def _blit_wrapped(surf, text, font, color, x, y, max_width, line_h=18):
        words = (text or "").split()
        line = ""
        for word in words:
            trial = (line + " " + word).strip()
            if font.size(trial)[0] <= max_width:
                line = trial
            else:
                if line:
                    surf.blit(font.render(line, True, color), (x, y))
                    y += line_h
                line = word
        if line:
            surf.blit(font.render(line, True, color), (x, y))

    def _click_collective(self, pos):
        if self.collective_close_rect().collidepoint(pos):
            self.collective_open = False
            return
        profile = self.save_store.profile(self.slot)
        for card, rect in zip(collective_stubs(), self.collective_card_rects()):
            if rect.collidepoint(pos):
                self.collective_status = collective_buy(profile, card["id"])
                self.save_store.persist()
                return

    def _draw_collective(self):
        surf = self._menu_surface or pygame.display.get_surface()
        if surf is None:
            return
        font, font_s = self._fonts()
        dim = pygame.Surface((MENU_W, MENU_H))
        dim.set_alpha(210)
        dim.fill((0, 0, 0))
        surf.blit(dim, (0, 0))
        panel = pygame.Rect(MENU_W // 2 - 190, 60, 380, 470)
        pygame.draw.rect(surf, PANEL, panel)
        pygame.draw.rect(surf, ACCENT, panel, 2)
        title = font.render("COLLECTIVE", True, TEXT)
        surf.blit(title, title.get_rect(center=(MENU_W // 2, 86)))
        profile = self.save_store.profile(self.slot)
        sub = font_s.render(
            f"{CURRENCY} {profile.dilithium}  ·  patches install on New Run",
            True, ACCENT,
        )
        surf.blit(sub, sub.get_rect(center=(MENU_W // 2, 118)))
        self._button(surf, self.collective_close_rect(), "Close", font_s, True)
        owned = set(profile.unlock_ids)
        for card, rect in zip(collective_stubs(), self.collective_card_rects()):
            have = card["id"] in owned
            can = (not have) and profile.dilithium >= card["cost"]
            pygame.draw.rect(surf, (36, 42, 32) if have else PANEL, rect)
            pygame.draw.rect(surf, (80, 180, 110) if have else (ACCENT if can else DISABLED), rect, 2)
            name = font_s.render(card["name"], True, TEXT)
            surf.blit(name, (rect.x + 12, rect.y + 10))
            cost = font_s.render("INSTALLED" if have else f"{card['cost']} {CURRENCY}", True, (140, 220, 160) if have else ACCENT)
            surf.blit(cost, (rect.right - cost.get_width() - 12, rect.y + 10))
            blurb = font_s.render(card["blurb"], True, (160, 165, 180))
            surf.blit(blurb, (rect.x + 12, rect.y + 36))
            fx = font_s.render(card["effect"], True, DISABLED)
            surf.blit(fx, (rect.x + 12, rect.y + 58))
        if self.collective_status:
            note = font_s.render(self.collective_status, True, TEXT)
            surf.blit(note, note.get_rect(center=(MENU_W // 2, 500)))

    def _draw_main_menu(self):
        surf = self._menu_surface or pygame.display.get_surface()
        if surf is None:
            return
        font, font_s = self._fonts()
        surf.fill(BG)
        title = font.render("BORG ASSIMILATION", True, TEXT)
        surf.blit(title, title.get_rect(center=(MENU_W // 2, 80)))
        sub = font_s.render("Select save slot  ·  Dev Tools to tune, then play", True, ACCENT)
        surf.blit(sub, sub.get_rect(center=(MENU_W // 2, 130)))
        for i, r in enumerate(self.slot_rects()):
            pygame.draw.rect(surf, PANEL, r)
            pygame.draw.rect(surf, ACCENT, r, 2)
            p = self.save_store.profile(i)
            label = font_s.render(f"Slot {i + 1}  —  runs {p.runs_played}", True, TEXT)
            surf.blit(label, label.get_rect(center=r.center))
        self._button(surf, self.devtools_button_rect(), "Dev Tools", font_s, True)

    def _draw_run_select(self):
        surf = self._menu_surface or pygame.display.get_surface()
        if surf is None:
            return
        font, font_s = self._fonts()
        surf.fill(BG)
        title = font.render("RUN SELECT", True, TEXT)
        surf.blit(title, title.get_rect(center=(MENU_W // 2, 80)))
        hint = font_s.render(f"Slot {self.slot + 1}  ·  Sort offer on New Run", True, ACCENT)
        surf.blit(hint, hint.get_rect(center=(MENU_W // 2, 140)))
        rs = self.run_select_rects()
        self._button(surf, rs["new"], "New Run", font_s, True)
        can_cont = self.save_store.has_checkpoint(self.slot)
        ckpt = self.save_store.checkpoints.get(self.slot)
        cont_label = f"Continue  ·  wave {ckpt.wave_number}" if can_cont and ckpt else "Continue (no checkpoint)"
        self._button(surf, rs["continue"], cont_label, font_s, can_cont)
        self._button(surf, rs["back"], "Back", font_s, True)
        p = self.save_store.profile(self.slot)
        queued = len(p.unlock_ids)
        self._button(
            surf,
            self.collective_button_rect(),
            f"Collective  ·  {CURRENCY} {p.dilithium}  ·  {queued} installed",
            font_s,
            True,
        )
        self._button(surf, self.devtools_button_rect(), "Dev Tools", font_s, True)

    def _draw_pause_overlay(self):
        if self.renderer is None:
            return
        screen = self.renderer.screen
        w, h = self.renderer.WIDTH, self.renderer.HEIGHT
        o = pygame.Surface((w, h))
        o.set_alpha(200)
        o.fill((0, 0, 0))
        screen.blit(o, (0, 0))
        font, font_s = self._fonts()
        title = font.render("PAUSED", True, TEXT)
        screen.blit(title, title.get_rect(center=(w // 2, h // 2 - 100)))
        sub = font_s.render("Game frozen — no shop, path, or combat", True, ACCENT)
        screen.blit(sub, sub.get_rect(center=(w // 2, h // 2 - 68)))
        rs = self.pause_rects((w, h))
        self._button(screen, rs["resume"], "Resume", font_s, True)
        self._button(screen, rs["forfeit"], "Forfeit run", font_s, True)
        self._button(screen, rs["settings"], "Settings (stub)", font_s, True)

    @staticmethod
    def _button(surf, rect, label, font, enabled):
        pygame.draw.rect(surf, PANEL if enabled else (20, 20, 24), rect)
        pygame.draw.rect(surf, ACCENT if enabled else DISABLED, rect, 2)
        col = TEXT if enabled else DISABLED
        txt = font.render(label, True, col)
        surf.blit(txt, txt.get_rect(center=rect.center))
