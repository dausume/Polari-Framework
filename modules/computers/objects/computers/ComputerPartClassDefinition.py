"""
@module computers.objects.computers.ComputerPartClassDefinition

Row class ComputerPartClassDefinition of the computers module — one class per file (design §7), split
from computers_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ComputerPartClassDefinition(treeObject):
    """One part KIND's declared-spec vocabulary + gate wiring."""

    @treeObjectInit
    def __init__(
        self,
        # The computerparts PART_KINDS key ('storage', 'gpu', ...).
        name: str = '',
        display_name: str = '',
        summary: str = '',
        # JSON list of {field, unit, meaning} — the specs a part
        # of this kind is EXPECTED to declare on its specs_json.
        declared_specs_json: str = '[]',
        # JSON list of {field, gate, counterpart} — which declared
        # specs participate in which assembly gate, against which
        # other kind ('socket' on cpu <-> motherboard, ...).
        interface_specs_json: str = '[]',
        # The honest gap: what stays unverified today and what
        # declaring it would start answering.
        gaps_note: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.summary = summary
        self.declared_specs_json = declared_specs_json
        self.interface_specs_json = interface_specs_json
        self.gaps_note = gaps_note
        self.published = published
        self.is_prior = is_prior
        self.notes = notes
