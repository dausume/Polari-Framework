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

from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.reticulum_basis import measurement_fresh

#: What an archipelago node IS.
ARCH_NODE_KIND_VALUES = ('peer-isle', 'device', 'relay')

#: Graded trust ladder — each grade names what the peer may ASK for.
#: 'propose-low-preapproved' is the ceiling: a higher grade may raise
#: auto-approval for NAMED low-authority operations (telemetry ingest,
#: gossip), never for irreversible ones.
TRUST_GRADE_VALUES = ('observe', 'gossip', 'telemetry', 'propose',
                      'propose-low-preapproved')

#: The ai_actions level ceiling a trust grade may auto-approve up to.
#: Level 3 = reversible-system, the same ceiling AUTO_MAX_LEVEL
#: defaults to; NOTHING in this table reaches 4+ (network-service and
#: above stay human-confirmed regardless of trust — "extension of our
#: isle" describes routing, not authority).
_GRADE_AUTO_LEVEL = {
    'observe': 0,
    'gossip': 0,
    'telemetry': 2,
    'propose': 2,
    'propose-low-preapproved': 3,
}


def effective_auto_level(grade):
    """Auto-approval ceiling for a trust grade. Unknown grades get 0 —
    an unrecognized grade is refused authority, never guessed into
    some."""
    return _GRADE_AUTO_LEVEL.get(grade, 0)


def reachable_now(node_fact, now_ms, horizon_ms=900_000):
    """§5c: reachability is a MEASUREMENT with a timestamp. True only
    when the node was heard inside the freshness horizon — listing
    hopeful names is exactly what this refuses to do."""
    return measurement_fresh(node_fact.get('last_heard_ms', 0), now_ms,
                             horizon_ms)


class ArchipelagoNode(treeObject):
    """A named node in `.arch`: the human/app surface of §3's mapping.
    Measured reachability lives here; declared trust lives on the
    ArchipelagoTrust row it names — the split is the point."""

    @treeObjectInit
    def __init__(self, name='', arch_name='', destination_name='',
                 node_kind='peer-isle', vouched_by='', trust_name='',
                 last_heard_ms=0, hop_count=0, link_quality='',
                 fidelity='declared', notes='', manager=None):
        self.name = name
        # The '<x>.arch' name; kept beside row name so a row rename
        # never silently changes what resolvers hand out.
        self.arch_name = arch_name
        self.destination_name = destination_name
        self.node_kind = node_kind
        # WHO vouches for this node (an identity name) — provenance,
        # not authority.
        self.vouched_by = vouched_by
        self.trust_name = trust_name
        # Measured reachability — timestamps, not hopes.
        self.last_heard_ms = last_heard_ms
        self.hop_count = hop_count
        self.link_quality = link_quality
        self.fidelity = fidelity
        self.notes = notes


class ArchipelagoTrust(treeObject):
    """What a peer may ASK for — graded, never boolean. may_ask_json
    is the named-operations list a grade covers; the ai_actions level
    ceiling derives from the grade and never reaches irreversible."""

    @treeObjectInit
    def __init__(self, name='', grade='observe', may_ask_json='[]',
                 granted_by='', granted_at='', notes='', manager=None):
        self.name = name
        self.grade = grade
        # Named low-authority operations this trust covers, e.g.
        # ["telemetry-ingest", "gossip"]. An empty list with a high
        # grade grants NOTHING — the list is the grant.
        self.may_ask_json = may_ask_json
        self.granted_by = granted_by
        self.granted_at = granted_at
        self.notes = notes
