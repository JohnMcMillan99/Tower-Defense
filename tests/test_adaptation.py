import pytest
from models.tower import Tower
from models.enemy import Enemy
from core.strategy_analyzer import StrategyAnalyzer
from data.loader import DataLoader


@pytest.fixture(autouse=True)
def setup_loader():
    loader = DataLoader()
    Tower.set_data_loader(loader)
    yield
    Tower._data_loader = None


class MockGame:
    """Lightweight stand-in for Game used by StrategyAnalyzer."""

    def __init__(self, towers=None):
        self.towers = towers or []
        self.round_num = 3


def test_analyzer_aggregates_tags():
    """Analyzer counts tags from placed towers."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Neural Processor")
    game = MockGame([t1, t2])
    analyzer = StrategyAnalyzer()
    profile = analyzer.analyze(game, force=True)
    assert profile.get("_tower_count") == 2.0
    assert profile.get("_pure_exposure") == 0.0  # base towers, gen 0


def test_analyzer_hybrid_exposure():
    """Placing hybrid towers increases _hybrid_exposure."""
    hybrid = Tower.merge_towers(
        Tower(0, 0, "Neural Processor"),
        Tower(0, 0, "Plasma Capacitor"),
    )
    hybrid.x = 1
    hybrid.y = 1
    game = MockGame([hybrid])
    analyzer = StrategyAnalyzer()
    profile = analyzer.analyze(game, force=True)
    assert profile["_hybrid_exposure"] > 0


def test_analyzer_pure_exposure():
    """Placing pure merged towers increases _pure_exposure."""
    pure = Tower.merge_towers(
        Tower(0, 0, "Neural Processor"),
        Tower(0, 0, "Neural Processor"),
    )
    pure.x = 1
    pure.y = 1
    game = MockGame([pure])
    analyzer = StrategyAnalyzer()
    profile = analyzer.analyze(game, force=True)
    assert profile["_pure_exposure"] > 0
    assert profile["_hybrid_exposure"] == 0.0


def test_adapt_to_profile_sets_resistances():
    """adapt_to_profile with hybrid exposure sets resistance entries."""
    e = Enemy([(0, 0), (1, 0)], "Drone", 1)
    profile = {"_hybrid_exposure": 5.0}
    rt = {
        "hybrid_exposure": {
            "factor_per_point": 0.05,
            "max_factor": 0.5,
            "applies_to_tags": ["hybrid"],
            "speed_boost_per_point": 0.02,
            "max_speed_boost": 0.4,
        }
    }
    e.adapt_to_profile(profile, rt)
    assert "hybrid" in e.resistances
    assert e.resistances["hybrid"] < 1.0


def test_adapt_to_profile_no_exposure():
    """With 0 hybrid exposure, resistances stay at 1.0."""
    e = Enemy([(0, 0), (1, 0)], "Drone", 1)
    profile = {"_hybrid_exposure": 0.0}
    e.adapt_to_profile(profile)
    assert e.get_resistance(["hybrid"]) == 1.0


def test_get_resistance_reduces_damage():
    """take_damage respects attacker_tags and resistances."""
    e = Enemy([(0, 0), (1, 0)], "Drone", 1)
    e.resistances["hybrid"] = 0.5
    base_hp = e.health
    e.take_damage(10, attacker_tags=["hybrid"])
    assert e.health == base_hp - 5


def test_get_resistance_no_match():
    """If attacker has no matching tags, full damage applies."""
    e = Enemy([(0, 0), (1, 0)], "Drone", 1)
    e.resistances["hybrid"] = 0.5
    base_hp = e.health
    e.take_damage(10, attacker_tags=["pure_lineage"])
    assert e.health == base_hp - 10


def test_speed_mult_after_adaptation():
    """Adapted enemies get speed_mult > 1.0 based on hybrid exposure."""
    e = Enemy([(0, 0), (1, 0)], "Drone", 1)
    profile = {"_hybrid_exposure": 10.0}
    rt = {
        "hybrid_exposure": {
            "factor_per_point": 0.05,
            "max_factor": 0.5,
            "applies_to_tags": ["hybrid"],
            "speed_boost_per_point": 0.02,
            "max_speed_boost": 0.4,
        }
    }
    e.adapt_to_profile(profile, rt)
    assert e.speed_mult > 1.0


def test_tell_empty_without_board():
    from core.strategy_analyzer import tell_from_profile
    assert tell_from_profile({}) == ""
    assert tell_from_profile({"_hybrid_exposure": 0.0, "_pure_exposure": 0.0}) == ""


def test_tell_pure_lines_latch_safe():
    from core.strategy_analyzer import tell_from_profile
    text = tell_from_profile({"_hybrid_exposure": 0.0, "_pure_exposure": 4.0})
    assert "pure" in text.lower()
    assert "latch" in text.lower() or "safe" in text.lower()


def test_tell_names_hybrid_resist_and_speed():
    from core.strategy_analyzer import tell_from_profile
    text = tell_from_profile({"_hybrid_exposure": 4.0})
    assert "hybrid" in text.lower()
    assert "-20%" in text
    assert "+8%" in text


def test_neural_lineage_on_base_traits():
    t = Tower(0, 0, "Neural Processor")
    assert "neural" in t.get_traits()
    p = Tower(0, 0, "Plasma Capacitor")
    assert "plasma" in p.get_traits()
    assert "neural" not in p.get_traits()


def test_one_tower_does_not_trigger_lineage_adapt():
    game = MockGame([Tower(0, 0, "Neural Processor")])
    game.round_num = 1
    profile = StrategyAnalyzer().analyze(game, force=True)
    e = Enemy([(0, 0), (1, 0)], "Drone", 1)
    e.adapt_to_profile(profile)
    assert e.get_resistance(["neural"]) == 1.0


def test_mono_neural_resists_neural_not_plasma():
    game = MockGame([Tower(0, 0, "Neural Processor"), Tower(1, 0, "Neural Processor")])
    game.round_num = 1
    profile = StrategyAnalyzer().analyze(game, force=True)
    assert profile.get("neural", 0) >= 2.0
    e = Enemy([(0, 0), (1, 0)], "Drone", 1)
    e.adapt_to_profile(profile)
    assert e.resistances["neural"] < 1.0
    hp = e.health
    e.take_damage(10, attacker_tags=Tower(0, 0, "Neural Processor").get_effective_traits())
    assert e.health == hp - int(10 * e.resistances["neural"])
    e2 = Enemy([(0, 0), (1, 0)], "Drone", 1)
    e2.adapt_to_profile(profile)
    hp2 = e2.health
    e2.take_damage(10, attacker_tags=Tower(0, 0, "Plasma Capacitor").get_effective_traits())
    assert e2.health == hp2 - 10


def test_tell_names_lineage():
    from core.strategy_analyzer import tell_from_profile
    text = tell_from_profile({"neural": 4.0, "_hybrid_exposure": 0.0, "_pure_exposure": 0.0})
    assert "neural" in text.lower()
    assert "-" in text


def _pure_at_gen(gen, name="Neural Processor"):
    layer = [Tower(0, 0, name) for _ in range(2 ** gen)]
    while len(layer) > 1:
        layer = [Tower.merge_towers(layer[i], layer[i + 1]) for i in range(0, len(layer), 2)]
    t = layer[0]
    assert t.merge_generation == gen
    return t


def test_apex_one_line_resists_harder_than_mixed_gen1():
    from core.strategy_analyzer import lineage_factor

    apex = [_pure_at_gen(3) for _ in range(3)]
    mixed = [_pure_at_gen(1, "Neural Processor"), _pure_at_gen(1, "Plasma Capacitor")]
    apex_profile = StrategyAnalyzer().analyze(MockGame(apex), force=True)
    mixed_profile = StrategyAnalyzer().analyze(MockGame(mixed), force=True)
    assert apex_profile.get("_tier_dominate") == "neural"
    assert "_tier_dominate" not in mixed_profile
    apex_f = lineage_factor(apex_profile.get("neural", 0))
    neural_f = lineage_factor(mixed_profile.get("neural", 0))
    plasma_f = lineage_factor(mixed_profile.get("plasma", 0))
    assert apex_f > neural_f
    assert apex_f > plasma_f
    e_apex = Enemy([(0, 0)], "Drone", 1)
    e_mix = Enemy([(0, 0)], "Drone", 1)
    e_apex.adapt_to_profile(apex_profile)
    e_mix.adapt_to_profile(mixed_profile)
    assert e_apex.get_resistance(["neural"]) < e_mix.get_resistance(["neural"])

