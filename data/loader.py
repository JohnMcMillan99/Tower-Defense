import os

# pygbag compatibility - YAML may not be available in browser
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

class DataLoader:
    """Loads game data from YAML files with fallback to Python dicts."""

    def __init__(self):
        self.yaml_dir = os.path.join(os.path.dirname(__file__), 'yaml')
        self.towers = {}
        self.enemies = {}
        self.meta_unlocks = {}
        self.assimilators = {}
        self._load_data()

    def _load_data(self):
        """Load all YAML data files."""
        if not YAML_AVAILABLE:
            print("YAML not available, using fallback data")
            self._load_fallback_data()
            return

        try:
            # Load towers data
            towers_file = os.path.join(self.yaml_dir, 'merges.yaml')
            if os.path.exists(towers_file):
                with open(towers_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.towers = data.get('towers', {})
            else:
                print(f"Warning: {towers_file} not found, using fallback data")
                self._load_fallback_towers()

            # Load enemies data
            enemies_file = os.path.join(self.yaml_dir, 'enemies.yaml')
            if os.path.exists(enemies_file):
                with open(enemies_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.enemies = data.get('enemies', {})
            else:
                print(f"Warning: {enemies_file} not found, using fallback data")
                self._load_fallback_enemies()

            # Load meta unlocks data
            meta_file = os.path.join(self.yaml_dir, 'meta_unlocks.yaml')
            if os.path.exists(meta_file):
                with open(meta_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.meta_unlocks = data.get('meta_unlocks', {})
            else:
                print(f"Warning: {meta_file} not found, using fallback data")
                self._load_fallback_meta_unlocks()

            # Load assimilators data
            assimilators_file = os.path.join(self.yaml_dir, 'assimilators.yaml')
            if os.path.exists(assimilators_file):
                with open(assimilators_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.assimilators = data.get('assimilators', {})
            else:
                print(f"Warning: {assimilators_file} not found, using fallback data")
                self._load_fallback_assimilators()

        except Exception as e:
            print(f"Error loading YAML data: {e}")
            self._load_fallback_data()

    def _load_fallback_towers(self):
        """Fallback tower data if YAML fails to load."""
        self.towers = {
            "Oscillator": {
                "dmg": 6, "range": 2, "fire_rate": 1, "fire_type": "TargetBeam",
                "traits": ["switch", "logic"], "base_cost": 3
            },
            "Resistor": {
                "dmg": 10, "range": 2, "fire_rate": 4, "fire_type": "Ball",
                "traits": ["charge", "burst"], "base_cost": 4
            },
            "Capacitor": {
                "dmg": 4, "range": 3, "fire_rate": 2, "fire_type": "DirectionalBeam",
                "traits": ["resist", "heat"], "base_cost": 3
            },
            "Inductor": {
                "dmg": 7, "range": 4, "fire_rate": 2, "fire_type": "Track",
                "traits": ["block", "flow"], "base_cost": 4
            },
            "Diode": {
                "dmg": 2, "range": 99, "fire_rate": 10, "fire_type": "Overwatch",
                "traits": ["filter", "magnetic"], "base_cost": 5
            },
            "Transistor": {
                "dmg": 0, "range": 0, "fire_rate": 0, "fire_type": "Spawner",
                "traits": ["egrem", "spawner"], "base_cost": 6
            }
        }

    def _load_fallback_enemies(self):
        """Fallback enemy data if YAML fails to load."""
        self.enemies = {
            "Drone": {"health": 10, "speed": 10, "difficulty": 1, "latch_eligible": False, "first_wave": 1},
            "Scout": {"health": 8, "speed": 6, "difficulty": 1, "latch_eligible": False, "first_wave": 3},
            "Harvester": {"health": 15, "speed": 12, "difficulty": 2, "latch_eligible": False, "first_wave": 5},
            "Adaptor": {"health": 20, "speed": 8, "difficulty": 2, "latch_eligible": False, "first_wave": 7},
            "Assimilator": {"health": 25, "speed": 10, "difficulty": 3, "latch_eligible": True, "first_wave": 9}
        }

    def _load_fallback_meta_unlocks(self):
        """Fallback meta unlocks data if YAML fails to load."""
        self.meta_unlocks = {
            "tier_1": [
                {"id": "bench_slot_1", "cost": 100, "effect": "bench_slots +1"},
                {"id": "reroll_cheap", "cost": 150, "effect": "reroll_cost 1"}
            ],
            "tier_2": [
                {"id": "tower_pool_oscillator", "cost": 300, "effect": "add_tower Oscillator"}
            ],
            "tier_3": [
                {"id": "latch_resist", "cost": 500, "effect": "latch_integrity_drain -0.1"}
            ]
        }

    def _load_fallback_assimilators(self):
        """Fallback assimilator data if YAML fails to load."""
        self.assimilators = {
            "chance_base": 0.4,
            "assimilate_time": 30,
            "stack_mult": {3: 1.2, 5: 1.5}
        }

    def _load_fallback_data(self):
        """Load all fallback data."""
        self._load_fallback_towers()
        self._load_fallback_enemies()
        self._load_fallback_meta_unlocks()
        self._load_fallback_assimilators()

    def get_tower_data(self, tower_type):
        """Get tower data by type."""
        return self.towers.get(tower_type, {})

    def get_enemy_data(self, enemy_type):
        """Get enemy data by type."""
        return self.enemies.get(enemy_type, {})

    def get_meta_unlocks(self):
        """Get all meta unlocks."""
        return self.meta_unlocks

    def get_assimilator_data(self):
        """Get assimilator configuration data."""
        return self.assimilators

    def get_tower_types(self):
        """Get list of all tower types."""
        return list(self.towers.keys())

    def get_enemy_types(self):
        """Get list of all enemy types."""
        return list(self.enemies.keys())