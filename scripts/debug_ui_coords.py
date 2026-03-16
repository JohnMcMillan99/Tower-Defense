#!/usr/bin/env python3

"""
Debug script to help identify UI coordinate mismatches.
This script logs the positions where UI elements are drawn vs. where clicks are detected.
Run from project root: python scripts/debug_ui_coords.py
"""
import json


def analyze_logs():
    """Analyze the debug logs to find coordinate mismatches."""
    try:
        import os
        log_path = os.path.join(os.path.dirname(__file__), "..", "debug.log")
        with open(log_path, "r") as f:
            lines = f.readlines()

        print("Analyzing debug logs for UI coordinate mismatches...")
        print("=" * 60)

        # Parse logs
        ui_positions = {}
        click_positions = {}
        click_areas = {}

        for line in lines:
            try:
                entry = json.loads(line.strip())
                location = entry.get('location', '')
                message = entry.get('message', '')
                data = entry.get('data', {})

                # Track UI element positions
                if 'Drawing' in message and 'x' in data and 'y' in data:
                    if 'shop toggle' in message:
                        ui_positions['shop_toggle'] = (data['x'], data['y'], data.get('width', 35), data.get('height', 35))
                    elif 'upgrade slot' in message:
                        slot_id = f"upgrade_slot_{data.get('slot_x', 0)}_{data.get('slot_y', 0)}"
                        ui_positions[slot_id] = (data['slot_x'], data['slot_y'], data.get('slot_w', 50), data.get('slot_h', 80))

                # Track click areas
                if 'Click in' in message:
                    area = message.replace('Click in ', '').replace(' area', '')
                    click_areas[area] = True

                # Track click positions
                if message == 'Left click detected':
                    click_positions[len(click_positions)] = (data['mouse_x'], data['mouse_y'])

                # Track specific click checks
                if 'toggle check' in message:
                    ui_positions['shop_toggle_check'] = (data['toggle_x'], data['toggle_y'], data['toggle_w'], data['toggle_h'])

                if 'Checking upgrade slot' in message:
                    slot_check = f"upgrade_slot_check_{data['slot_x']}_{data['slot_y']}"
                    ui_positions[slot_check] = (data['slot_x'], data['slot_y'], data['slot_w'], data['slot_h'])

            except:
                continue

        print(f"Found {len(ui_positions)} UI element positions")
        print(f"Found {len(click_positions)} click positions")
        print(f"Click areas detected: {list(click_areas.keys())}")
        print()

        # Analyze shop toggle
        if 'shop_toggle' in ui_positions and 'shop_toggle_check' in ui_positions:
            draw_pos = ui_positions['shop_toggle']
            check_pos = ui_positions['shop_toggle_check']
            if draw_pos[:2] != check_pos[:2]:
                print("❌ SHOP TOGGLE MISMATCH:")
                print(f"  Drawn at: {draw_pos}")
                print(f"  Click check: {check_pos}")
                print()

        # Analyze upgrade bench
        upgrade_draws = [k for k in ui_positions.keys() if k.startswith('upgrade_slot_') and not k.endswith('_check')]
        upgrade_checks = [k for k in ui_positions.keys() if k.startswith('upgrade_slot_') and k.endswith('_check')]

        print(f"Upgrade slots drawn: {len(upgrade_draws)}")
        print(f"Upgrade slot checks: {len(upgrade_checks)}")

        # Check for mismatches
        mismatches = []
        for draw_key in upgrade_draws:
            draw_pos = ui_positions[draw_key]
            # Find corresponding check
            for check_key in upgrade_checks:
                check_pos = ui_positions[check_key]
                if abs(draw_pos[0] - check_pos[0]) < 10 and abs(draw_pos[1] - check_pos[1]) < 10:
                    if draw_pos != check_pos:
                        mismatches.append((draw_key, draw_pos, check_pos))
                    break

        if mismatches:
            print("❌ UPGRADE SLOT MISMATCHES:")
            for key, draw_pos, check_pos in mismatches:
                print(f"  {key}:")
                print(f"    Drawn: {draw_pos}")
                print(f"    Check: {check_pos}")
        else:
            print("✅ No upgrade slot coordinate mismatches found")

        print()
        print("Recent clicks:")
        for i, (x, y) in list(click_positions.items())[-5:]:  # Last 5 clicks
            print(f"  Click {i}: ({x}, {y})")

    except FileNotFoundError:
        print("No debug.log file found. Set DEBUG=True in config.py and run the game to generate logs.")
    except Exception as e:
        print(f"Error analyzing logs: {e}")

if __name__ == "__main__":
    analyze_logs()