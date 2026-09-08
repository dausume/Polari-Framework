"""
@module cntfet.objects.cnt.AlignedCNTFETDevice

Row class AlignedCNTFETDevice of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AlignedCNTFETDevice(treeObject):
    """The composed one-tube device — references the decomposed
    objects by name. SIBLING of electrodevice's percolation-film
    FET (D5), never its successor; nothing here scales film results."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        polarity: str = 'n',
        material: str = '',
        geometry: str = '',
        gate_stack: str = '',
        contact: str = '',
        transport: str = '',
        parasitics: str = '',
        temperature_k: float = 300.0,
        manufacturing_regime: str = 'aggressively_scaled',
        # S3: which process set (cnt_process_basis rows sharing
        # this name) predicts the population around the targets.
        process_set: str = '',
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.polarity = polarity
        self.material = material
        self.geometry = geometry
        self.gate_stack = gate_stack
        self.contact = contact
        self.transport = transport
        self.parasitics = parasitics
        self.temperature_k = temperature_k
        self.manufacturing_regime = manufacturing_regime
        self.process_set = process_set
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes

    @property
    def figures_of_merit(self):
        """fi-2: the device's figures of merit + their characteristic
        ideals, computed LIVE from the derived model (never stored —
        a property is invisible to persistence, which walks
        __dict__). The generic scoring engine reaches these through
        objectRef bindings with path 'figures_of_merit.<key>'
        (cnt_scoring seeds); an underived device answers with a
        named refusal, not zeros."""
        from cntfet.cnt_scoring_seed import figures_of_merit
        return figures_of_merit(getattr(self, 'manager', None),
                                self.name)
