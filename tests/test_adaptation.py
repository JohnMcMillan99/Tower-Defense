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
