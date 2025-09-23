from sc2.ids.unit_typeid import UnitTypeId
from sharpy.combat import MicroRules
from terranbot.micro_banshees import MicroBanshees

class MicroRulesStock(MicroRules):
    def load_default_micro(self):
        self.unit_micros[UnitTypeId.BANSHEE] = MicroBanshees()
        super().load_default_micro()