"""Sort directive library + harness (Slice C)."""
from collections import Counter

from models.drone_data import DroneData
from core.sort_directives import (
    AssimilationMergeDirective,
    DescendingSpikeDirective,
    DroneBubbleDirective,
    PivotPartitionDirective,
    PowerSortDirective,
    PriorityExtractDirective,
    ResistanceBucketDirective,
    get_directive,
    list_directives,
)
from core.sort_orchestrator import SortOrchestrator, build_run_pool, unlocked_types_for_wave


def _sample_pool(n=40, seed=1):
    return build_run_pool(seed, planned_waves=5, wave_size_fn=lambda w: 8, unlocked_fn=unlocked_types_for_wave)[:n]


def test_registry_has_mvp_library():
    names = set(list_directives())
    for expected in (
        "PowerSort",
        "DescendingSpike",
        "DroneBubble",
        "AssimilationMerge",
        "PivotPartition",
        "PriorityExtract",
        "ResistanceBucket",
    ):
        assert expected in names
        d = get_directive(expected)
        assert d.name == expected


def test_each_directive_preserves_pool_size():
    pool = _sample_pool(36)
    sizes = [6, 6, 6, 6, 6, 6]
    for name in list_directives():
        waves = get_directive(name).restructure(pool, sizes, seed=99)
        flat = [d for w in waves for d in w]
        assert len(flat) == len(pool), name
        # Same multiset of types
        assert Counter(d.enemy_type for d in flat) == Counter(d.enemy_type for d in pool)


def test_power_sort_vs_descending_opposite_ends():
    pool = [
        DroneData.from_type("Drone", 1, noise=-2),
        DroneData.from_type("Assimilator", 1, noise=2),
        DroneData.from_type("Scout", 1),
        DroneData.from_type("Harvester", 1),
    ]
    asc = PowerSortDirective().restructure(pool, [2, 2], 1)
    desc = DescendingSpikeDirective().restructure(pool, [2, 2], 1)
    assert asc[0][0].power <= asc[0][1].power
    assert desc[0][0].power >= desc[0][1].power
    assert asc[0][0].power <= desc[0][0].power


def test_directives_differ_for_same_seed():
    """Different algorithms should not all produce identical first-wave type lists."""
    first_waves = {}
    for name in list_directives():
        orch = SortOrchestrator.create(seed=42, directive_name=name, planned_waves=8)
        first_waves[name] = tuple(d.enemy_type for d in orch.next_wave())
    # At least PowerSort and DescendingSpike should differ
    assert first_waves["PowerSort"] != first_waves["DescendingSpike"]
    # Library should not collapse to one pattern
    unique = set(first_waves.values())
    assert len(unique) >= 3


def test_resistance_bucket_groups_types_early():
    pool = _sample_pool(48, seed=3)
    waves = ResistanceBucketDirective().restructure(pool, [8] * 6, seed=3)
    # First wave should be dominated by a single type (bucket feel)
    counts = Counter(d.enemy_type for d in waves[0])
    dominant = max(counts.values())
    assert dominant >= len(waves[0]) * 0.6


def test_harness_module_runs():
    from tools.sort_harness import main

    assert main(["--list"]) == 0
    assert main(["--seed", "1", "--directive", "DroneBubble", "--waves", "3"]) == 0
    assert main(["--all", "--seed", "2", "--waves", "2"]) == 0
