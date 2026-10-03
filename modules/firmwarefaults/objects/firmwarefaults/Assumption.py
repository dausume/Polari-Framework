"""
@module firmwarefaults.objects.firmwarefaults.Assumption

Assumption — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Assumption(treeObject):
    """What it is: Something firmware silently relies on — "a 32-bit read of g_ms is atomic", "every message arrives",
    "one edge, one interrupt", "a write completes" (FIRMWARE_SCENARIO_PLAN.md §0/§1). A fault BREAKS one; a technique
    RESTORES one. `who_relies` is the code that depends on it (file + symbol), `checkable_by` how it can be checked:
    a scenario on the twin, a static rule, or a formal tier.
    Related concepts: `FirmwareFault.assumption_broken`, `Technique.restores`, `Scenario.breaks`.
    """

    plain_words = ('An assumption is something a program quietly counts on being true, for example that a message always '
                   'arrives. Faults happen when an assumption turns out to be false.')

    @treeObjectInit
    def __init__(self, name: str = '', statement: str = '', holder: str = '', who_relies: str = '', checkable_by: str = 'scenario',
                 holds_in_shipped: str = 'yes', provenance: str = '', notes: str = '', manager=None):
        self.name = name
        self.statement = statement  # in plain words
        self.holder = holder  # FirmwareBuild / FirmwareVariant / board template the assumption is about
        self.who_relies = who_relies  # file:symbol that depends on it
        self.checkable_by = checkable_by  # scenario | static | formal
        self.holds_in_shipped = holds_in_shipped  # yes | no | n/a — whether the shipped UNO firmware already makes it true
        self.provenance = provenance
        self.notes = notes
