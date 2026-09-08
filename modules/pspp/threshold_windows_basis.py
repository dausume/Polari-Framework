"""
@module pspp.threshold_windows_basis

The THRESHOLD-SHAPED (asymmetric/banded) ReactionWindow variant the
p.193 graded detail needed and the symmetric center+tolerance shape
could not express (handoff item: 'preferred 1.3-1.52 / 4.0-4.2 +
crack thresholds <1.1 / <3.7 — recorded, not yet modeled' — modeled
HERE).

A ThresholdReactionWindow grades one descriptor through an ORDERED,
CONTIGUOUS, FULL-COVERAGE list of bands, each carrying its own grade
AND its own physical behavior note ('numerous cracks', 'free
potassium-silicate phase') — asymmetry and hard thresholds are just
bands. Bands are half-open [lo, hi); lo=None ⇒ -inf, hi=None ⇒ +inf.

Banded rows COMPLEMENT the symmetric patent-claim rows: where both
exist for one (family, descriptor), the banded row wins in merged
grading (finer cited data beats the binary claim; the symmetric row
stays as the patent-claim record).

Also here: CONDITION-GATE windows — thresholds that open/close
reaction pathways rather than grade quality (p.188 §8.5.3: mild
depolymerization frees Q0 only when the Na-silicate solution has
MR < 1.20; p.196 pins the K routes to the SAME threshold). A rule
names gate windows in condition_windows_json; the pspp-8 stepper
refuses to fire the rule where the gate grades 'failure'.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.custom.network_stepping (condition gates)
  - pspp.custom.pspp_views / pspp.custom.experiment_guidance (merged grading)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/threshold_windows/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from pspp.reaction_windows_basis import GRADES

from pspp.objects.threshold_windows._shared import SEED_THRESHOLD_WINDOWS, WINDOW_ROLES, _P193, _row, banded_window_dict, grade_composition_merged, grade_value_banded, merged_family_windows, validate_banded_window  # noqa: F401
from pspp.objects.threshold_windows.ThresholdReactionWindow import ThresholdReactionWindow  # noqa: F401
