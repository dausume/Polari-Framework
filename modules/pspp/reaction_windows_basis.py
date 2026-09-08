"""
@module pspp.reaction_windows_basis

Reaction WINDOWS, not magic ratios (Ch.8 convergence): the book's
composition ranges are empirical regions where geopolymerization
proceeds properly — graded, not pass/fail. A ReactionWindow row grades
one computed descriptor (pspp.custom.composition_math derives it) as
ideal / acceptable / marginal / failure around a center with widening
tolerances.

The first REAL windows arrived 2026-07-18 with the pp.191-192 patent
pages (US 4,349,386 Table A; US 4,472,199 Table C): the patents claim
BINARY ranges, so those seeds set all three tolerances to the range
half-width — 'ideal' there means 'inside the claimed range', and
finer grading honestly waits for finer data (the partially-visible
"preferably…" text on p.191 was cut off in the photo).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - future pspp-4 process admissibility + pspp-6 slice gates
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/reaction_windows/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.reaction_windows._shared import GRADES, SEED_REACTION_WINDOWS, _TABLE_A, _TABLE_C, _range_window, grade_composition, grade_value, window_dict  # noqa: F401
from pspp.objects.reaction_windows.ReactionWindow import ReactionWindow  # noqa: F401
