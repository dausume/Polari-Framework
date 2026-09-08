"""
@module computers.objects.computers_ports.InterconnectDefinition

Row class InterconnectDefinition of the computers module — one class per file (design §7), split
from computers_ports_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class InterconnectDefinition(treeObject):
    """One connector/port standard — the matching token between a
    part's ports_provided and another's ports_required."""

    @treeObjectInit
    def __init__(
        self,
        # The matching token ('usb-c', 'ddr4-dimm', 'pcie-x16').
        name: str = '',
        display_name: str = '',
        # socket | slot | port | header | connector | mount
        kind: str = 'port',
        # data | power | data+power
        carries: str = 'data',
        # internal (inside the case) | external (a case-face port)
        attachment: str = 'internal',
        summary: str = '',
        # The honest gap for this token today.
        gaps_note: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.carries = carries
        self.attachment = attachment
        self.summary = summary
        self.gaps_note = gaps_note
        self.published = published
        self.is_prior = is_prior
        self.notes = notes
