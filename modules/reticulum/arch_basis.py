"""
@module reticulum.arch_basis

`.arch` — the archipelago (ret-1a, plan §5c): named, trusted
Reticulum nodes treated as an EXTENSION of our isle — for ROUTING AND
NAMING, never for authority. Motivating cases (Dustin): three isles
across town sharing data over LoRa; a remote-controlled tractor.

Two treeObjects:

  ArchipelagoNode   <name>.arch ⇄ a ReticulumDestination, what it IS,
                    who vouches for it, and MEASURED reachability kept
                    separate from declared trust — so `.arch` answers
                    "who can I actually reach right now" honestly.
  ArchipelagoTrust  GRADED, never a boolean: what a peer may ASK for.
                    Trust is a reason to accept a proposal for
                    consideration, not permission to write. ret-8
                    applies to trusted peers too.

@consumers reticulum.reticulum_api (/api/reticulum/arch)
@see modules/reticulum/reticulum_basis.py (vocabulary + path facts)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/arch/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from reticulum.reticulum_basis import measurement_fresh

from reticulum.objects.arch._shared import ARCH_NODE_KIND_VALUES, TRUST_GRADE_VALUES, _GRADE_AUTO_LEVEL, effective_auto_level, reachable_now  # noqa: F401
from reticulum.objects.arch.ArchipelagoNode import ArchipelagoNode  # noqa: F401
from reticulum.objects.arch.ArchipelagoTrust import ArchipelagoTrust  # noqa: F401
