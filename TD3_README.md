# Tower Defense 3: Borg Assimilation

A Borg-themed tower defense roguelike with a **merge-based tower progression system**. Combine towers to create stronger variants, manage a limited bench, and defend against waves of assimilating enemies.

## Overview

**Theme**: Star Trek Borg Collective - Assimilation & Adaptation
- Towers represent Borg network nodes/modifications that evolve through "assimilation" (merging)
- Enemies are Borg drones at various adaptation levels, growing stronger as they assimilate
- Upgrade progression mirrors biological and technological adaptation

**Core Mechanic**: 2-for-1 Tower Merging with Tier Progression
- Buy towers from the shop, place them on a 10-slot bench
- Drag benched towers to the grid or merge two towers of the **same tier**
- Merged towers inherit both parents' stats + bonuses (dmg +50%, range +1, fire_rate +20%)
- Tier system prevents rushing: must combine base towers before combining merged ones
- Lineage tracking shows merge history through parent tree

---

## Current Features

### ✅ Implemented Systems

#### 1. **Shop & Bench Management**
- **5-slot shop** with reroll button (cost: 2 gold)
- **3-way shop toggle** (T/M/U): cycles between **Towers**, **Map Tiles**, and **Upgrades**
- **10-slot tower bench** below shop for tower inventory
- **3-slot map tile bench** (bottom left) for expansion tiles
- **3-slot upgrade bench** (bottom right) for purchased upgrades
- Click shop cards to add to appropriate bench based on current mode
- Reroll refreshes shop slots for current mode

#### 2. **Tower Types** (5 Borg-themed hardware components)

| Tower | Color | Base DMG | Range | Fire Rate | Fire Type | Role |
|-------|-------|----------|-------|-----------|-----------|------|
| **Neural Processor** | Blue | 6 | 2 | 1 | TargetBeam | Balanced targeting |
| **Plasma Capacitor** | Green | 10 | 2 | 4 | Ball | Burst damage |
| **Thermal Regulator** | Orange | 4 | 3 | 2 | DirectionalBeam | Area denial |
| **Signal Router** | Purple | 7 | 4 | 2 | Track | Path control |
| **Quantum Field Gen** | Yellow | 2 | 99 | 10 | Overwatch | Global coverage |
| **Nanite Swarm** | Dark Grey | 0 | 0 | 0 | Spawner | Enemy generation |

#### 3. **Tower Merging System**
- **2-for-1 Merge**: Combine 2 towers → 1 stronger tower
- **Tier-based Locking**: Only towers at the same tier can merge
  - Tier 0: Base towers (no parents)
  - Tier 1: Merged once (2 parents)
  - Tier 2: Merged twice (4 parents)
  - Tier N: Merged N times (2^N parents)
- **Merge Stat Bonuses**:
  - Damage: +50% per merge level
  - Range: +1 per merge level
  - Fire Rate: +20% per merge level
- **Visual Preview**: Green highlight box shows which two towers would merge
- **Confirm/Cancel UI**: Accept or reject merge before committing

#### 4. **Enemy Types** (5 Borg adaptation levels)

| Enemy | HP | Speed | Difficulty | First Wave | Description |
|-------|----|----|------------|------------|---|
| **Drone** | 10 | 1.0 | 1.0 | Wave 1 | Basic foot soldiers |
| **Scout** | 15 | 1.5 | 1.2 | Wave 3 | Fast recon units |
| **Harvester** | 25 | 0.8 | 1.5 | Wave 5 | Resource gatherers |
| **Adaptor** | 35 | 1.2 | 1.8 | Wave 7 | Adaptive combatants |
| **Assimilator** | 50 | 1.0 | 2.0 | Wave 9 | Queen-class threats |

#### 5. **Wave-Based Difficulty System**
- **Progressive Enemy Unlock**: New enemy types introduced at specific waves
  - Waves 1-2: Drones only
  - Waves 3+: Drones + Scouts
  - Waves 5+: Add Harvesters
  - Waves 7+: Add Adaptors
  - Waves 9+: Add Assimilators
- **Stat Scaling**: Enemy HP scales per wave: `HP = base_hp × (1 + (wave - 1) × 0.2 × difficulty)`
- **Wave Control**: Play/Pause button, Next Wave button, manual wave triggering

#### 6. **Tile-Based Map Expansion**
- **Purchasable map tiles**: Straight, Left Turn, Right Turn, Loop (from tiles shop mode)
- **Path connection**: Tiles must connect to existing paths; rotation support (0°, 90°, 180°, 270°)
- **Map tile bench**: 3 slots; select tile, rotate with A/D or &lt;/&gt; buttons, place on grid
- **Dynamic grid expansion**: Grid grows when tiles extend beyond current bounds

