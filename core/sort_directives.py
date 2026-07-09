"""Sort Directive protocol + registry (Slice C: multi-directive library)."""
from __future__ import annotations

import random
from typing import Callable, List, Protocol, Sequence

from models.drone_data import DroneData


class SortDirective(Protocol):
    """Orders a raw pool and chunks it into per-wave lists."""

    name: str
    display_name: str

    def restructure(
        self,
        raw_pool: Sequence[DroneData],
        wave_sizes: Sequence[int],
        seed: int,
    ) -> List[List[DroneData]]:
        ...


def chunk_by_sizes(ordered: Sequence[DroneData], wave_sizes: Sequence[int]) -> List[List[DroneData]]:
    """Split a flat ordered pool into waves of the given sizes (leftover → last extra wave)."""
    waves: List[List[DroneData]] = []
    idx = 0
    n = len(ordered)
    for size in wave_sizes:
        take = max(0, int(size))
        chunk = list(ordered[idx:idx + take])
        idx += take
        waves.append(chunk)
        if idx >= n:
            break
    if idx < n:
        waves.append(list(ordered[idx:]))
    return waves


# ---------------------------------------------------------------------------
# Directives
# ---------------------------------------------------------------------------

class PowerSortDirective:
    """Sort entire pool by power (ascending), then fixed chunk. Weak → strong."""

    name = "PowerSort"
    display_name = "Power Sort"

    def restructure(self, raw_pool, wave_sizes, seed):
        _ = seed
        return chunk_by_sizes(sorted(raw_pool), wave_sizes)


class DescendingSpikeDirective:
    """Strong-first pressure: reverse power sort. Scout tell: early waves hard."""

    name = "DescendingSpike"
    display_name = "Descending Spike"

    def restructure(self, raw_pool, wave_sizes, seed):
        _ = seed
        return chunk_by_sizes(sorted(raw_pool, reverse=True), wave_sizes)


