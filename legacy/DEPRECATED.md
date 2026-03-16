# Deprecated Code

This folder contains legacy code that has been superseded by the refactored codebase.

## td_visual.py

**Status**: Deprecated. Use `main.py` instead.

The monolithic `td_visual.py` (1800+ lines) has been replaced by the modular structure:
- `main.py` - Entry point
- `core/game.py` - Game state
- `core/economy.py` - Shop, bench, merge logic
- `core/wave_manager.py` - Wave spawning
- `ui/renderer.py` - Pygame rendering
- `ui/events.py` - Input handling

This file is kept for reference only and should not be used.
