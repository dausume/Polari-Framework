"""
@module reticulum.replication_basis

State replication — parent state + child state (ret-7b, plan §5f).
The git shape: keeping the last-known-common ancestor beside your own
working state is what makes divergence DETECTABLE instead of
catastrophic. Keyframes are mandatory, not an optimisation — on a
one-way (receive-only) path they are the ONLY recovery mechanism.

Three treeObjects:

  WatchedObject       WHICH objects are replicated (class/name/query),
                      direction, cadence, bearer policy, conflict
                      policy — and publication_class, defaulting to
                      the MOST RESTRICTIVE (the HAM segment is a
                      public, permanent broadcast; §5g item 3).
  ObjectStateVersion  parent/child versions with content hashes and a
                      monotonic counter. Hash + version make a repeat
                      a NO-OP — what makes a lossy link safe to retry.
  StateConflict       a detected divergence carrying both sides.
                      Under the 'propose' policy it becomes a PROPOSAL
                      through the ret-8 seam; a remote isle
                      overwriting local rows because it spoke last is
                      exactly what the rule exists to prevent.

@consumers reticulum.reticulum_api
@see modules/reticulum/reticulum_basis.py, plan §5f
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/replication/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.objects.replication._shared import CONFLICT_POLICY_VALUES, CONFLICT_STATUS_VALUES, PUBLICATION_CLASS_VALUES, STATE_ROLE_VALUES, WATCH_DIRECTION_VALUES, delta_usable, detect_conflict, keyframe_due, repeat_is_noop  # noqa: F401
from reticulum.objects.replication.WatchedObject import WatchedObject  # noqa: F401
from reticulum.objects.replication.ObjectStateVersion import ObjectStateVersion  # noqa: F401
from reticulum.objects.replication.StateConflict import StateConflict  # noqa: F401
