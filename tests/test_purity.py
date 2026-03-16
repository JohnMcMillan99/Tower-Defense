import pytest
from models.tower import Tower
from data.loader import DataLoader


@pytest.fixture(autouse=True)
def setup_loader():
    """Ensure Tower has a data loader for all purity/hybrid tests."""
    loader = DataLoader()
    Tower.set_data_loader(loader)
    yield
    Tower._data_loader = None


def test_calculate_purity_pure():
    """Pure merge of 2x same type -> purity 100."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Neural Processor")
    merged = Tower.merge_towers(t1, t2)
    assert merged.calculate_purity() == 100
    assert merged.get_merge_type() == "pure"


def test_calculate_purity_hybrid():
    """Hybrid merge of different types -> purity < 100."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Plasma Capacitor")
    merged = Tower.merge_towers(t1, t2)
    assert merged.calculate_purity() == 0
    assert merged.get_merge_type() == "hybrid"


def test_calculate_purity_base():
    """Unmerged tower -> purity 100 (no parents)."""
    t = Tower(0, 0, "Neural Processor")
    assert t.calculate_purity() == 100
    assert t.get_merge_type() == "base"


def test_apply_lineage_bonuses_gen1_pure():
    """Pure gen1 tower gets pure_lineage + exponential bonus from traits.yaml."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Neural Processor")
    merged = Tower.merge_towers(t1, t2)
    base_t0 = Tower(0, 0, "Neural Processor")
    base_boost = 1.0 + 1 * 0.3
    raw_dmg = int(base_t0.dmg * base_boost)
    assert merged.dmg > raw_dmg, "Pure gen1 should have lineage bonuses applied"


def test_apply_lineage_bonuses_gen2_pure():
    """Pure gen2 tower gets mastery bonus on top of pure_lineage."""
    t1a = Tower.merge_towers(Tower(0, 0, "Plasma Capacitor"), Tower(0, 0, "Plasma Capacitor"))
    t1b = Tower.merge_towers(Tower(0, 0, "Plasma Capacitor"), Tower(0, 0, "Plasma Capacitor"))
    t2 = Tower.merge_towers(t1a, t1b)
    assert t2.calculate_purity() == 100
    assert t2.merge_generation == 2
    assert t2.dmg > t1a.dmg, "Gen2 pure should be stronger than gen1 pure"


def test_hybrid_merge_cortex():
    """Neural + Plasma merge -> Cortex Assimilator via hybrid_trees."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Plasma Capacitor")
    merged = Tower.merge_towers(t1, t2)
    assert merged.base_type == "Cortex Assimilator"
    assert merged.merge_generation == 1


def test_hybrid_merge_thermal_router():
    """Thermal Regulator + Signal Router -> Thermal Router."""
    t1 = Tower(0, 0, "Thermal Regulator")
    t2 = Tower(0, 0, "Signal Router")
    merged = Tower.merge_towers(t1, t2)
    assert merged.base_type == "Thermal Router"


def test_hybrid_merge_quantum_burst():
    """Quantum Field Gen + Plasma Capacitor -> Quantum Burst Engine."""
    t1 = Tower(0, 0, "Quantum Field Gen")
    t2 = Tower(0, 0, "Plasma Capacitor")
    merged = Tower.merge_towers(t1, t2)
    assert merged.base_type == "Quantum Burst Engine"


def test_hybrid_merge_neural_field():
    """Neural Processor + Quantum Field Gen -> Neural Field Generator."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Quantum Field Gen")
    merged = Tower.merge_towers(t1, t2)
    assert merged.base_type == "Neural Field Generator"


def test_hybrid_not_in_tree():
    """Combo not in hybrid_trees keeps first tower's base_type."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Thermal Regulator")
    merged = Tower.merge_towers(t1, t2)
    assert merged.base_type == "Neural Processor"


def test_can_merge_same_type():
    """Same type + same tier can merge."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Neural Processor")
    assert Tower.can_merge(t1, t2) is True


def test_can_merge_hybrid_tree():
    """Hybrid tree pair + same tier can merge."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Plasma Capacitor")
    assert Tower.can_merge(t1, t2) is True


def test_can_merge_different_tier():
    """Different tier cannot merge."""
    t0 = Tower(0, 0, "Neural Processor")
    t1 = Tower.merge_towers(Tower(0, 0, "Neural Processor"), Tower(0, 0, "Neural Processor"))
    assert Tower.can_merge(t0, t1) is False


def test_get_display_name_pure_gen1():
    """Pure gen1 -> '{base_type} Enhanced'."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Neural Processor")
    merged = Tower.merge_towers(t1, t2)
    assert merged.get_display_name() == "Neural Processor Enhanced"


def test_get_display_name_pure_gen2():
    """Pure gen2 -> 'Advanced {base_type}'."""
    t1a = Tower.merge_towers(Tower(0, 0, "Neural Processor"), Tower(0, 0, "Neural Processor"))
    t1b = Tower.merge_towers(Tower(0, 0, "Neural Processor"), Tower(0, 0, "Neural Processor"))
    t2 = Tower.merge_towers(t1a, t1b)
    assert t2.get_display_name() == "Advanced Neural Processor"


def test_get_display_name_pure_gen3():
    """Pure gen3 -> '{base_type} Apex'."""
    t0 = [Tower(0, 0, "Neural Processor") for _ in range(8)]
    t1 = [Tower.merge_towers(t0[i], t0[i + 1]) for i in range(0, 8, 2)]
    t2 = [Tower.merge_towers(t1[i], t1[i + 1]) for i in range(0, 4, 2)]
    t3 = Tower.merge_towers(t2[0], t2[1])
    assert t3.merge_generation == 3
    assert t3.get_display_name() == "Neural Processor Apex"


def test_get_display_name_hybrid():
    """Hybrid tower uses its result name."""
    t1 = Tower(0, 0, "Neural Processor")
    t2 = Tower(0, 0, "Plasma Capacitor")
    merged = Tower.merge_towers(t1, t2)
    assert merged.get_display_name() == "Cortex Assimilator"


def test_get_display_name_base():
    """Unmerged tower -> just base_type."""
    t = Tower(0, 0, "Signal Router")
    assert t.get_display_name() == "Signal Router"


def test_get_traits_base():
    """Base tower returns TOWER_TRAITS tags."""
    t = Tower(0, 0, "Neural Processor")
    traits = t.get_traits()
    assert "switch" in traits or "logic" in traits


def test_get_traits_pure_gen1():
    """Pure gen1 tower auto-generates pure lineage tags."""
    merged = Tower.merge_towers(
        Tower(0, 0, "Neural Processor"),
        Tower(0, 0, "Neural Processor"),
    )
    traits = merged.get_traits()
    assert "pure_lineage" in traits
    assert "pure_neural_processor_gen1" in traits


def test_get_traits_hybrid():
    """Hybrid tower gets 'hybrid' tag."""
    merged = Tower.merge_towers(
        Tower(0, 0, "Neural Processor"),
        Tower(0, 0, "Plasma Capacitor"),
    )
    traits = merged.get_traits()
    assert "hybrid" in traits
