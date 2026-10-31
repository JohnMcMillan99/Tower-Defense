# Tower Defense 3: Borg Assimilation

A Borg-themed tower defense roguelike. Buy hardware, merge it, grow the path, and survive an 80-wave Sort. The swarm adapts to what you actually placed.

**Theme**: Assimilation and adaptation — towers are network nodes; enemies are drones that learn your board.

**Core verb**: 2-for-1 merge. Same-tier towers combine. Pure lines stay latch-immune; hybrids hit harder and the swarm notices.

---

## Play loop

1. **Main menu** — pick a save slot (profile Dilithium + unlocks persist).
2. **Run select** — New Run, Continue (last WaveClear checkpoint), or Collective shop.
3. **Compile** — pick one of three Sort Directives plus 0–2 modifiers.
4. **In-run** — shop towers, merge on the 5-slot bench, place on the grid, spend the 4-slot loot bag (path tiles + upgrades share it). Shop, place, and merge stay legal while enemies are on the map.
5. **WaveClear** — checkpoint. Quit mid-wave forfeits the run. Wave 80 is victory.

Auto mode chains waves with a 2-second clear beat. Target clock: ~20 minutes to wave 80, typical death around wave 45–50 (~12 minutes).

---

## How to run

Python **3.11+**. Use the project venv (pygame is installed there).

```powershell
cd "c:\Users\Johnm\Tower Defense"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
python main.py --minimal
```

Browser (pygbag), from the **parent** of this folder:

```powershell
pygbag "Tower Defense"
```

Then open http://localhost:8000. Web mode scales enemy counts down.

Set `DEBUG = True` in `config.py` to write `debug.log`.

---

## Controls

| Input | Action |
|-------|--------|
| Click shop card | Buy onto the tower bench |
| Reroll | Refresh the tower shop (3 gold) |
| Click bench tower, then grid | Place |
| Click two same-tier bench towers | Merge preview; confirm or egrem (wrong-tier) |
| Right-click bench / grid tower | Sell (partial refund) |
| 1–4 | Select loot-bag slot |
| Selected path tile + A / D or rotate buttons | Rotate; click path end to place |
| Selected upgrade + click tower | Apply (3 upgrades per tower) |
| Next Wave / Auto | Start or chain waves |
| Esc | Pause (Resume / Forfeit). Settings is a stub |
| Arrow keys / middle-drag | Pan |
| Mouse wheel | Zoom |
| Home | Reset camera |

---

## Shipped systems

### Shop, bench, loot

- **5-slot tower shop** only. No T/M/U mode toggle.
- **5-slot tower bench**. Collective "Aux Rack" adds a sixth on the next New Run.
- **4-slot shared loot bag** — path tiles and upgrades compete. A full bag refuses the drop and records a miss (`loot_misses`). There is no displace UI.
- New Run seeds one Straight tile. Mini-boss (every 5) and boss (every 20) grant a tile plus an upgrade. Egrem kills can drop a tile.
- Starting gold 25, lives 20. Kill and wave gold are halved vs the old economy. Sell bench 50%; sell from grid 45%.

### Towers

| Tower | Color | DMG | Range | Fire rate | Fire type | Role |
|-------|-------|-----|-------|-----------|-----------|------|
| Neural Processor | Blue | 6 | 2 | 1 | TargetBeam | Balanced |
| Plasma Capacitor | Green | 10 | 2 | 4 | Ball | Burst |
| Thermal Regulator | Orange | 4 | 3 | 2 | DirectionalBeam | Area denial |
| Signal Router | Purple | 7 | 4 | 2 | Track | Path control |
| Quantum Field Gen | Yellow | 2 | 99 | 10 | Overwatch | Global |
| Nanite Swarm | Dark grey | 0 | 0 | 0 | Spawner | Wrong-tier egrem result |

Merge same tier → one stronger tower (damage ×1.5, range +1, fire rate ×1.2 per generation, plus purity bonuses). Wrong-tier confirm is **egrem**: costs gold, leaves a Nanite Swarm, injects noise, and can type-swap the next wave.

Pure merge (same lineage) is latch-immune. Hybrid merge is stronger and gives the swarm resist + speed.

### Enemies

| Enemy | HP | Speed | First wave | Notes |
|-------|----|-------|------------|-------|
| Drone | 10 | 10 | 1 | Basic |
| Scout | 8 | 6 | 3 | Fast |
| Harvester | 15 | 12 | 5 | Tanky |
| Adaptor | 20 | 8 | 7 | Mid |
| Assimilator | 25 | 10 | 9 | Can latch adjacent base/hybrid towers |

HP scales with wave: `HP = base × (1 + (wave-1) × hp_scale_per_wave × difficulty)`. Default `hp_scale_per_wave` is 3.5. Mini-boss / boss waves also apply HP and speed mults from `REWARD_CONFIG`.

### Sort Directives

Compile picks the run's wave order **and** a combat hook (`DIRECTIVE_COMBAT` in `config.py`):

| Directive | Wave shape | Combat hook |
|-----------|------------|-------------|
| Power Sort | Weak → strong | Slightly less lineage resist |
| Descending Spike | Hard open | Lineage adapt starts sooner |
| Drone Bubble | Local shuffles | Lower latch chance |
| Assimilation Merge | Mono runs, then mash | Higher latch chance |
| Pivot Partition | Tease, elite, high side | Faster latch fill |
| Priority Extract | Clumps then a pop | Hybrid speed up |
| Resistance Bucket | Type-tagged stretches | Stronger lineage resist |

Round Guide shows intel (Contact → Scan → Tap → Matrix). Egrem kills raise intel and can scramble the next forecast.

### Combat depth (live)

- **Adaptation** — each wave, the swarm resists the lineages and hybrid tags you stacked. Mono boards get eaten.
- **Latch** — Assimilators stick to adjacent **towers** (not walls). Soak silences the tower and adds heat; killing the virus unlatches. Pure merges are immune.
- **Path tiles** — placing a tile lengthens the track (more shots, more latch surface).
- **Milestone spikes** — waves 5/10/15/20… hit harder and drop loot.

### Screens and saves

- App stack: Main menu → Run select → In-run. Esc pause is an overlay.
- Profile save (`saves/profiles.json`): Dilithium, Collective unlocks, WaveClear checkpoint.
- Checkpoint is a **build** snapshot only (gold, path, towers, bench, shop, loot, Sort cursor). Combat is never saved. Mid-wave quit = forfeit.
- Collective (3 live patches, Dilithium): Aux Rack (+1 bench), Cache Flush (reroll costs 1), Seed Capacitor (+5 start gold). Applies on the next New Run.

### HUD

Shop (5/8) + loot bag (3/8) over the tower bench. Right rail: CORE (wave, gold, lives, intel), Round Guide stamps, inspector. Circuit Relic glyphs are procedural 32×32 (PNG in `assets/glyphs/` overrides). Dev Tools (menus only) expose combat / economy knobs.

---

## Architecture

```
Tower Defense/
├── main.py                 # pygame + pygbag loop; constructs App
├── config.py               # All live tunables (economy, waves, adapt, latch, intel, clock)
├── core/
│   ├── app.py              # Screen stack, Compile, pause, Collective, save hooks
│   ├── game.py             # Run state
│   ├── economy.py          # Shop, bench, merge, loot bag, egrem
│   ├── wave_manager.py     # Spawn, latch tick, milestones, Auto clock
│   ├── sort_directives.py  # Seven directive restructure() impls
│   ├── sort_orchestrator.py
│   ├── run_setup.py        # Compile offer → RunSetup
│   ├── strategy_analyzer.py
│   ├── save.py / checkpoint.py
│   ├── collective.py       # Three Dilithium patches
│   └── board.py            # Latch scan; walls exist in API only
├── models/                 # tower, enemy, assimilator, path_wall
├── ui/                     # layout, renderer, events, glyphs, swarm_fx, devtools
├── data/yaml/              # merges, enemies, traits, event waves, unused meta tables
├── map/                    # path_graph, augment_manager (cell effects unwired)
├── tests/
└── tools/                  # latch_probe, sort_harness
```

Tune combat in `config.py` (and Dev Tools). YAML is for merge trees, traits, and event-wave rosters — not the HP/latch knobs.

---

## Tests

Project venv:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_adaptation.py tests/test_wave_pressure.py tests/test_sort_directives.py tests/test_path_tiles.py tests/test_rewards_economy.py tests/test_slice_d.py tests/test_run_loop.py -q
```

Do not run `tests/test_runtime.py`, `tests/test_quick_run.py`, or `tests/test_rendering_issue.py` under pytest — they open a display.

---

## Parked (not regressions)

Intentionally out of the current play build:

- Path walls / `initialize_from_map` — latch-to-wall is test-only
- Cell augments / `apply_cell_effects_to_tower` — tags can stamp; they do not change combat
- Loot displace UI — full bag misses
- `tft_timer` prep clock
- Settings, audio, Relic PNGs, pygbag juice
- `meta_unlocks.yaml` / `meta_sort.yaml` — not wired; Collective is the three stubs
- `assimilators.yaml` — unused; live latch is `LATCH_CONFIG`

Known leftovers (not parked features): right-click rotate can also sell if the cursor is over a tower; same-tier merge confirm is silent when you cannot afford it; HUD Play is a no-op (use Esc).

---

## Dependencies

- Python 3.11+ (3.11.2 used in the project venv)
- pygame 2.0+, PyYAML 6.0+, pytest 7.0+, pygbag 0.9+ (see `requirements.txt`)
