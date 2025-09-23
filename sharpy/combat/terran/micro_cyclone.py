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
        self.lock_targets: dict[int, Optional[int]] = dict()  # Maps cyclone tag to locked target tag

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
            return Action(kite_position, False, AbilityId.MOVE_MOVE)

        # Scenario 1: Lock-on is ready - get within range to activate then back away
        if can_lock_on:
            if distance_to_closest <= self.lock_on_range:
                # Close enough to lock-on, use the ability
                self.lock_targets[unit.tag] = closest_enemy.tag
                return Action(closest_enemy, False, AbilityId.LOCKON_LOCKON)
            else:
                # Move closer to get in lock-on range
                return Action(closest_enemy, False, AbilityId.MOVE_MOVE)

        # Scenario 2: Has active lock-on - aim for distance 14 from target or 12 from nearest enemy
        if has_active_lock_on:
            if unit.tag in self.lock_targets and self.lock_targets[unit.tag] is not None:
                active_target = self.knowledge.unit_cache.by_tag(self.lock_targets[unit.tag])
                if active_target is not None:
                    closest_threat, threat_range = self._get_closest_to_hitting(unit, relevant_enemies)
                    engage_distance = self.preferred_lock_on_distance
                    kite_position = self._get_kite_position(unit, closest_threat, self.preferred_lock_on_distance)
                    while kite_position.distance_to(active_target) > self.lock_on_active_range:
                        engage_distance -= 1
                        possible_kite = self._get_kite_position(unit, closest_threat, engage_distance)
                        if possible_kite.distance_to(closest_threat) <= self.unit_values.real_range(closest_threat, unit):
                            break
                        kite_position = possible_kite
                    return Action(kite_position, False, AbilityId.MOVE_MOVE)
                else:
                    # Fallback: locked target no longer exists
                    has_active_lock_on = False
            else:
                closest_threat, threat_range = self._get_closest_to_hitting(unit, relevant_enemies)
                kite_position = self._get_kite_position(unit, closest_threat, self.fallback_distance)
                return Action(kite_position, False, AbilityId.MOVE_MOVE)
        else:
            self.lock_targets[unit.tag] = None

        # Scenario 3: Lock-on is on cooldown - stay out of enemy attack range
        if not can_lock_on and not has_active_lock_on:
            closest_threat, threat_range = self._get_closest_to_hitting(unit, relevant_enemies)
            threat_range = max(threat_range, self.min_range)
            kite_position = self._get_kite_position(unit, closest_threat, threat_range + 1)
            return Action(kite_position, False, AbilityId.MOVE_MOVE)

        # Default: use parent behavior
        return super().unit_solve_combat(unit, current_command)

    def _get_closest_to_hitting(self, unit: Unit, enemies: Units) -> tuple[Optional[Unit], float]:
        """Get the enemy that is closest to being able to attack the cyclone"""
        closest_enemy = None
        closest_distance = float('inf')
        for enemy in enemies:
            enemy_range = self.unit_values.real_range(enemy, unit)
            distance = unit.distance_to(enemy) - enemy_range
            if distance < closest_distance:
                closest_distance = distance
                closest_enemy = enemy
        return closest_enemy, closest_distance


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
