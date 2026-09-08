"""
@module composition.archetype_basis

arch-5: PART ARCHETYPES — the machine-elements schema (practice map
§3: every Shigley chapter is one of these). An archetype joins the
two halves that already existed separately:

  role_refs       the MATERIAL-facing half (composition.custom.part_roles
                  — predicates, graded thresholds, evidence demands)
  equation_refs   the BEHAVIOUR-facing half (EquationDefinition
                  rows via motors.physics_equations_seed — DATA
                  references, reachable by name without importing)

plus its parameter set, its characteristic failure modes, its
selection procedure as ordered data, and its DESIGN MATRIX (which
knobs move which outcomes, and in what order to tune).

@consumers polariServer seed passes, composition.composition_seed,
composition.composition_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/archetype/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import named, resolve_named
from composition.design_matrix_basis import matrix_report
from composition.custom.part_roles import ROLE_REQUIREMENTS

from composition.objects.archetype._shared import EQUATION_LEVELS, _loads, archetype_report  # noqa: F401
from composition.objects.archetype.PartArchetypeDefinition import PartArchetypeDefinition  # noqa: F401
