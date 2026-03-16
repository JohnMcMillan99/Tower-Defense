#!/usr/bin/env python3

"""
Test script to run the full game loop and identify where the solid color screen issue occurs.
This tests pygame rendering and game loop execution.
"""

import sys
import traceback
import pygame
import asyncio

def test_full_game_loop(feature_level=5):
    """Test running the full game loop with pygame."""
    print(f"Testing full game loop with FEATURE_LEVEL = {feature_level}")

    try:
        # Initialize pygame first
        print("Initializing pygame...")
        pygame.init()
        print("Pygame initialized")

        # Import and create game components
        print("Importing game components...")
        from core.game import Game
        from ui.renderer import Renderer
        from ui.events import EventHandler

        print("Creating Game instance...")
        game = Game(web_mode=False, feature_level=feature_level)
        print("Game created")

        print("Creating Renderer instance...")
        renderer = Renderer(game)
        print("Renderer created")

        print("Creating EventHandler instance...")
        handler = EventHandler(game, renderer)
        print("EventHandler created")

        # Try to run a few frames
        print("Starting game loop test...")
        clock = pygame.time.Clock()
        frame = 0
        max_frames = 10

        while handler.running and frame < max_frames:
            frame += 1
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

        print(f"Game loop test completed successfully after {frame} frames")
        pygame.quit()
        return True

    except Exception as e:
        print(f"Game loop test failed: {e}")
        traceback.print_exc()
        try:
            pygame.quit()
        except:
            pass
        return False

def main():
    print("Tower Defense Runtime Testing")
    print("This script tests the full game loop to find where the solid color screen occurs.")

    # Test with current default level
    success = test_full_game_loop(feature_level=5)

    if success:
        print("\nSUCCESS: Game loop runs without crashes")
        print("The solid color screen issue may be:")
        print("1. Visual rendering issue (wrong colors/shapes)")
        print("2. Issue only occurs after longer gameplay")
        print("3. Web-specific issue (try running in browser)")
    else:
        print("\nFAILURE: Game loop crashed")
        print("Check the stack trace above for the failure point.")

if __name__ == "__main__":
    main()