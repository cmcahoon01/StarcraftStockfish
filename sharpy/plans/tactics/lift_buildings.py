from typing import Dict, Optional, Set
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sharpy.interfaces import IPreviousUnitsManager, IBuildingSolver
from sharpy.knowledges import Knowledge
from sharpy.plans.acts import ActBase


class LiftBuildings(ActBase):
    """Lifts buildings when they are close to being destroyed and manages their escape and landing."""
    
    # Buildings that can be lifted and their corresponding lift abilities
    LIFTABLE_BUILDINGS = {
        UnitTypeId.COMMANDCENTER: AbilityId.LIFT_COMMANDCENTER,
        UnitTypeId.ORBITALCOMMAND: AbilityId.LIFT_ORBITALCOMMAND,
        UnitTypeId.BARRACKS: AbilityId.LIFT_BARRACKS,
        UnitTypeId.FACTORY: AbilityId.LIFT_FACTORY,
        UnitTypeId.STARPORT: AbilityId.LIFT_STARPORT,
    }
    
    # Corresponding land abilities
    LAND_ABILITIES = {
        UnitTypeId.COMMANDCENTER: AbilityId.LAND_COMMANDCENTER,
        UnitTypeId.ORBITALCOMMAND: AbilityId.LAND_ORBITALCOMMAND,
        UnitTypeId.BARRACKS: AbilityId.LAND_BARRACKS,
        UnitTypeId.FACTORY: AbilityId.LAND_FACTORY,
        UnitTypeId.STARPORT: AbilityId.LAND_STARPORT,
    }

    def __init__(self):
        super().__init__()
        self.flying_buildings: Set[int] = set()
        # Store original positions of lifted buildings
        self.lifted_building_origins: Dict[int, Point2] = {}
        # Store target landing positions for buildings
        self.building_target_positions: Dict[int, Point2] = {}

    async def start(self, knowledge: "Knowledge"):
        await super().start(knowledge)
        self.previous_units_manager = knowledge.get_required_manager(IPreviousUnitsManager)
        self.building_solver = knowledge.get_required_manager(IBuildingSolver)

    async def execute(self) -> bool:
        # Process all our liftable buildings
        for building in self.ai.structures:  # type: Unit
            if building.type_id in self.LIFTABLE_BUILDINGS:
                if building.tag not in self.flying_buildings:
                    await self.manage_grounded_building(building)
                else:
                    await self.manage_flying_building(building.tag)

        return True

    async def manage_grounded_building(self, building: Unit):
        if self.building_in_danger(building):
            await self.lift_building(building)

    async def lift_building(self, building: Unit):
        """Lift a building that is in danger."""
        # Store the original position
        self.lifted_building_origins[building.tag] = building.position
        
        # Cancel all current activities/production before lifting
        if not building.is_idle:
            # Cancel any production queue
            building(AbilityId.CANCEL_LAST)
            # Stop any current command
            building(AbilityId.STOP)
        
        # Execute lift command
        lift_ability = self.LIFTABLE_BUILDINGS[building.type_id]
        resp = building(lift_ability)
        print(f"Lifting {building.type_id.name}, response: {resp}, flying? {building.is_flying}")
        if resp:  # If lift command was successful
            self.flying_buildings.add(building.tag)


    def remove_building(self, building_tag):
        # if building_tag in self.flying_buildings:
        #     self.flying_buildings.remove(building_tag)
        if building_tag in self.lifted_building_origins:
            del self.lifted_building_origins[building_tag]
        if building_tag in self.building_target_positions:
            del self.building_target_positions[building_tag]
        if building_tag in self.building_solver.structure_target_move_location:
            del self.building_solver.structure_target_move_location[building_tag]


    async def manage_flying_building(self, buildingTag: int):
        """Manage a flying building - flee from enemies or try to land."""
        building = self.ai.structures.find_by_tag(buildingTag)
        if not building or building.health <= 0:
            self.remove_building(buildingTag)
            return

        # Find nearby enemies that can attack air
        nearby_air_attackers = self.get_nearby_air_attackers(building.position, 10)
        
        if nearby_air_attackers:
            # Flee from enemies
            await self.flee_from_enemies(building, nearby_air_attackers)
        else:
            # Try to land
            await self.try_to_land(building)

    def get_nearby_air_attackers(self, position: Point2, distance: float):
        """Get enemy units that can attack air within the specified distance."""
        enemies = self.ai.enemy_units.closer_than(distance, position)
        air_attackers = []
        
        for enemy in enemies:
            # Check if the enemy can attack air
            # if enemy.can_attack_air:
            air_attackers.append(enemy)

        return air_attackers

    async def flee_from_enemies(self, building: Unit, enemies):
        """Move the building away from enemies."""
        if not enemies:
            return
            
        # Calculate the average position of enemies
        enemy_center = Point2((
            sum(enemy.position.x for enemy in enemies) / len(enemies),
            sum(enemy.position.y for enemy in enemies) / len(enemies)
        ))
        
        # Move away from the enemy center
        flee_direction = building.position - enemy_center
        if flee_direction.length == 0:
            # If we're exactly on the enemy center, move toward our main base
            flee_direction = self.ai.start_location - enemy_center
        
        flee_direction = flee_direction.normalized
        flee_position = building.position + flee_direction * 8
        
        # Ensure the flee position is within map bounds
        flee_position = self.clamp_to_map(flee_position)
        
        # Only move if not already moving to this position
        if not building.is_moving or building.order_target != flee_position:
            building.move(flee_position)

    async def try_to_land(self, building: Unit):
        """Try to land the building at its original position or find a new spot."""
        if building.tag not in self.lifted_building_origins:
            # No stored origin, find a new landing spot
            await self.find_and_set_landing_spot(building)
        
        original_position = self.lifted_building_origins[building.tag]
        
        # Check if we can land at the original position
        if self.can_land_at_position(building, original_position):
            print(f"Landing {building.type_id.name} back at original position {original_position}, {building.is_moving}")
            await self.land_building_at_position(building, original_position)
        else:
            # Find an alternative landing spot
            print(f"Original position blocked, finding new landing spot for {building.type_id.name}, {building.is_moving}")
            await self.find_and_set_landing_spot(building)

    def can_land_at_position(self, building: Unit, position: Point2) -> bool:
        """Check if a building can land at the specified position."""
        # Check if position is clear of other buildings (excluding the flying building itself)
        buildings = self.ai.structures.filter(lambda b: b.tag != building.tag and not b.is_flying)
        return not buildings.closer_than(1, position)

    async def find_and_set_landing_spot(self, building: Unit):
        """Find a new landing spot for the building."""
        landing_position = await self.find_landing_position(building)
        if landing_position:
            self.building_target_positions[building.tag] = landing_position
            await self.land_building_at_position(building, landing_position)
        else:
            # If we can't find a good landing spot, try to get away from immediate danger
            # and try again later
            if building.health < building.health_max * 0.5:  # Still in danger
                # Move toward our main base as a safe direction
                safe_direction = self.ai.start_location - building.position
                if safe_direction.length > 0:
                    safe_direction = safe_direction.normalized
                    safe_position = building.position + safe_direction * 5
                    safe_position = self.clamp_to_map(safe_position)
                    if not building.is_moving or building.order_target != safe_position:
                        building.move(safe_position)

    async def find_landing_position(self, building: Unit) -> Optional[Point2]:
        """Find a suitable landing position for the building using the building solver."""
        reserved_landing_locations: Set[Point2] = set(self.building_solver.structure_target_move_location.values())
        
        # Use building solver's 3x3 grid for most buildings (2x2 for supply depots, but we don't lift those)
        for position in self.building_solver.buildings3x3:
            # Skip if another building is already targeting this position
            if position in reserved_landing_locations:
                continue
            if self.can_land_at_position(building, position):
                return position
        
        return None

    async def land_building_at_position(self, building: Unit, position: Point2):
        """Land the building at the specified position."""
        # Reserve the position in the building solver
        self.building_solver.structure_target_move_location[building.tag] = position
        
        # Check if we're close enough to land
        if building.position.distance_to(position) > 2:
            # Move closer first
            if not building.is_moving or building.order_target != position:
                building.move(position)
        else:
            # We're close enough, try to land
            land_ability = self.LAND_ABILITIES.get(building.type_id)
            if land_ability and not building.is_using_ability(land_ability):
                resp = building(land_ability, position)
                print(f"Landing {building.type_id.name}, response: {resp}")

    def building_in_danger(self, building: Unit) -> bool:
        """Check if a building is in danger and should be lifted."""
        # Only lift completed buildings
        if building.build_progress < 1.0:
            return False
            
        previous_building = self.previous_units_manager.last_unit(building.tag)
        if previous_building:
            health = building.health
            # Lift when building is below 40% health and losing health
            danger_threshold = building.health_max * 1
            if health < previous_building.health and health < danger_threshold:
                return True
        return False

    def clamp_to_map(self, position: Point2) -> Point2:
        """Ensure position is within map bounds."""
        x = max(0, min(position.x, self.ai.game_info.map_size.x))
        y = max(0, min(position.y, self.ai.game_info.map_size.y))
        return Point2((x, y))