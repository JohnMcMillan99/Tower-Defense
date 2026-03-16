#!/usr/bin/env python3

"""
Quick test script to run the game for just a few frames and see where it fails.
"""

import sys
import pygame
import asyncio
import traceback

def test_quick_run():
    """Run the game for just 3 frames to see where it fails."""
    print("Testing quick game run...")

    try:
        # Import components
        from core.game import Game
        from ui.renderer import Renderer
        from ui.events import EventHandler

        print("Components imported successfully")

        # Initialize pygame
        pygame.init()
        print("Pygame initialized")

        # Create game
        game = Game(web_mode=False, feature_level=10)
        print("Game created")

        # Create renderer
        renderer = Renderer(game)
        print("Renderer created")

        # Create event handler
        handler = EventHandler(game, renderer)
        print("Event handler created")

        # Create clock
        clock = pygame.time.Clock()

        print("Starting 3-frame test...")

        # Run for 3 frames
        for frame in range(1, 4):
            print(f"Running frame {frame}...")

            # Handle events
            handler.handle_events(frame)

            # Update game state
            if not game.paused:
                game.wave_manager.update_wave(frame)

            # Render
            renderer.draw(frame)

            # Flip display
            pygame.display.flip()
            clock.tick(60)

            print(f"Frame {frame} completed successfully")

        print("Test completed successfully!")
        pygame.quit()
        return True

    except Exception as e:
        print(f"Test failed with error: {e}")
        traceback.print_exc()
        try:
            pygame.quit()
        except:
            pass
        return False

if __name__ == "__main__":
    success = test_quick_run()
    if success:
        print("Game runs successfully for 3 frames")
    else:
        print("Game fails within 3 frames - check logs for details")