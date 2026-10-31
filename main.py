import argparse
import asyncio
import sys
import pygame
from core.app import App
from config import log_debug

parser = argparse.ArgumentParser(description="Tower Defense 3: Borg Assimilation")
parser.add_argument("--minimal", action="store_true", help="Use minimal mode (reduced features)")
args = parser.parse_args()
FEATURE_MODE = "minimal" if args.minimal else "full"

WEB_MODE = sys.platform == "emscripten"

if WEB_MODE:
    import platform
    platform.document.body.style.background = "#0a0a0f"
    platform.window.infobox.style.display = "none"

log_debug("Starting pygame initialization", location="main.py")
try:
    pygame.init()
    log_debug("pygame.init() successful", location="main.py")
except Exception as e:
    log_debug("pygame.init() failed", {"error": str(e)}, location="main.py")

log_debug("Creating App", location="main.py")
app = App(web_mode=WEB_MODE, minimal_mode=(FEATURE_MODE == "minimal"))
log_debug("App created", location="main.py")

clock = pygame.time.Clock()
frame = 0


async def main():
    global frame
    log_debug("Main game loop starting", location="main.py")
    try:
        while app.running:
            frame += 1
            if app.game is not None:
                app.game.current_frame = frame
            if frame <= 5:
                log_debug(f"Frame {frame} starting", {"screen": app.screen}, location="main.py")

            try:
                app.handle_events(frame)
            except Exception as e:
                log_debug(f"Frame {frame}: Event handling failed", {"error": str(e)}, location="main.py")
                raise

            try:
                app.update(frame)
            except Exception as e:
                log_debug(f"Frame {frame}: Game state update failed", {"error": str(e)}, location="main.py")
                raise

            try:
                app.draw(frame)
            except Exception as e:
                log_debug(f"Frame {frame}: Rendering failed", {"error": str(e)}, location="main.py")
                raise

            try:
                pygame.display.flip()
                clock.tick(60)
            except Exception as e:
                log_debug(f"Frame {frame}: Display flip failed", {"error": str(e)}, location="main.py")
                raise

            await asyncio.sleep(0)

        log_debug("Main game loop ended normally", location="main.py")
    except Exception as e:
        log_debug("Main game loop crashed", {"error": str(e), "frame": frame}, location="main.py")
        raise
    finally:
        pygame.quit()


asyncio.run(main())
