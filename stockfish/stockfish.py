from sc2.data import Race
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sharpy.knowledges import KnowledgeBot, Knowledge
from sharpy.plans.tactics.harass import Harass
from sharpy.plans.terran import *
from sharpy.plans.tactics.lift_buildings import LiftBuildings
from stockfish.orders.banshee_harass import BansheeHarass
from stockfish.orders.zone_gather_stock import PlanZoneGatherStock

class StockBuildOrder(BuildOrder):
    def __init__(self, knowledge: Knowledge):
        class EnemyIs(RequireBase):
            def __init__(self, race):
                super().__init__()
                self.race = race
            def check(self) -> bool:
                return knowledge.ai.enemy_race.value == self.race.value
        class EnemyIsNot(RequireBase):
            def __init__(self, race):
                super().__init__()
                self.race = race
            def check(self) -> bool:
                return knowledge.ai.enemy_race.value != self.race.value

        build_steps_scv = [
            Step(
                None,
                ActUnit(UnitTypeId.SCV, UnitTypeId.COMMANDCENTER, 16 + 6),
                skip=UnitExists(UnitTypeId.COMMANDCENTER, 2),
            ),
            Step(None, ActUnit(UnitTypeId.SCV, UnitTypeId.COMMANDCENTER, 32 + 12)),
        ]

        build_steps_buildings = [
            Step(Supply(13), GridBuilding(UnitTypeId.SUPPLYDEPOT, 1)),
            # Step(UnitReady(UnitTypeId.SUPPLYDEPOT, 0.95), DefensiveBuilding(UnitTypeId.BARRACKS, DefensePosition.WallBarracks, 0)),
            Step(UnitReady(UnitTypeId.SUPPLYDEPOT, 0.95), GridBuilding(UnitTypeId.BARRACKS, 1)),
            StepBuildGas(1, Supply(16)),
            Step(None, MorphOrbitals(1), skip_until=UnitReady(UnitTypeId.BARRACKS, 1)),
            Expand(2),
            Step(Supply(16), GridBuilding(UnitTypeId.SUPPLYDEPOT, 2)),
            DefensiveBuilding(UnitTypeId.BUNKER, DefensePosition.Entrance, 1),
            StepBuildGas(2, UnitExists(UnitTypeId.MARINE, 1, include_pending=True)),
            Step(None, GridBuilding(UnitTypeId.FACTORY, 1), skip_until=UnitReady(UnitTypeId.BARRACKS, 1)),
            Step(None, GridBuilding(UnitTypeId.STARPORT, 1), skip_until=UnitReady(UnitTypeId.FACTORY, 1)),
            Step(None, BuildAddon(UnitTypeId.STARPORTTECHLAB, UnitTypeId.STARPORT, 1)),
            Step(None, GridBuilding(UnitTypeId.ENGINEERINGBAY, 1)),
            Step(None, GridBuilding(UnitTypeId.FACTORY, 2)),
            Step(None, Expand(3), skip_until=RequireCustom(self.should_expand)),
            Step(
                None,
                Expand(4),
                skip_until=All([RequireCustom(self.should_expand), UnitReady(UnitTypeId.COMMANDCENTER, 3)]),
            ),
            BuildGas(3),
            BuildGas(4),
            Step(None, GridBuilding(UnitTypeId.BARRACKS, 2)),
            Step(None, BuildAddon(UnitTypeId.BARRACKSTECHLAB, UnitTypeId.BARRACKS, 1)),
            Step(None, GridBuilding(UnitTypeId.ARMORY, 2)),
            Step(None, GridBuilding(UnitTypeId.BARRACKS, 5)),
            Step(None, BuildAddon(UnitTypeId.BARRACKSREACTOR, UnitTypeId.BARRACKS, 3)),
            Step(None, GridBuilding(UnitTypeId.ENGINEERINGBAY, 2)),
            Step(None, BuildGas(6), skip_until=UnitExists(UnitTypeId.COMMANDCENTER, 1) or UnitExists(UnitTypeId.PLANETARYFORTRESS, 2)),
            Step(None, GridBuilding(UnitTypeId.FACTORY, 6)),
        ]

        need_detection = [
            Step(Any([EnemyBuildingExists(UnitTypeId.DARKSHRINE),
                        EnemyUnitExistsAfter(UnitTypeId.DARKTEMPLAR),
                        EnemyUnitExistsAfter(UnitTypeId.BANSHEE),]),None),
            Step(UnitReady(UnitTypeId.STARPORT, 1), ActUnit(UnitTypeId.RAVEN, UnitTypeId.STARPORT, 1, priority=True)),
        ]

        air_counter = [
            Step(Any([EnemyUnitExistsAfter(UnitTypeId.TEMPEST),
                      EnemyUnitExistsAfter(UnitTypeId.VOIDRAY),
                      EnemyUnitExistsAfter(UnitTypeId.LIBERATOR),
                      EnemyUnitExistsAfter(UnitTypeId.BATTLECRUISER),
                      EnemyUnitExistsAfter(UnitTypeId.MUTALISK),
                      EnemyUnitExistsAfter(UnitTypeId.BROODLORD)]),None),
            Step(None, DefensiveBuilding(UnitTypeId.MISSILETURRET, DefensePosition.CenterMineralLine, 1)),
            Step(None, DefensiveBuilding(UnitTypeId.MISSILETURRET, DefensePosition.CenterMineralLine, 0)),
            Step(None, GridBuilding(UnitTypeId.STARPORT, 4)),
            Step(UnitReady(UnitTypeId.STARPORT, 1), ActUnit(UnitTypeId.VIKINGFIGHTER, UnitTypeId.STARPORT, 12, priority=True)),
        ]


        build_steps_harass = [
            Step(UnitReady(UnitTypeId.BARRACKS, 1), ActUnit(UnitTypeId.REAPER, UnitTypeId.BARRACKS, 1),
                 skip=Any([EnemyIs(Race.Terran), UnitExists(UnitTypeId.REAPER, 1, include_killed=True)])),
            Step(UnitExists(UnitTypeId.FACTORY, 1), ActUnit(UnitTypeId.HELLION, UnitTypeId.FACTORY, 2),
                 skip=Any([EnemyIsNot(Race.Zerg), UnitExists(UnitTypeId.HELLION, 2, include_killed=True)])),
            Step(UnitReady(UnitTypeId.STARPORTTECHLAB, 1), ActUnit(UnitTypeId.BANSHEE, UnitTypeId.STARPORT, 2, priority=True)),
            Step(None, ActUnit(UnitTypeId.CYCLONE, UnitTypeId.FACTORY, 3)),
        ]

        build_steps_mech = [
            Step(UnitReady(UnitTypeId.FACTORYTECHLAB, 1), ActUnit(UnitTypeId.SIEGETANK, UnitTypeId.FACTORY, 20, priority=True)),
        ]

        build_steps_marines = [
            Step(UnitReady(UnitTypeId.BARRACKS, 1), ActUnit(UnitTypeId.MARINE, UnitTypeId.BARRACKS, 4)),
            Step(None, ActUnit(UnitTypeId.MEDIVAC, UnitTypeId.STARPORT, 2), skip_until=UnitExists(UnitTypeId.MARINE, 10, include_pending=True)),
            Step(Minerals(250), ActUnit(UnitTypeId.MARINE, UnitTypeId.BARRACKS, 100)),
        ]

        morph_commands = [
            # Step(None, MorphOrbitals(2), skip_until=UnitReady(UnitTypeId.BARRACKS, 1)),
            Step(UnitReady(UnitTypeId.ENGINEERINGBAY, 1), MorphPlanetary(1)),
            Step(None, MorphOrbitals(2)),
        ]

        tech = [
            Step(None, Tech(UpgradeId.BANSHEECLOAK), skip_until=UnitExists(UnitTypeId.STARPORTTECHLAB, 1)),
            Step(None, Tech(UpgradeId.SHIELDWALL), skip_until=UnitExists(UnitTypeId.BARRACKSTECHLAB, 1)),
            Step(None, Tech(UpgradeId.STIMPACK), skip_until=UnitExists(UnitTypeId.BARRACKSTECHLAB, 1)),
            Step(None, Tech(UpgradeId.TERRANVEHICLEWEAPONSLEVEL1)),
            Step(None, Tech(UpgradeId.TERRANINFANTRYARMORSLEVEL1)),
            Step(None, Tech(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)),
            Step(None, Tech(UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1)),
            # Step(None, Tech(UpgradeId.DRILLCLAWS), skip_until=UnitExists(UnitTypeId.FACTORYTECHLAB, 1)),
            Step(None, Tech(UpgradeId.TERRANVEHICLEWEAPONSLEVEL2)),
            Step(None, Tech(UpgradeId.TERRANINFANTRYARMORSLEVEL2)),
            Step(None, Tech(UpgradeId.TERRANINFANTRYWEAPONSLEVEL2)),
            Step(None, Tech(UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2)),
            Step(None, Tech(UpgradeId.TERRANVEHICLEWEAPONSLEVEL3)),
            Step(None, Tech(UpgradeId.TERRANINFANTRYARMORSLEVEL3)),
            Step(None, Tech(UpgradeId.TERRANINFANTRYWEAPONSLEVEL3)),
            Step(None, Tech(UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3)),
                    ]

        build_order = [
            build_steps_scv,
            need_detection,
            air_counter,
            build_steps_buildings,
            tech,
            morph_commands,
            build_steps_harass,
            build_steps_mech,
            build_steps_marines,
            BuildAddon(UnitTypeId.FACTORYTECHLAB, UnitTypeId.FACTORY, 99),
            Step(None, AutoDepot(), skip_until=Supply(28))
        ]
        super().__init__(build_order)

    @staticmethod
    def should_expand(knowledge):
        excess = 0
        for zone in knowledge.zone_manager.our_zones:
            if zone.our_townhall is not None:
                excess += zone.our_townhall.surplus_harvesters

        return excess > 5

class Stockfish(KnowledgeBot):
    def __init__(self):
        super().__init__("Stockfish")

    @property
    def my_race(self):
        return Race.Terran

    async def create_plan(self) -> BuildOrder:
        self.attack = PlanZoneAttack(50)
        speed_mine = Step(None, SpeedMining())

        tactics = [
            MineOpenBlockedBase(),
            PlanCancelBuilding(),
            # LiftBuildings(), # Broken
            LowerDepots(),
            PlanZoneDefense(),
            ScanEnemy(120),
            CallMule(),
            DistributeWorkers(),
            ManTheBunkers(),
            speed_mine,
            Repair(),
            ContinueBuilding(),
            PlanZoneGatherStock(),
            BansheeHarass(),
            Harass(),
            self.attack,
            PlanFinishEnemy(),
        ]
        return BuildOrder([StockBuildOrder(self.knowledge), tactics])
