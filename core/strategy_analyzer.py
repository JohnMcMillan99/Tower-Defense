class StrategyAnalyzer:
    """Aggregates placed-tower trait tags into an exposure profile used by enemy adaptation."""

    def __init__(self):
        self._cached_profile = {}
        self._last_analyzed_wave = -1

    def analyze(self, game, force=False):
        """Build an exposure dict from all placed towers' trait tags.

        Returns dict[str, float] mapping each tag to its weighted exposure score.
        Only re-computes every 3 waves unless *force* is True.
        """
        if not force and game.round_num == self._last_analyzed_wave:
            return self._cached_profile

        if not force and game.round_num % 3 != 0 and self._cached_profile:
            return self._cached_profile

        exposure = {}
        for tower in game.towers:
            traits = tower.get_traits()
            weight = 1.0 + tower.merge_generation * 0.5
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

        self._cached_profile = exposure
        self._last_analyzed_wave = game.round_num
        return exposure
