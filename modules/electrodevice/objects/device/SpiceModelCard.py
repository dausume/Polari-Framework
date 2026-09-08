"""
@module electrodevice.objects.device.SpiceModelCard

Row class SpiceModelCard of the electrodevice module — one class per file (design §7), split
from device_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SpiceModelCard(treeObject):
    """The SPICE abstraction of one device — embeddable .subckt text
    generated from the derived parameters, with provenance in the
    comments so the netlist itself says where its numbers came from."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device_name: str = '',
        version: int = 0,
        card_text: str = '',
        derived_from_json: str = '{}',
        generated_at: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.version = version
        self.card_text = card_text
        self.derived_from_json = derived_from_json
        self.generated_at = generated_at
