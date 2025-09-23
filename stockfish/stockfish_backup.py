from sc2.data import Race
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sharpy.knowledges import KnowledgeBot
from sharpy.plans.terran import *
from stockfish.orders.banshee_harass import BansheeHarass
from stockfish.orders.zone_gather_stock import PlanZoneGatherStock

class StockBuildOrder(BuildOrder):
    def __init__(self):
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
            Step(UnitReady(UnitTypeId.SUPPLYDEPOT, 0.95), GridBuilding(UnitTypeId.BARRACKS, 1)),
            StepBuildGas(1, Supply(16)),
            DefensiveBuilding(UnitTypeId.BUNKER, DefensePosition.Entrance, 0),
            Step(UnitReady(UnitTypeId.BUNKER), Expand(2)),
            StepBuildGas(2, UnitExists(UnitTypeId.MARINE, 1, include_pending=True)),
            Step(None, GridBuilding(UnitTypeId.FACTORY, 1), skip_until=UnitReady(UnitTypeId.BARRACKS, 1)),
            Step(None, GridBuilding(UnitTypeId.ENGINEERINGBAY, 1), skip_until=UnitReady(UnitTypeId.BARRACKS, 1)),
            Step(None, MorphPlanetary(1), skip_until=UnitReady(UnitTypeId.ENGINEERINGBAY, 1)),
            Step(UnitReady(UnitTypeId.FACTORY, 1), GridBuilding(UnitTypeId.STARPORT, 1)),
            Step(
                UnitReady(UnitTypeId.STARPORT, 1), BuildAddon(UnitTypeId.STARPORTTECHLAB, UnitTypeId.STARPORT, 1),
            ),
            Step(None, Tech(UpgradeId.BANSHEECLOAK)),
            Step(
                None,
                BuildAddon(UnitTypeId.FACTORYTECHLAB, UnitTypeId.FACTORY, 1),
                skip_until=UnitReady(UnitTypeId.FACTORY, 1),
            ),
            Step(None, GridBuilding(UnitTypeId.FACTORY, 2)),
            Step(None, BuildAddon(UnitTypeId.FACTORYTECHLAB, UnitTypeId.FACTORY, 2)),
            Step(None, Expand(3), skip_until=RequireCustom(self.should_expand)),
            Step(
                None,
                Expand(4),
                skip_until=All([RequireCustom(self.should_expand), UnitReady(UnitTypeId.COMMANDCENTER, 3)]),
            ),
            # BuildStep(None, GridBuilding(UnitTypeId.FACTORY, 3)),
            BuildGas(3),
            Step(None, GridBuilding(UnitTypeId.BARRACKS, 2)),
            Step(None, BuildAddon(UnitTypeId.BARRACKSTECHLAB, UnitTypeId.BARRACKS, 1)),
            Step(None, Tech(UpgradeId.SHIELDWALL)),
            BuildGas(4),
            # BuildStep(None, GridBuilding(UnitTypeId.ARMORY, 1)),
            Step(None, GridBuilding(UnitTypeId.BARRACKS, 5)),
            Step(None, BuildAddon(UnitTypeId.BARRACKSREACTOR, UnitTypeId.BARRACKS, 3)),
            Step(None, GridBuilding(UnitTypeId.FACTORY, 3)),
            Step(None, BuildAddon(UnitTypeId.FACTORYTECHLAB, UnitTypeId.FACTORY, 3)),
        ]

        need_detection = [
            Step(Any([EnemyBuildingExists(UnitTypeId.DARKSHRINE),
                        EnemyUnitExistsAfter(UnitTypeId.DARKTEMPLAR),
                        EnemyUnitExistsAfter(UnitTypeId.BANSHEE),]),None),
            Step(UnitReady(UnitTypeId.STARPORT, 1), ActUnit(UnitTypeId.RAVEN, UnitTypeId.STARPORT, 1, priority=True)),
        ]

        build_steps_mech = [
            Step(UnitExists(UnitTypeId.BANSHEE, count=0, include_killed=True) or
                 UnitExists(UnitTypeId.BANSHEE, count=1, include_killed=True),
                    ActUnit(UnitTypeId.BANSHEE, UnitTypeId.STARPORT, 2, priority=True)),
            Step(Minerals(300), ActUnit(UnitTypeId.MEDIVAC, UnitTypeId.STARPORT, 2)),
            # Step(UnitExists(UnitTypeId.FACTORY, 1), ActUnit(UnitTypeId.HELLION, UnitTypeId.FACTORY, 2)),
            Step(UnitReady(UnitTypeId.FACTORYTECHLAB, 1), ActUnit(UnitTypeId.SIEGETANK, UnitTypeId.FACTORY, 20))
        ]

        build_steps_marines = [
            Step(UnitReady(UnitTypeId.BARRACKS, 1), ActUnit(UnitTypeId.MARINE, UnitTypeId.BARRACKS, 4)),
            Step(Minerals(250), ActUnit(UnitTypeId.MARINE, UnitTypeId.BARRACKS, 100)),
        ]

        build_order = [
            build_steps_scv,
            need_detection,
            build_steps_buildings,
            Step(None, MorphOrbitals(1), skip_until=UnitReady(UnitTypeId.BARRACKS, 1)),
            Step(None, MorphPlanetary(1), skip_until=UnitReady(UnitTypeId.ENGINEERINGBAY, 1) and UnitReady(UnitTypeId.ORBITALCOMMAND, 0.1)),
            build_steps_mech,
            build_steps_marines,
            BuildAddon(UnitTypeId.FACTORYTECHLAB, UnitTypeId.FACTORY, 99),
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
        speed_mine = Step(None, SpeedMining(), lambda ai: ai.client.game_step < 5)

        tactics = [
            AutoDepot(),
            MineOpenBlockedBase(),
            PlanCancelBuilding(),
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
            self.attack,
            PlanFinishEnemy(),
        ]
        return BuildOrder([StockBuildOrder(), tactics])
