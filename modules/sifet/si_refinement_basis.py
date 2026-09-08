"""
@module sifet.si_refinement_basis

fp-4 (2026-08-27): silicon REFINEMENT as data — the grade ladder
MG-Si → UMG-Si → SoG-Si (PV) → EG-Si (semiconductor), the unit steps
that move material up the ladder, the ROUTES that chain them, and
the computable models each step cites so a feed can be pushed
through a route and graded honestly.
Plan: AI-Notes/plans/FET_CELL_POWER_SILICON_PLAN.md §1 fp-4, §2 dec 5.

The characteristic equation of the whole arc is Scheil segregation
during solidification from the melt:

  C_s(f_s) = k_eff · C_0 · (1 − f_s)^(k_eff − 1)

k_eff (the effective segregation coefficient, solid/liquid) is per
IMPURITY: metals (Fe, Al, Ca, Ti…) have k ≪ 1 and are stripped in
one directional pass; B (0.8) and P (0.35) have k close to 1 and
barely move — which is WHY PV-grade silicon is reachable by open
solidification-based routes and semiconductor-grade (9N–11N in B/P)
is not: B/P must be removed by a different physics (evaporation
under vacuum for P, reactive gas/plasma for B, or the Siemens
distillation of chlorosilanes) and the open literature documents
the PV-grade endpoint of those, not the 11N one.

Cross-references (by NAME, not duplicated here):
  techtree: TechNode 'silicon-refinement' (electronics tree),
            'silicon-supply' / 'silicon-supply-pv-grade' /
            'silicon-supply-semiconductor-grade' (supply tree),
            'silicon' (materials tree)  — techtree.techtree_seed
  materials: diamond-cubic silicon seed (msci/ssp) per
            MATERIALS_TECH_TREE_PLAN.md §"Silicon" row
  ceramics ladder rung style: pspp.ceramics_ladder_basis.LadderRung

Honesty: every step / route carries `openness` ∈
  'open-research'          documented in open literature; an
                           open-source implementation is plausible
  'industrial-proprietary' chemistry open, process know-how closed
  'novel-needed'           no open route to the grade; candidate
                           directions are labelled PRIOR rows
and a route's openness is the WORST of its steps. Every numeric
prior is labelled `confidence` and cited; 'to verify' is written
where a value is remembered rather than checked against the source.

@consumers
  - sifet.refinement_selftest
  - sifet API (GET /api/sifet/refinement — wired by the integrator)
  - polariServer (SiliconGrade / RefinementStep / RefinementRoute
    registration + SEED_* lists)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/si_refinement/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from objectTreeDecorators import treeObject, treeObjectInit

from sifet.objects.si_refinement._shared import CITATIONS, DEFAULT_MG_FEED_PPM, GRADE_LIMITS_PPM, IMPURITIES, OPENNESS, REFINEMENT_KNOBS, SEED_REFINEMENT_ROUTES, SEED_REFINEMENT_STEPS, SEED_SILICON_GRADES, SEED_SI_REFINEMENT_GRAPHS, SEGREGATION_K, _NOVEL, _OPENNESS_RANK, _cite, _imp, _js, _k_json, _route_graph, _rows, _step, apply_step, evaporation_removal, get_row, grade_for, grade_ladder, impurity_ladder_rows, multipass_zone, refinement_report, route_openness, route_simulation, scheil_pass, scheil_rows  # noqa: F401
from sifet.objects.si_refinement.SiliconGrade import SiliconGrade  # noqa: F401
from sifet.objects.si_refinement.RefinementStep import RefinementStep  # noqa: F401
from sifet.objects.si_refinement.RefinementRoute import RefinementRoute  # noqa: F401
