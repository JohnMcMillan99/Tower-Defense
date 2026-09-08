"""DroneData — comparable unit records for Sort Directive orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


# Base combat weight by enemy type (used for power sort keys)
TYPE_POWER = {
    "Drone": 10,
    "Scout": 12,
    "Harvester": 18,
    "Adaptor": 22,
    "Assimilator": 30,
}

TYPE_SPEED = {
    "Drone": 10,
    "Scout": 14,
    "Harvester": 8,
    "Adaptor": 11,
    "Assimilator": 9,
}

TYPE_ARMOR = {
    "Drone": 0,
    "Scout": 0,
    "Harvester": 1,
    "Adaptor": 1,
    "Assimilator": 2,
}


@dataclass(order=True)
class DroneData:
    """One planned enemy in the run pool. Sort keys use power then type name."""

    power: int
    enemy_type: str = field(compare=False)
    speed: int = field(default=10, compare=False)
    armor: int = field(default=0, compare=False)
    traits: Tuple[str, ...] = field(default_factory=tuple, compare=False)
    value: int = field(default=1, compare=False)
    origin_wave: int = field(default=1, compare=False)

    @classmethod
    def from_type(cls, enemy_type: str, wave_num: int = 1, noise: int = 0) -> "DroneData":
        et = enemy_type if enemy_type in TYPE_POWER else "Drone"
        base = TYPE_POWER[et]
        # Wave scales power so later-origin units sort higher before directive reorders
        power = base + (wave_num - 1) * 2 + int(noise)
        return cls(
            power=power,
            enemy_type=et,
            speed=TYPE_SPEED.get(et, 10),
            armor=TYPE_ARMOR.get(et, 0),
            traits=(et.lower(),),
            value=max(1, TYPE_POWER[et] // 10),
            origin_wave=wave_num,
        )

    def to_dict(self):
        return {
            "type": self.enemy_type,
            "power": self.power,
            "speed": self.speed,
            "armor": self.armor,
            "traits": list(self.traits),
            "value": self.value,
            "origin_wave": self.origin_wave,
        }
