import argparse
import asyncio
import sys
import pygame
from core.game import Game
from ui.renderer import Renderer
from ui.events import EventHandler
from config import log_debug

# Parse --minimal flag for reduced features (debugging/performance)
parser = argparse.ArgumentParser(description="Tower Defense 3: Borg Assimilation")
parser.add_argument("--minimal", action="store_true", help="Use minimal mode (reduced features)")
args = parser.parse_args()
FEATURE_MODE = "minimal" if args.minimal else "full"

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
log_debug("Starting pygame initialization", location="main.py")
try:
    pygame.init()
    log_debug("pygame.init() successful", location="main.py")
except Exception as e:
    log_debug("pygame.init() failed", {"error": str(e)}, location="main.py")

# Create game and UI components
log_debug("Creating Game instance", location="main.py")
try:
    game = Game(web_mode=WEB_MODE, minimal_mode=(FEATURE_MODE == "minimal"))
    log_debug("Game instance created successfully", location="main.py")
except Exception as e:
    log_debug("Game creation failed", {"error": str(e)}, location="main.py")
    raise

log_debug("Creating Renderer instance", location="main.py")
try:
    renderer = Renderer(game)
    log_debug("Renderer instance created successfully", location="main.py")
except Exception as e:
    log_debug("Renderer creation failed", {"error": str(e)}, location="main.py")
    raise

log_debug("Creating EventHandler instance", location="main.py")
try:
    handler = EventHandler(game, renderer)
    log_debug("EventHandler instance created successfully", location="main.py")
except Exception as e:
    log_debug("EventHandler creation failed", {"error": str(e)}, location="main.py")
    raise

clock = pygame.time.Clock()
frame = 0


async def main():
    global frame
    log_debug("Main game loop starting", location="main.py")
    try:
        while handler.running:
            frame += 1
            if frame <= 5:
                log_debug(f"Frame {frame} starting", location="main.py")

            # Handle events
            try:
                handler.handle_events(frame)
                if frame <= 5:
                    log_debug(f"Frame {frame}: Events handled", location="main.py")
            except Exception as e:
                log_debug(f"Frame {frame}: Event handling failed", {"error": str(e)}, location="main.py")
                raise

            # Update game state (if not paused)
            if not game.paused:
                try:
                    game.wave_manager.update_wave(frame)
                    if frame <= 5:
                        log_debug(f"Frame {frame}: Game state updated", location="main.py")
                except Exception as e:
                    log_debug(f"Frame {frame}: Game state update failed", {"error": str(e)}, location="main.py")
                    raise

            # Render everything
            try:
                renderer.draw(frame)
                if frame <= 5:
                    log_debug(f"Frame {frame}: Rendering completed", location="main.py")
            except Exception as e:
                log_debug(f"Frame {frame}: Rendering failed", {"error": str(e)}, location="main.py")
                raise

            # Display and maintain frame rate
            try:
                pygame.display.flip()
                clock.tick(60)
                if frame <= 5:
                    log_debug(f"Frame {frame}: Display flipped", location="main.py")
            except Exception as e:
                log_debug(f"Frame {frame}: Display flip failed", {"error": str(e)}, location="main.py")
                raise

            await asyncio.sleep(0)  # Yield to browser event loop

        log_debug("Main game loop ended normally", location="main.py")
    except Exception as e:
        log_debug("Main game loop crashed", {"error": str(e), "frame": frame}, location="main.py")
        raise
    finally:
        pygame.quit()


asyncio.run(main())
