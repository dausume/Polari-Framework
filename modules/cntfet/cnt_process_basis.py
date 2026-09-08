"""
@module cntfet.cnt_process_basis

S3: manufacturing processes as FIRST-CLASS OBJECTS contributing
DISTRIBUTIONS, never ideal values (plan D7). A device declares its
targets (chirality, Lg, t_ox, Rc prior); the process set predicts
what a real line would produce around those targets; Monte Carlo
(cnt_montecarlo) instantiates the population. The manufacturing
feedback loop — method -> measured capability -> process model ->
device MC -> yield -> dominant limitation — is the point.

The six process classes are the plan's D7 list. Every distribution
parameter carries source + confidence; UNSOURCED sigmas are
engineering priors, flagged low-confidence and TUNABLE — and the
MC engine refuses a process row whose distributions_confidence is
'none' (refusal, not silent idealization).

manufacturing_regime coherence (D6): process rows declare which
regime they describe; binding a device to a process set from a
different regime is refused loudly (a coarse solution-processed
line cannot fabricate a 15 nm aligned device).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - cntfet.custom.cnt_montecarlo (the sampling engine)
  - cntfet.cntfet_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_process/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.objects.cnt_process._shared import SEED_ALIGNMENT_PROCESSES, SEED_CONTACT_PROCESSES, SEED_GATESTACK_PROCESSES, SEED_LITHOGRAPHY_PROCESSES, SEED_PLACEMENT_PROCESSES, SEED_PURIFICATION_PROCESSES, _PRIOR  # noqa: F401
from cntfet.objects.cnt_process.CNTAlignmentProcess import CNTAlignmentProcess  # noqa: F401
from cntfet.objects.cnt_process.CNTPlacementProcess import CNTPlacementProcess  # noqa: F401
from cntfet.objects.cnt_process.CNTPurificationProcess import CNTPurificationProcess  # noqa: F401
from cntfet.objects.cnt_process.ContactFormationProcess import ContactFormationProcess  # noqa: F401
from cntfet.objects.cnt_process.LithographyProcess import LithographyProcess  # noqa: F401
from cntfet.objects.cnt_process.GateStackProcess import GateStackProcess  # noqa: F401
from cntfet.objects.cnt_process.CNTFETMonteCarloRun import CNTFETMonteCarloRun  # noqa: F401
