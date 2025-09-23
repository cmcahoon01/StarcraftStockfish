from typing import Set, List

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sharpy.plans.acts import ActBase
from sharpy.plans.acts.terran import MorphOrbitals

class StockMorphCommands(ActBase):
    def __init__(self, target_bases=None):
        super().__init__()
        if target_bases is None:
            target_bases = [2]
        self.target_bases = target_bases

    async def execute(self) -> bool:
        planetaries_needed = len(self.target_bases)
        command_centers = self.cache.own(UnitTypeId.COMMANDCENTER)
        orbitals = self.cache.own(UnitTypeId.ORBITALCOMMAND)
        planetary_forts = self.cache.own(UnitTypeId.PLANETARYFORTRESS)
        centers = command_centers | orbitals | planetary_forts
        centers = centers.ready.sorted_by_distance_to(
            self.zone_manager.own_main_zone.center_location
        )
        need_transform = []
        for i, center in enumerate(centers):
            if i + 1 in self.target_bases:
                if center.type_id == UnitTypeId.COMMANDCENTER:
                    need_transform.append(center)
                elif center.type_id == UnitTypeId.PLANETARYFORTRESS:
                    planetaries_needed -= 1

        ignore_tags: Set[int] = set()
        print(f"Planetary forts needed: {planetaries_needed}, have {len(planetary_forts)}")
        for target in need_transform:  # type: Unit
            if target.orders and target.orders[0].ability.id == AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS:
                ignore_tags.add((target.tag))
                continue
            if target.tag in ignore_tags:
                continue
            if self.knowledge.can_afford(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS):
                print(target(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS, subtract_cost=True))
                ignore_tags.add(target.tag)
                planetaries_needed -= 1
                print(f"Transforming {target.type_id} to Planetary Fortress")
            else:
                self.knowledge.reserve_costs(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS)
                print(f"Cannot afford Planetary Fortress upgrade, have {self.ai.minerals}, need 150")
                print(f"Cannot afford Planetary Fortress upgrade, have {self.ai.vespene}, need 150")
                print(f"Can afford: {self.knowledge.can_afford(AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS)}")

        if planetaries_needed <= 0:
            MorphOrbitals()

        if len(ignore_tags) < len(need_transform):
            return False
        return True
