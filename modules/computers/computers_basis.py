"""
@module computers.computers_basis

cmp-c (Dustin 2026-08-25): computer ASSEMBLY + use-case PROFILES
as their OWN app, separable from microchip creation and levels.
The module GROWS FROM computerparts (ai-8) rather than beside it:
ComputerPartDefinition stays the catalog row; what is new here is

  - ComputerPartClassDefinition (cmp-c-1): the component TAXONOMY
    as rows — per part kind, which specs the kind DECLARES, which
    of them feed assembly gates, and which gaps stay honestly
    unverified until someone declares them (the ai-8 discipline:
    'unverified — <spec> not declared' is an affordance, not a
    failure).
  - ComputerAssemblyDefinition (cmp-c-2): a named assembly
    wrapping a ComputerBuildDefinition, gated by the DFA-style
    named checks in computers_gates and viewable as a composition
    tree (interfaces are all designed-separable, so composition's
    own rule derives 'assembly' — materializing real composition
    rows is the later arch-8-style splice, pending Dustin's
    decision 1 confirmation).
  - ComputerProfileDefinition (cmp-c-3): a use case as DATA — a
    declared requirements floor (the ai-6 hosting-gauge shape) an
    assembly is scored against with evidence-bearing verdicts.
    Profiles are rows, never hardcoded (knobs ethos). The
    database-binding profile is DECLARE-ONLY v1: it records the
    residence intent; real topology hooks are the
    object-ownership arc's half.

@consumers
  - computers.computers_api (/api/computers)
  - computers.computers_gates / computers_fit (row reads)
  - polariServer defClassList (tables + CRUDE)
  - computers.selftest_computers
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


class ComputerAssemblyDefinition(treeObject):
    """A named computer assembly over one build's parts list."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('assembly-xeon-6338n').
        name: str = '',
        display_name: str = '',
        # The ComputerBuildDefinition this assembly realizes.
        build_ref: str = '',
        # Optional composition splice points (empty until the
        # materialization phase lands).
        archetype_ref: str = '',
        node_ref: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.build_ref = build_ref
        self.archetype_ref = archetype_ref
        self.node_ref = node_ref
        self.published = published
        self.is_prior = is_prior
        self.notes = notes


class ComputerProfileDefinition(treeObject):
    """A use case as a declared requirements floor (data row)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('profile-assistive-ai').
        name: str = '',
        display_name: str = '',
        # What the machine is FOR, in a sentence.
        use_case: str = '',
        # JSON floors in the ai-6 gauge vocabulary: cores, ram_mb,
        # disk_mb, vram_mb, plus gpu_required / fpga_required
        # booleans. 0 / absent = no floor declared.
        floors_json: str = '{}',
        # 'none' | 'declare' — declare-only v1 of the DB-residence
        # intent (object-ownership arc wires the real hooks).
        db_binding: str = 'none',
        # The database this profile intends to host (declare-only).
        db_ref: str = '',
        # dl-6 planner perf-class key this profile corresponds to
        # ('normal'|'highmem'|'highcpu'|'gpu'|'small') — the
        # cmp-c-5 splice point.
        planner_class: str = '',
        # WHY the floors are what they are (evidence-bearing).
        rationale: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.use_case = use_case
        self.floors_json = floors_json
        self.db_binding = db_binding
        self.db_ref = db_ref
        self.planner_class = planner_class
        self.rationale = rationale
        self.published = published
        self.is_prior = is_prior
        self.notes = notes


def field_of(row, name, default=''):
    """Dict-or-object accessor (the computerparts _field pattern) —
    every pure function here runs against seed dicts in selftests
    and live rows in the API."""
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)
