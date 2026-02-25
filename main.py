import asyncio
import sys
import pygame
from core.game import Game
from ui.renderer import Renderer
from ui.events import EventHandler

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

# Create game and UI components
game = Game(web_mode=WEB_MODE)
renderer = Renderer(game)
handler = EventHandler(game, renderer)
clock = pygame.time.Clock()
frame = 0

async def main():
    global frame
    while handler.running:
        frame += 1

        # Handle events
        handler.handle_events(frame)

        # Update game state (if not paused)
        if not game.paused:
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