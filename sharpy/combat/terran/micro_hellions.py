from typing import Optional

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from sharpy.combat import Action, GenericMicro, MoveType


class MicroHellions(GenericMicro):
    def __init__(self):
        super().__init__()
        self.attack_range = 5  # Hellion attack range
        self.safe_distance_buffer = 1.5  # Buffer to stay outside enemy range

    def unit_solve_combat(self, unit: Unit, current_command: Action) -> Action:
        # Handle retreat scenarios first
        if self.move_type in {MoveType.PanicRetreat, MoveType.DefensiveRetreat}:
            return current_command

        # Get nearby enemies that can threaten the hellion
        threatening_enemies = self._get_threatening_enemies(unit)
        
        # Priority 1: Stay out of range of all enemy attack ranges
        if threatening_enemies:
            enemy_in_range = self._get_closest_threat(unit, threatening_enemies)
            if enemy_in_range:
                threat_range = self.unit_values.real_range(enemy_in_range, unit)
                current_distance = unit.distance_to(enemy_in_range)
                
                if current_distance <= threat_range + self.safe_distance_buffer:
                    # Need to kite away from this threat
                    kite_position = self._get_kite_position(unit, enemy_in_range, threat_range + self.safe_distance_buffer + 1)
                    return Action(kite_position, False, AbilityId.MOVE_MOVE)

        # Priority 2: Fire at any enemy in range (5 for hellions)
        enemies_in_attack_range = self.enemies_near_by.not_structure.in_attack_range_of(unit)
        if enemies_in_attack_range and self.ready_to_shoot(unit):
            # Find the best target to attack
            target = self._select_best_target(unit, enemies_in_attack_range)
            if target:
                return Action(target, True)

        # Priority 3: Move towards any nearby workers
        nearby_workers = self._get_nearby_workers(unit)
        if nearby_workers:
            closest_worker = nearby_workers.closest_to(unit)
            return Action(closest_worker, False, AbilityId.MOVE_MOVE)

        # Priority 4: Move towards the original target position
        # But don't attack structures - use non-attack move if no enemy units nearby
        if current_command.is_attack and len(self.enemies_near_by.not_structure) == 0:
            return Action(current_command.target, False, AbilityId.MOVE_MOVE)

        # Default behavior - keep moving towards original target
        return Action(self.original_target, False, AbilityId.MOVE_MOVE)

    def _get_threatening_enemies(self, unit: Unit) -> Units:
        """Get enemies that can potentially attack the hellion."""
        # Filter for enemies that can attack ground and are within their attack range + some buffer
        threatening = Units([], self.ai)
        for enemy in self.enemies_near_by.not_structure:
            enemy_range = self.unit_values.real_range(enemy, unit)
            if enemy_range > 0:  # Can attack this unit
                distance = unit.distance_to(enemy)
                # Include enemies that are close to being in range
                if distance <= enemy_range + 3:
                    threatening.append(enemy)
        return threatening

    def _get_closest_threat(self, unit: Unit, threatening_enemies: Units) -> Optional[Unit]:
        """Get the enemy that poses the most immediate threat."""
        closest_threat = None
        closest_effective_distance = float('inf')
        
        for enemy in threatening_enemies:
            enemy_range = self.unit_values.real_range(enemy, unit)
            distance = unit.distance_to(enemy)
            # Calculate how close the enemy is to being able to attack
            effective_distance = distance - enemy_range
            
            if effective_distance < closest_effective_distance:
                closest_effective_distance = effective_distance
                closest_threat = enemy
                
        return closest_threat

    def _get_kite_position(self, unit: Unit, enemy: Unit, desired_distance: float) -> Point2:
        """Calculate a kite position to maintain desired distance from enemy."""
        # Calculate direction away from enemy
        direction = unit.position - enemy.position
        if direction.x == 0 and direction.y == 0:
            # If positions are identical, choose a direction towards our target
            direction = self.original_target - enemy.position
            if direction.x == 0 and direction.y == 0:
                direction = Point2((1, 0))  # Fallback direction

        # Normalize and scale to desired distance
        direction = direction.normalized
        kite_position = enemy.position + direction * desired_distance

        # Use pathing manager to find a good position if available
        return self.pather.find_weak_influence_ground(kite_position, 2)

    def _select_best_target(self, unit: Unit, enemies_in_range: Units) -> Optional[Unit]:
        """Select the best target to attack from enemies in range."""
        if not enemies_in_range:
            return None
            
        # Prioritize workers if they're in range
        workers = enemies_in_range.filter(lambda u: u.type_id in {
            UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV
        })
        if workers:
            return workers.closest_to(unit)
            
        # Otherwise, prioritize low-health enemies or closest enemy
        if len(enemies_in_range) == 1:
            return enemies_in_range.first
            
        # Find lowest health percentage enemy
        best_target = None
        lowest_hp_ratio = float('inf')
        
        for enemy in enemies_in_range:
            if enemy.health_max > 0:
                hp_ratio = enemy.health / enemy.health_max
                if hp_ratio < lowest_hp_ratio:
                    lowest_hp_ratio = hp_ratio
                    best_target = enemy
                    
        return best_target or enemies_in_range.closest_to(unit)

    def _get_nearby_workers(self, unit: Unit) -> Units:
        """Get nearby enemy workers within a reasonable distance."""
        worker_types = {UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV}
        workers = Units([], self.ai)
        
        for enemy in self.enemies_near_by:
            if enemy.type_id in worker_types:
                distance = unit.distance_to(enemy)
                # Only consider workers within a reasonable distance
                if distance <= 15:  # Reasonable pursuit distance
                    workers.append(enemy)
                    
        return workers