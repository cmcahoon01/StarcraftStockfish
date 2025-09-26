from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sharpy.managers.core.roles import UnitTask
from sharpy.plans.tactics.terran import PlanZoneGatherTerran

class PlanZoneGatherStock(PlanZoneGatherTerran):
    async def execute(self) -> bool:
        random_variable = (self.ai.state.game_loop % 120) * 0.1
        random_variable *= 0.6
        unit: Unit
        if self.gather_point != self.gather_point_solver.gather_point:
            self.gather_set.clear()
            self.gather_point = self.gather_point_solver.gather_point
            main_ramp = self.zone_manager.own_main_zone.ramp
            if main_ramp and main_ramp.bottom_center.distance_to(self.gather_point) < 5:
                # Nudge gather point just a slightly further
                self.gather_point = self.gather_point.towards(main_ramp.bottom_center, -3)

        unit: Unit
        for unit in self.cache.own([UnitTypeId.BARRACKS, UnitTypeId.FACTORY]).tags_not_in(self.gather_set):
            # Rally point is set to prevent units from spawning on the wrong side of wall in
            pos: Point2 = unit.position
            pos = pos.towards(self.gather_point_solver.gather_point, 3)
            unit(AbilityId.RALLY_BUILDING, pos)
            self.gather_set.append(unit.tag)

        units = []
        units.extend(self.roles.idle)

        for unit in units:
            if unit.type_id.value == UnitTypeId.BANSHEE.value and self.roles.unit_role(unit) == UnitTask.Harassing:
                continue  # Skip Banshees
            harassing_types = {UnitTypeId.CYCLONE.value, UnitTypeId.HELLION.value, UnitTypeId.REAPER.value, UnitTypeId.BANSHEE.value}
            if unit.type_id.value in harassing_types:
                continue
            if self.unit_values.should_attack(unit):
                d = unit.position.distance_to(self.gather_point)
                if unit.type_id == UnitTypeId.SIEGETANK and d < random_variable:
                    ramp = self.zone_manager.expansion_zones[0].ramp
                    if unit.distance_to(ramp.bottom_center) > 5 and unit.distance_to(ramp.top_center) > 4:
                        unit(AbilityId.SIEGEMODE_SIEGEMODE)
                elif (d > 6.5 and unit.type_id != UnitTypeId.SIEGETANKSIEGED) or d > 9:
                    self.combat.add_unit(unit)

        for unit in self.roles.idle:
            if unit.type_id == UnitTypeId.WIDOWMINE:
                if unit.position.distance_to(self.gather_point) < 4 and unit.is_ready and not unit.is_burrowed:
                    unit(AbilityId.BURROWDOWN_WIDOWMINE)

        self.combat.execute(self.gather_point)
        return True  # Always non blocking
