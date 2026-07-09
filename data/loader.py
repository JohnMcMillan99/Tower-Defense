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
        self.traits = {}
        self.trait_bonuses = {}
        self.trait_rules = {}
        self.hybrid_trees = []
        self.pure_naming_rules = {}
        self.augment_rules = {}
        self.resistance_tables = {}
        self.event_waves = []
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
                    self.resistance_tables = data.get('resistance_tables', {})
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

            # Load traits data
            traits_file = os.path.join(self.yaml_dir, 'traits.yaml')
            if os.path.exists(traits_file):
                with open(traits_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.traits = data.get('traits', {})
                    self.trait_bonuses = data.get('trait_bonuses', {})
                    self.trait_rules = data.get('trait_rules', {})
            else:
                print(f"Warning: {traits_file} not found, using fallback data")
                self._load_fallback_traits()

            # Extract hybrid_trees and pure_naming_rules from merges.yaml top-level
            merges_file = os.path.join(self.yaml_dir, 'merges.yaml')
            if os.path.exists(merges_file):
                with open(merges_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.hybrid_trees = data.get('hybrid_trees', [])
                    self.pure_naming_rules = data.get('pure_naming_rules', {})

            # Load augment rules
            augment_file = os.path.join(self.yaml_dir, 'augment_rules.yaml')
            if os.path.exists(augment_file):
                with open(augment_file, 'r') as f:
                    self.augment_rules = yaml.safe_load(f) or {}

            # Load event waves
            event_file = os.path.join(self.yaml_dir, 'event_waves.yaml')
            if os.path.exists(event_file):
                with open(event_file, 'r') as f:
                    data = yaml.safe_load(f)
                    self.event_waves = data.get('event_waves', [])

        except Exception as e:
            print(f"Error loading YAML data: {e}")
            self._load_fallback_data()

    def _load_fallback_towers(self):
        """Fallback tower data if YAML fails to load (Borg-themed names)."""
        self.towers = {
            "Neural Processor": {
                "dmg": 6, "range": 2, "fire_rate": 1, "fire_type": "TargetBeam",
                "traits": ["switch", "logic"], "base_cost": 3
            },
            "Plasma Capacitor": {
                "dmg": 10, "range": 2, "fire_rate": 4, "fire_type": "Ball",
                "traits": ["charge", "burst"], "base_cost": 4
            },
            "Thermal Regulator": {
                "dmg": 4, "range": 3, "fire_rate": 2, "fire_type": "DirectionalBeam",
                "traits": ["resist", "heat"], "base_cost": 3
            },
            "Signal Router": {
                "dmg": 7, "range": 4, "fire_rate": 2, "fire_type": "Track",
                "traits": ["block", "flow"], "base_cost": 4
            },
            "Quantum Field Gen": {
                "dmg": 2, "range": 99, "fire_rate": 10, "fire_type": "Overwatch",
                "traits": ["filter", "magnetic"], "base_cost": 5
            },
            "Nanite Swarm": {
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
                {"id": "tower_pool_neural_processor", "cost": 300, "effect": "add_tower Neural Processor"}
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

    def _load_fallback_traits(self):
        """Fallback trait data if YAML fails to load."""
        self.traits = {}
        self.trait_bonuses = {
            "pure_lineage": {"dmg_mult": 2.0, "range_bonus": 2, "fire_rate_mult": 1.5, "purity_requirement": 100},
            "exponential_bonus": {"dmg_mult": 1.0, "stack_mult": 1.25},
            "mastery": {"dmg_mult": 1.5, "resistance": 0.8},
            "apex": {"dmg_mult": 2.0, "immunity": ["enemy_adaptation"]},
            "hybrid": {"dmg_mult": 0.8, "adaptation_penalty": 1.5},
            "hybrid_exposure": {"enemy_speed_boost": 0.2, "enemy_resistance": 0.3},
        }
        self.trait_rules = {
            "purity_generation": {
                "threshold_100": ["pure_lineage", "exponential_bonus"],
                "threshold_80": ["partial_pure"],
                "threshold_50": ["hybrid_penalty"],
                "threshold_0": ["impure"],
            },
            "merge_type_detection": {"pure": "all_parents_same_type", "hybrid": "mixed_parent_types"},
            "naming_conventions": {
                "pure": {"gen1": "{base_type} Enhanced", "gen2": "Advanced {base_type}", "gen3": "{base_type} Apex"},
                "hybrid": {},
            },
        }
        self.hybrid_trees = [
            {"parents": ["Thermal Regulator", "Plasma Capacitor"], "result": "Thermal Plasma Core",
             "dmg": 7, "range": 3, "fire_rate": 3, "fire_type": "Ball", "traits": ["thermal_plasma", "hybrid"]},
            {"parents": ["Neural Processor", "Plasma Capacitor"], "result": "Cortex Assimilator",
             "dmg": 8, "range": 2, "fire_rate": 2, "fire_type": "TargetBeam", "traits": ["neural_plasma", "hybrid"]},
            {"parents": ["Thermal Regulator", "Signal Router"], "result": "Thermal Router",
             "dmg": 5, "range": 4, "fire_rate": 2, "fire_type": "DirectionalBeam", "traits": ["thermal_signal", "hybrid"]},
            {"parents": ["Quantum Field Gen", "Plasma Capacitor"], "result": "Quantum Burst Engine",
             "dmg": 6, "range": 50, "fire_rate": 6, "fire_type": "Overwatch", "traits": ["quantum_plasma", "hybrid"]},
            {"parents": ["Neural Processor", "Quantum Field Gen"], "result": "Neural Field Generator",
             "dmg": 4, "range": 50, "fire_rate": 5, "fire_type": "TargetBeam", "traits": ["neural_quantum", "hybrid"]},
        ]
        self.pure_naming_rules = {
            "gen1": "{base_type} Enhanced",
            "gen2": "Advanced {base_type}",
            "gen3": "{base_type} Apex",
        }

    def _load_fallback_data(self):
        """Load all fallback data."""
        self._load_fallback_towers()
        self._load_fallback_enemies()
        self._load_fallback_meta_unlocks()
        self._load_fallback_assimilators()
        self._load_fallback_traits()

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

    def get_traits_data(self):
        """Get all trait definitions."""
        return self.traits

    def get_trait_tags(self, trait_name):
        """Get trait tags for a specific trait."""
        return self.traits.get(trait_name, [])

    def get_trait_bonuses(self):
        """Get trait bonus definitions."""
        return self.trait_bonuses

    def get_trait_rules(self):
        """Get trait rule definitions."""
        return self.trait_rules

    def get_hybrid_trees(self):
        """Get hybrid merge tree definitions."""
        return self.hybrid_trees

    def get_pure_naming_rules(self):
        """Get pure tower naming convention rules."""
        return self.pure_naming_rules

    def get_augment_rules(self):
        """Get augment/corruption rule definitions."""
        return self.augment_rules

    def get_resistance_tables(self):
        """Get enemy resistance table definitions."""
        return self.resistance_tables

    def get_event_waves(self):
        """Get event wave definitions."""
        return self.event_waves

    def get_event_wave(self, wave_num):
        """Get event wave config for a specific wave number, or None."""
        for ew in self.event_waves:
            if ew.get("wave") == wave_num:
                return ew
        return None

    def get_tower_types(self):
        """Get list of all tower types."""
        return list(self.towers.keys())

    def get_enemy_types(self):
        """Get list of all enemy types."""
        return list(self.enemies.keys())