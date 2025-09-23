from typing import Optional

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from sharpy.combat import Action, GenericMicro, MoveType


class MicroCyclone(GenericMicro):
    def __init__(self):
        super().__init__()
        self.lock_on_range = 7  # Range to initiate lock-on
        self.lock_on_active_range = 15  # Range when lock-on is active
        self.min_range = 4  # Minimum range from any enemy
        self.preferred_lock_on_distance = 14  # Preferred distance from lock-on target
        self.fallback_distance = 12  # Distance from nearest enemy when locked on

    def unit_solve_combat(self, unit: Unit, current_command: Action) -> Action:
        # Handle retreat scenarios first
        if self.move_type in {MoveType.PanicRetreat, MoveType.DefensiveRetreat}:
            return current_command

        # Get relevant enemies that the cyclone can engage
        relevant_enemies = self.enemies_near_by.visible
        if not relevant_enemies.exists:
            return current_command

        closest_enemy = relevant_enemies.closest_to(unit)
        distance_to_closest = unit.distance_to(closest_enemy)

        # Check lock-on states
        can_lock_on = self.knowledge.cooldown_manager.is_ready(unit.tag, AbilityId.LOCKON_LOCKON)
        has_active_lock_on = self.knowledge.cooldown_manager.is_ready(unit.tag, AbilityId.CANCEL_LOCKON)

        # Always maintain minimum range of 4 from nearest enemy
        if distance_to_closest < self.min_range:
            kite_position = self._get_kite_position(unit, closest_enemy, self.min_range + 1)
            return Action(kite_position, False)

        # Scenario 1: Lock-on is ready - get within range to activate then back away
        if can_lock_on:
            if distance_to_closest <= self.lock_on_range:
                # Close enough to lock-on, use the ability
                return Action(closest_enemy, True, AbilityId.LOCKON_LOCKON)
            else:
                # Move closer to get in lock-on range
                return Action(closest_enemy, False)

        # Scenario 2: Has active lock-on - aim for distance 14 from target or 12 from nearest enemy
        if has_active_lock_on:
            # Try to maintain preferred distance from lock-on target (closest enemy)
            if distance_to_closest < self.preferred_lock_on_distance:
                # Too close to target, kite away to preferred distance
                kite_position = self._get_kite_position(unit, closest_enemy, self.preferred_lock_on_distance)
                return Action(kite_position, False)
            elif distance_to_closest > self.lock_on_active_range:
                # Too far, might lose lock-on, move closer
                return Action(closest_enemy, False)
            else:
                # In good range, attack if ready, otherwise use fallback distance logic
                if self.ready_to_shoot(unit):
                    return Action(closest_enemy, True)
                else:
                    # Not ready to shoot, maintain fallback distance from nearest enemy
                    target_distance = max(self.fallback_distance, self.min_range + 1)
                    if distance_to_closest < target_distance:
                        kite_position = self._get_kite_position(unit, closest_enemy, target_distance)
                        return Action(kite_position, False)

        # Scenario 3: Lock-on is on cooldown - stay out of enemy attack range
        if not can_lock_on and not has_active_lock_on:
            max_enemy_range = self._get_max_enemy_attack_range(unit, relevant_enemies)
            safe_distance = max_enemy_range + 1  # Stay just outside enemy range
            
            if distance_to_closest < safe_distance:
                # Too close to enemies, kite away to safe distance
                kite_position = self._get_kite_position(unit, closest_enemy, safe_distance)
                return Action(kite_position, False)

        # Default: use parent behavior
        return super().unit_solve_combat(unit, current_command)

    def _get_max_enemy_attack_range(self, unit: Unit, enemies: Units) -> float:
        """Calculate the maximum attack range of nearby enemies."""
        max_range = 0
        for enemy in enemies:
            enemy_range = self.unit_values.real_range(enemy, unit)
            max_range = max(max_range, enemy_range)
        return max_range

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
