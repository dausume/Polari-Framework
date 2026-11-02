"""
BenchSystem - one class per file (design section 7); bss-0 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5, "template").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BenchSystem(treeObject):
    """What it is: ONE BENCH CONCEPT AS A TEMPLATE - which Hardware System (a board family and a circuit with part choices open), which Firmware
    System (a cmod `CGraph`: catoms composed, isotopes open) and which `ThermalSystem` go together. A `BenchSolution` is this with every choice made:
    its Hardware, Firmware and Thermal Solutions must each name the System composed here, or the whole check says what does not match. The user's
    rule (2026-11-01): a System is the baseline template; a Solution is the finalized specific result, bound and simulated as a whole.
    Related concepts: `HardwareSystem`, cmod `CGraph`, `ThermalSystem`, `BenchSolution`.
    """

    plain_words = ('A bench system is the recipe for a kind of bench setup: which family of boards and circuit, which firmware design, and which '
                   'way of handling heat - before any specific part or value is chosen.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', hardware_system: str = '', firmware_system: str = '', thermal_system: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.title = title
        self.hardware_system = hardware_system  # a HardwareSystem name (the template; bss-0 D-bss-1)
        self.firmware_system = firmware_system  # a cmod CGraph name
        self.thermal_system = thermal_system    # a ThermalSystem name
        self.notes = notes
