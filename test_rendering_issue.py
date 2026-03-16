#!/usr/bin/env python3

"""
Test script to isolate the pygame rendering issue causing the solid color screen.
This focuses on the rendering components that are failing.
"""

import sys
import traceback

def test_pygame_rendering():
    """Test pygame rendering initialization and basic drawing."""
    print("Testing pygame rendering components...")

    try:
        # Test basic pygame import and init
        print("1. Testing pygame import...")
        import pygame
        print("   ✓ pygame imported successfully")

        print("2. Testing pygame.init()...")
        pygame.init()
        print("   ✓ pygame.init() successful")

        print("3. Testing display mode...")
        screen = pygame.display.set_mode((800, 600))
        print("   ✓ display mode set successfully")

        print("4. Testing basic drawing...")
        screen.fill((100, 100, 100))  # Fill with gray
        pygame.draw.rect(screen, (255, 0, 0), (100, 100, 100, 100))  # Draw red rectangle
        pygame.display.flip()
        print("   ✓ basic drawing successful")

        print("5. Testing font loading...")
        try:
            font = pygame.font.SysFont("consolas", 16)
            text_surface = font.render("Test Text", True, (255, 255, 255))
            screen.blit(text_surface, (200, 200))
            pygame.display.flip()
            print("   ✓ font rendering successful")
        except Exception as e:
            print(f"   ✗ font rendering failed: {e}")
            # Try fallback
            try:
                font = pygame.font.Font(None, 16)
                text_surface = font.render("Test Text", True, (255, 255, 255))
                screen.blit(text_surface, (200, 200))
                pygame.display.flip()
                print("   ✓ fallback font rendering successful")
            except Exception as e2:
                print(f"   ✗ fallback font also failed: {e2}")

        # Clean up
        pygame.quit()
        print("6. pygame.quit() successful")

        return True

    except Exception as e:
        print(f"❌ PYGAME RENDERING TEST FAILED")
        print(f"Error: {e}")
        print("Traceback:")
        traceback.print_exc()
        return False

def test_game_renderer():
    """Test the actual game renderer components."""
    print("\nTesting game renderer components...")

    try:
        # Import game components
        print("1. Testing game imports...")
        from core.game import Game
        print("   ✓ Game imported")

        print("2. Testing game initialization...")
        game = Game(web_mode=True, feature_level=1)  # Start with minimal features
        print("   ✓ Game initialized")

        print("3. Testing renderer import...")
        from ui.renderer import Renderer
        print("   ✓ Renderer imported")

        print("4. Testing renderer initialization...")
        renderer = Renderer(game)
        print("   ✓ Renderer initialized")

        print("5. Testing basic draw call...")
        # This would normally require a pygame display, but let's see what happens
        try:
            renderer.draw(0)  # Try to draw frame 0
            print("   ✓ Basic draw call successful")
        except Exception as e:
            print(f"   ✗ Draw call failed: {e}")
            # This might be expected if pygame display isn't set up properly

        return True

    except Exception as e:
        print(f"❌ GAME RENDERER TEST FAILED")
        print(f"Error: {e}")
        print("Traceback:")
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("PYGAME RENDERING ISSUE ISOLATION TEST")
    print("=" * 60)
    print("This test isolates the solid color screen bug to pygame rendering components.")

    # Test 1: Basic pygame functionality
    pygame_ok = test_pygame_rendering()

    # Test 2: Game renderer components
    game_renderer_ok = test_game_renderer()

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)

    if pygame_ok and game_renderer_ok:
        print("✅ All rendering tests passed - issue may be in main loop or event handling")
    elif not pygame_ok:
        print("❌ Issue is in basic pygame functionality")
        print("   Possible causes:")
        print("   - pygame installation issues")
        print("   - display/driver problems")
        print("   - font loading failures")
    elif not game_renderer_ok:
        print("❌ Issue is in game renderer components")
        print("   Possible causes:")
        print("   - Renderer initialization failures")
        print("   - Surface creation issues")
        print("   - Font loading in renderer")
        print("   - Visual effects (tier effects, enemy rendering)")

    print("\nNEXT STEPS:")
    print("1. Check pygame installation: pip install pygame")
    print("2. Test on different display/driver")
    print("3. Check font availability")
    print("4. Try web mode if desktop fails")

if __name__ == "__main__":
    main()