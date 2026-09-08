"""@module reticulum.objects.replication._shared — what the replication row classes share (constants, seeds, helpers); split from replication_basis.py (sap-2c)."""

WATCH_DIRECTION_VALUES = ('publish', 'subscribe', 'both')
PUBLICATION_CLASS_VALUES = ('local-only', 'mesh-only', 'public')
CONFLICT_POLICY_VALUES = ('propose', 'parent-wins', 'child-wins',
                          'newest-wins')
STATE_ROLE_VALUES = ('parent', 'child')
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
