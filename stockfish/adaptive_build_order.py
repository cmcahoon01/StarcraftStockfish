from typing import Dict, List, Tuple, Optional
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sharpy.knowledges import Knowledge
from sharpy.plans.acts import ActUnit, ActBase
from sharpy.plans.acts.grid_building import GridBuilding
from sharpy.plans.build_step import Step
from sharpy.plans.require import UnitReady, UnitExists, Supply
from sharpy.plans.acts.terran import *
from sharpy.plans.terran import *


class AdaptiveBuildOrder(ActBase):
    """
    Adaptive build order that prioritizes units based on counter requirements.
    When no counters are needed, falls back to a default build order.
    """
    
    def __init__(self, knowledge: Knowledge):
        super().__init__()
        self.knowledge = knowledge
        self._default_build_order = self._create_default_build_order()
    
    def _create_default_build_order(self) -> List[Step]:
        """Create a minimal default build order for when no counters are needed"""
        return [
            # Basic economy
            Step(None, ActUnit(UnitTypeId.SCV, UnitTypeId.COMMANDCENTER, 22)),
            
            # Basic buildings
            Step(Supply(13), GridBuilding(UnitTypeId.SUPPLYDEPOT, 1)),
            Step(UnitReady(UnitTypeId.SUPPLYDEPOT, 0.95), GridBuilding(UnitTypeId.BARRACKS, 1)),
            Step(Supply(16), GridBuilding(UnitTypeId.SUPPLYDEPOT, 2)),
            Step(None, BuildGas(1), skip_until=UnitReady(UnitTypeId.BARRACKS, 1)),
            Step(None, GridBuilding(UnitTypeId.FACTORY, 1), skip_until=UnitReady(UnitTypeId.BARRACKS, 1)),
            Step(None, GridBuilding(UnitTypeId.STARPORT, 1), skip_until=UnitReady(UnitTypeId.FACTORY, 1)),
            
            # Basic units
            Step(UnitReady(UnitTypeId.BARRACKS, 1), ActUnit(UnitTypeId.MARINE, UnitTypeId.BARRACKS, 8)),
            Step(UnitReady(UnitTypeId.FACTORY, 1), ActUnit(UnitTypeId.HELLION, UnitTypeId.FACTORY, 2)),
            
            # Supply management
            Step(None, AutoDepot(), skip_until=Supply(28))
        ]
    
    async def execute(self) -> bool:
        """Main execution logic for adaptive build order"""
        counter_request = self.knowledge.unit_counter_request
        
        if not counter_request.has_requirements():
            # No counter requirements, use default build order
            return await self._execute_default_build_order()
        
        # Execute adaptive logic
        await self._ensure_production_capacity()
        await self._build_counter_units()
        await self._execute_default_build_order()  # Fill in gaps
        
        return True
    
    async def _execute_default_build_order(self) -> bool:
        """Execute the default build order steps"""
        all_complete = True
        for step in self._default_build_order:
            result = await step.execute()
            if not result:
                all_complete = False
        return all_complete
    
    async def _ensure_production_capacity(self):
        """Ensure we have enough production buildings for required units"""
        counter_request = self.knowledge.unit_counter_request
        cache = self.knowledge.unit_cache
        
        # Check capacity for each unit type
        for unit_type, required_count in counter_request.required_units.items():
            current_count = cache.own(unit_type).amount
            needed = required_count - current_count
            
            if needed > 0:
                production_buildings = self._get_production_buildings_for_unit(unit_type)
                for building_type in production_buildings:
                    required_buildings = self._calculate_required_buildings(unit_type, needed)
                    current_buildings = cache.own(building_type).ready.amount
                    
                    if current_buildings < required_buildings:
                        # Need more production buildings
                        await self._build_production_building(building_type)
    
    def _get_production_buildings_for_unit(self, unit_type: UnitTypeId) -> List[UnitTypeId]:
        """Get the building types that can produce the given unit"""
        unit_to_building = {
            UnitTypeId.MARINE: [UnitTypeId.BARRACKS],
            UnitTypeId.MARAUDER: [UnitTypeId.BARRACKS],
            UnitTypeId.REAPER: [UnitTypeId.BARRACKS],
            UnitTypeId.GHOST: [UnitTypeId.BARRACKS],
            UnitTypeId.HELLION: [UnitTypeId.FACTORY],
            UnitTypeId.CYCLONE: [UnitTypeId.FACTORY],
            UnitTypeId.SIEGETANK: [UnitTypeId.FACTORY],
            UnitTypeId.THOR: [UnitTypeId.FACTORY],
            UnitTypeId.VIKINGFIGHTER: [UnitTypeId.STARPORT],
            UnitTypeId.MEDIVAC: [UnitTypeId.STARPORT],
            UnitTypeId.LIBERATOR: [UnitTypeId.STARPORT],
            UnitTypeId.RAVEN: [UnitTypeId.STARPORT],
            UnitTypeId.BANSHEE: [UnitTypeId.STARPORT],
            UnitTypeId.BATTLECRUISER: [UnitTypeId.STARPORT],
        }
        return unit_to_building.get(unit_type, [])
    
    def _calculate_required_buildings(self, unit_type: UnitTypeId, needed_units: int) -> int:
        """Calculate how many production buildings are needed for the given units"""
        # Simple heuristic: assume we want to be able to produce all needed units 
        # within a reasonable timeframe
        if unit_type in [UnitTypeId.MARINE, UnitTypeId.MARAUDER]:
            return max(1, (needed_units + 4) // 5)  # 5 marines per barracks capacity
        elif unit_type in [UnitTypeId.HELLION, UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK]:
            return max(1, (needed_units + 2) // 3)  # 3 units per factory capacity
        elif unit_type in [UnitTypeId.VIKINGFIGHTER, UnitTypeId.MEDIVAC, UnitTypeId.BANSHEE]:
            return max(1, (needed_units + 1) // 2)  # 2 units per starport capacity
        else:
            return max(1, needed_units // 2)
    
    async def _build_production_building(self, building_type: UnitTypeId):
        """Build a specific production building if resources allow"""
        if not self.knowledge.can_afford(building_type):
            return
            
        # Create a building step and execute it
        if building_type in [UnitTypeId.BARRACKS, UnitTypeId.FACTORY, UnitTypeId.STARPORT]:
            building_step = GridBuilding(building_type, 99)  # Build as many as needed
            await building_step.start(self.knowledge)
            await building_step.execute()
    
    async def _build_counter_units(self):
        """Build units according to counter requirements, prioritizing ratios"""
        counter_request = self.knowledge.unit_counter_request
        cache = self.knowledge.unit_cache
        
        # Calculate priority queue based on unit ratios
        unit_priorities = []
        for unit_type, required_count in counter_request.required_units.items():
            current_count = cache.own(unit_type).amount
            if current_count < required_count:
                ratio = current_count / max(1, required_count)  # Avoid division by zero
                needed = required_count - current_count
                unit_priorities.append((ratio, unit_type, needed))
        
        # Sort by ratio (lowest ratio = highest priority)
        unit_priorities.sort(key=lambda x: x[0])
        
        # Build units in priority order, considering resources
        for ratio, unit_type, needed in unit_priorities:
            if self._should_build_unit(unit_type):
                await self._build_unit(unit_type, needed)
    
    def _should_build_unit(self, unit_type: UnitTypeId) -> bool:
        """Determine if we should build this unit type based on resources and production capacity"""
        if not self.knowledge.can_afford(unit_type):
            return False
        
        # Check if we have production buildings available
        production_buildings = self._get_production_buildings_for_unit(unit_type)
        cache = self.knowledge.unit_cache
        
        for building_type in production_buildings:
            idle_buildings = cache.own(building_type).ready.idle
            if idle_buildings.amount > 0:
                return True
        
        return False
    
    async def _build_unit(self, unit_type: UnitTypeId, max_count: int):
        """Build a specific unit type up to max_count"""
        production_buildings = self._get_production_buildings_for_unit(unit_type)
        
        for building_type in production_buildings:
            unit_step = ActUnit(unit_type, building_type, max_count, priority=True)
            await unit_step.start(self.knowledge)
            await unit_step.execute()
            break  # Only need to create one ActUnit step
    
    async def start(self, knowledge: Knowledge):
        """Initialize the build order"""
        await super().start(knowledge)
        
        # Initialize all default build order steps
        for step in self._default_build_order:
            await step.start(knowledge)