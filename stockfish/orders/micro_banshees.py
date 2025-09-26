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
        acted = self.handle_cloak(unit, current_command)
        if acted:
            return acted

        if self.move_type in {MoveType.PanicRetreat, MoveType.DefensiveRetreat}:
            return current_command

        relevant_enemies = self.enemies_near_by
        closest_enemy = relevant_enemies.closest_to(unit) if relevant_enemies.exists else None
        a_move = not closest_enemy.is_structure if closest_enemy else False
        current_command.is_attack = a_move

        return current_command

    def handle_cloak(self, unit: Unit, current_command: Action):
        relevant_enemies = self.enemies_near_by

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

        if unit.has_buff(BuffId.BANSHEECLOAK) and requested_mode == AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE:
            return Action(target=None, is_attack=False, ability=AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE)
        elif not unit.has_buff(BuffId.BANSHEECLOAK) and requested_mode == AbilityId.BEHAVIOR_CLOAKON_BANSHEE:
            return Action(target=None, is_attack=False, ability=AbilityId.BEHAVIOR_CLOAKON_BANSHEE)

        return None