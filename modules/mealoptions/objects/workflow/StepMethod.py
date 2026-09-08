"""
@module mealoptions.objects.workflow.StepMethod

Row class StepMethod of the mealoptions module — one class per file (design §7), split
from workflow_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StepMethod(treeObject):
    """One WAY to do a task kind (decision 12): tool x duration
    model x skill; picks its own R6 retention row when it cooks."""

    @treeObjectInit
    def __init__(self, name: str = '', task_kind: str = '',
                 display_name: str = '', tool_name: str = '',
                 # duration model: base + per-100g, scaled by the
                 # cook's SKILL_FACTORS (labeled priors).
                 base_min: float = 0.0,
                 per_100g_min: float = 0.0,
                 # minimum skill to use safely ('' = anyone).
                 skill_floor: str = '',
                 # whether the cook attends it the whole time (active
                 # minutes are THE optimizer score) or it runs itself
                 # (oven/rice-cooker — only base_min is active).
                 attended: bool = True,
                 # R6 retention code this method maps to ('' = honest
                 # none — decision 13: none-if-unknown).
                 retention_code: str = '',
                 provenance: str = 'seeded',
                 duration_fidelity: str = 'estimate',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.task_kind = task_kind
        self.display_name = display_name
        self.tool_name = tool_name
        self.base_min = base_min
        self.per_100g_min = per_100g_min
        self.skill_floor = skill_floor
        self.attended = attended
        self.retention_code = retention_code
        self.provenance = provenance
        self.duration_fidelity = duration_fidelity
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
