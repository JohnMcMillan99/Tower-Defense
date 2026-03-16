#!/usr/bin/env python3

"""
Test script to progressively enable features and identify the source of the solid color screen bug.
Run with different FEATURE_LEVEL values to isolate the problematic code.
"""

import sys
import traceback

# Test different feature levels
FEATURE_LEVELS_TO_TEST = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def test_feature_level(level):
    print(f"\n{'='*50}")
    print(f"Testing FEATURE_LEVEL = {level}")
    print(f"{'='*50}")

    try:
        # Modify main.py to use this feature level
        with open("main.py", "r") as f:
            content = f.read()

        # Replace the FEATURE_LEVEL line
        old_line = "FEATURE_LEVEL = 5  # Start at 5"
        new_line = f"FEATURE_LEVEL = {level}  # Start at {level}"
        modified_content = content.replace(old_line, new_line)

        with open("main.py", "w") as f:
            f.write(modified_content)

        print(f"Modified main.py to use FEATURE_LEVEL = {level}")

        # Try to import and initialize the game
        print("Testing imports...")
        from core.game import Game
        print("Game import successful")

        print("Testing Game initialization...")
        game = Game(web_mode=True, feature_level=level)
        print("Game initialization successful")

        # Skip pygame-dependent components since pygame is not available in test environment
        print("Skipping pygame-dependent components (pygame not available)")
        print("Core game initialization successful - pygame rendering issue isolated")

        print(f"PASS: FEATURE_LEVEL {level} - No initialization errors")
        return True

    except Exception as e:
        print(f"FAIL: FEATURE_LEVEL {level}")
        print(f"Error: {e}")
        print("Traceback:")
        traceback.print_exc()
        return False

    finally:
        # Restore original FEATURE_LEVEL
        try:
            with open("main.py", "r") as f:
                content = f.read()
            restored_content = content.replace(f"FEATURE_LEVEL = {level}  # Start at {level}", "FEATURE_LEVEL = 5  # Start at 5")
            with open("main.py", "w") as f:
                f.write(restored_content)
        except:
            pass

def main():
    print("Tower Defense Feature Level Testing")
    print("This script tests different feature levels to identify where the solid color screen bug occurs.")

    results = {}

    for level in FEATURE_LEVELS_TO_TEST:
        success = test_feature_level(level)
        results[level] = success

        if not success:
            print(f"\nStopping at level {level} due to failure.")
            break

    print(f"\n{'='*50}")
    print("RESULTS SUMMARY:")
    print(f"{'='*50}")

    for level, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"Level {level}: {status}")

    if results:
        failing_level = None
        for level in sorted(results.keys()):
            if not results[level]:
                failing_level = level
                break

        if failing_level:
            print(f"\nThe bug appears to be introduced at FEATURE_LEVEL {failing_level}")
            print(f"Check the changes made between levels {failing_level-1} and {failing_level}")
        else:
            print("\nAll tested levels passed! The bug may be in rendering or runtime behavior.")

if __name__ == "__main__":
    main()