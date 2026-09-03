import random
from models.enemy import Enemy
from models.assimilator import Assimilator
from core.strategy_analyzer import StrategyAnalyzer
from core.sort_orchestrator import unlocked_types_for_wave, default_wave_size
from config import log_debug, REWARD_CONFIG, INTEL_CONFIG, SORT_CONFIG, ECONOMY_CONFIG, RUN_FLOW_CONFIG
from models.drone_data import DroneData


class WaveManager:
    def __init__(self, game):
        self.game = game
        self.strategy_analyzer = StrategyAnalyzer()
        self._strategy_profile = {}

    def _snapshot_wave_combat_stats(self, frame):
        """Freeze per-tower damage/kills for the wave that just ended."""
        dur = max(1, frame - self.game.wave_start_frame)
        self.game.last_wave_duration_frames = dur
        for t in self.game.towers:
            t.damage_dealt_last_wave = t.damage_dealt_this_wave
            t.kills_last_wave = t.kills_this_wave
            t.damage_dealt_this_wave = 0
            t.kills_this_wave = 0

    @staticmethod
    def unlocked_types_for_wave(wave_num):
        """Enemy types eligible for a normal wave (shared by spawn + preview)."""
        return unlocked_types_for_wave(wave_num)

    def wave_size_for(self, wave_num):
        return default_wave_size(wave_num, getattr(self.game, "web_mode", False))

    def _orchestrator(self):
        return getattr(self.game, "sort_orchestrator", None)

    def _intel_tier(self, intel=None):
        if intel is None:
            intel = getattr(self.game, "intel", 0)
        tiers = INTEL_CONFIG.get("tiers", [])
        chosen = tiers[0] if tiers else {
            "min": 0, "horizon": 1, "show_types": False, "show_percents": False, "label": "Contact",
        }
        for tier in tiers:
            if intel >= tier.get("min", 0):
                chosen = tier
        return chosen, int(intel)

    def _loot_kind_for_wave(self, wave_num):
        """Loot granted when this wave is cleared (None / mini_boss / boss)."""
        if wave_num <= 0:
            return None
        mini_iv = REWARD_CONFIG.get("mini_boss_wave_interval", 5)
        boss_iv = REWARD_CONFIG.get("boss_wave_interval", 20)
        if wave_num % boss_iv == 0:
            return "boss"
        if wave_num % mini_iv == 0:
            return "mini_boss"
        return None

    def waves_until_loot(self, from_wave=None):
        """Waves until next mini-boss / boss clear (0 = this wave grants loot)."""
        wave = from_wave if from_wave is not None else self.game.round_num
        mini_iv = REWARD_CONFIG.get("mini_boss_wave_interval", 5)
        boss_iv = REWARD_CONFIG.get("boss_wave_interval", 20)

        def until(interval):
            rem = wave % interval
            return 0 if rem == 0 else interval - rem

        u_mini, u_boss = until(mini_iv), until(boss_iv)
        if u_boss <= u_mini:
            return {"waves": u_boss, "kind": "boss"}
        return {"waves": u_mini, "kind": "mini_boss"}

    def preview_upcoming(self, intel=None, waves=None):
        """
        Forecast upcoming waves for the Round Guide HUD.

        Uses SortOrchestrator when enabled; falls back to unlock-weight stub.
        Returns:
          waves, loot, intel / tier, directive (name/display when known)
        """
        tier, intel_val = self._intel_tier(intel)
        horizon = int(waves if waves is not None else tier.get("horizon", 1))
        show_types = bool(tier.get("show_types", False))
        show_percents = bool(tier.get("show_percents", False))
        start = self.game.round_num
        orch = self._orchestrator() if SORT_CONFIG.get("enabled", True) else None
        orch_forecasts = orch.forecast(horizon) if orch else None
        forecasts = []

        # Orchestrator remaining[0] is the next *normal* slot; event waves skip a slot.
        # Walk horizon wave numbers and only consume orch offsets for non-event waves.
        orch_offset = 0
        for offset in range(horizon):
            wnum = start + offset
            event = None
            if hasattr(self.game, "data_loader") and self.game.data_loader:
                event = self.game.data_loader.get_event_wave(wnum)

            entry = {
                "wave": wnum,
                "relative": offset + 1,
                "revealed": True,
                "kind": "event" if event else "normal",
                "event_name": (event or {}).get("name") if event else None,
                "count": 0,
                "composition": {},
                "is_exact": False,
                "loot": self._loot_kind_for_wave(wnum),
                "show_types": show_types,
                "show_percents": show_percents,
            }

            if event:
                composition = event.get("composition", {}) or {}
                entry["composition"] = {k: int(v) for k, v in composition.items()}
                entry["count"] = sum(entry["composition"].values())
                entry["is_exact"] = True
                entry["confidence"] = 1.0
                # Event waves still consume a plan slot (skip_wave_slot on spawn)
                orch_offset += 1
            elif orch_forecasts is not None and orch_offset < len(orch_forecasts):
                fc = orch_forecasts[orch_offset]
                orch_offset += 1
                counts = fc.get("composition", {}) or {}
                entry["count"] = int(fc.get("count", 0))
                entry["is_exact"] = True
                entry["confidence"] = self._forecast_confidence(intel_val, offset)
                if show_types and counts and entry["count"] > 0:
                    if show_percents:
                        total = float(entry["count"])
                        # Soften percents toward equal when confidence is low
                        conf = entry["confidence"]
                        equal = 100.0 / len(counts)
                        entry["composition"] = {
                            t: round(equal + conf * (100.0 * n / total - equal), 1)
                            for t, n in counts.items()
                        }
                    else:
                        entry["composition"] = {t: int(n) for t, n in counts.items()}
                else:
                    entry["composition"] = {}
            else:
                types = self.unlocked_types_for_wave(wnum)
                size = self.wave_size_for(wnum)
                entry["count"] = size
                entry["confidence"] = self._forecast_confidence(intel_val, offset)
                if show_types and types:
                    pct = round(100.0 / len(types), 1)
                    entry["composition"] = {t: pct for t in types}
                    entry["is_exact"] = False
                else:
                    entry["composition"] = {}
                    entry["is_exact"] = False

            forecasts.append(entry)

        conf = self._forecast_confidence(intel_val, 0)
        result = {
            "waves": forecasts,
            "loot": self.waves_until_loot(start),
            "intel": intel_val,
            "intel_max": int(INTEL_CONFIG.get("max_intel", 100)),
            "tier": tier,
            "tier_label": tier.get("label", "Contact"),
            "confidence": conf,
            "noise_injections": int(getattr(self.game, "noise_injections", 0)),
        }
        if orch:
            result["directive"] = orch.directive_name
            result["directive_display"] = orch.directive_display
            result["modifiers"] = list(getattr(self.game, "run_setup", None) and self.game.run_setup.modifier_ids or [])
            setup = getattr(self.game, "run_setup", None)
            hidden = bool(setup and setup.directive_hidden)
            result["directive_hidden"] = hidden
            # Reveal name at Matrix intel (75+) even if started hidden
            if intel_val >= 75 or not hidden:
                result["directive_hint"] = orch.directive_display
            else:
                result["directive_hint"] = "???"
            if setup and setup.modifier_ids:
                from core.run_setup import MODIFIER_DEFS
                result["modifier_labels"] = [
                    MODIFIER_DEFS[m]["name"] for m in setup.modifier_ids if m in MODIFIER_DEFS
                ]
        return result

    def _forecast_confidence(self, intel_val, wave_offset=0):
        """0–1 scout confidence from intel, horizon distance, and egrem noise."""
        intel_w = float(INTEL_CONFIG.get("confidence_intel_weight", 0.7))
        noise_pen = float(INTEL_CONFIG.get("confidence_noise_penalty", 0.08))
        floor = float(INTEL_CONFIG.get("confidence_floor", 0.15))
        intel_max = max(1, int(INTEL_CONFIG.get("max_intel", 100)))
        base = intel_w * (intel_val / intel_max)
        # Farther waves are fuzzier
        base *= max(0.35, 1.0 - 0.18 * wave_offset)
        noise = int(getattr(self.game, "noise_injections", 0))
        conf = base - noise * noise_pen
        return max(floor, min(1.0, conf))

    def try_inject_egrem_noise(self):
        """Egrem kill may inject extra drones into the remaining sort pool."""
        orch = self._orchestrator()
        if not orch:
            return 0
        chance = float(INTEL_CONFIG.get("egrem_noise_chance", 0.45))
        if random.random() >= chance:
            return 0
        lo = int(INTEL_CONFIG.get("egrem_noise_min", 1))
        hi = int(INTEL_CONFIG.get("egrem_noise_max", 2))
        n = random.randint(lo, max(lo, hi))
        types = self.unlocked_types_for_wave(self.game.round_num)
        drones = [
            DroneData.from_type(random.choice(types), wave_num=self.game.round_num, noise=random.randint(-1, 3))
            for _ in range(n)
        ]
        orch.inject(drones, at_front=random.random() < 0.35)
        self.game.noise_injections = int(getattr(self.game, "noise_injections", 0)) + 1
        return n

    def start_next_wave(self, frame=None, forced=False):
        if self.game.wave_active:
            return
        from config import play_rules
        pause = getattr(self.game, "paused", False) is True
        if not forced and not play_rules(self.game, pause_open=pause).next_wave:
            return
        self.game.wave_active = True
        f = frame if frame is not None else getattr(self.game, "current_frame", 0)
        self.game.wave_start_frame = f

        self._strategy_profile = self.strategy_analyzer.analyze(self.game)
        rt = self.game.data_loader.get_resistance_tables() if hasattr(self.game, 'data_loader') else {}

        log_debug("wave_strategy_profile", {
            "wave": self.game.round_num,
            "hybrid_exposure": self._strategy_profile.get("_hybrid_exposure", 0),
            "pure_exposure": self._strategy_profile.get("_pure_exposure", 0),
            "tower_count": self._strategy_profile.get("_tower_count", 0),
            "corruption_tiles": getattr(self.game, 'augment_manager', None) and self.game.augment_manager.tiles_placed_count or 0,
        }, location="wave_manager.py")

        tower_purity = []
        for t in self.game.towers:
            if t.merge_generation >= 1:
                tower_purity.append({"type": t.base_type, "gen": t.merge_generation, "purity": t.calculate_purity()})
        if tower_purity:
            log_debug("tower_purity_snapshot", {"towers": tower_purity}, location="wave_manager.py")

        event = self.game.data_loader.get_event_wave(self.game.round_num) if hasattr(self.game, 'data_loader') else None
        self.game.spawn_queue = []

        if event:
            orch = self._orchestrator()
            if orch:
                orch.skip_wave_slot()
            self._spawn_event_wave(event, rt)
        else:
            self._spawn_normal_wave(rt)

        for t in self.game.towers:
            if t.base_type == "Nanite Swarm":
                if self.game.web_mode:
                    spawn_count = random.randint(0, 1)
                else:
                    spawn_count = random.randint(1, 2)
                for _ in range(spawn_count):
                    assim = Assimilator(
                        self.game.path,
                        self.game.round_num + 2,
                        is_egrem_spawned=True,
                        web_mode=self.game.web_mode,
                    )
                    assim.set_game_reference(self.game)
                    self.game.spawn_queue.append(assim)
        self.game.spawn_timer = 0

    def _spawn_from_drones(self, drones, rt):
        """Materialize DroneData chunk into spawn_queue enemies."""
        for d in drones:
            enemy_type = getattr(d, "enemy_type", "Drone")
            if enemy_type == "Assimilator":
                enemy = Assimilator(self.game.path, self.game.round_num, web_mode=self.game.web_mode)
                enemy.set_game_reference(self.game)
            else:
                enemy = Enemy(self.game.path, enemy_type, self.game.round_num, web_mode=self.game.web_mode)
            enemy.adapt_to_profile(self._strategy_profile, rt)
            self.game.spawn_queue.append(enemy)

    def _spawn_normal_wave(self, rt):
        orch = self._orchestrator() if SORT_CONFIG.get("enabled", True) else None
        if orch:
            drones = orch.next_wave()
            if drones:
                self._spawn_from_drones(drones, rt)
                return
            # Plan exhausted — fall through to legacy random fill
        wave_size = self.wave_size_for(self.game.round_num)
        types = self.unlocked_types_for_wave(self.game.round_num)
        for _ in range(wave_size):
            enemy_type = random.choice(types)
            if enemy_type == "Assimilator":
                enemy = Assimilator(self.game.path, self.game.round_num, web_mode=self.game.web_mode)
                enemy.set_game_reference(self.game)
            else:
                enemy = Enemy(self.game.path, enemy_type, self.game.round_num, web_mode=self.game.web_mode)
            enemy.adapt_to_profile(self._strategy_profile, rt)
            self.game.spawn_queue.append(enemy)

    def _spawn_event_wave(self, event, rt):
        """Build spawn_queue from an event wave definition."""
        composition = event.get("composition", {})
        hp_mult = event.get("hp_mult", 1.0)
        speed_mult = event.get("speed_mult", 1.0)

        for enemy_type, count in composition.items():
            for _ in range(count):
                if enemy_type == "Assimilator":
                    enemy = Assimilator(self.game.path, self.game.round_num, web_mode=self.game.web_mode)
                    enemy.set_game_reference(self.game)
                else:
                    enemy = Enemy(self.game.path, enemy_type, self.game.round_num, web_mode=self.game.web_mode)
                enemy.max_health = int(enemy.max_health * hp_mult)
                enemy.health = enemy.max_health
                enemy.speed_mult *= speed_mult
                enemy.adapt_to_profile(self._strategy_profile, rt)
                self.game.spawn_queue.append(enemy)

        random.shuffle(self.game.spawn_queue)

    def update_wave(self, frame):
        if not self.game.wave_active or self.game.paused:
            return
        self.game.spawn_timer += 1
        if self.game.spawn_queue and self.game.spawn_timer >= self.game.spawn_interval:
            self.game.spawn_timer = 0
            self.game.enemies.append(self.game.spawn_queue.pop(0))

        # Update towers (including egrem spawning)
        for t in self.game.towers:
            t.update(self.game.enemies, frame, self.game)

        # Apply auras (int + cap: never walk a 99-range Overwatch diamond)
        for t in self.game.towers:
            if "resist_2" in t.upgrades:
                aura_r = max(0, min(8, int(getattr(t, "range", 0) or 0)))
                if aura_r < 1:
                    continue
                for dy in range(-aura_r, aura_r + 1):
                    for dx in range(-aura_r, aura_r + 1):
                        if abs(dx) + abs(dy) > aura_r:
                            continue
                        nx, ny = t.x + dx, t.y + dy
                        if 0 <= nx < len(self.game.enemy_grid[0]) and 0 <= ny < len(self.game.enemy_grid):
                            for e in self.game.enemy_grid[ny][nx]:
                                if e.alive and not e.leaked:
                                    e.apply_debuff('slow', 30, 60)

        # Update enemy grid
        for row in self.game.enemy_grid:
            for cell in row:
                cell.clear()
        for e in self.game.enemies:
            pos = e.get_position()
            if pos:
                self.game.enemy_grid[pos[1]][pos[0]].append(e)

        # Assimilator latch logic (Circuit Stronghold)
        if hasattr(self.game, 'board') and self.game.board:
            assim_data = self.game.data_loader.get_assimilator_data() or {}
            base_chance = assim_data.get('chance_base', 0.4)

            for e in self.game.enemies[:]:
                # Must be Assimilator subclass (plain Enemy with type "Assimilator" has no latch_to)
                if not isinstance(e, Assimilator) or getattr(e, 'is_latched', False):
                    continue
                pos = e.get_position()
                if pos:
                    ax, ay = pos
                    tx, ty, ttype = self.game.board.scan_latch_targets(ax, ay)
                    if tx is not None:
                        # Check for repel AoE from pure towers
                        repel_active = False
                        for t in self.game.towers:
                            if t.camouflage_repels():
                                distance = abs(t.x - ax) + abs(t.y - ay)
                                if distance <= t.range:
                                    repel_active = True
                                    break

                        if not repel_active:
                            if random.random() < base_chance:
                                if e.latch_to(tx, ty, ttype, self.game.board.wall_manager):
                                    if ttype == 'wall':
                                        wall = self.game.board.wall_manager.get_wall(tx, ty)
                                        if wall:
                                            e.stack_count = wall.get_latch_count()
                                    e.set_game_reference(self.game)

        # Update latched assimilators
        for e in self.game.enemies[:]:
            if getattr(e, 'is_latched', False):
                e.update_latch(self.game.board.wall_manager)

        # Integrity drain (0.02/stack)
        self.game.integrity_tick()

        for e in self.game.enemies[:]:
            e.move()
            if e.leaked:
                self.game.lives -= 1
                self.game.enemies.remove(e)
        for e in self.game.enemies[:]:
            if not e.alive:
                base = max(1, (3 + e.difficulty * 3) // 2)
                gold = max(1, int(base * ECONOMY_CONFIG.get("kill_gold_mult", 0.5)))
                self.game.gold += gold
                # Add XP for enemy kill (full mode only)
                if not getattr(self.game, 'minimal_mode', True) and hasattr(self.game, 'xp'):
                    base_xp = e.TYPES[e.enemy_type].get("base_xp", 5)
                    self.game.xp += base_xp * e.difficulty
                # Egrem-spawned kills: path tiles + scout intel + pool noise
                if getattr(e, "is_egrem_spawned", False):
                    self.game.economy.try_grant_egrem_tile_drop()
                    if hasattr(self.game, "add_intel"):
                        self.game.add_intel(INTEL_CONFIG.get("egrem_intel_gain", 8))
                    self.try_inject_egrem_noise()
                self.game.enemies.remove(e)
        if self.game.lives <= 0:
            self.game.game_over = True
            self.game.run_over_reason = "defeat"
            self.game.final_wave = self.game.round_num
            self.game.final_gold = self.game.gold
            self.game.wave_active = False
            cb = getattr(self.game, "on_run_over", None)
            if callable(cb):
                cb("defeat")
        if self.game.wave_active and not self.game.enemies and not self.game.spawn_queue:
            cleared_wave = self.game.round_num
            raw_bonus = (len(self.game.towers) * 3 + cleared_wave * 4) // 2
            bonus = max(0, int(raw_bonus * ECONOMY_CONFIG.get("wave_bonus_mult", 0.5)))
            self.game.gold += bonus
            # Soften noise memory each clear so confidence can recover
            if getattr(self.game, "noise_injections", 0) > 0:
                self.game.noise_injections = max(0, self.game.noise_injections - 1)
            # Add XP bonus for wave clear (full mode only)
            if not getattr(self.game, 'minimal_mode', True) and hasattr(self.game, 'xp'):
                self.game.xp += cleared_wave * 50
            self.game.wave_bonus_text = f"Wave {cleared_wave} cleared  ·  +{bonus} gold"
            self.game.wave_bonus_show_until = frame + 300
            # Mini-boss / boss milestone upgrade loot (tunable in config.REWARD_CONFIG)
            self.game.economy.grant_wave_upgrade_rewards(cleared_wave)
            self._snapshot_wave_combat_stats(frame)
            self.game.round_num += 1
            self.game.wave_active = False
            # Check for SPL level up (full mode only)
            if not getattr(self.game, 'minimal_mode', True) and hasattr(self.game, 'check_spl_level_up'):
                self.game.check_spl_level_up()
            cleared_cb = getattr(self.game, "on_wave_cleared", None)
            if callable(cleared_cb):
                cleared_cb(cleared_wave)
            victory_waves = int(RUN_FLOW_CONFIG.get("victory_waves") or 0)
            endless = bool(RUN_FLOW_CONFIG.get("endless_after_victory", False))
            if victory_waves and cleared_wave >= victory_waves and not endless:
                self.game.game_over = True
                self.game.run_over_reason = "victory"
                self.game.final_wave = cleared_wave
                self.game.final_gold = self.game.gold
                over_cb = getattr(self.game, "on_run_over", None)
                if callable(over_cb):
                    over_cb("victory")
                return
            if RUN_FLOW_CONFIG.get("mode") == "auto_chain" or self.game.auto_mode:
                self.start_next_wave(frame, forced=True)

    def spawn_enemy_at_position(self, enemy_type, x, y, wave_num=1):
        """Spawn an enemy at a specific grid position (for egrem towers)."""
        if not self.game.path:
            return None
        if 0 <= x < self.game.width and 0 <= y < self.game.height:
            # Find the closest path point to this position
            closest_pos = min(self.game.path, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
            closest_idx = self.game.path.index(closest_pos)
            # Share the live path list + start index so expand/tile appends stay valid
            if enemy_type == "Assimilator":
                enemy = Assimilator(self.game.path, wave_num, is_egrem_spawned=True, web_mode=self.game.web_mode)
                enemy.position_index = closest_idx
                enemy.set_game_reference(self.game)
            else:
                enemy = Enemy(self.game.path, enemy_type, wave_num, is_egrem_spawned=True, web_mode=self.game.web_mode)
                enemy.position_index = closest_idx
            self.game.enemies.append(enemy)
            # Add to enemy_grid immediately so towers can target it
            pos = enemy.get_position()
            if pos and 0 <= pos[0] < self.game.width and 0 <= pos[1] < self.game.height:
                self.game.enemy_grid[pos[1]][pos[0]].append(enemy)
            return enemy
        return None