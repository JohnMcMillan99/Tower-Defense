"""Dev Tools overlay — accordion of live catalog leaves (sliders / toggles)."""
from __future__ import annotations

import pygame

from core.devtools import catalog
from core.dev_presets import BUILTIN_IDS, BUILTIN_LABELS, USER_SLOTS

BG = (10, 10, 15)
PANEL = (22, 22, 32)
RAIL = (16, 16, 24)
ROW = (32, 32, 46)
ROW_DIRTY = (42, 38, 28)
TEXT = (220, 220, 220)
MUTED = (140, 145, 160)
ACCENT = (90, 140, 200)
ON = (80, 180, 120)
OFF = (90, 70, 70)
TRACK = (50, 50, 65)
FILL = (90, 140, 200)
HEADER = (18, 18, 26)

ROW_H = 40
RAIL_W = 168
PAD = 16


class DevToolsPanel:
    def __init__(self):
        self.open = False
        self.section = 0
        self.scroll = 0
        self.dragging = None  # (table_id, path)
        self.selected_preset = "easy"
        self.status = ""
        self._font = None
        self._font_s = None
        self._hover_path = None

    def open_panel(self):
        catalog().ensure()
        self.open = True
        self.scroll = 0
        self.dragging = None
        if catalog().active_preset:
            self.selected_preset = catalog().active_preset
        self.status = ""

    def close(self):
        self.open = False
        self.dragging = None

    def toggle(self):
        if self.open:
            self.close()
        else:
            self.open_panel()

    def _fonts(self):
        if self._font is None:
            try:
                self._font = pygame.font.SysFont("consolas", 20)
                self._font_s = pygame.font.SysFont("consolas", 14)
            except Exception:
                self._font = pygame.font.Font(None, 22)
                self._font_s = pygame.font.Font(None, 16)
        return self._font, self._font_s

    def _layout(self, size):
        w, h = size
        panel = pygame.Rect(20, 16, w - 40, h - 32)
        header = pygame.Rect(panel.x, panel.y, panel.w, 64)
        footer = pygame.Rect(panel.x, panel.bottom - 44, panel.w, 44)
        rail = pygame.Rect(panel.x, header.bottom, RAIL_W, footer.top - header.bottom)
        body = pygame.Rect(rail.right, header.bottom, panel.w - RAIL_W, rail.h)
        close = pygame.Rect(panel.right - 88, panel.y + 14, 72, 28)
        reset = pygame.Rect(panel.right - 200, panel.y + 14, 104, 28)
        return panel, header, rail, body, footer, close, reset

    def handle_event(self, event, size) -> bool:
        """True if the overlay consumed the event."""
        if not self.open:
            return False
        cat = catalog()
        cat.ensure()
        panel, header, rail, body, footer, close, reset = self._layout(size)

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if body.collidepoint(mx, my) or rail.collidepoint(mx, my):
                if rail.collidepoint(mx, my):
                    return True
                max_s = self._max_scroll(body, cat)
                self.scroll = max(0, min(max_s, self.scroll - event.y * ROW_H))
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = None
            return True

        if event.type == pygame.MOUSEMOTION:
            if self.dragging:
                table_id, path, track = self.dragging
                if track.w > 0:
                    ratio = (event.pos[0] - track.x) / track.w
                    cat.set_from_ratio(table_id, path, ratio)
            return True

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return True

        pos = event.pos
        if close.collidepoint(pos):
            self.close()
            return True
        if reset.collidepoint(pos):
            cat.reset_all()
            self.selected_preset = "easy"
            self.status = "Loaded Easy"
            return True
        chips = self._preset_chips(footer)
        for pid, rect in chips:
            if rect.collidepoint(pos):
                self._click_preset(cat, pid)
                return True
        if not panel.collidepoint(pos):
            self.close()
            return True

        # Section rail
        for i, t in enumerate(cat.tables):
            r = pygame.Rect(rail.x + 8, rail.y + 8 + i * 32, rail.w - 16, 28)
            if r.collidepoint(pos):
                self.section = i
                self.scroll = 0
                return True

        # Rows
        if body.collidepoint(pos):
            hits = self._row_hits(body, cat)
            for leaf, row, minus, plus, track, toggle in hits:
                if toggle and toggle.collidepoint(pos):
                    cat.nudge(leaf.table_id, leaf.path, 1)
                    return True
                if minus and minus.collidepoint(pos):
                    cat.nudge(leaf.table_id, leaf.path, -1)
                    return True
                if plus and plus.collidepoint(pos):
                    cat.nudge(leaf.table_id, leaf.path, 1)
                    return True
                if track and track.collidepoint(pos):
                    ratio = (pos[0] - track.x) / max(1, track.w)
                    cat.set_from_ratio(leaf.table_id, leaf.path, ratio)
                    self.dragging = (leaf.table_id, leaf.path, track)
                    return True
        return True

    def _click_preset(self, cat, pid: str):
        if pid == "save":
            target = self.selected_preset if self.selected_preset in USER_SLOTS else None
            slot = cat.save_loadout(target)
            self.selected_preset = slot
            self.status = f"Saved loadout {BUILTIN_LABELS[slot]}"
            return
        self.selected_preset = pid
        if pid in BUILTIN_IDS:
            cat.apply_preset(pid)
            self.status = f"Loaded {BUILTIN_LABELS[pid]}"
            return
        if cat.apply_preset(pid):
            self.status = f"Loaded loadout {BUILTIN_LABELS[pid]}"
        else:
            self.status = f"Loadout {BUILTIN_LABELS[pid]} empty — Save writes here"

    def _preset_chips(self, footer):
        x = footer.x + 10
        y = footer.y + 8
        chips = []
        for pid in BUILTIN_IDS + USER_SLOTS + ("save",):
            w = 70 if pid in BUILTIN_IDS else (56 if pid == "save" else 32)
            if pid == USER_SLOTS[0]:
                x += 12
            if pid == "save":
                x += 12
            chips.append((pid, pygame.Rect(x, y, w, 28)))
            x += w + 6
        return chips

    def _max_scroll(self, body, cat):
        if not cat.tables:
            return 0
        n = len(cat.leaves(cat.tables[self.section].id))
        need = 28 + n * ROW_H + 16
        return max(0, need - body.h)

    def _row_hits(self, body, cat):
        if not cat.tables:
            return []
        t = cat.tables[self.section]
        leaves = cat.leaves(t.id)
        y = body.y + 28 - self.scroll
        hits = []
        inner = pygame.Rect(body.x + PAD, body.y, body.w - PAD * 2, body.h)
        for leaf in leaves:
            row = pygame.Rect(inner.x, y, inner.w, ROW_H - 4)
            minus = plus = track = toggle = None
            if leaf.kind == "bool":
                toggle = pygame.Rect(row.right - 84, row.y + 6, 76, 24)
            elif leaf.kind == "enum":
                minus = pygame.Rect(row.right - 210, row.y + 6, 24, 24)
                plus = pygame.Rect(row.right - 28, row.y + 6, 24, 24)
            else:
                minus = pygame.Rect(row.right - 268, row.y + 6, 24, 24)
                track = pygame.Rect(minus.right + 6, row.y + 12, 170, 12)
                plus = pygame.Rect(track.right + 6, row.y + 6, 24, 24)
            hits.append((leaf, row, minus, plus, track, toggle))
            y += ROW_H
        return hits

    def draw(self, surf):
        if not self.open or surf is None:
            return
        cat = catalog()
        cat.ensure()
        if self.section >= len(cat.tables):
            self.section = 0
        w, h = surf.get_size()
        panel, header, rail, body, footer, close, reset = self._layout((w, h))
        font, font_s = self._fonts()

        dim = pygame.Surface((w, h))
        dim.set_alpha(210)
        dim.fill((0, 0, 0))
        surf.blit(dim, (0, 0))

        pygame.draw.rect(surf, PANEL, panel)
        pygame.draw.rect(surf, ACCENT, panel, 2)
        pygame.draw.rect(surf, HEADER, header)
        pygame.draw.rect(surf, RAIL, rail)
        pygame.draw.line(surf, ACCENT, (rail.right, rail.top), (rail.right, rail.bottom), 1)
        pygame.draw.line(surf, ACCENT, (header.left, header.bottom), (header.right, header.bottom), 1)

        dirty = cat.dirty_count()
        title = font.render("DEV TOOLS", True, TEXT)
        surf.blit(title, (panel.x + 18, panel.y + 10))
        loaded = BUILTIN_LABELS.get(cat.active_preset or "", "custom")
        extra = f"  ·  {self.status}" if self.status else ""
        hint = font_s.render(
            f"{dirty} changed  ·  preset {loaded}  ·  New Run reads these{extra}",
            True, MUTED,
        )
        surf.blit(hint, (panel.x + 18, panel.y + 36))

        self._chip(surf, reset, "Reset all", font_s, True)
        self._chip(surf, close, "Close", font_s, True)

        pygame.draw.rect(surf, HEADER, footer)
        pygame.draw.line(surf, ACCENT, (footer.left, footer.top), (footer.right, footer.top), 1)
        for pid, rect in self._preset_chips(footer):
            if pid == "save":
                self._chip(surf, rect, "Save", font_s, True)
                continue
            filled = True if pid in BUILTIN_IDS else cat.store.has_user(pid)
            selected = pid == self.selected_preset
            pygame.draw.rect(surf, ACCENT if selected else (ROW if filled else (20, 20, 24)), rect)
            pygame.draw.rect(surf, ACCENT if selected or filled else (70, 70, 80), rect, 1)
            txt = font_s.render(
                BUILTIN_LABELS[pid],
                True,
                TEXT if (filled or pid in BUILTIN_IDS) else MUTED,
            )
            surf.blit(txt, txt.get_rect(center=rect.center))

        for i, t in enumerate(cat.tables):
            r = pygame.Rect(rail.x + 8, rail.y + 8 + i * 32, rail.w - 16, 28)
            active = i == self.section
            pygame.draw.rect(surf, ACCENT if active else ROW, r)
            col = TEXT if active else MUTED
            label = font_s.render(t.title, True, col)
            surf.blit(label, label.get_rect(midleft=(r.x + 8, r.centery)))

        if cat.tables:
            t = cat.tables[self.section]
            blurb = font_s.render(t.blurb, True, MUTED)
            surf.set_clip(body)
            surf.blit(blurb, (body.x + PAD, body.y + 6 - min(self.scroll, 20)))
            for leaf, row, minus, plus, track, toggle in self._row_hits(body, cat):
                if row.bottom < body.y or row.top > body.bottom:
                    continue
                pygame.draw.rect(surf, ROW_DIRTY if leaf.dirty else ROW, row)
                lab = font_s.render(leaf.label, True, TEXT if leaf.dirty else MUTED)
                surf.blit(lab, (row.x + 8, row.y + 10))
                if leaf.kind == "bool":
                    on = bool(leaf.value)
                    pygame.draw.rect(surf, ON if on else OFF, toggle)
                    txt = font_s.render("ON" if on else "OFF", True, TEXT)
                    surf.blit(txt, txt.get_rect(center=toggle.center))
                elif leaf.kind == "enum":
                    pygame.draw.rect(surf, TRACK, minus)
                    pygame.draw.rect(surf, TRACK, plus)
                    surf.blit(font_s.render("<", True, TEXT), font_s.render("<", True, TEXT).get_rect(center=minus.center))
                    surf.blit(font_s.render(">", True, TEXT), font_s.render(">", True, TEXT).get_rect(center=plus.center))
                    val = font_s.render(str(leaf.value), True, TEXT)
                    mid = pygame.Rect(minus.right, row.y, plus.left - minus.right, row.h)
                    surf.blit(val, val.get_rect(center=mid.center))
                else:
                    pygame.draw.rect(surf, TRACK, minus)
                    pygame.draw.rect(surf, TRACK, plus)
                    surf.blit(font_s.render("-", True, TEXT), font_s.render("-", True, TEXT).get_rect(center=minus.center))
                    surf.blit(font_s.render("+", True, TEXT), font_s.render("+", True, TEXT).get_rect(center=plus.center))
                    pygame.draw.rect(surf, TRACK, track)
                    span = max(0.001, leaf.hi - leaf.lo)
                    ratio = (float(leaf.value) - leaf.lo) / span
                    fill_w = int(track.w * max(0.0, min(1.0, ratio)))
                    pygame.draw.rect(surf, FILL, (track.x, track.y, fill_w, track.h))
                    shown = f"{leaf.value:.2f}" if leaf.kind == "float" else str(int(leaf.value))
                    val = font_s.render(shown, True, TEXT)
                    surf.blit(val, val.get_rect(midleft=(plus.right + 8, row.centery)))
            surf.set_clip(None)

    @staticmethod
    def _chip(surf, rect, label, font, enabled):
        pygame.draw.rect(surf, ROW, rect)
        pygame.draw.rect(surf, ACCENT if enabled else (70, 70, 80), rect, 1)
        txt = font.render(label, True, TEXT)
        surf.blit(txt, txt.get_rect(center=rect.center))
