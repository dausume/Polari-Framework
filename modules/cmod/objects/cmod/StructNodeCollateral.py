"""
@module cmod.objects.cmod.StructNodeCollateral

StructNodeCollateral - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNodeCollateral(treeObject):
    """What it is: ONE MEASURABLE EFFECT OF A NODE'S CHANGE OUTSIDE THE STRUCTS - a pin's level, a net's current, a part's temperature rise, a frame's
    bytes on the wire, or the timing from the edge's start to the change - with the engine that can measure it (the twin's pin trace, ngspice, the
    Cauer ladder; a scope on hardware) and the bound it is checked against. Collaterals are what the physics engines are for; a node with none runs on
    the twin alone. `source` says whether a person declared it or the derivation did (from a reads-field assertion's pins, a sends-to-bridge).
    Related concepts: `StructNode` (the parent), `CatomAssertion`, instruments `ScopeChannel`, pcb `PartThermalModel`.
    """

    plain_words = 'A collateral is something you could put a probe on when this node is reached - a pin, a current, a temperature, a frame.'

    @treeObjectInit
    def __init__(self, name: str = '', node: str = '', kind: str = 'pin-level', signal: str = '', engine: str = 'twin', bound: str = '', source: str = 'derived',
                 notes: str = '', manager=None):
        self.name = name        # '<node>:<kind>:<signal>'
        self.node = node        # a StructNode name
        self.kind = kind        # pin-level | net-current | temperature | frame | timing
        self.signal = signal    # the pin (PD6), the net, the part ref, the bridge
        self.engine = engine    # twin | ngspice | cauer | scope
        self.bound = bound      # 'high' | '<= 20 mA' | '<= 45 C' | 'within 60 ms' | ''
        self.source = source    # derived | person
        self.notes = notes
