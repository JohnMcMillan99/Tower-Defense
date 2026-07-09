import pytest
from map.augment_manager import AugmentManager
from data.loader import DataLoader
from models.tower import Tower


@pytest.fixture
def loader():
    return DataLoader()


@pytest.fixture
def mgr(loader):
    return AugmentManager(loader)


def test_corruption_before_threshold(mgr):
    """Before tiles_threshold (5), should_corrupt returns False."""
    for _ in range(4):
        mgr.on_tile_placed()
    assert mgr.should_corrupt() is False


def test_corruption_at_threshold(mgr):
    """At tiles_threshold (5), should_corrupt returns True."""
    for _ in range(5):
        mgr.on_tile_placed()
    assert mgr.should_corrupt() is True


def test_apply_augment(mgr):
    """apply_augment adds a tag to a cell."""
    mgr.apply_augment((3, 4), "augment_range_boost")
    assert "augment_range_boost" in mgr.get_cell_augments((3, 4))


def test_apply_augment_no_duplicates(mgr):
    """Same tag applied twice -> only stored once."""
    mgr.apply_augment((3, 4), "augment_range_boost")
    mgr.apply_augment((3, 4), "augment_range_boost")
    assert mgr.get_cell_augments((3, 4)).count("augment_range_boost") == 1


def test_remove_augment(mgr):
    mgr.apply_augment((1, 1), "blocked")
    mgr.remove_augment((1, 1), "blocked")
    assert mgr.get_cell_augments((1, 1)) == []


def test_get_augment_effects(mgr):
    """augment_range_boost should give +1 range per augment_rules.yaml."""
    mgr.apply_augment((0, 0), "augment_range_boost")
    effects = mgr.get_augment_effects((0, 0))
    assert effects.get("range_bonus", 0) == 1


def test_tower_on_augmented_cell(loader, mgr):
    """Tower placed on cell with range_boost augment gets +1 range."""
    Tower.set_data_loader(loader)
    t = Tower(0, 0, "Neural Processor")
    base_range = t.range
    mgr.apply_augment((0, 0), "augment_range_boost")
    mgr.apply_cell_effects_to_tower(t)
    assert t.range == base_range + 1
    Tower._data_loader = None


def test_no_augment_no_change(loader, mgr):
    """Tower on cell with no augments is not modified."""
    Tower.set_data_loader(loader)
    t = Tower(0, 0, "Neural Processor")
    dmg_before = t.dmg
    range_before = t.range
    mgr.apply_cell_effects_to_tower(t)
    assert t.dmg == dmg_before
    assert t.range == range_before
    Tower._data_loader = None
