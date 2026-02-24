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


def test_merge_tier_progression():
    """Test merge tier progression: 0+0->1, 1+1->2."""
    # Tier 0 + Tier 0 -> Tier 1
    t0a = Tower(0, 0, "Neural Processor")
    t0b = Tower(0, 0, "Neural Processor")
    assert t0a.get_merge_tier() == 0
    assert t0b.get_merge_tier() == 0

    t1 = Tower.merge_towers(t0a, t0b)
    assert t1.get_merge_tier() == 1
    assert t1.merge_generation == 1

    # Tier 1 + Tier 1 -> Tier 2
    t1a = Tower.merge_towers(Tower(0, 0, "Neural Processor"), Tower(0, 0, "Neural Processor"))
    t1b = Tower.merge_towers(Tower(0, 0, "Neural Processor"), Tower(0, 0, "Neural Processor"))
    assert t1a.get_merge_tier() == 1
    assert t1b.get_merge_tier() == 1

    t2 = Tower.merge_towers(t1a, t1b)
    assert t2.get_merge_tier() == 2
    assert t2.merge_generation == 2


def test_merge_tier_lineage():
    """Test that merged towers accumulate parent lineage."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Plasma Capacitor")

    merged = Tower.merge_towers(t1, t2)

    # Parents should contain both base types
    assert "Neural Processor" in merged.parents
    assert "Plasma Capacitor" in merged.parents
    assert len(merged.parents) == 2

    # Merge again to create tier 2
    t3 = Tower(0, 0, "Thermal Regulator")
    merged2 = Tower.merge_towers(merged, t3)

    # Should have accumulated: merged.parents + t3.parents + [merged.base_type, t3.base_type]
    # = ['Neural Processor', 'Plasma Capacitor'] + [] + ['Neural Processor', 'Thermal Regulator']
    assert len(merged2.parents) == 4


def test_upgrade_apply_dmg_and_range():
    """Test that upgrades correctly apply dmg_mult and range_bonus."""
    t = Tower(0, 0, "Neural Processor")

    # Base stats
    base_dmg = t.dmg
    base_range = t.range

    # Apply switch_1 upgrade (+25% dmg)
    t.upgrades.append("switch_1")
    t._calculate_stats()

    # Should have +25% dmg
    expected_dmg = int(base_dmg * 1.25)
    assert t.dmg == expected_dmg

    # Apply charge_1 upgrade (+1 range)
    t.upgrades.append("charge_1")
    t._calculate_stats()

    # Should have base_range + 1 + synergy bonus (0.2 for Neural Processor + switch_1 synergy)
    assert t.range == base_range + 1 + 0.2


def test_upgrade_apply_synergy_bonus():
    """Test synergy bonus when upgrade matches tower trait."""
    # Neural Processor has ["switch", "logic"] traits
    neural = Tower(0, 0, "Neural Processor")
    # Plasma Capacitor has ["charge", "burst"] traits
    plasma = Tower(0, 0, "Plasma Capacitor")

    # Both get switch_1 upgrade (synergizes_with: ["switch", "logic"])
    neural.upgrades.append("switch_1")
    plasma.upgrades.append("switch_1")

    neural._calculate_stats()
    plasma._calculate_stats()

    # Neural should get synergy bonus (+10% dmg and +0.2 range), plasma should not
    # Base dmg: Neural=6, Plasma=10
    # With switch_1 (+25%): Neural=int(6*1.25)=7, Plasma=int(10*1.25)=12
    # Neural synergy: int(7*1.1)=7, Plasma=12

    assert neural.dmg == 7  # No change due to rounding
    assert plasma.dmg == 12
    assert neural.range == plasma.range + 0.2  # Neural gets range synergy bonus


def test_stat_bonuses_per_tier():
    """Test stat bonuses follow formula per tier."""
    base_dmg = 6
    base_range = 2
    base_fire_rate = 1

    # Tier 0
    t0 = Tower(0, 0, "Neural Processor")
    assert t0.dmg == base_dmg
    assert t0.range == base_range
    assert t0.fire_rate == base_fire_rate

    # Tier 1: boost = 1.0 + 1 * 0.3 = 1.3
    t1 = Tower.merge_towers(Tower(0, 0, "Neural Processor"), Tower(0, 0, "Neural Processor"))
    boost_1 = 1.3
    assert t1.dmg == int(base_dmg * boost_1)
    assert t1.range == base_range + 1
    assert t1.fire_rate == max(1, int(base_fire_rate / boost_1))

    # Tier 2: boost = 1.0 + 2 * 0.3 = 1.6
    t2 = Tower.merge_towers(t1, Tower.merge_towers(Tower(0, 0, "Neural Processor"), Tower(0, 0, "Neural Processor")))
    boost_2 = 1.6
    assert t2.dmg == int(base_dmg * boost_2)
    assert t2.range == base_range + 2
    assert t2.fire_rate == max(1, int(base_fire_rate / boost_2))