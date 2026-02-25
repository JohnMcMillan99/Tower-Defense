import asyncio
import sys
import pygame
from core.game import Game
from ui.renderer import Renderer
from ui.events import EventHandler

# DEBUG: Incremental feature level to find visual bug.
# 0=bare bones, 1=game+shop, 2=+bench, 3=+panel, 4=+grid, 5=+map/upgrade benches,
# 6=+merge preview, 7=+towers/enemies, 8=+dialogs, 9=+previews, 10=+beams,
# 11=+swarm fx, 12=full
FEATURE_LEVEL = 12

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
pygame.init()

# Create game and UI components (minimal when FEATURE_LEVEL 0)
game = Game(web_mode=WEB_MODE) if FEATURE_LEVEL > 0 else None
renderer = Renderer(game, feature_level=FEATURE_LEVEL)
handler = EventHandler(game, renderer) if FEATURE_LEVEL > 0 else None
clock = pygame.time.Clock()
frame = 0

async def main():
    global frame
    running = True
    while running:
        if handler and not handler.running:
            running = False
            break
        frame += 1

        # Handle events
        if handler:
            handler.handle_events(frame)
        else:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            if not running:
                break

        # Update game state (if not paused) - skip when feature level 0
        if FEATURE_LEVEL > 0 and game and not game.paused:
            game.wave_manager.update_wave(frame)

        # Render everything
        renderer.draw(frame)

        # Display and maintain frame rate
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)  # Yield to browser event loop
    # Cleanup
    pygame.quit()

asyncio.run(main())