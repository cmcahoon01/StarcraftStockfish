from typing import Optional

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sharpy.combat import Action, GenericMicro, MoveType


class MicroCyclone(GenericMicro):
    def __init__(self):
        super().__init__()
        self.lock_on_range = 6  # Range to initiate lock-on
        self.lock_on_active_range = 9  # Range when lock-on is active
        self.kite_distance = 1.5  # Additional distance to maintain when kiting

    def unit_solve_combat(self, unit: Unit, current_command: Action) -> Action:
        # Handle retreat scenarios first
        if self.move_type in {MoveType.PanicRetreat, MoveType.DefensiveRetreat}:
            return current_command

        # Get relevant enemies that the cyclone can engage
        relevant_enemies = self.enemies_near_by.visible
        if not relevant_enemies.exists:
            return current_command

        closest_enemy = relevant_enemies.closest_to(unit)
        distance_to_enemy = unit.distance_to(closest_enemy)

        # Check if we can use lock-on ability
        can_lock_on = self.knowledge.cooldown_manager.is_ready(unit.tag, AbilityId.LOCKON_LOCKON)

        # Check if we currently have an active lock-on
        has_active_lock_on = self.knowledge.cooldown_manager.is_ready(unit.tag, AbilityId.CANCEL_LOCKON)

        # If we can lock-on and enemy is within lock-on range but not too close
        if can_lock_on and distance_to_enemy <= self.lock_on_range and distance_to_enemy > 3:
            # Use lock-on ability on the closest enemy
            return Action(closest_enemy, True, AbilityId.LOCKON_LOCKON)

        # If we have an active lock-on, maintain maximum range while staying in lock-on range
        if has_active_lock_on:
            ideal_range = self.lock_on_active_range - self.kite_distance

            if distance_to_enemy < ideal_range:
                # Too close, kite away
                kite_position = self._get_kite_position(unit, closest_enemy, ideal_range)
                return Action(kite_position, False)
            elif distance_to_enemy > self.lock_on_active_range:
                # Too far, might lose lock-on, move closer
                return Action(closest_enemy, False)
            else:
                # In good position, attack if ready
                if self.ready_to_shoot(unit):
                    return Action(closest_enemy, True)
                else:
                    # Not ready to shoot, maintain position or micro-kite slightly
                    kite_position = self._get_kite_position(unit, closest_enemy, distance_to_enemy + 0.5)
                    return Action(kite_position, False)

        # If we can't lock-on and don't have active lock-on, move to engage range
        if distance_to_enemy > self.lock_on_range:
            # Move closer to engage
            return Action(closest_enemy, False)
        elif distance_to_enemy < 4:
            # Too close, kite away to safer distance
            kite_position = self._get_kite_position(unit, closest_enemy, self.lock_on_range - 1)
            return Action(kite_position, False)

        # Default: use parent behavior
        return super().unit_solve_combat(unit, current_command)

    def _get_kite_position(self, unit: Unit, enemy: Unit, desired_distance: float) -> Point2:
        """Calculate a kite position to maintain desired distance from enemy."""
        # Calculate direction away from enemy
        direction = unit.position - enemy.position
        if direction.x == 0 and direction.y == 0:
            # If positions are identical, choose a random direction
            direction = Point2((1, 0))

        # Normalize and scale to desired distance
        direction = direction.normalized
        kite_position = enemy.position + direction * desired_distance

        # Use pathing manager to find a good position if available
        if unit.is_flying:
            return self.pather.find_weak_influence_air(kite_position, 2)
        else:
            return self.pather.find_weak_influence_ground(kite_position, 2)

    def should_retreat(self, unit: Unit) -> bool:
        # Cyclones should be more aggressive about staying in the fight when they have lock-on
        has_active_lock_on = self.knowledge.cooldown_manager.is_ready(unit.tag, AbilityId.CANCEL_LOCKON)

        if has_active_lock_on:
            # Only retreat if health is very low when we have lock-on
            if unit.shield_max + unit.health_max > 0:
                health_percentage = (unit.shield + unit.health) / (unit.shield_max + unit.health_max)
            else:
                health_percentage = 0
            return health_percentage < 0.15
        else:
            # Use normal retreat logic when no lock-on
            return super().should_retreat(unit)
