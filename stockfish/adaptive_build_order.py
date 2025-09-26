from typing import Dict, List, Tuple, Optional
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sharpy.knowledges import Knowledge
from sharpy.plans.acts import ActUnit, ActBase
from sharpy.plans.acts.grid_building import GridBuilding
from sharpy.plans.build_step import Step
from sharpy.plans.require import UnitReady, UnitExists, Supply
from sharpy.plans.acts.terran import *


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
        """Ensure we have enough production buildings and tech labs for required units"""
        counter_request = self.knowledge.unit_counter_request
        cache = self.knowledge.unit_cache
        
        # Check capacity for each unit type
        for unit_type, required_count in counter_request.required_units.items():
            current_count = cache.own(unit_type).amount
            needed = required_count - current_count
            
            if needed > 0:
                production_buildings = self._get_production_buildings_for_unit(unit_type)
                required_addon = self._get_required_addon_for_unit(unit_type)
                
                for building_type in production_buildings:
                    required_buildings = self._calculate_required_buildings(unit_type, needed)
                    current_buildings = cache.own(building_type).ready.amount
                    
                    if current_buildings < required_buildings:
                        # Need more production buildings
                        await self._build_production_building(building_type, required_buildings)
                    
                    # If unit requires tech lab, ensure we have enough tech labs
                    if required_addon:
                        await self._ensure_tech_lab_capacity(building_type, required_addon, needed)
    
    def _get_production_buildings_for_unit(self, unit_type: UnitTypeId) -> List[UnitTypeId]:
        """Get the building types that can produce the given unit"""
        unit_to_building = {
            # Barracks units (reactor compatible)
            UnitTypeId.MARINE: [UnitTypeId.BARRACKS],
            UnitTypeId.REAPER: [UnitTypeId.BARRACKS],
            
            # Barracks units (tech lab required)
            UnitTypeId.MARAUDER: [UnitTypeId.BARRACKS],
            UnitTypeId.GHOST: [UnitTypeId.BARRACKS],
            
            # Factory units (reactor compatible)
            UnitTypeId.HELLION: [UnitTypeId.FACTORY],
            UnitTypeId.HELLBAT: [UnitTypeId.FACTORY],
            
            # Factory units (tech lab required)
            UnitTypeId.CYCLONE: [UnitTypeId.FACTORY],
            UnitTypeId.SIEGETANK: [UnitTypeId.FACTORY],
            UnitTypeId.THOR: [UnitTypeId.FACTORY],
            
            # Starport units (reactor compatible)
            UnitTypeId.VIKINGFIGHTER: [UnitTypeId.STARPORT],
            UnitTypeId.MEDIVAC: [UnitTypeId.STARPORT],
            UnitTypeId.LIBERATOR: [UnitTypeId.STARPORT],
            
            # Starport units (tech lab required)
            UnitTypeId.RAVEN: [UnitTypeId.STARPORT],
            UnitTypeId.BANSHEE: [UnitTypeId.STARPORT],
            UnitTypeId.BATTLECRUISER: [UnitTypeId.STARPORT],
            
            # SCVs from command centers and upgrades
            UnitTypeId.SCV: [UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS],
        }
        return unit_to_building.get(unit_type, [])
    
    def _get_required_addon_for_unit(self, unit_type: UnitTypeId) -> Optional[UnitTypeId]:
        """Get the addon type required to produce the given unit, if any"""
        tech_lab_units = {
            # Barracks tech lab units
            UnitTypeId.MARAUDER: UnitTypeId.BARRACKSTECHLAB,
            UnitTypeId.GHOST: UnitTypeId.BARRACKSTECHLAB,
            
            # Factory tech lab units
            UnitTypeId.CYCLONE: UnitTypeId.FACTORYTECHLAB,
            UnitTypeId.SIEGETANK: UnitTypeId.FACTORYTECHLAB,
            UnitTypeId.THOR: UnitTypeId.FACTORYTECHLAB,
            
            # Starport tech lab units
            UnitTypeId.RAVEN: UnitTypeId.STARPORTTECHLAB,
            UnitTypeId.BANSHEE: UnitTypeId.STARPORTTECHLAB,
            UnitTypeId.BATTLECRUISER: UnitTypeId.STARPORTTECHLAB,
        }
        return tech_lab_units.get(unit_type, None)
    
    def _get_addon_for_building(self, building_type: UnitTypeId, addon_type: UnitTypeId) -> UnitTypeId:
        """Get the specific addon type for a building type"""
        # This mapping ensures we get the right tech lab for the right building
        addon_mapping = {
            (UnitTypeId.BARRACKS, UnitTypeId.BARRACKSTECHLAB): UnitTypeId.BARRACKSTECHLAB,
            (UnitTypeId.FACTORY, UnitTypeId.FACTORYTECHLAB): UnitTypeId.FACTORYTECHLAB,
            (UnitTypeId.STARPORT, UnitTypeId.STARPORTTECHLAB): UnitTypeId.STARPORTTECHLAB,
        }
        return addon_mapping.get((building_type, addon_type), addon_type)
    
    async def _ensure_tech_lab_capacity(self, building_type: UnitTypeId, required_addon: UnitTypeId, needed_units: int):
        """Ensure we have enough tech labs for the required production"""
        cache = self.knowledge.unit_cache
        
        # Count buildings with the required addon
        buildings_with_addon = 0
        if required_addon == UnitTypeId.BARRACKSTECHLAB:
            buildings_with_addon = cache.own(UnitTypeId.BARRACKSTECHLAB).ready.amount
        elif required_addon == UnitTypeId.FACTORYTECHLAB:
            buildings_with_addon = cache.own(UnitTypeId.FACTORYTECHLAB).ready.amount
        elif required_addon == UnitTypeId.STARPORTTECHLAB:
            buildings_with_addon = cache.own(UnitTypeId.STARPORTTECHLAB).ready.amount
        
        # Calculate how many tech labs we need
        required_tech_labs = self._calculate_required_buildings(None, needed_units)  # Use same logic as buildings
        
        if buildings_with_addon < required_tech_labs:
            # Need to build more tech labs
            await self._build_tech_lab(building_type, required_addon, required_tech_labs - buildings_with_addon)
    
    async def _build_tech_lab(self, building_type: UnitTypeId, addon_type: UnitTypeId, count: int):
        """Build tech labs on production buildings"""
        if not self.knowledge.can_afford(addon_type):
            return
        
        # Build tech lab addon
        addon_step = BuildAddon(addon_type, building_type, count)
        await addon_step.start(self.knowledge)
        await addon_step.execute()
    
    def _calculate_required_buildings(self, unit_type: UnitTypeId, needed_units: int) -> int:
        """Calculate how many production buildings are needed for the given units"""
        # Simple heuristic: assume we want to be able to produce all needed units 
        # within a reasonable timeframe
        if unit_type in [UnitTypeId.MARINE, UnitTypeId.MARAUDER]:
            return max(1, (needed_units + 4) // 5)  # marines per barracks capacity
        elif unit_type in [UnitTypeId.HELLION, UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK]:
            return max(1, (needed_units + 4) // 5)  # units per factory capacity
        elif unit_type in [UnitTypeId.VIKINGFIGHTER, UnitTypeId.MEDIVAC, UnitTypeId.BANSHEE]:
            return max(1, (needed_units + 4) // 5)  # units per starport capacity
        else:
            return max(1, needed_units // 5)
    
    async def _build_production_building(self, building_type: UnitTypeId, required_count: int):
        """Build a specific production building if resources allow"""
        if not self.knowledge.can_afford(building_type):
            return
            
        # Create a building step and execute it
        if building_type in [UnitTypeId.BARRACKS, UnitTypeId.FACTORY, UnitTypeId.STARPORT]:
            building_step = GridBuilding(building_type, required_count)  # Build as many as needed
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
        
        # Re-prioritize based on resource availability
        unit_priorities = self._prioritize_by_resources(unit_priorities)
        
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
        required_addon = self._get_required_addon_for_unit(unit_type)
        cache = self.knowledge.unit_cache
        
        for building_type in production_buildings:
            # If unit needs tech lab, check for buildings with tech labs
            if required_addon:
                if required_addon == UnitTypeId.BARRACKSTECHLAB:
                    available_buildings = cache.own(UnitTypeId.BARRACKSTECHLAB).ready.idle
                elif required_addon == UnitTypeId.FACTORYTECHLAB:
                    available_buildings = cache.own(UnitTypeId.FACTORYTECHLAB).ready.idle
                elif required_addon == UnitTypeId.STARPORTTECHLAB:
                    available_buildings = cache.own(UnitTypeId.STARPORTTECHLAB).ready.idle
                else:
                    continue  # Unknown addon type
                
                if available_buildings.amount > 0:
                    return True
            else:
                # Unit doesn't need tech lab, check for idle buildings without addons or with reactors
                idle_buildings = cache.own(building_type).ready.idle
                if idle_buildings.amount > 0:
                    # Additional check: make sure building doesn't have a tech lab if we want reactor-compatible units
                    # For now, just return True if there are idle buildings
                    return True
        
        return False
    
    def _get_unit_resource_cost(self, unit_type: UnitTypeId) -> tuple[int, int]:
        """Get the mineral and gas cost for a unit type"""
        # Simplified cost mapping - in real implementation this would use game data
        unit_costs = {
            UnitTypeId.SCV: (50, 0),
            UnitTypeId.MARINE: (50, 0),
            UnitTypeId.MARAUDER: (100, 25),
            UnitTypeId.REAPER: (50, 50),
            UnitTypeId.GHOST: (150, 125),
            UnitTypeId.HELLION: (100, 0),
            UnitTypeId.HELLBAT: (100, 0),
            UnitTypeId.CYCLONE: (150, 100),
            UnitTypeId.SIEGETANK: (150, 125),
            UnitTypeId.THOR: (300, 200),
            UnitTypeId.VIKINGFIGHTER: (150, 75),
            UnitTypeId.MEDIVAC: (100, 100),
            UnitTypeId.LIBERATOR: (150, 150),
            UnitTypeId.RAVEN: (100, 200),
            UnitTypeId.BANSHEE: (150, 100),
            UnitTypeId.BATTLECRUISER: (400, 300),
        }
        return unit_costs.get(unit_type, (100, 50))  # Default cost
    
    def _prioritize_by_resources(self, unit_priorities: List[Tuple[float, UnitTypeId, int]]) -> list:
        """
        Re-prioritize unit building based on current resource availability.
        If floating lots of minerals but low gas, prioritize mineral-only units.
        """
        if not hasattr(self.knowledge, 'ai') or not hasattr(self.knowledge.ai, 'minerals'):
            return unit_priorities  # Can't check resources, return original priorities
        
        try:
            current_minerals = self.knowledge.ai.minerals
            current_gas = self.knowledge.ai.vespene
            
            # If we have lots of minerals but low gas, prefer mineral-only units
            if current_minerals > 300 and current_gas < 100:
                mineral_only_units = []
                gas_units = []
                
                for priority_data in unit_priorities:
                    ratio, unit_type, needed = priority_data
                    mineral_cost, gas_cost = self._get_unit_resource_cost(unit_type)
                    
                    if gas_cost == 0:
                        mineral_only_units.append(priority_data)
                    else:
                        gas_units.append(priority_data)
                
                # Prioritize mineral-only units when we're floating minerals
                return mineral_only_units + gas_units
            
            # If we have lots of gas but low minerals, prefer gas-heavy units
            elif current_gas > 200 and current_minerals < 200:
                gas_heavy_units = []
                other_units = []
                
                for priority_data in unit_priorities:
                    ratio, unit_type, needed = priority_data
                    mineral_cost, gas_cost = self._get_unit_resource_cost(unit_type)
                    
                    if gas_cost >= mineral_cost:  # Gas-heavy unit
                        gas_heavy_units.append(priority_data)
                    else:
                        other_units.append(priority_data)
                
                return gas_heavy_units + other_units
        
        except AttributeError:
            pass  # Resource info not available, use original priorities
        
        return unit_priorities
    
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