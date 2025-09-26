import sys
import os
sys.path.append('/home/runner/work/StarcraftStockfish/StarcraftStockfish/python-sc2')

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


def test_unit_counter_request():
    """Test UnitCounterRequest functionality"""
    print("Testing UnitCounterRequest...")
    
    # Test initialization
    request = UnitCounterRequest()
    assert len(request.required_units) == 0
    assert len(request.required_buildings) == 0
    assert not request.has_requirements()
    print("✓ Initialization test passed")
    
    # Test adding unit requirements
    request.add_unit_requirement(UnitTypeId.MARINE, 10)
    request.add_unit_requirement(UnitTypeId.VIKINGFIGHTER, 5)
    assert request.get_unit_requirement(UnitTypeId.MARINE) == 10
    assert request.get_unit_requirement(UnitTypeId.VIKINGFIGHTER) == 5
    assert request.get_unit_requirement(UnitTypeId.SIEGETANK) == 0
    assert request.has_requirements()
    print("✓ Unit requirements test passed")
    
    # Test adding building requirements
    request.add_building_requirement(UnitTypeId.BARRACKS, 3)
    request.add_building_requirement(UnitTypeId.STARPORT, 2)
    assert request.get_building_requirement(UnitTypeId.BARRACKS) == 3
    assert request.get_building_requirement(UnitTypeId.STARPORT) == 2
    assert request.get_building_requirement(UnitTypeId.FACTORY) == 0
    print("✓ Building requirements test passed")
    
    # Test clear
    request.clear()
    assert not request.has_requirements()
    assert len(request.required_units) == 0
    assert len(request.required_buildings) == 0
    print("✓ Clear test passed")
    
    print("All UnitCounterRequest tests passed!")


def test_production_building_mapping():
    """Test production building mapping logic"""
    print("Testing production building mapping...")
    
    def get_production_buildings_for_unit(unit_type: UnitTypeId):
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
    
    # Test various unit types
    assert UnitTypeId.BARRACKS in get_production_buildings_for_unit(UnitTypeId.MARINE)
    assert UnitTypeId.FACTORY in get_production_buildings_for_unit(UnitTypeId.SIEGETANK)
    assert UnitTypeId.STARPORT in get_production_buildings_for_unit(UnitTypeId.VIKINGFIGHTER)
    assert get_production_buildings_for_unit(UnitTypeId.COMMANDCENTER) == []
    
    print("✓ Production building mapping test passed")


def test_capacity_calculation():
    """Test production capacity calculation"""
    print("Testing capacity calculation...")
    
    def calculate_required_buildings(unit_type: UnitTypeId, needed_units: int) -> int:
        """Calculate how many production buildings are needed for the given units"""
        if unit_type in [UnitTypeId.MARINE, UnitTypeId.MARAUDER]:
            return max(1, (needed_units + 4) // 5)  # 5 marines per barracks capacity
        elif unit_type in [UnitTypeId.HELLION, UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK]:
            return max(1, (needed_units + 2) // 3)  # 3 units per factory capacity
        elif unit_type in [UnitTypeId.VIKINGFIGHTER, UnitTypeId.MEDIVAC, UnitTypeId.BANSHEE]:
            return max(1, (needed_units + 1) // 2)  # 2 units per starport capacity
        else:
            return max(1, needed_units // 2)
    
    # Test Marines - should require more barracks for large numbers
    assert calculate_required_buildings(UnitTypeId.MARINE, 10) >= 2
    assert calculate_required_buildings(UnitTypeId.MARINE, 2) >= 1
    
    # Test Vikings - should require fewer starports
    assert calculate_required_buildings(UnitTypeId.VIKINGFIGHTER, 4) >= 2
    assert calculate_required_buildings(UnitTypeId.VIKINGFIGHTER, 1) >= 1
    
    print("✓ Capacity calculation test passed")


if __name__ == "__main__":
    test_unit_counter_request()
    test_production_building_mapping()
    test_capacity_calculation()
    print("\nAll tests passed successfully! 🎉")