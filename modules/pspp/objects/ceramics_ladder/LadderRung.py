"""
@module pspp.objects.ceramics_ladder.LadderRung

Row class LadderRung of the pspp module — one class per file (design §7), split
from ceramics_ladder_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LadderRung(treeObject):
    """One rung of the furnace escalation ladder."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        order: int = 0,
        # Furnace temperature this rung reaches, Celsius.
        max_temp_c: float = 0.0,
        heat_source: str = '',
        # JSON list of {sample, track, role} — the lining options
        # (CeramicSample names; track local|non-local). '' sample = a
        # non-ceramic lining (e.g. the geopolymer oven itself).
        lining_options_json: str = '[]',
        # The rung whose OUTPUT builds this furnace ('' = start).
        prerequisite_rung: str = '',
        # JSON list of {kind, ref, note} unlocked here — kind is
        # 'material' | 'capability'.
        unlocks_json: str = '[]',
        # The manufacturing-tools furnace TechNode this backs.
        tech_node: str = '',
        # 'thermal' (temperature is the gate) | 'atmosphere'
        # (controlled-atmosphere/catalyst is the real gate, not heat).
        gate_kind: str = 'thermal',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.max_temp_c = max_temp_c
        self.heat_source = heat_source
        self.lining_options_json = lining_options_json
        self.prerequisite_rung = prerequisite_rung
        self.unlocks_json = unlocks_json
        self.tech_node = tech_node
        self.gate_kind = gate_kind
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes
