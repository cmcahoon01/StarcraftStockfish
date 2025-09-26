#!/usr/bin/env python3
"""
Example demonstration of the Adaptive Build Order system.

This script shows how future counter logic would populate the UnitCounterRequest
and how the adaptive build order would respond to different enemy compositions.
"""

import sys
sys.path.append('/home/runner/work/StarcraftStockfish/StarcraftStockfish/python-sc2')

from typing import Dict
from sc2.ids.unit_typeid import UnitTypeId

# Import our adaptive build order classes
exec(open('/home/runner/work/StarcraftStockfish/StarcraftStockfish/stockfish/unit_counter_request.py').read())


def simulate_counter_logic(enemy_composition: str, unit_request: UnitCounterRequest):
    """
    Simulate how future counter logic would populate unit requirements 
    based on enemy composition analysis.
    """
    unit_request.clear()
    
    if enemy_composition == "mass_air":
        # Enemy has lots of air units - need anti-air
        print("🎯 Enemy detected: Mass Air Units")
        print("   Counter strategy: Vikings + Marines + Ravens for detection")
        unit_request.add_unit_requirement(UnitTypeId.VIKINGFIGHTER, 12)
        unit_request.add_unit_requirement(UnitTypeId.MARINE, 20)
        unit_request.add_unit_requirement(UnitTypeId.RAVEN, 2)  # Tech lab unit!
        unit_request.add_building_requirement(UnitTypeId.STARPORT, 3)
        unit_request.add_building_requirement(UnitTypeId.BARRACKS, 4)
        
    elif enemy_composition == "heavy_armor":
        # Enemy has heavy armored units - need siege tanks and marauders
        print("🎯 Enemy detected: Heavy Armored Units")
        print("   Counter strategy: Siege Tanks + Marauders (both need tech labs!)")
        unit_request.add_unit_requirement(UnitTypeId.SIEGETANK, 8)  # Tech lab unit!
        unit_request.add_unit_requirement(UnitTypeId.MARAUDER, 15)  # Tech lab unit!
        unit_request.add_unit_requirement(UnitTypeId.SCV, 50)  # Test SCV production
        unit_request.add_building_requirement(UnitTypeId.FACTORY, 2)
        unit_request.add_building_requirement(UnitTypeId.BARRACKS, 3)
        
    elif enemy_composition == "swarm":
        # Enemy has many weak units - need splash damage
        print("🎯 Enemy detected: Swarm Units")
        print("   Counter strategy: Hellions + Marines + some Siege Tanks")
        unit_request.add_unit_requirement(UnitTypeId.HELLION, 8)  # No tech lab needed
        unit_request.add_unit_requirement(UnitTypeId.MARINE, 25)  # No tech lab needed
        unit_request.add_unit_requirement(UnitTypeId.SIEGETANK, 4)  # Tech lab unit!
        unit_request.add_building_requirement(UnitTypeId.FACTORY, 2)
        unit_request.add_building_requirement(UnitTypeId.BARRACKS, 5)
    
    else:
        print("🎯 No specific enemy threat detected")
        print("   Using default build order")


class MockGameState:
    """Mock game state to simulate current unit counts"""
    
    def __init__(self):
        self.current_units = {
            UnitTypeId.MARINE: 5,
            UnitTypeId.MARAUDER: 0,
            UnitTypeId.VIKINGFIGHTER: 1,
            UnitTypeId.SIEGETANK: 0,
            UnitTypeId.HELLION: 2,
            UnitTypeId.RAVEN: 0,
            UnitTypeId.SCV: 20,  # Test SCV production
        }
        
        self.current_buildings = {
            UnitTypeId.BARRACKS: 1,
            UnitTypeId.FACTORY: 1,
            UnitTypeId.STARPORT: 1,
            UnitTypeId.COMMANDCENTER: 1,
            UnitTypeId.ORBITALCOMMAND: 0,
            UnitTypeId.PLANETARYFORTRESS: 0,
        }
        
        self.current_addons = {
            UnitTypeId.BARRACKSTECHLAB: 0,
            UnitTypeId.FACTORYTECHLAB: 0,
            UnitTypeId.STARPORTTECHLAB: 0,
        }
    
    def get_unit_count(self, unit_type: UnitTypeId) -> int:
        return self.current_units.get(unit_type, 0)
    
    def get_building_count(self, building_type: UnitTypeId) -> int:
        return self.current_buildings.get(building_type, 0)
    
    def get_addon_count(self, addon_type: UnitTypeId) -> int:
        return self.current_addons.get(addon_type, 0)


