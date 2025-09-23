from typing import Optional, Dict

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from sharpy.combat import Action, GenericMicro, MoveType, MicroStep
from sc2.ids.buff_id import BuffId

class MicroBanshees(GenericMicro):
    def __init__(self):
        self.can_attack_air: bool = False
        self.can_detect: bool = False
        self.has_reached_base: bool = False
        super().__init__()

    def unit_solve_combat(self, unit: Unit, current_command: Action) -> Action:
        if self.move_type in {MoveType.PanicRetreat, MoveType.DefensiveRetreat}:
            return current_command

        closest = self.closest_units.get(unit.tag)
        if not closest or closest.distance_to(unit) > 14:
            # not in combat
            return current_command

        relevant_enemies = self.enemies_near_by.visible

        self.can_attack_air = False
        self.can_detect = False
        if relevant_enemies.exists:
            if relevant_enemies.filter(lambda unit: unit.can_attack_air).exists:
                self.can_attack_air = True
            if relevant_enemies.filter(lambda unit: unit.is_detector).exists:
                self.can_detect = True

        relevant_enemies = self.ai.enemy_units.closer_than(11, unit)

        can_attack_air = False
        can_detect = False

        if relevant_enemies.filter(lambda unit: unit.can_attack_air).exists:
            can_attack_air = True
        if relevant_enemies.filter(lambda unit: unit.is_detector).exists:
            can_detect = True

        if not can_detect and can_attack_air:
            requested_mode = AbilityId.BEHAVIOR_CLOAKON_BANSHEE
        else:
            requested_mode = AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE

        # if (can_detect and can_attack_air) or unit.health_percentage < 0.5:
        #     threats = relevant_enemies.filter(lambda unit: unit.can_attack_air) | relevant_enemies.filter(
        #         lambda unit: unit.is_detector)
        #     if threats.exists:
        #         closest_threat = threats.closest_to(unit)
        #         backstep: Point2 = unit.position.towards(closest_threat.position, -5)
        #         backstep = self.pather.find_weak_influence_air(backstep, 4)
        #         return Action(target=backstep, is_attack=False)

        if unit.has_buff(BuffId.BANSHEECLOAK) and requested_mode == AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE:
            return Action(target=None, is_attack=False, ability=AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE)
        elif not unit.has_buff(BuffId.BANSHEECLOAK) and requested_mode == AbilityId.BEHAVIOR_CLOAKON_BANSHEE:
            return Action(target=None, is_attack=False, ability=AbilityId.BEHAVIOR_CLOAKON_BANSHEE)

        return current_command