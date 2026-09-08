"""
@module techtree.objects.techtree_content.RealArtifact

Row class RealArtifact of the techtree module — one class per file (design §7), split
from techtree_content_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class RealArtifact(treeObject):
    """One finalized physical design filling a REAL segment."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Where the geometry lives: a mathshapes/CAD-import ref.
        cad_ref: str = '',
        # Electronics/mechanical design data beyond the geometry.
        hardware_design_ref: str = '',
        # Proven to WORK — physical evidence, not simulation.
        proven: bool = False,
        # JSON evidence for `proven` (build logs, test reports).
        evidence_json: str = '[]',
        # JSON: how to BUY it (vendors, parts, price points).
        commercial_route_json: str = '{}',
        # JSON: how to MAKE it open-source (guide, tooling, BOM).
        self_manufacture_route_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.cad_ref = cad_ref
        self.hardware_design_ref = hardware_design_ref
        self.proven = proven
        self.evidence_json = evidence_json
        self.commercial_route_json = commercial_route_json
        self.self_manufacture_route_json = self_manufacture_route_json
        self.notes = notes
