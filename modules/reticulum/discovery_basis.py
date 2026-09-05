"""
@module reticulum.discovery_basis

PEER DISCOVERY + ADJUDICATION (ret-1d, plan §5o, DECIDED row 21):
every announce/broadcast HEARD becomes an observation; a HUMAN
decides what it becomes.

  PeerSighting   measured evidence that someone is out there: hashes,
                 aspects, which interface/bearer heard them, when and
                 how often. Status 'unadjudicated' until decided —
                 hearing is not admitting.

Adjudication outcomes:
  archipelago  "this is one of our own devices" → enters .arch
               (an ArchipelagoNode is created; trust GRADES stay
               separate — admission is routing and naming, never
               authority).
  mesh         a stranger we still want to see → enters .mesh:
               reachability-tracked, interactions capped at the
               mesh rung (data rules, census, proposals).
  ignored      heard, noted, not shown again (the row stays — an
               ignored peer that returns on a new bearer is a fact).

@consumers reticulum.reticulum_api (/api/reticulum/peers),
           the sidecar's announce listener (peersHeard in /status)
@see modules/reticulum/arch_basis.py (.arch), meshapp_basis.py
     (the mesh rung .mesh peers are capped at), plan §5o
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Sighting lifecycle. 'unadjudicated' is neither .arch nor .mesh —
#: a peer nobody has decided about is a question, not a member.
SIGHTING_STATUS_VALUES = ('unadjudicated', 'archipelago', 'mesh',
                          'ignored')

#: What an adjudication may decide.
ADJUDICATION_VALUES = ('archipelago', 'mesh', 'ignored')


def adjudicate(sighting, decision, decided_by, arch_name=''):
    """The adjudication act as a pure rule. Returns
    (ok, changes | refusal): changes = fields to write on the
    sighting (+ 'createArchNode' payload when admitted to .arch).
    Refusals carry the standing three keys.

    'archipelago' REQUIRES an arch_name — "it's ours" means naming
    it into OUR namespace, and a nameless admission would be a
    routing entry nobody can use."""
    if decision not in ADJUDICATION_VALUES:
        return (False, {
            'evidence': 'unknown decision %r' % (decision,),
            'knob': 'decision ∈ %s' % (ADJUDICATION_VALUES,),
            'action': 'choose archipelago (ours), mesh (stranger '
                      'worth seeing) or ignored',
        })
    if not decided_by:
        return (False, {
            'evidence': 'adjudication without an identified decider',
            'knob': 'Keycloak-verified caller',
            'action': 'authenticate — admission is a human act with '
                      'a name on it',
        })
    if sighting.get('status') == decision:
        return (False, {
            'evidence': 'sighting is already %r' % (decision,),
            'knob': 'PeerSighting.status',
            'action': 'nothing to do',
        })
    changes = {'status': decision, 'adjudicated_by': decided_by}
    if decision == 'archipelago':
        if not arch_name:
            return (False, {
                'evidence': 'admission to .arch without an arch name',
                'knob': 'archName in the adjudication call',
                'action': 'name the node (e.g. barn-isle.arch) — '
                          'admission IS naming',
            })
        changes['createArchNode'] = {
            'name': arch_name.removesuffix('.arch'),
            'arch_name': arch_name if arch_name.endswith('.arch')
            else arch_name + '.arch',
            'destination_name': sighting.get('dest_hash', ''),
            'node_kind': 'peer-isle',
            'vouched_by': decided_by,
            'last_heard_ms': sighting.get('last_heard_ms', 0),
            'fidelity': 'measured-real',
        }
    return (True, changes)


def merge_heard(existing, heard, now_ms):
    """Fold one sidecar peers-heard entry into a sighting dict:
    counts accumulate, last_heard advances, first_heard survives,
    and a NEW bearer for a known peer is recorded (an ignored peer
    returning on a new bearer is a fact worth keeping)."""
    if existing is None:
        return {
            'identity_hash': heard.get('identityHash', ''),
            'dest_hash': heard.get('destHash', ''),
            'aspects': heard.get('aspects', ''),
            'heard_via': heard.get('interface', ''),
            'first_heard_ms': heard.get('lastHeardMs', now_ms),
            'last_heard_ms': heard.get('lastHeardMs', now_ms),
            'announce_count': heard.get('count', 1),
            'status': 'unadjudicated',
        }
    out = dict(existing)
    out['last_heard_ms'] = max(existing.get('last_heard_ms', 0),
                               heard.get('lastHeardMs', now_ms))
    out['announce_count'] = existing.get('announce_count', 0) \
        + heard.get('count', 1)
    via = existing.get('heard_via', '')
    new_via = heard.get('interface', '')
    if new_via and new_via not in via.split(','):
        out['heard_via'] = ','.join(v for v in (via, new_via) if v)
    return out


class PeerSighting(treeObject):
    """One peer as HEARD: evidence with timestamps, adjudicated by a
    named human into .arch, .mesh, or ignored. Row name = the
    destination hash (the stable thing a stranger shows us)."""

    @treeObjectInit
    def __init__(self, name='', identity_hash='', dest_hash='',
                 aspects='', heard_via='', first_heard_ms=0,
                 last_heard_ms=0, announce_count=0,
                 status='unadjudicated', adjudicated_by='',
                 adjudicated_at='', arch_node_name='', notes='',
                 manager=None):
        self.name = name
        self.identity_hash = identity_hash
        self.dest_hash = dest_hash
        self.aspects = aspects
        # comma-joined interface names — WHICH radios heard it.
        self.heard_via = heard_via
        self.first_heard_ms = first_heard_ms
        self.last_heard_ms = last_heard_ms
        self.announce_count = announce_count
        self.status = status
        self.adjudicated_by = adjudicated_by
        self.adjudicated_at = adjudicated_at
        # the ArchipelagoNode created on admission, when any.
        self.arch_node_name = arch_node_name
        self.notes = notes
