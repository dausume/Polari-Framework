"""
@module testing.capability_basis

acct-0: the accountability spine — every critical capability is an
OBJECT in the tree, not a line in a log ([[object-coherence]]).

  CapabilityCheck  one named check per critical seam (a wrapped
                   existing suite/selftest, a live probe, or a gate
                   assert), carrying its category, criticality,
                   runner reference, and last observed status +
                   evidence.
  CheckRun         one execution of the matrix (or a filtered slice):
                   timestamped, environment- and build-stamped, with
                   the per-check result rows and the blocking_green
                   verdict a pipeline gates on.

TEST-BUILD ONLY: these classes register only when the `testing`
module is enabled (POLARI_TEST_BUILD / explicit POLARI_MODULES entry
— see polariApiServer.module_gating OPT_IN_PACKAGES). A normal build
has no tables, no CRUDE surface, no /api/accountability route; that
absence is itself asserted by testing.custom.absence_probe.
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/capability/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from testing.objects.capability._shared import CHECK_CATEGORIES, CHECK_KINDS, CHECK_STATUSES, CRITICALITIES  # noqa: F401
from testing.objects.capability.CapabilityCheck import CapabilityCheck  # noqa: F401
from testing.objects.capability.CheckRun import CheckRun  # noqa: F401
