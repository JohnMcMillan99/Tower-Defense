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
- **5-slot shop** with reroll button
- **10-slot inventory bench** below shop
- Click shop cards to add to bench (cards appear as tower objects)
- Drag towers from bench to grid or to other bench slots
- Reroll cost: 1 gold (not yet fully implemented in wave loop)

#### 2. **Tower Types** (5 Borg-themed variants)

| Tower | Color | Base DMG | Range | Fire Rate | Role |
|-------|-------|----------|-------|-----------|------|
| **Firewall** | Blue | 6 | 3 | 1.0 | Network defense, balanced |
| **Antivirus** | Green | 9 | 2 | 1.0 | High damage, short-range |
| **Encryption** | Purple | 8 | 3 | 1.2 | Fast-firing, medium damage |
| **Monitor** | Orange | 4 | 4 | 1.0 | Long-range, low damage |
| **Validator** | Red | 7 | 3 | 1.0 | Mid-tier specialist |

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

#### 6. **Visual Interface** (Pygame)
- Game grid visualization (3×20 path grid)
- Shop at top with tower cards
- Bench slots displayed below shop
- Control panel with wave controls, pause, volume (mocked)
- Enemy path overlaid on grid
- Tower and enemy rendering with Borg-themed colors
- Status display showing current wave, gold, lives

#### 7. **Game Flow**
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
└── TD3_README.md       # This file
```

### Core Classes

#### `Tower` (lines 340-408)
```python
class Tower:
    BASE_TYPES = {
        "Firewall": {"dmg": 6, "range": 3, "fire_rate": 1.0},
        "Antivirus": {"dmg": 9, "range": 2, "fire_rate": 1.0},
        # ... etc
    }
    
    def __init__(self, tower_type, x, y, parents=None)
    def _calculate_stats(self)
    def merge_towers(tower1, tower2)  # Static method
    def get_merge_tier(self)           # Returns len(parents) // 2
```

#### `Enemy` (lines 275-334)
```python
class Enemy:
    TYPES = {
        "Drone": {"health": 10, "speed": 1.0, "difficulty": 1.0, ...},
        # ... 4 more types
    }
    
    def __init__(self, x, y, enemy_type, wave_num)
    def _calculate_stats(self)  # Scales health based on wave_num
```

#### `Game` (lines 461-705)
- Central state manager
- Manages shop, bench (10 slots), towers on grid, enemies
- Handles merging logic: `select_for_merge()`, `confirm_merge()`, `cancel_merge()`
- Wave spawning: `spawn_wave()` - progressively introduces enemy types
- Wave updates: `update_wave()` - moves enemies, calculates damage

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
- **Firewall** = External defense perimeter
- **Antivirus** = Immune response, concentrated defense
- **Encryption** = Signal jamming, fast interruption
- **Monitor** = Surveillance network, far-reaching coverage
- **Validator** = Authentication checkpoints, selective filtering

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
```powershell
python td_visual.py
```

### Controls
- **Click shop card** → Add to bench
- **Drag bench tower** → Move to grid or other bench slot
- **Select tower** → Highlight for merge (turn green)
- **Select second tower** → Merge preview appears (if same tier)
- **Click Merge button** → Confirm merge
- **Click Cancel** → Discard merge
- **Play/Pause button** → Toggle wave progression
- **Next Wave button** → Skip to next wave

---

## Current State & Testing

### ✅ What Works
- Shop UI fully functional (card selection, bench placement)
- Tower merging logic and UI (tier restrictions, preview, confirm)
- Enemy type system with progressive introduction
- Wave scaling (enemies get harder each wave)
- Pygame rendering (towers render with correct colors, enemies spawn/move)
- Game loop integration (waves progress, enemies spawn at intervals)

### 🟡 Partially Tested
- Tower damage calculations (implemented but not heavily tested against waves)
- Enemy movement speed (implemented, may need tuning)
- Gold economy (not fully connected to gameplay)

### ❌ Not Yet Implemented
- **Gold System**: Killing enemies should reward gold
- **Lives System**: Losing all lives = game over
- **Game Over Screen**: End state UI
- **Sound/Music**: Audio effects (volume button is placeholder)
- **Difficulty Modes**: Hard, Hardcore variants
- **Leaderboard**: High score tracking
- **Tower Targeting**: Currently towers don't actively target enemies (path-based)
- **Ability System**: Special tower abilities on cooldown
- **Map Variations**: Multiple procedural paths

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

Current focus: Core economy and wave systems stable; next priorities are visual polish (projectiles, range preview) and advanced mechanics (tower synergies).

---

## Prioritized Feature Roadmap

| Priority | Feature / Fix | Status | Est. Effort | Notes |
|----------|---------------|--------|-------------|-------|
| **1** | **Gold on kill + interest mechanic** | ✅ Done | Low | Enemies award gold based on difficulty; 10% interest bonus at wave completion |
| **2** | **Projectiles / attack visuals** | 📋 Pending | Medium | Would improve visual feedback when towers shoot |
| **3** | **Staggered enemy spawning** | ✅ Done | Low–Medium | Enemies spawn gradually from queue every 30 frames, preventing overwhelming waves |
| **4** | **Game Over + Restart screen** | ✅ Done | Low | Overlay shows final wave reached and gold earned; click to restart |
| **5** | **Fix bench → grid placement** | ✅ Done | Low | Click bench card to select, then click grid to place (no additional cost) |
| **6** | **Range preview on hover/selection** | 📋 Pending | Medium | Would help players plan tower placement |
| **7** | **Sell from bench** | ✅ Done | Low | Right-click bench card to sell for 50% refund |
| **8** | **Tower upgrade path / synergies** | 📋 Pending | Medium–High | Could add multiplicative bonuses for specific parent combinations |
| **9** | **Enemy death particles / sound** | 📋 Pending | Low–Medium | Would add audio-visual polish to kills |
| **10** | **Persistent high score** | 📋 Pending | Low | Would save best wave reached to encouragereplay |
