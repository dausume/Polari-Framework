"""
@cross-cutting
@module mealoptions.workflow_basis
@tags @xc:bindings

nmp-10 — cooking as a task-oriented WORKFLOW (decisions 10/12/13),
the VOCABULARY half moved here in mo-1 with names unchanged:

  KitchenToolDefinition  the tool vocabulary (seeded, USER-EXTENDABLE
                         — decision 13: declare any tool the catalog
                         never heard of; same CRUDE surface).
  CookingTaskDefinition  a task KIND naming WHAT (dice, batch-cook,
                         pan-fry…), honoring ONE uniform STEP
                         CONTRACT: inputs+state -> outputs+state,
                         duration (from the method), equipment slot.
  StepMethod             one WAY to do a task kind: tool x duration
                         model x skill floor x optional R6 retention
                         mapping (bake != fry nutritionally).
                         Provenance mine-vs-seeded; duration
                         fidelity estimate-vs-observed.
  StorageActionDefinition freeze/refrigerate/thaw/reheat as
                         first-class actions with the USDA FSIS
                         safety windows (public domain, cited).
  CookingWorkflow        a saved week DAG (graphs-as-data for the
                         EXISTING polariNoCode editor — a step-node
                         vocabulary, never a new editor).

The OWNED / STATED rows stay in nutrition.workflow_basis: KitchenTool
(a household's inventory), MethodPreference (a person's pin),
ToolAdvisorDismissal (a household's "stop suggesting"). The skill
vocabulary (SKILL_LEVELS / SKILL_FACTORS) lives in household; a
StepMethod's skill_floor is a plain string naming one of its levels.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.workflow_analysis (via nutrition.workflow_basis)
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/workflow/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mealoptions.objects.workflow._shared import FIDELITY, PROVENANCES, SEED_KITCHEN_TOOLS, SEED_STEP_METHODS, SEED_STORAGE_ACTIONS, SEED_TASK_KINDS, _method, _task, _tool  # noqa: F401
from mealoptions.objects.workflow.KitchenToolDefinition import KitchenToolDefinition  # noqa: F401
from mealoptions.objects.workflow.CookingTaskDefinition import CookingTaskDefinition  # noqa: F401
from mealoptions.objects.workflow.StepMethod import StepMethod  # noqa: F401
from mealoptions.objects.workflow.StorageActionDefinition import StorageActionDefinition  # noqa: F401
from mealoptions.objects.workflow.CookingWorkflow import CookingWorkflow  # noqa: F401