class DroneBubbleDirective:
    """
    Bubble-pass feel: start shuffled, apply limited adjacent swaps toward sorted.
    Leaves local inversions — adjacent waves look similar but shuffled.
    """

    name = "DroneBubble"
    display_name = "Drone Bubble"

    def restructure(self, raw_pool, wave_sizes, seed):
        rng = random.Random(seed)
        items = list(raw_pool)
        rng.shuffle(items)
        # Partial bubble: ~25% of full passes so order stays choppy
        n = len(items)
        passes = max(1, n // 4)
        for _ in range(passes):
            swapped = False
            for i in range(n - 1):
                if items[i].power > items[i + 1].power:
                    items[i], items[i + 1] = items[i + 1], items[i]
                    swapped = True
            if not swapped:
                break
        return chunk_by_sizes(items, wave_sizes)


class AssimilationMergeDirective:
    """
    Merge-sort inspired: early waves are homogeneous type runs;
    later waves mash merged runs together.
    """

    name = "AssimilationMerge"
    display_name = "Assimilation Merge"

    def restructure(self, raw_pool, wave_sizes, seed):
        rng = random.Random(seed)
        # Group by type, shuffle within, then interleave growing merges
        by_type: dict = {}
        for d in raw_pool:
            by_type.setdefault(d.enemy_type, []).append(d)
        runs = []
        for etype in sorted(by_type.keys()):
            group = list(by_type[etype])
            rng.shuffle(group)
            runs.append(group)

        # Bottom-up merge of runs → flat list that starts mono then mixes
        while len(runs) > 1:
            merged = []
            for i in range(0, len(runs), 2):
                if i + 1 < len(runs):
                    merged.append(self._merge_runs(runs[i], runs[i + 1]))
                else:
                    merged.append(runs[i])
            runs = merged
        ordered = runs[0] if runs else []
        return chunk_by_sizes(ordered, wave_sizes)

    @staticmethod
    def _merge_runs(a: List[DroneData], b: List[DroneData]) -> List[DroneData]:
        out = []
        i = j = 0
        # Alternate taking from each run in growing batches (1,2,4…)
        batch = 1
        take_a = True
        while i < len(a) or j < len(b):
            if take_a:
                take = min(batch, len(a) - i)
                out.extend(a[i:i + take])
                i += take
            else:
                take = min(batch, len(b) - j)
                out.extend(b[j:j + take])
                j += take
            take_a = not take_a
            if take_a:
                batch = min(batch * 2, max(len(a), len(b), 1))
        return out


class PivotPartitionDirective:
    """
    Quicksort-inspired: pick elite pivot, then low partition, then high.
    Scout tell: sudden spike unit then tone shift.
    """

    name = "PivotPartition"
    display_name = "Pivot Partition"

    def restructure(self, raw_pool, wave_sizes, seed):
        rng = random.Random(seed)
        items = list(raw_pool)
        if not items:
            return chunk_by_sizes(items, wave_sizes)
        # Pivot = high-power elite (top quartile pick)
        ranked = sorted(items, key=lambda d: d.power)
        pivot_idx = min(len(ranked) - 1, max(0, int(len(ranked) * 0.75) + rng.randint(0, max(0, len(ranked) // 10))))
        pivot = ranked[pivot_idx]
        rest = [d for d in items if d is not pivot]
        low = [d for d in rest if d.power <= pivot.power]
        high = [d for d in rest if d.power > pivot.power]
        rng.shuffle(low)
        rng.shuffle(high)
        # Pivot early (after a small low teaser), then remaining low, then high
        teaser_n = min(len(low), max(1, len(low) // 8))
        ordered = low[:teaser_n] + [pivot] + low[teaser_n:] + high
        return chunk_by_sizes(ordered, wave_sizes)


class PriorityExtractDirective:
    """
    Heap-inspired: extract same-priority bursts then a stronger pop.
    Scout tell: rhythmic clumps + one stronger unit.
    """

    name = "PriorityExtract"
    display_name = "Priority Extract"

    def restructure(self, raw_pool, wave_sizes, seed):
        rng = random.Random(seed)
        # Bucket by coarse power band, shuffle bands, extract band-by-band
        bands: dict = {}
        for d in raw_pool:
            band = d.power // 5
            bands.setdefault(band, []).append(d)
        band_keys = sorted(bands.keys())
        # Occasional band reorder for seed variety (swap neighbors)
        for _ in range(max(1, len(band_keys) // 3)):
            if len(band_keys) < 2:
                break
            i = rng.randint(0, len(band_keys) - 2)
            if rng.random() < 0.4:
                band_keys[i], band_keys[i + 1] = band_keys[i + 1], band_keys[i]

        ordered: List[DroneData] = []
        for k in band_keys:
            group = list(bands[k])
            rng.shuffle(group)
            # Within band: dump most, then one "pop" (highest power) at end of band
            if len(group) >= 2:
                group.sort(key=lambda d: d.power)
                pop = group.pop()
                rng.shuffle(group)
                ordered.extend(group)
                ordered.append(pop)
            else:
                ordered.extend(group)
        return chunk_by_sizes(ordered, wave_sizes)


class ResistanceBucketDirective:
    """
    Radix-ish: bucket by type trait digit, emit one bucket per wave stretch.
    Scout tell: waves share a trait/type tag.
    """

    name = "ResistanceBucket"
    display_name = "Resistance Bucket"

    def restructure(self, raw_pool, wave_sizes, seed):
        rng = random.Random(seed)
        by_type: dict = {}
        for d in raw_pool:
            by_type.setdefault(d.enemy_type, []).append(d)
        # Order types by average power, with seeded jitter
        types = list(by_type.keys())
        types.sort(key=lambda t: (sum(d.power for d in by_type[t]) / max(1, len(by_type[t])), t))
        if len(types) > 1 and rng.random() < 0.5:
            i = rng.randint(0, len(types) - 2)
            types[i], types[i + 1] = types[i + 1], types[i]
        ordered: List[DroneData] = []
        for t in types:
            group = list(by_type[t])
            group.sort(key=lambda d: d.power)
            ordered.extend(group)
        return chunk_by_sizes(ordered, wave_sizes)


DIRECTIVE_REGISTRY: dict[str, Callable[[], SortDirective]] = {
    "PowerSort": PowerSortDirective,
    "DescendingSpike": DescendingSpikeDirective,
    "DroneBubble": DroneBubbleDirective,
    "AssimilationMerge": AssimilationMergeDirective,
    "PivotPartition": PivotPartitionDirective,
    "PriorityExtract": PriorityExtractDirective,
    "ResistanceBucket": ResistanceBucketDirective,
}


def list_directives() -> List[str]:
    return list(DIRECTIVE_REGISTRY.keys())


def get_directive(name: str) -> SortDirective:
    factory = DIRECTIVE_REGISTRY.get(name) or DIRECTIVE_REGISTRY["PowerSort"]
    return factory()
