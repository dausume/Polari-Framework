"""
@module cntfet.cnt_targets_basis

Dustin 2026-08-29: "These cells are not made to work with these kinds
of FETs … saying they are failing does not make sense unless they are
something we are actively trying to make the FET work for. We should
have a mapping between FETs and the cells they are meant to map to."

So: a BUDGET belongs to a DESIGN TARGET (what a thing is engineered
FOR — low-power logic, general logic, high-performance logic, analog
signal, research reference), and a FET (and every library / cell /
block built on it) is MAPPED to the targets it was engineered for.
A budget check is pass / fail ONLY against a mapped target; against
any other target it is INFORMATIONAL ("would meet / would not meet")
— never a red "fail" on a device that was never meant to meet it.

@consumers cnt_power.budget_report, cnt_api, polariServer (seeds),
  fet-overview (frontend)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_targets/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.objects.cnt_targets._shared import DEFAULT_TARGET, SEED_DESIGN_TARGETS, SEED_FET_TARGET_MAPPINGS, SEED_TARGET_POWER_BUDGETS, _map, _rows, mapping_for, targets_for_device, targets_index  # noqa: F401
from cntfet.objects.cnt_targets.DesignTarget import DesignTarget  # noqa: F401
from cntfet.objects.cnt_targets.FETTargetMapping import FETTargetMapping  # noqa: F401
