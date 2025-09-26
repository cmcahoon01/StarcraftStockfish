from typing import Dict
from sc2.ids.unit_typeid import UnitTypeId


class UnitCounterRequest:
    """
    Class to store the required units/buildings to counter enemy compositions.
    This will be populated by future logic that analyzes enemy units and determines counters.
    """
    
    def __init__(self):
        # Dictionary mapping unit types to required counts
        # e.g., {UnitTypeId.MARINE: 15, UnitTypeId.VIKINGFIGHTER: 2, UnitTypeId.SIEGETANK: 5}
        self.required_units: Dict[UnitTypeId, int] = {}
        
        # Dictionary mapping building types to required counts  
        # e.g., {UnitTypeId.BARRACKS: 3, UnitTypeId.STARPORT: 2, UnitTypeId.FACTORY: 1}
        self.required_buildings: Dict[UnitTypeId, int] = {}
    
    def add_unit_requirement(self, unit_type: UnitTypeId, count: int):
        """Add or update a unit requirement"""
        self.required_units[unit_type] = count
    
    def add_building_requirement(self, building_type: UnitTypeId, count: int):
        """Add or update a building requirement"""
        self.required_buildings[building_type] = count
    
    def get_unit_requirement(self, unit_type: UnitTypeId) -> int:
        """Get the required count for a specific unit type"""
        return self.required_units.get(unit_type, 0)
    
    def get_building_requirement(self, building_type: UnitTypeId) -> int:
        """Get the required count for a specific building type"""
        return self.required_buildings.get(building_type, 0)
    
    def has_requirements(self) -> bool:
        """Check if there are any counter requirements set"""
        return len(self.required_units) > 0 or len(self.required_buildings) > 0
    
    def clear(self):
        """Clear all requirements"""
        self.required_units.clear()
        self.required_buildings.clear()