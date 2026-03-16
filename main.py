import asyncio
import sys
import pygame
from core.game import Game
from ui.renderer import Renderer
from ui.events import EventHandler

# Feature toggle system (1-10 scale) - dial up/down to isolate issues
FEATURE_LEVEL = 10  # All features enabled by default

# Feature levels:
# 1: Basic game (no new features)
# 2: + XP/SPL state variables only
# 3: + Enemy base_xp
# 4: + Level-up logic
# 5: + XP on kill/clear
# 6: + Economy SPL filtering
# 7: + New tile variants
# 8: + Visual tier effects
# 9: + Enemy black+green visuals
# 10: + SPL/XP UI display

# Detect web/browser mode (pygbag runs on emscripten)
WEB_MODE = sys.platform == "emscripten"

# In browser: match page background and hide "Ready to start" overlay so game canvas is visible
if WEB_MODE:
    import platform
    platform.document.body.style.background = "#0a0a0f"
    # Template hides infobox after shell.source(main), but that never runs (game loop blocks).
    # Hide it here so the game canvas underneath is revealed when user clicks.
    platform.window.infobox.style.display = "none"

# Initialize pygame
# #region agent log
import json
import time
def log_debug(msg, data=None):
    log_entry = {
        "sessionId": "b53f80",
        "id": f"log_{int(time.time()*1000)}_main",
        "timestamp": int(time.time() * 1000),
        "location": "main.py",
        "message": msg,
        "data": data or {},
        "runId": "black_screen_debug",
        "hypothesisId": "pygame_init_failure"
    }
    try:
        with open("debug-b53f80.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except:
        pass
# #endregion

log_debug("Starting pygame initialization")
try:
    pygame.init()
    log_debug("pygame.init() successful")
except Exception as e:
    log_debug("pygame.init() failed", {"error": str(e)})

# Create game and UI components
log_debug("Creating Game instance")
try:
    game = Game(web_mode=WEB_MODE, feature_level=FEATURE_LEVEL)
    log_debug("Game instance created successfully")
except Exception as e:
    log_debug("Game creation failed", {"error": str(e)})

log_debug("Creating Renderer instance")
try:
    renderer = Renderer(game)
    log_debug("Renderer instance created successfully")
except Exception as e:
    log_debug("Renderer creation failed", {"error": str(e)})

log_debug("Creating EventHandler instance")
try:
    handler = EventHandler(game, renderer)
    log_debug("EventHandler instance created successfully")
except Exception as e:
    log_debug("EventHandler creation failed", {"error": str(e)})
clock = pygame.time.Clock()
frame = 0

async def main():
    global frame
    log_debug("Main game loop starting")
    try:
        while handler.running:
            frame += 1
            if frame <= 5:  # Only log first 5 frames
                log_debug(f"Frame {frame} starting")

            # Handle events
            try:
                handler.handle_events(frame)
                if frame <= 5:
                    log_debug(f"Frame {frame}: Events handled")
            except Exception as e:
                log_debug(f"Frame {frame}: Event handling failed", {"error": str(e)})

            # Update game state (if not paused)
            if not game.paused:
                try:
                    game.wave_manager.update_wave(frame)
                    if frame <= 5:
                        log_debug(f"Frame {frame}: Game state updated")
                except Exception as e:
                    log_debug(f"Frame {frame}: Game state update failed", {"error": str(e)})

            # Render everything
            try:
                renderer.draw(frame)
                if frame <= 5:
                    log_debug(f"Frame {frame}: Rendering completed")
            except Exception as e:
                log_debug(f"Frame {frame}: Rendering failed", {"error": str(e)})

            # Display and maintain frame rate
            try:
                pygame.display.flip()
                clock.tick(60)
                if frame <= 5:
                    log_debug(f"Frame {frame}: Display flipped")
            except Exception as e:
                log_debug(f"Frame {frame}: Display flip failed", {"error": str(e)})

            await asyncio.sleep(0)  # Yield to browser event loop

        log_debug("Main game loop ended normally")
    except Exception as e:
        log_debug("Main game loop crashed", {"error": str(e), "frame": frame})
        raise
    # Cleanup
    pygame.quit()

asyncio.run(main())