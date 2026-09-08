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
  - nutrition.custom.workflow_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-10
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/workflow/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from household.household_basis import SKILL_FACTORS, SKILL_LEVELS  # noqa: F401
from mealoptions.workflow_basis import (  # noqa: F401
    FIDELITY, PROVENANCES, KitchenToolDefinition,
    CookingTaskDefinition, StepMethod, StorageActionDefinition,
    CookingWorkflow, SEED_KITCHEN_TOOLS, SEED_TASK_KINDS,
    SEED_STEP_METHODS, SEED_STORAGE_ACTIONS,
)

from nutrition.objects.workflow.KitchenTool import KitchenTool  # noqa: F401
from nutrition.objects.workflow.MethodPreference import MethodPreference  # noqa: F401
from nutrition.objects.workflow.ToolAdvisorDismissal import ToolAdvisorDismissal  # noqa: F401