def simulate_adaptive_build_priority(unit_request: UnitCounterRequest, game_state: MockGameState):
    """
    Simulate how the adaptive build order would prioritize unit construction
    based on current vs required ratios and tech lab requirements.
    """
    if not unit_request.has_requirements():
        print("📋 No counter requirements - using default build order")
        return
    
    print("\n📋 Adaptive Build Order Analysis:")
    print("=" * 50)
    
    # Tech lab requirements function (copied from adaptive build order)
    def get_required_addon_for_unit(unit_type: UnitTypeId):
        tech_lab_units = {
            UnitTypeId.MARAUDER: UnitTypeId.BARRACKSTECHLAB,
            UnitTypeId.GHOST: UnitTypeId.BARRACKSTECHLAB,
            UnitTypeId.CYCLONE: UnitTypeId.FACTORYTECHLAB,
            UnitTypeId.SIEGETANK: UnitTypeId.FACTORYTECHLAB,
            UnitTypeId.THOR: UnitTypeId.FACTORYTECHLAB,
            UnitTypeId.RAVEN: UnitTypeId.STARPORTTECHLAB,
            UnitTypeId.BANSHEE: UnitTypeId.STARPORTTECHLAB,
            UnitTypeId.BATTLECRUISER: UnitTypeId.STARPORTTECHLAB,
        }
        return tech_lab_units.get(unit_type, None)
    
    # Calculate unit priorities based on ratios
    unit_priorities = []
    for unit_type, required_count in unit_request.required_units.items():
        current_count = game_state.get_unit_count(unit_type)
        if current_count < required_count:
            ratio = current_count / max(1, required_count)
            needed = required_count - current_count
            tech_lab_needed = get_required_addon_for_unit(unit_type)
            unit_priorities.append((ratio, unit_type, current_count, required_count, needed, tech_lab_needed))
    
    # Sort by ratio (lowest ratio = highest priority)
    unit_priorities.sort(key=lambda x: x[0])
    
    print("Unit Build Priorities (lowest ratio = highest priority):")
    for i, (ratio, unit_type, current, required, needed, tech_lab) in enumerate(unit_priorities, 1):
        unit_name = unit_type.name
        tech_lab_info = f" (needs {tech_lab.name})" if tech_lab else " (no tech lab)"
        print(f"  {i}. {unit_name:<15} | Current: {current:2d} | Required: {required:2d} | Ratio: {ratio:.2f} | Need: {needed:2d}{tech_lab_info}")
    
    # Check production capacity
    print("\nProduction Capacity Analysis:")
    for building_type, required_count in unit_request.required_buildings.items():
        current_count = game_state.get_building_count(building_type)
        building_name = building_type.name
        if current_count < required_count:
            print(f"  ⚠️  {building_name:<15} | Current: {current_count} | Required: {required_count} | Need to build: {required_count - current_count}")
        else:
            print(f"  ✅ {building_name:<15} | Current: {current_count} | Required: {required_count} | Sufficient capacity")
    
    # Check tech lab requirements
    print("\nTech Lab Requirements:")
    tech_labs_needed = set()
    for unit_type, required_count in unit_request.required_units.items():
        current_count = game_state.get_unit_count(unit_type)
        if current_count < required_count:
            tech_lab = get_required_addon_for_unit(unit_type)
            if tech_lab:
                tech_labs_needed.add(tech_lab)
    
    if tech_labs_needed:
        for tech_lab in tech_labs_needed:
            current_addons = game_state.get_addon_count(tech_lab)
            # Simple heuristic: need at least 1 tech lab for every 5 units
            needed_addons = 1  # Simplified for demo
            addon_name = tech_lab.name
            if current_addons < needed_addons:
                print(f"  ⚠️  {addon_name:<15} | Current: {current_addons} | Need to build: {needed_addons - current_addons}")
            else:
                print(f"  ✅ {addon_name:<15} | Current: {current_addons} | Sufficient")
    else:
        print("  ✅ No tech labs required for current unit requests")


def main():
    """Main demonstration function"""
    print("🎮 Adaptive Build Order Demonstration")
    print("=" * 60)
    
    # Initialize our systems
    unit_request = UnitCounterRequest()
    game_state = MockGameState()
    
    print("\n🏗️  Current Game State:")
    print(f"   Units: {game_state.current_units}")
    print(f"   Buildings: {game_state.current_buildings}")
    
    # Test different enemy compositions
    enemy_scenarios = ["mass_air", "heavy_armor", "swarm", "balanced"]
    
    for i, scenario in enumerate(enemy_scenarios, 1):
        print(f"\n{'='*60}")
        print(f"📊 Scenario {i}: {scenario.replace('_', ' ').title()}")
        print(f"{'='*60}")
        
        # Simulate enemy analysis and counter determination
        simulate_counter_logic(scenario, unit_request)
        
        # Show how adaptive build order would respond
        simulate_adaptive_build_priority(unit_request, game_state)
    
    print(f"\n{'='*60}")
    print("✨ Demonstration complete!")
    print("\n💡 Key Features Demonstrated:")
    print("   • Dynamic counter unit selection based on enemy composition")
    print("   • Ratio-based build prioritization (builds most needed units first)")
    print("   • Production capacity planning (ensures enough buildings)")
    print("   • Tech lab requirement checking (Siege Tanks need Factory Tech Labs)")
    print("   • SCV production from Command Centers and upgrades")
    print("   • Fallback to default build order when no threats detected")
    print("\n🔮 Future Integration:")
    print("   • Enemy composition analysis will be implemented separately")
    print("   • This system provides the framework for adaptive responses")
    print("   • Existing bot tactics and micro remain unchanged")


if __name__ == "__main__":
    main()