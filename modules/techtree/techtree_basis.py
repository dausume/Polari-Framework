"""
@cross-cutting
@module techtree.techtree_basis
@tags @xc:bindings

Tech Tree as data (tt-3, TECH_TREE_TOPOLOGY_PLAN Part B): a tech
tree is an EXPANSION of topology — the same node-logic graph where
the rectangular containers are TECHNOLOGIES instead of Polari
containers. Each technology carries up to four SEGMENTS (theory /
real / business / politics), filled by assignments that reference
modules (theory) or the tt-6 content objects (real / business /
politics). Completion is DERIVED — segments_present and
completion_level are computed by techtree_analysis, never hand-set
(the drift/observation idiom).

A complete baseline tree = the Open Source Economic Baseline (OSEB)
— the overall end goal of the whole Polari project.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - techtree.techtree_analysis / techtree.techtree_api
  - polari-platform-angular tech-tree render mode (tt-4)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Segment vocabulary + render colors (B1): blue theory, red real,
#: yellow business, purple politics. A segment renders ONLY when
#: populated by at least one assignment.
SEGMENT_KINDS = ('theory', 'real', 'business', 'politics')
SEGMENT_COLORS = {'theory': '#1e88e5', 'real': '#e53935',
                  'business': '#fdd835', 'politics': '#8e24aa'}


class TechTreeDefinition(treeObject):
    """One tech tree = one DOMAIN of technologies (tt-8): e.g.
    'Electronics / Microelectronics', 'Raw Supply Chain', 'Open
    Source Economy & Politics'. Configurable per org (B6): a
    business's tree is the set of technologies it depends on to do
    business. Trees flagged is_baseline are the OSEB's domain
    components — reaching the end of ALL of them, combined, is the
    Open Source Economic Baseline (baseline_report)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Display title ('' = derive from name), e.g.
        # 'Electronics / Microelectronics'.
        title: str = '',
        # The org/business this tree belongs to ('' = unowned/shared).
        owner: str = '',
        description: str = '',
        is_active: bool = False,
        # This tree is one of the OSEB's domain components; the
        # baseline is the COMBINATION of all such trees complete.
        is_baseline: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.owner = owner
        self.description = description
        self.is_active = is_active
        self.is_baseline = is_baseline
        self.notes = notes


class TechNode(treeObject):
    """One TECHNOLOGY in a tree — the rectangular container of the
    tech-tree render mode. segments_present + completion_level are
    DERIVED by techtree_analysis (never stored here)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<tree>/<technology>'.
        name: str = '',
        tree_name: str = '',
        # Display title ('' = derive from name).
        title: str = '',
        description: str = '',
        # JSON list of TechNode names this technology depends on —
        # the durable dependency statement; TechDependencyEdge rows
        # are derived from it (sync_edges) so designation has rows
        # to stamp, mirroring ModuleDependencyEdge.
        depends_on_json: str = '[]',
        # JSON layout hints for the renderer ({} = auto-placed).
        layout_hints_json: str = '{}',
        # tt-9: CROSS-TREE relationships — never edges (edges are
        # tree-scoped); a JSON list of {tree, node, relation} the
        # renderer shows as zoom-to chips naming the home tree
        # ('produces' / 'supplied-by' / ...).
        cross_refs_json: str = '[]',
        # mtt-2: DigitizedDataset names this technology needs to be
        # QUANTITATIVELY complete. A referenced dataset that is
        # missing, provisional, or points-empty surfaces as a DERIVED
        # data gap (digitize it -> the gap auto-clears). Structural
        # (theory) completion and data completeness are separate axes:
        # a node can be 'built' yet still carry open data asks.
        data_dependencies_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.tree_name = tree_name
        self.title = title
        self.description = description
        self.depends_on_json = depends_on_json
        self.layout_hints_json = layout_hints_json
        self.cross_refs_json = cross_refs_json
        self.data_dependencies_json = data_dependencies_json
        self.notes = notes


class TechSegment(treeObject):
    """Per-node, per-kind segment KNOB row: the weight a present
    segment contributes to node completion. Optional — an absent row
    means weight 1.0; presence/completion always derive from the
    assignments, never from this row."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<tech_node>:<kind>'.
        name: str = '',
        tech_node: str = '',
        tree_name: str = '',
        # SEGMENT_KINDS entry.
        kind: str = 'theory',
        weight: float = 1.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.tech_node = tech_node
        self.tree_name = tree_name
        self.kind = kind
        self.weight = weight
        self.notes = notes


class TechSegmentAssignment(treeObject):
    """The join that FILLS a segment (B2): one referenced item per
    row. What ref_name points at depends on segment_kind —
    theory: a Polari module id; real: a RealArtifact.name;
    business: a BusinessModelDefinition.name; politics: a
    PolicyDefinition.name. The done-criterion per kind lives in
    techtree_analysis (first-cut done-tests, evidence-bearing)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<tech_node>:<kind>:<ref_name>'.
        name: str = '',
        tech_node: str = '',
        tree_name: str = '',
        # SEGMENT_KINDS entry.
        segment_kind: str = 'theory',
        # The referenced module / artifact / business model / policy.
        ref_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.tech_node = tech_node
        self.tree_name = tree_name
        self.segment_kind = segment_kind
        self.ref_name = ref_name
        self.notes = notes


class TechDependencyEdge(treeObject):
    """tech_node DEPENDS-ON depends_on_tech, derived from
    TechNode.depends_on_json by sync_edges. Carries the same
    transient/primary designation as ModuleDependencyEdge (tt-1):
    a technology needed by N>1 others is solid under one primary
    dependent and a dashed transient copy under the rest."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<tech_node>-><depends_on_tech>'.
        name: str = '',
        tree_name: str = '',
        tech_node: str = '',
        depends_on_tech: str = '',
        is_primary: bool = False,
        is_transient: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.tree_name = tree_name
        self.tech_node = tech_node
        self.depends_on_tech = depends_on_tech
        self.is_primary = is_primary
        self.is_transient = is_transient
        self.notes = notes
