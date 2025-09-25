from enum import Enum
from typing import Optional, List, cast

from sc2.ids.unit_typeid import UnitTypeId
from sharpy.combat.group_combat_manager import GroupCombatManager
from sharpy.interfaces import IGatherPointSolver, IZoneManager, IEnemyUnitsManager, IGameAnalyzer, ICombatManager
from sharpy.managers.extensions import GameAnalyzer
from sharpy.plans.acts import ActBase
from sharpy.managers.extensions.game_states.advantage import (
    at_least_small_disadvantage,
    at_least_small_advantage,
    at_least_clear_advantage,
    at_least_clear_disadvantage,
)
from sharpy.general.zone import Zone
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

from sharpy.managers.core.roles import UnitTask
from sharpy.combat import MoveType, Action, MicroStep, MicroRules, CombatUnits
from sharpy.general.extended_power import ExtendedPower
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sharpy.managers.core import *
    from sharpy.knowledges import Knowledge

class Harass(ActBase):
    gather_point_solver: IGatherPointSolver
    zone_manager: IZoneManager
    combat_manager: ICombatManager
    enemy_units_manager: IEnemyUnitsManager
    game_analyzer: Optional[IGameAnalyzer]
    pather: "PathingManager"

    DISTANCE_TO_INCLUDE = 18
    DISTANCE2_TO_INCLUDE = 18 * 18

    def __init__(self):
        super().__init__()
        self.microRules = MicroRules()

    async def start(self, knowledge: "Knowledge"):
        await super().start(knowledge)
        self.unit_values = knowledge.unit_values
        self.pather = self.knowledge.pathing_manager
        self.game_analyzer = self.knowledge.get_manager(IGameAnalyzer)
        if self.game_analyzer is None:
            self.print(f"IGameAnalyzer not found, turning attack_on_advantage off.")
            self.attack_on_advantage = False
        self.gather_point_solver = knowledge.get_required_manager(IGatherPointSolver)
        self.zone_manager = knowledge.get_required_manager(IZoneManager)
        self.enemy_units_manager = knowledge.get_required_manager(IEnemyUnitsManager)
        self.microRules.load_default_methods()
        self.microRules.load_default_micro()
        await self.microRules.start(knowledge)
        self.combat_manager: GroupCombatManager = cast(GroupCombatManager, self.combat)
        self.combat_manager.rules = self.microRules
        await self.combat_manager.start(knowledge)


    async def execute(self) -> bool:
        target = self._get_target()
        self.assign_harassers()
        self.handle_attack(target)

        return True

    def assign_harassers(self):
        harassing_types = {UnitTypeId.CYCLONE.value, UnitTypeId.HELLION.value, UnitTypeId.REAPER.value}
        for unit in self.roles.free_units:
            if unit.type_id.value in harassing_types:
                self.roles.set_task(UnitTask.Harassing, unit)

    def handle_attack(self, target):
        harassers: Units = self.roles.units(UnitTask.Harassing)

        for unit in harassers:
            self.combat.add_unit(unit)

        self.roles.refresh_tasks(harassers)

        for unit in harassers:
            self.handle_combat(unit, target)

    def handle_combat(self, unit: Unit, target: Optional[Point2]):
        type_id = unit.type_id
        units: Units = Units([unit], self.ai)
        group: CombatUnits = CombatUnits(units, self.knowledge)
        self.combat_manager.add_unit(unit)
        self.combat_manager.attack_to(group, target, MoveType.Harass)
        self.combat_manager.remove_unit(unit)


    def _get_target(self) -> Optional[Point2]:
        our_main = self.zone_manager.expansion_zones[0].center_location
        proxy_buildings = self.ai.enemy_structures.closer_than(70, our_main)

        if proxy_buildings.exists:
            return proxy_buildings.closest_to(our_main).position

        # Select expansion to attack.
        # Enemy main zone should the last element in expansion_zones.
        enemy_zones = list(filter(lambda z: z.is_enemys, self.zone_manager.expansion_zones))

        best_zone = None
        best_score = 100000
        start_position = self.gather_point_solver.gather_point
        if self.roles.attacking_units:
            start_position = self.roles.attacking_units.center

        for zone in enemy_zones:  # type: Zone
            not_like_points = zone.center_location.distance_to(start_position)
            not_like_points += zone.enemy_static_power.power * 5
            if not_like_points < best_score:
                best_zone = zone
                best_score = not_like_points

        if best_zone is not None:
            return best_zone.center_location

        if self.ai.enemy_structures.exists:
            return self.ai.enemy_structures.closest_to(our_main).position

        return None
