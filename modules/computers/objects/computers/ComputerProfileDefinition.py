"""
@module computers.objects.computers.ComputerProfileDefinition

Row class ComputerProfileDefinition of the computers module — one class per file (design §7), split
from computers_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
