"""
@cross-cutting
@module nutrition.workflow_basis
@tags @xc:bindings

nmp-10 — cooking as a task-oriented WORKFLOW (decisions 10/12/13).
mo-1 (MEAL_OPTIONS_MODULE_PLAN.md) MOVED the vocabulary half —
KitchenToolDefinition, CookingTaskDefinition, StepMethod,
StorageActionDefinition, CookingWorkflow, FIDELITY, PROVENANCES and
the seeds — to mealoptions.workflow_basis with names unchanged; this
module RE-EXPORTS them so every `from nutrition.workflow_basis
import X` keeps working, and KEEPS the owned / stated rows:

  KitchenTool            one household's inventory row.
  MethodPreference       a stated pin ("hand-dice") — beats
                         time-optimality; the delta is shown, never
                         judged.
  ToolAdvisorDismissal   a remembered "stop suggesting this tool".

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.workflow_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-10
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""

from objectTreeDecorators import treeObject, treeObjectInit
# hh-1: the skill vocabulary + the labeled level priors (refined per
# person from observed durations) live in the household layer now;
# re-exported here so existing importers keep working.
from household.household_basis import SKILL_FACTORS, SKILL_LEVELS  # noqa: F401
# mo-1: the cooking vocabulary — re-exported (names unchanged).
from mealoptions.workflow_basis import (  # noqa: F401
    FIDELITY, PROVENANCES, KitchenToolDefinition,
    CookingTaskDefinition, StepMethod, StorageActionDefinition,
    CookingWorkflow, SEED_KITCHEN_TOOLS, SEED_TASK_KINDS,
    SEED_STEP_METHODS, SEED_STORAGE_ACTIONS,
)


class KitchenTool(treeObject):
    """One inventory row: does THIS household own the tool?"""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 tool_name: str = '', owned: bool = True,
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.household_name = household_name
        self.tool_name = tool_name
        self.owned = owned
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class MethodPreference(treeObject):
    """A stated pin — preference beats time-optimality."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '',
                 household_name: str = '', task_kind: str = '',
                 method_name: str = '',
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.person_name = person_name
        self.household_name = household_name
        self.task_kind = task_kind
        self.method_name = method_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ToolAdvisorDismissal(treeObject):
    """A remembered 'stop suggesting this tool' (never a nag)."""

    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 tool_name: str = '',
                 is_prior: bool = False, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.household_name = household_name
        self.tool_name = tool_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
