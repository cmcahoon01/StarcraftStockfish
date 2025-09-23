from typing import Optional, Dict, Set

from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.upgrade_id import UpgradeId
from sharpy.interfaces import IZoneManager
from sharpy.knowledges import Knowledge
from sharpy.managers.core.roles import UnitTask
from sharpy.plans.acts import ActBase
from sc2.position import Point2
from sc2.unit import Unit
from sc2.ids.unit_typeid import UnitTypeId

class BansheeHarass(ActBase):
    """
    Selects a scout worker and performs basic scout sweep across
    start and expansion locations.
    """

    zone_manager: IZoneManager

    def __init__(self):
        super().__init__()
        self.banshee_tags: Dict[int, bool] = {}
        self.all_banshee_tags: Set[int] = set()
        self.can_harass = True
        self.dead_banshees = 0

    async def start(self, knowledge: Knowledge):
        await super().start(knowledge)
        self.zone_manager = knowledge.get_required_manager(IZoneManager)

    async def allocate_banshees(self):
        # check if cloaking is researched
        if not UpgradeId.BANSHEECLOAK in self.ai.state.upgrades or self.dead_banshees >= 2:
            return
        banshees = self.ai.units.of_type({UnitTypeId.BANSHEE}).tags_not_in(self.banshee_tags)
        for banshee in banshees:
            self.all_banshee_tags.add(banshee.tag)
            if banshee.health_percentage < 0.4 or banshee.energy_percentage < 0.1:
                continue
            self.banshee_tags[banshee.tag] = False
            self.roles.set_task(UnitTask.Harassing, banshee)

    async def deallocate_banshees(self):
        for tag in list(self.banshee_tags):
            banshee: Optional[Unit] = self.ai.units.find_by_tag(tag)
            if banshee is None or banshee.health <= 0:
                if tag in self.banshee_tags:
                    del self.banshee_tags[tag]
                continue
            if banshee.health_percentage < 0.3 or banshee.energy_percentage < 0.1 or self.dead_banshees >= 2 or not self.can_harass:
                if tag in self.banshee_tags:
                    del self.banshee_tags[tag]
                self.roles.set_task(UnitTask.Defending, banshee)
                self.combat.add_unit(banshee)
                continue

    async def control(self, banshee: Unit, target: Point2):
        relevant_enemies = self.ai.enemy_units.closer_than(15, banshee)
        reached_target = self.banshee_tags[banshee.tag]

        if not reached_target and banshee.position.distance_to(target) < 2:
            self.banshee_tags[banshee.tag] = True
            reached_target = True

        can_attack_air = False
        can_detect = False
        if not relevant_enemies.exists and not reached_target:
            banshee.move(target)
            return

        if relevant_enemies.filter(lambda unit: unit.can_attack_air).exists:
            can_attack_air = True
        if relevant_enemies.filter(lambda unit: unit.is_detector).exists:
            can_detect = True

        if not can_detect and can_attack_air:
            requested_mode = AbilityId.BEHAVIOR_CLOAKON_BANSHEE
        else:
            requested_mode = AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE

        if (can_detect and can_attack_air) or banshee.health_percentage < 0.5:
            threats = relevant_enemies.filter(lambda unit: unit.can_attack_air) | relevant_enemies.filter(
                lambda unit: unit.is_detector)
            if threats.exists:
                closest_threat = threats.closest_to(banshee)
                backstep: Point2 = banshee.position.towards(closest_threat.position, -5)
                backstep = self.pather.find_weak_influence_air(backstep, 4)
                banshee.move(backstep)
                return

        if banshee.has_buff(BuffId.BANSHEECLOAK) and requested_mode == AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE:
            banshee(AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE)
            return
        elif not banshee.has_buff(BuffId.BANSHEECLOAK) and requested_mode == AbilityId.BEHAVIOR_CLOAKON_BANSHEE:
            banshee(AbilityId.BEHAVIOR_CLOAKON_BANSHEE)
            return

        if not reached_target:
            banshee.move(target)
            return

        self.harass(banshee, relevant_enemies)

    def harass(self, unit: Unit, enemy_units):
        # Define worker types
        worker_types = {UnitTypeId.SCV, UnitTypeId.DRONE, UnitTypeId.PROBE}
        # Filter workers
        workers = enemy_units.filter(lambda u: u.type_id in worker_types and u.is_visible)
        if workers:
            target = min(workers, key=lambda u: (u.health, unit.distance_to(u)))
            return unit.attack(target)
        # Prioritize military: lowest health, then closest
        military = enemy_units.filter(
            lambda u: u.type_id not in worker_types and not u.is_structure and u.is_visible)
        if military:
            target = min(military, key=lambda u: (u.health, unit.distance_to(u)))
            return unit.attack(target)
        # No valid targets
        self.can_harass = False
        return None

    def count_dead_banshees(self):
        # Count dead banshees
        alive_banshees = self.ai.units.of_type({UnitTypeId.BANSHEE})
        self.dead_banshees = len(self.all_banshee_tags) - len(alive_banshees)

    async def execute(self) -> bool:
        await self.allocate_banshees()
        self.count_dead_banshees()
        await self.deallocate_banshees()

        if not self.banshee_tags:
            return True  # Non blocking

        for tag in self.banshee_tags:
            banshee: Optional[Unit] = self.ai.units.find_by_tag(tag)

            enemy_start = self.zone_manager.enemy_start_location
            if enemy_start is None:
                continue

            self.roles.refresh_task(banshee)

            worker_types = {
                UnitTypeId.SCV,
                UnitTypeId.DRONE,
                UnitTypeId.PROBE,
            }

            closest_workers = (
                self.ai.enemy_units.of_type(worker_types).closest_to(banshee)
                if self.ai.enemy_units.of_type(worker_types).exists
                else None
            )
            await self.control(banshee, enemy_start)

        return True