#### 7. **Upgrade Shop & Bench**
- **Upgrade shop mode**: Buy upgrades from shop (12 types: synergistic + wildcard)
- **Upgrade bench**: 3 slots in bottom-right; store purchased upgrades
- **Apply flow**: Select upgrade from bench → click tower on grid to apply
- **Upgrade capacity**: 3 upgrades per tower (configurable per tower type for balancing)
- **Visual feedback**: Green/red tower borders when upgrade selected (can/cannot apply)
- **Keyboard shortcuts**: 1–3 keys select upgrade bench slots

#### 8. **Visual Interface** (Pygame)
- Procedurally generated path grid with expandable borders
- Shop at top; tower bench, map tile bench, upgrade bench
- Right panel: wave controls, pause, auto mode, tower stats when selected
- Camera: pan (arrow keys / middle-drag), zoom (mouse wheel)
- Enemy path overlaid on grid; tower and enemy rendering with Borg-themed colors

#### 9. **Game Flow**
- Enemy path generated procedurally via PathGenerator (from TD3.py)
- Towers placed on grid interact with passing enemies
- Tower damage calculation: `dmg = base_dmg × fire_rate`
- Enemy pathfinding along generated path
- Wave progression with enemy spawning at intervals

---

## Architecture

### File Structure
```
Tower Defense/
├── td_visual.py        # Main pygame app and game loop
├── TD3.py              # PathGenerator algorithm
├── requirements.txt    # Dependencies
├── TD3_README.md       # This file
├── data/
│   ├── tiles.py        # Map expansion tile definitions
│   ├── units.py        # Tower types and traits
│   └── upgrades.py     # Software upgrade definitions
├── models/
│   ├── enemy.py        # Enemy types and behavior
│   └── tower.py        # Tower model with merge/upgrade logic
└── map/
    └── path_graph.py   # Path connectivity for tile placement
```

### Core Classes

#### `Tower` (models/tower.py)
```python
class Tower:
    UPGRADE_CAPACITY = 3  # Max upgrades per tower

    def __init__(self, x, y, tower_type, parents=None)
    def _calculate_stats(self)
    def merge_towers(tower1, tower2)  # Static method
    def get_merge_tier(self)           # Returns merge_generation
    def get_effective_traits(self)     # Base + upgrade traits
```

#### `Enemy` (models/enemy.py)
```python
class Enemy:
    TYPES = {
        "Drone": {"health": 10, "speed": 1.0, "difficulty": 1.0, ...},
        # ... 4 more types
    }
    
    def __init__(self, x, y, enemy_type, wave_num)
    def _calculate_stats(self)  # Scales health based on wave_num
```

#### `Game` (td_visual.py)
- Central state manager
- Manages shop (5 slots), tower bench (10 slots), map tile bench (3), upgrade bench (3)
- Shop modes: `generate_shop()` for towers/tiles/upgrades
- Merging: `select_for_merge()`, `confirm_merge()`, `cancel_merge()`, `_complete_egrem()`
- Upgrades: `apply_upgrade_from_bench()`, `move_to_bench()` for all modes
- Map expansion: `can_place_tile()`, `place_map_tile()`, `expand_grid()`
- Wave spawning: `start_next_wave()`, `update_wave()`

#### Main Pygame Loop (lines 1056-1180+)
- 60 FPS game loop
- Event handling: clicks for shop/bench/grid, drag operations
- Drawing: shop cards, bench, grid, towers (color-coded by type), enemies
- Wave updates via `game.update_wave()`

---

## Borg Theme & Lore

### Design Philosophy
The game mirrors Borg assimilation mechanics:
- **Towers** = Network nodes that adapt & grow stronger through assimilation (merging)
- **Merging** = Assimilation process combining two systems into one
- **Enemy Waves** = Progressive drone adaptation levels, becoming harder as they "assimilate" defenses
- **Tier System** = Biological/technological hierarchy in Borg collective

### Enemy Progression Narrative
1. **Drones** (Waves 1-2): Basic foot soldiers, low threat
2. **Scouts** (Waves 3+): Reconnaissance units, faster, learning patrol patterns
3. **Harvesters** (Waves 5+): Gather resources from defense matrix
4. **Adaptors** (Waves 7+): High-level combat specialists, counter tower strategies
5. **Assimilators** (Waves 9+): Queen-level threats, apex of adaptation

### Tower Types as Specializations
- **Neural Processor** = Balanced targeting (switch, logic)
- **Plasma Capacitor** = Burst damage (charge, burst)
- **Thermal Regulator** = Area denial (resist, heat)
- **Signal Router** = Path control (block, flow)
- **Quantum Field Gen** = Global coverage (filter, magnetic)
- **Nanite Swarm** = Egrem spawner (wrong-tier merge result)

