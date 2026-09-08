"""
@module pspp.objects.research_tools.ResearchTool

Row class ResearchTool of the pspp module — one class per file (design §7), split
from research_tools_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ResearchTool(treeObject):
    """One buildable open-source research instrument."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        measures: str = '',
        # Plain-language: how it works + how you build it.
        how_plain: str = '',
        # JSON list of {part, tier, note} — the key components.
        parts_json: str = '[]',
        # Rollup accessibility (worst part tier) — ACCESSIBILITY_TIERS.
        accessibility_tier: str = 'common-industrial',
        # BUILD_DIFFICULTY entry.
        difficulty: str = 'moderate',
        # Plain safety note.
        safety: str = '',
        # JSON list of TOOL_DOMAINS it serves.
        domains_json: str = '[]',
        # What the reading DIRECTLY is vs what it only correlates with
        # ('' = it measures its quantity directly).
        correlation_caveat: str = '',
        # The tech-tree research node this backs.
        tech_node: str = '',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.measures = measures
        self.how_plain = how_plain
        self.parts_json = parts_json
        self.accessibility_tier = accessibility_tier
        self.difficulty = difficulty
        self.safety = safety
        self.domains_json = domains_json
        self.correlation_caveat = correlation_caveat
        self.tech_node = tech_node
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes
