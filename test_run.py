#!/usr/bin/env python3

import asyncio
import sys
import pygame
from core.game import Game
from ui.renderer import Renderer
from ui.events import EventHandler

print("Starting test run...")

try:
    # Detect web/browser mode (pygbag runs on emscripten)
    WEB_MODE = sys.platform == "emscripten"
    print(f"Web mode: {WEB_MODE}")

    # Initialize pygame
    pygame.init()
    print("Pygame initialized")

    # Create game and UI components
    print("Creating game...")
    game = Game(web_mode=WEB_MODE)
    print("Game created")

    print("Creating renderer...")
    renderer = Renderer(game)
    print("Renderer created")

    print("Creating event handler...")
    handler = EventHandler(game, renderer)
    print("Event handler created")

    clock = pygame.time.Clock()
    frame = 0

    print("Starting main loop...")

    async def main():
        global frame
        try:
            while handler.running and frame < 5:  # Limit to 5 frames for testing
                frame += 1
                print(f"Frame {frame}")

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

            print("Game loop ended normally")
        except Exception as e:
            print(f"Error in main loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            pygame.quit()

    print("Running asyncio...")
    asyncio.run(main())

except Exception as e:
    print(f"Error during startup: {e}")
    import traceback
    traceback.print_exc()