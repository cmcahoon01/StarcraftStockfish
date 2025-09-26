import pytest
from unittest import mock
from sc2.ids.unit_typeid import UnitTypeId
from stockfish.unit_counter_request import UnitCounterRequest
from stockfish.adaptive_build_order import AdaptiveBuildOrder


class TestUnitCounterRequest:
    def test_init(self):
        """Test UnitCounterRequest initialization"""
        request = UnitCounterRequest()
        assert len(request.required_units) == 0
        assert len(request.required_buildings) == 0
        assert not request.has_requirements()
    
    def test_add_unit_requirement(self):
        """Test adding unit requirements"""
        request = UnitCounterRequest()
        request.add_unit_requirement(UnitTypeId.MARINE, 10)
        request.add_unit_requirement(UnitTypeId.VIKINGFIGHTER, 5)
        
        assert request.get_unit_requirement(UnitTypeId.MARINE) == 10
        assert request.get_unit_requirement(UnitTypeId.VIKINGFIGHTER) == 5
        assert request.get_unit_requirement(UnitTypeId.SIEGETANK) == 0
        assert request.has_requirements()
    
    def test_add_building_requirement(self):
        """Test adding building requirements"""
        request = UnitCounterRequest()
        request.add_building_requirement(UnitTypeId.BARRACKS, 3)
        request.add_building_requirement(UnitTypeId.STARPORT, 2)
        
        assert request.get_building_requirement(UnitTypeId.BARRACKS) == 3
        assert request.get_building_requirement(UnitTypeId.STARPORT) == 2
        assert request.get_building_requirement(UnitTypeId.FACTORY) == 0
        assert request.has_requirements()
    
    def test_clear(self):
        """Test clearing requirements"""
        request = UnitCounterRequest()
        request.add_unit_requirement(UnitTypeId.MARINE, 10)
        request.add_building_requirement(UnitTypeId.BARRACKS, 3)
        
        assert request.has_requirements()
        request.clear()
        assert not request.has_requirements()
        assert len(request.required_units) == 0
        assert len(request.required_buildings) == 0


class MockCache:
    def __init__(self):
        self._units = {}
    
    def own(self, unit_type):
        class MockUnits:
            def __init__(self, amount):
                self.amount = amount
                self.ready = self
                self.idle = self
        
        return MockUnits(self._units.get(unit_type, 0))
    
    def set_unit_count(self, unit_type, count):
        self._units[unit_type] = count


class MockKnowledge:
    def __init__(self):
        self.unit_counter_request = UnitCounterRequest()
        self.unit_cache = MockCache()
        self._minerals = 1000
        self._gas = 1000
    
    def can_afford(self, unit_type):
        return True  # Simplified for testing


class TestAdaptiveBuildOrder:
    def test_init(self):
        """Test AdaptiveBuildOrder initialization"""
        knowledge = MockKnowledge()
        build_order = AdaptiveBuildOrder(knowledge)
        assert build_order.knowledge == knowledge
        assert len(build_order._default_build_order) > 0
    
    def test_get_production_buildings_for_unit(self):
        """Test getting production buildings for various unit types"""
        knowledge = MockKnowledge()
        build_order = AdaptiveBuildOrder(knowledge)
        
        assert UnitTypeId.BARRACKS in build_order._get_production_buildings_for_unit(UnitTypeId.MARINE)
        assert UnitTypeId.FACTORY in build_order._get_production_buildings_for_unit(UnitTypeId.SIEGETANK)
        assert UnitTypeId.STARPORT in build_order._get_production_buildings_for_unit(UnitTypeId.VIKINGFIGHTER)
        assert build_order._get_production_buildings_for_unit(UnitTypeId.COMMANDCENTER) == []
    
    def test_calculate_required_buildings(self):
        """Test calculation of required buildings"""
        knowledge = MockKnowledge()
        build_order = AdaptiveBuildOrder(knowledge)
        
        # Marines should require more barracks for large numbers
        assert build_order._calculate_required_buildings(UnitTypeId.MARINE, 10) >= 2
        assert build_order._calculate_required_buildings(UnitTypeId.MARINE, 2) >= 1
        
        # Vikings should require fewer starports
        assert build_order._calculate_required_buildings(UnitTypeId.VIKINGFIGHTER, 4) >= 2
        assert build_order._calculate_required_buildings(UnitTypeId.VIKINGFIGHTER, 1) >= 1