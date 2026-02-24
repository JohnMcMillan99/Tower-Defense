import pytest
from models.tower import Tower


def test_merge_tiers():
    """Test that merging towers increases their tier."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Neural Processor")
    merged = Tower.merge_towers(t1, t2)
    assert merged.get_merge_tier() == 1
    assert merged.dmg > t1.dmg  # Check bonuses applied


def test_upgrade_capacity():
    """Test that towers can have up to UPGRADE_CAPACITY upgrades."""
    t = Tower(0, 0, "Neural Processor")
    # Tower starts with no upgrades
    assert len(t.upgrades) == 0
    assert t.UPGRADE_CAPACITY == 3

    # Simulate adding upgrades (normally done through economy manager)
    for i in range(t.UPGRADE_CAPACITY):
        t.upgrades.append(f"upgrade_{i}")

    assert len(t.upgrades) == t.UPGRADE_CAPACITY

    # Adding one more should be prevented (checked in economy manager)
    assert len(t.upgrades) <= t.UPGRADE_CAPACITY


def test_merge_towers_static():
    """Test the static merge_towers method."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Neural Processor")

    # Set some initial properties
    t1.gold_invested = 5
    t2.gold_invested = 3
    t1.upgrades = ["upgrade_1"]
    t2.upgrades = ["upgrade_2"]

    merged = Tower.merge_towers(t1, t2)

    # Check tier increased
    assert merged.get_merge_tier() == 1

    # Check gold invested combined
    assert merged.gold_invested == t1.gold_invested + t2.gold_invested

    # Check upgrades combined (unique)
    assert set(merged.upgrades) == {"upgrade_1", "upgrade_2"}

    # Check base type preserved
    assert merged.base_type == "Neural Processor"


def test_tower_stats_calculation():
    """Test that tower stats are calculated correctly."""
    t = Tower(0, 0, "Neural Processor")

    # Base stats for Neural Processor
    base_dmg = 6
    base_range = 2
    base_fire_rate = 1

    # Tier 0 tower should have base stats
    assert t.dmg == base_dmg
    assert t.range == base_range
    assert t.fire_rate == base_fire_rate

    # Merge to create tier 1 tower
    t1 = Tower.merge_towers(t, Tower(0, 0, "Neural Processor"))

    # Tier 1 should have boosted stats
    boost = 1.0 + 1 * 0.3  # 1.3x
    assert t1.dmg == int(base_dmg * boost)
    assert t1.range == base_range + 1  # +1 per tier
    assert t1.fire_rate == max(1, int(base_fire_rate / boost))


def test_different_tower_types():
    """Test that different tower types have different base stats."""
    neural = Tower(0, 0, "Neural Processor")
    plasma = Tower(0, 0, "Plasma Capacitor")

    # Different base damage
    assert neural.dmg != plasma.dmg

    # Different fire rates
    assert neural.fire_rate != plasma.fire_rate

    # Same base range initially
    assert neural.range == plasma.range == 2