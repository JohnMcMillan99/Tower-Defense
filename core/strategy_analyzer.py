class StrategyAnalyzer:
    """Aggregates placed-tower trait tags into an exposure profile used by enemy adaptation."""

    def __init__(self):
        self._cached_profile = {}
        self._last_analyzed_wave = -1

    def analyze(self, game, force=False):
        """Build an exposure dict from all placed towers' trait tags.

        Returns dict[str, float] mapping each tag to its weighted exposure score.
        Recomputes every ADAPTATION_CONFIG.recompute_every_n_waves (1 = each wave start)
        unless *force* is True.
        """
        from config import ADAPTATION_CONFIG
        n = max(1, int(ADAPTATION_CONFIG.get("recompute_every_n_waves", 1)))
        if not force and game.round_num == self._last_analyzed_wave and self._cached_profile:
            return self._cached_profile
        if not force and n > 1 and self._cached_profile and game.round_num % n != 0:
            return self._cached_profile

        exposure = {}
        tier = ADAPTATION_CONFIG.get("tier") or {}
        base_w = float(tier.get("base_weight", 1.0))
        per_g = float(tier.get("per_generation", 1.0))
        for tower in game.towers:
            traits = tower.get_traits()
            weight = base_w + tower.merge_generation * per_g
            for tag in traits:
                exposure[tag] = exposure.get(tag, 0.0) + weight

        hybrid_score = 0.0
        pure_score = 0.0
        for tower in game.towers:
            if tower.get_merge_type() == "hybrid":
                hybrid_score += 1.0 + tower.merge_generation
            elif tower.get_merge_type() == "pure" and tower.merge_generation >= 1:
                pure_score += 1.0 + tower.merge_generation
        exposure["_hybrid_exposure"] = hybrid_score
        exposure["_pure_exposure"] = pure_score
        exposure["_tower_count"] = float(len(game.towers))
        self._apply_lineage_dominance(exposure, tier)

        self._cached_profile = exposure
        self._last_analyzed_wave = game.round_num
        return exposure

    @staticmethod
    def _apply_lineage_dominance(exposure, tier):
        """Same-line boards get extra lineage score so mixing tiers/types is the answer."""
        tags = set(lineage_tag_map().values())
        total = sum(float(exposure.get(tag, 0) or 0) for tag in tags)
        if total <= 0:
            return
        share_cut = float(tier.get("dominate_share", 0.65))
        mult = float(tier.get("dominate_mult", 1.35))
        dominated = None
        for tag in tags:
            score = float(exposure.get(tag, 0) or 0)
            if score / total >= share_cut:
                exposure[tag] = score * mult
                dominated = tag
        if dominated:
            exposure["_tier_dominate"] = dominated


def lineage_tag_map():
    from config import ADAPTATION_CONFIG
    return dict((ADAPTATION_CONFIG.get("lineage") or {}).get("tags") or {})


def lineage_scores(profile):
    tags = set(lineage_tag_map().values())
    out = {}
    for key, value in (profile or {}).items():
        if key in tags:
            out[key] = float(value)
    return out


def lineage_factor(score, cfg=None, hooks=None):
    from config import ADAPTATION_CONFIG
    cfg = dict(cfg if cfg is not None else (ADAPTATION_CONFIG.get("lineage") or {}))
    hooks = hooks or {}
    if "lineage_min_score" in hooks:
        cfg["min_score"] = hooks["lineage_min_score"]
    if float(score) < float(cfg.get("min_score", 1.5)):
        return 0.0
    factor = min(
        float(score) * float(cfg.get("factor_per_point", 0.06)),
        float(cfg.get("max_factor", 0.45)),
    )
    factor *= float(hooks.get("lineage_factor_mult", 1.0))
    return min(factor, float(cfg.get("max_factor", 0.45)))


def tell_from_profile(profile) -> str:
    """One HUD line matching adapt_to_profile math. Empty if the swarm has nothing to answer."""
    if not profile:
        return ""
    from config import ADAPTATION_CONFIG
    hybrid = float(profile.get("_hybrid_exposure", 0) or 0)
    pure = float(profile.get("_pure_exposure", 0) or 0)
    lin_cfg = ADAPTATION_CONFIG.get("lineage") or {}
    hooks = (profile or {}).get("_combat_hooks") or {}
    best_tag = None
    best_score = 0.0
    for tag, score in lineage_scores(profile).items():
        if score > best_score:
            best_tag, best_score = tag, score
    lin_factor = lineage_factor(best_score, lin_cfg, hooks) if best_tag else 0.0

    parts = []
    if lin_factor > 0 and best_tag:
        parts.append(f"Adapted: {best_tag} -{int(round(lin_factor * 100))}%")
    if hybrid > 0:
        cfg = ADAPTATION_CONFIG.get("hybrid_exposure") or {}
        factor = min(hybrid * float(cfg.get("factor_per_point", 0.05)), float(cfg.get("max_factor", 0.5)))
        speed = min(
            hybrid * float(cfg.get("speed_boost_per_point", 0.02)) * float(hooks.get("hybrid_speed_mult", 1.0)),
            float(cfg.get("max_speed_boost", 0.4)),
        )
        resist_pct = int(round(factor * 100))
        speed_pct = int(round(speed * 100))
        if resist_pct > 0 or speed_pct > 0:
            if parts:
                if resist_pct > 0:
                    parts.append(f"hybrids -{resist_pct}%")
            else:
                parts.append(f"Adapted: hybrids -{resist_pct}%")
            if speed_pct > 0:
                parts.append(f"+{speed_pct}% spd")
    if parts:
        return " · ".join(parts)
    if pure > 0:
        return "Pure lines latch-safe"
    return ""

