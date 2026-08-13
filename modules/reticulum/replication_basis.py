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

from objectTreeDecorators import treeObject, treeObjectInit

#: Replication direction for a watched object.
WATCH_DIRECTION_VALUES = ('publish', 'subscribe', 'both')

#: §5g item 3: state crossing the ham core must be EXPLICITLY marked
#: publishable. Default = most restrictive. The gateway refuses
#: anything but 'public' on an amateur interface, by name.
PUBLICATION_CLASS_VALUES = ('local-only', 'mesh-only', 'public')

#: Conflict policy is a KNOB PER WATCHED OBJECT, never global.
#: 'propose' is the one that fits this suite.
CONFLICT_POLICY_VALUES = ('propose', 'parent-wins', 'child-wins',
                          'newest-wins')

#: Which side of the two-state model a version row records.
STATE_ROLE_VALUES = ('parent', 'child')

#: Conflict lifecycle.
CONFLICT_STATUS_VALUES = ('open', 'proposed', 'resolved')


def detect_conflict(held_parent_version, arriving_parent_version):
    """§5f conflict DETECTION: if the arriving update's parent version
    is not the parent we hold, both sides moved. Pure — the replicator
    applies it, the selftest pins it. None/0 held parent means we have
    no baseline yet (a late joiner needs a keyframe, not a conflict)."""
    if not held_parent_version:
        return False
    return arriving_parent_version != held_parent_version


def delta_usable(receiver_parent_version, delta_parent_version):
    """A receiver whose parent is unknown or different cannot use a
    delta (§5f keyframes): the publisher's periodic FULL snapshot is
    what recovers it. Pure gate for the subscribe side."""
    if not receiver_parent_version:
        return False
    return receiver_parent_version == delta_parent_version


def repeat_is_noop(held_version, held_hash, arriving_version,
                   arriving_hash):
    """Hash + version make a REPEAT a no-op — what makes a lossy link
    safe to retry on. True when the arriving state is exactly what we
    already hold."""
    return bool(held_version) and held_version == arriving_version \
        and held_hash == arriving_hash


def keyframe_due(seq, keyframe_every_n):
    """Publisher-side keyframe cadence: every Nth update is a FULL
    snapshot. N<=1 means every send is a keyframe (the honest default
    for receive-only paths, where no receiver can ask for one)."""
    if keyframe_every_n is None or keyframe_every_n <= 1:
        return True
    return seq % keyframe_every_n == 0


class WatchedObject(treeObject):
    """WHICH objects are replicated, and under what policy. Everything
    here is a knob with a conservative default; nothing silently picks
    for you."""

    @treeObjectInit
    def __init__(self, name='', class_name='', object_name='',
                 query_json='', direction='publish',
                 publication_class='local-only',
                 bearer_policy_json='{}', cadence_seconds=300,
                 keyframe_every_n=10, conflict_policy='propose',
                 enabled=False, notes='', manager=None):
        self.name = name
        # By class, by name, or by query — the three selection shapes.
        self.class_name = class_name
        self.object_name = object_name
        self.query_json = query_json
        self.direction = direction
        self.publication_class = publication_class
        self.bearer_policy_json = bearer_policy_json
        self.cadence_seconds = cadence_seconds
        self.keyframe_every_n = keyframe_every_n
        self.conflict_policy = conflict_policy
        self.enabled = enabled
        self.notes = notes


class ObjectStateVersion(treeObject):
    """One side of the two-state model. parent rows are stored
    VERBATIM as received (evidence of what the other side believes)
    and never edited locally; child rows are ours."""

    @treeObjectInit
    def __init__(self, name='', watched_name='', role='child',
                 version=0, content_hash='', payload_json='',
                 received_at_ms=0, source_arch_name='', notes='',
                 manager=None):
        self.name = name
        self.watched_name = watched_name
        self.role = role
        # Monotonic per (watched, role).
        self.version = version
        self.content_hash = content_hash
        self.payload_json = payload_json
        self.received_at_ms = received_at_ms
        # Which .arch node this parent state arrived from.
        self.source_arch_name = source_arch_name
        self.notes = notes


class StateConflict(treeObject):
    """A detected divergence, both sides carried. status 'proposed'
    means it went through the ai_actions seam and awaits a human."""

    @treeObjectInit
    def __init__(self, name='', watched_name='', held_parent_version=0,
                 child_version=0, arriving_version=0,
                 arriving_parent_version=0, both_sides_json='{}',
                 detected_at_ms=0, status='open', resolution='',
                 proposal_ref='', notes='', manager=None):
        self.name = name
        self.watched_name = watched_name
        self.held_parent_version = held_parent_version
        self.child_version = child_version
        self.arriving_version = arriving_version
        self.arriving_parent_version = arriving_parent_version
        self.both_sides_json = both_sides_json
        self.detected_at_ms = detected_at_ms
        self.status = status
        self.resolution = resolution
        # The ai_actions proposal this conflict became, when policy
        # is 'propose' — the record CITES the proposal, never IS one.
        self.proposal_ref = proposal_ref
        self.notes = notes
