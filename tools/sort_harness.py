"""
Console harness: print wave compositions for a seed + Sort Directive.

Usage:
  python tools/sort_harness.py
  python tools/sort_harness.py --seed 42 --directive DroneBubble --waves 12
  python tools/sort_harness.py --all --seed 7 --waves 8
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

# Allow running from repo root or tools/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sort_directives import list_directives
from core.sort_orchestrator import SortOrchestrator


def format_wave(i: int, chunk) -> str:
    counts = Counter(d.enemy_type for d in chunk)
    parts = [f"{n}×{t}" for t, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]
    avg_p = sum(d.power for d in chunk) / max(1, len(chunk))
    return f"  W{i:02d} n={len(chunk):2d}  avgP={avg_p:5.1f}  {', '.join(parts)}"


def print_run(seed: int, directive: str, waves: int, web_mode: bool = False):
    orch = SortOrchestrator.create(
        seed=seed,
        directive_name=directive,
        planned_waves=waves,
        web_mode=web_mode,
    )
    print(f"=== {orch.directive_display} ({orch.directive_name})  seed={seed}  waves={waves} ===")
    for i in range(waves):
        chunk = orch.next_wave()
        if not chunk:
            print(f"  W{i + 1:02d} (empty — plan exhausted)")
            break
        print(format_wave(i + 1, chunk))
    print()


def main(argv=None):
    p = argparse.ArgumentParser(description="Print Sort Directive wave compositions")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--directive", default="PowerSort", help="Directive name, or use --all")
    p.add_argument("--waves", type=int, default=10)
    p.add_argument("--all", action="store_true", help="Run every registered directive")
    p.add_argument("--web", action="store_true", help="Use web_mode wave sizes")
    p.add_argument("--list", action="store_true", help="List directive names and exit")
    p.add_argument("--modifier", action="append", default=[], help="Modifier id (repeatable)")
    p.add_argument("--hidden", action="store_true", help="Mark directive as hidden")
    args = p.parse_args(argv)

    if args.list:
        for name in list_directives():
            print(name)
        return 0

    names = list_directives() if args.all else [args.directive]
    for name in names:
        from core.run_setup import RunSetup
        setup = RunSetup(
            seed=args.seed,
            directive_name=name,
            directive_hidden=args.hidden,
            modifier_ids=args.modifier,
        )
        orch = SortOrchestrator.create(run_setup=setup, planned_waves=args.waves, web_mode=args.web)
        print(f"=== {orch.directive_display} ({orch.directive_name})  seed={args.seed}  waves={args.waves} ===")
        if setup.modifier_ids:
            print(f"  modifiers: {', '.join(setup.modifier_ids)}")
        if setup.directive_hidden:
            print("  (hidden)")
        for i in range(args.waves):
            chunk = orch.next_wave()
            if not chunk:
                print(f"  W{i + 1:02d} (empty — plan exhausted)")
                break
            print(format_wave(i + 1, chunk))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
