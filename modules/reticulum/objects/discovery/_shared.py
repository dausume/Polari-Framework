"""@module reticulum.objects.discovery._shared — what the discovery row classes share (constants, seeds, helpers); split from discovery_basis.py (sap-2c)."""

SIGHTING_STATUS_VALUES = ('unadjudicated', 'archipelago', 'mesh',
                          'ignored')
ADJUDICATION_VALUES = ('archipelago', 'mesh', 'ignored')
ACTOR_MODES = ('isle', 'keycloak')
def resolve_actor(user, mode='isle', isle_identity='', instance_name=''):
    """(ok, actor | refusal). A KC user always wins (a person with a
    name). Otherwise mode 'isle' names the isle's Reticulum identity
    ('isle:<hash>' — or 'isle:<instance>' while the sidecar is not
    reachable, stated), and mode 'keycloak' refuses."""
    if user and user.get('sub'):
        return True, {'actor': user.get('username') or user['sub'],
                      'tier': 'keycloak'}
    if mode not in ACTOR_MODES:
        return False, {'evidence': f'RETICULUM_ACTOR_MODE={mode!r} is not '
                                   f'one of {ACTOR_MODES}'}
    if mode == 'keycloak':
        return False, {'evidence': 'this isle runs RETICULUM_ACTOR_MODE='
                                   'keycloak — a Keycloak-verified caller '
                                   'is required for this act',
                       'knob': 'RETICULUM_ACTOR_MODE=isle (the '
                               'lightweight default: the isle identity '
                               'acts)'}
    if isle_identity:
        return True, {'actor': f'isle:{isle_identity[:16]}',
                      'tier': 'isle'}
    if instance_name:
        return True, {'actor': f'isle:{instance_name}', 'tier': 'isle',
                      'note': 'sidecar identity not reachable — the '
                              'instance name stands in'}
    return False, {'evidence': 'no Keycloak user, no sidecar identity '
                               'and no POLARI_INSTANCE_NAME — nothing '
                               'to sign this act with'}
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
