"""
@module aquaponics.objects.vermicompost.CompostLoopDefinition

Row class CompostLoopDefinition of the aquaponics module — one class per file (design §7), split
from vermicompost_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CompostLoopDefinition(treeObject):
    """Binds a compost bin + a pot system + the mode into one runnable,
    rankable configuration (mirrors PotSystemDefinition)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        bin_name: str = '',
        # The PotSystemDefinition whose water this bin enriches.
        pot_system_name: str = '',
        # Overrides the bin's mode when set (else the bin's mode).
        mode: str = '',
        # Assumed loop flow (L/hr) pending aqp-3; a knob so aqp-7 runs
        # independently. When the bound pot system's water carries
        # flow_rate_l_per_hr, the analysis prefers that.
        assumed_flow_l_per_hr: float = 1.5,
        # Persisted enrichment snapshot (JSON) — simulate writes it;
        # scoring binds to it. Empty until first computed.
        enrichment_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.bin_name = bin_name
        self.pot_system_name = pot_system_name
        self.mode = mode
        self.assumed_flow_l_per_hr = assumed_flow_l_per_hr
        self.enrichment_result_json = enrichment_result_json
        self.provenance_id = provenance_id
        self.notes = notes