---

## How to Run

### Setup
```powershell
cd "c:\Users\Johnm\Tower Defense"
python -m venv .venv                    # Create virtual env with Python 3.11
.venv\Scripts\Activate.ps1              # Activate
pip install -r requirements.txt         # Install pygame
```

### Run Game

#### Desktop (Local)
```powershell
python main.py
```

#### Browser (Web)
```powershell
pip install pygbag  # Install pygbag for browser packaging
pygbag "Tower Defense"  # From parent directory of Tower Defense/
```
Then open [http://localhost:8000](http://localhost:8000) in your browser and click to start the game. Note: Browser mode runs with reduced enemy counts for performance.

### Project Structure (Post-Refactor)

The codebase has been modularized for better maintainability:

```
Tower-Defense/
├── main.py                 # Entry point: initializes game and UI
├── core/                   # Game logic
│   ├── game.py            # Game state and orchestration
│   ├── economy.py         # Shop, bench, merge, egrem logic
│   └── wave_manager.py    # Enemy spawning and wave updates
├── models/                # Entity classes (Tower, Enemy)
├── map/                   # Path graph logic
├── data/                  # Game constants (units, tiles, upgrades)
├── ui/                    # User interface
│   ├── renderer.py        # Pygame drawing and camera
│   └── events.py          # Input handling
├── utils/                 # Utilities
│   └── path_generator.py  # Map path generation
├── tests/                 # Unit tests (pytest)
│   ├── test_tower.py
│   ├── test_enemy.py
│   ├── test_path.py
│   └── test_path_sim.py
└── requirements.txt       # Dependencies (pygame, pytest)
```

### Controls
- **Shop mode toggle (T/M/U)** → Cycle towers / map tiles / upgrades
- **Click shop card** → Add to bench (tower, tile, or upgrade depending on mode)
- **Reroll (R)** → Refresh shop (cost: 2 gold)
- **Select tower from bench** → Click to place on grid
- **Select tower for merge** → Click two same-tier towers; click Merge/egrem to confirm
- **Right-click bench tower** → Sell (50% refund)
- **Map tiles**: Select from bench → rotate with A/D or &lt;/&gt; → click grid to place
- **Upgrades**: Buy in shop → select from upgrade bench (click or 1–3 keys) → click tower to apply
- **Right-click upgrade bench** → Deselect upgrade
- **Click placed tower** → Open upgrade dialog (stats, sell, close)
- **Arrow keys / middle-drag** → Pan camera; **mouse wheel** → Zoom
- **Play/Pause / Next Wave / Auto** → Wave controls

---

## Current State & Testing

### ✅ What Works
- **Shop**: 3-way toggle (towers/tiles/upgrades), 5-slot shop, reroll
- **Benches**: Tower bench (10), map tile bench (3), upgrade bench (3)
- **Tower merging**: Tier restrictions, preview, confirm; Egrem (wrong-tier) spawning towers
- **Tile-based expansion**: Purchasable tiles, rotation, path connection, dynamic grid growth
- **Upgrade shop & bench**: Buy upgrades, store in bench, apply to towers (3 capacity each)
- **Upgrade system**: Trait synergies, heat mechanics, 12 upgrade types
- **Enemy system**: 5 types, progressive unlock, debuffs (slow, stun)
- **Wave scaling**: Staggered spawning, auto mode, gold/lives
- **Tower fire types**: Beam, ball, directional, track, overwatch, radius, spawner
- **Camera**: Pan (arrows/middle-drag), zoom (mouse wheel)

### 🟡 Partially Tested
- Tower damage calculations (implemented but balance needs tuning)
- Enemy movement speed and debuff effects
- Upgrade synergies and heat/overheat mechanics
- Egrem spawning balance

### ❌ Major Gaps / Future Features
- **Tower Merge Complexity**: Generic tier progression. Missing unique combinations, merge trees, strategic depth.
- **Enemy Adaptation**: Static types. Missing dynamic response to player strategies.
- **Enemy Difficulty Tiers**: Types don't map to normal/elite/mini-boss/boss/event with tied scaling.
- **Per-Tower Upgrade Capacity**: Currently 3 for all; tune individually for balancing.
- **Performance Optimizations**: Spatial hashing, object pooling for larger maps/enemies.
- **Sound/Music**: Audio effects (volume button is placeholder).
- **Difficulty Modes**: Hard, Hardcore variants.
- **Leaderboard**: High score tracking.

---

## Notes for Future Development

### Performance Considerations
- Enemy movement slowed to every 4 frames (prevents frame-rate dependent speed)
- Can optimize further with spatial hashing for collision detection if enemy count >100

### Balance Tuning Opportunities
- Tower damage values calibrated for ~3 waves of testing
- Enemy spawn rates, density, and wave structure can be adjusted
- Merge bonus percentages (+50% dmg, +1 range) can be tweaked for progression curve

### Code Structure for Additions
- **New Tower Type**: Add to `Tower.BASE_TYPES` dict with stats
- **New Enemy Type**: Add to `Enemy.TYPES` dict, update `spawn_wave()` unlock logic
- **New Wave Mechanic**: Modify `Game.update_wave()` and wave loop in main pygame function

### Dependencies
- **Python 3.11.2** (required for full compatibility)
- **Pygame 2.0+** (2.6.1 currently installed)
- **TD3.PathGenerator** (map path generation algorithm)

---

## Development History

1. **Phase 1**: Created TD3.py PathGenerator prototype with console shop/inventory system
2. **Phase 2**: Added pygame visualization and game loop
3. **Phase 3**: Implemented shop UI, bench system (10 slots), tower placement
4. **Phase 4**: Built tower merging system with parent tracking and tier restriction
5. **Phase 5**: Expanded to 5 tower types with Borg theme and wave-based control
6. **Phase 6**: Implemented 5 enemy types with progressive unlock and difficulty scaling
7. **Phase 7**: Fixed tower rendering (attribute refactor from `.type` → `.base_type`)
8. **Phase 8**: Cleaned up TD3.py (removed unused code), kept only PathGenerator
9. **Phase 9**: Implemented gold economy loops (purchase costs, kill rewards, interest bonuses)
10. **Phase 10**: Added game over screen with restart button and final stats display
11. **Phase 11**: Implemented staggered enemy spawning (queue-based) to prevent overwhelming waves
12. **Phase 12**: Fixed bench-to-grid placement workflow and added bench selling (right-click for 50% refund)
13. **Phase 13**: Tile-based map expansion (purchasable tiles, rotation, path connection, dynamic grid)
14. **Phase 14**: 3-way shop toggle (towers/tiles/upgrades), upgrade shop, upgrade bench, apply-from-bench flow
15. **Phase 15**: Tower upgrade capacity (3 per tower), visual feedback for upgrade application

Current focus: Shop/bench/upgrade flow complete; next priorities are balance tuning and advanced mechanics.

---

## Phased Development Roadmap

### Phase 1: Expanding Grid System (Completed)
**Goal**: Implement tile-based map expansion with shop rotation.
- **Tile-Based Expansion**: Purchasable map tiles (Straight, Left/Right Turn, Loop) with embedded paths.
- **Path Connection**: Tiles must connect to existing paths, with rotation support (0–270°).
- **Shop Rotation**: Cycles between Towers, Map Tiles, Upgrades (T/M/U toggle).
- **Upgrade Shop & Bench**: Buy upgrades from shop, store in 3-slot bench, apply to towers.
- **Status**: Implemented.

### Phase 2: Enemy Complexity Overhaul
**Goal**: Add adaptive enemies with tiered difficulty.
- **Enemy Tiers**: Normal, Elite, Mini-Boss, Boss, Event types.
- **Adaptation System**: Enemies adjust stats based on player strategy profile.
- **Dynamic Scaling**: Stats tied to difficulty tiers, not just wave numbers.
- **Performance**: Precomputed adaptations, lightweight debuff system.

### Phase 3: Tower Merge Depth
**Goal**: Unique merge combinations and synergies.
- **Merge Trees**: Specific parent combinations unlock special towers.
- **Synergy Bonuses**: Multiplicative effects for strategic merges.
- **Evolution System**: Branching progression paths.

### Phase 4: Advanced Mechanics Integration
**Goal**: Polish and balance all systems.
- **Event Waves**: Special enemy compositions and goals.
- **Performance Monitoring**: FPS tracking, optimization passes.
- **Balance Tuning**: Iterative testing of scaling curves.

### Legacy Roadmap (Completed/Outdated)

| Feature / Fix | Status | Notes |
|---------------|--------|-------|
| **Gold on kill + interest mechanic** | ✅ Done | Fully implemented |
| **Staggered enemy spawning** | ✅ Done | Queue-based system active |
| **Game Over + Restart screen** | ✅ Done | With final stats display |
| **Bench placement workflow** | ✅ Done | Click-to-select, place on grid |
| **Sell from bench** | ✅ Done | Right-click for 50% refund |
| **Upgrade system** | ✅ Done | Traits, synergies, heat mechanics |
| **Tile-based expansion** | ✅ Done | Purchasable tiles, rotation, path connection |
| **Upgrade shop & bench** | ✅ Done | 3-way shop, upgrade bench, apply-from-bench flow |
| **Auto wave mode** | ✅ Done | Toggle for automatic progression |
