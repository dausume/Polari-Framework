"""@module reticulum.objects.meshapp._shared — what the meshapp row classes share (constants, seeds, helpers); split from meshapp_basis.py (sap-2c)."""
import json

APP_SCOPE_VALUES = ('isle', 'arch', 'mesh', 'web')
MESH_APP_ROLE_VALUES = ('observer', 'user', 'relay-only', 'server')
KC_LINK_MODE_VALUES = ('disabled', 'optional')
_SCOPE_RANK = {s: i for i, s in enumerate(APP_SCOPE_VALUES)}
def scope_allows(app_scope, origin_scope):
    """May a caller from `origin_scope` reach an app exposed at
    `app_scope`? The ladder rule: an app is reachable from its own
    rung and every rung BELOW it (closer to home), never from above.
    Unknown scopes refuse — the ladder has four rungs, not a
    default. Returns (bool, reason)."""
    if app_scope not in _SCOPE_RANK:
        return (False, 'unknown app scope %r' % (app_scope,))
    if origin_scope not in _SCOPE_RANK:
        return (False, 'unknown origin scope %r' % (origin_scope,))
    if _SCOPE_RANK[origin_scope] <= _SCOPE_RANK[app_scope]:
        return (True, '')
    return (False,
            'app is %s-scoped; a caller from the %s does not reach '
            'it (raise the app\'s AppArchExposure deliberately, or '
            'not at all)' % (app_scope, origin_scope))
def adaptive_cadence(current_interval_s, consumer_return_intervals_s,
                     min_interval_s, max_interval_s, headroom=1.5,
                     max_step=2.0):
    """§5n: pace the lighthouse to what consumers COLLECTIVELY
    demonstrate — the median consumer's return interval, with
    headroom, clamped to [min, max] and rate-limited to max_step per
    adjustment (no oscillation). No returns at all -> drift toward
    the ceiling (broadcast survives silence; it just slows).
    Evidence-bearing: returns (new_interval_s, evidence dict)."""
    evidence = {'current': current_interval_s,
                'samples': len(consumer_return_intervals_s or []),
                'floor': min_interval_s, 'ceiling': max_interval_s}
    if not consumer_return_intervals_s:
        target = min(current_interval_s * max_step, max_interval_s)
        evidence['reason'] = ('no consumer returns in window — '
                              'slowing toward the ceiling')
    else:
        ordered = sorted(consumer_return_intervals_s)
        median = ordered[len(ordered) // 2]
        evidence['medianReturn'] = median
        target = median * headroom
        evidence['reason'] = ('paced to the median consumer return '
                              '(%.1fs) x headroom %.1f' % (median,
                                                           headroom))
    # rate-limit, then clamp — the floor is the airtime budget's
    # voice and always wins.
    lo = current_interval_s / max_step
    hi = current_interval_s * max_step
    target = max(lo, min(hi, target))
    target = max(min_interval_s, min(max_interval_s, target))
    evidence['new'] = round(target, 2)
    return (round(target, 2), evidence)
def user_census(expected_users, observed_identity_count,
                over_factor=1.5):
    """§5n accountability: how many users SHOULD exist vs how many
    distinct RNS identities were seen. A named finding — a relay
    that silently gains a thousand consumers is a different thing
    than the one you configured. expected 0/None = no expectation
    declared (stated, not defaulted)."""
    if not expected_users:
        return {'state': 'no-expectation',
                'observed': observed_identity_count,
                'evidence': 'no expected_users declared on the relay '
                            '— set one to make the census meaningful'}
    ratio = observed_identity_count / expected_users
    if ratio > over_factor:
        state = 'over'
    elif observed_identity_count < expected_users:
        state = 'under'
    else:
        state = 'as-expected'
    return {'state': state, 'observed': observed_identity_count,
            'expected': expected_users,
            'evidence': '%d distinct Reticulum identities seen vs %d '
                        'expected (%.0f%%)'
                        % (observed_identity_count, expected_users,
                           ratio * 100)}
SEED_KIT_PROFILES = [
    {'name': 'everyday-node',
     'display_name': 'Everyday node',
     'devices_json': json.dumps({'lora': 1, 'ham-rx': 1,
                                 'wifi-halow': 1}),
     'intent': 'everyday',
     'notes': 'One person, one of each: LoRa for the mesh, a ham '
              'receiver for the broadcast core (§5g — listening is '
              'free), one HaLow for bandwidth.'},
    {'name': 'meshapp-broadcaster',
     'display_name': 'Mesh-app broadcaster',
     'devices_json': json.dumps({'ham-tx': 1, 'wifi-halow': 3}),
     'intent': 'broadcaster',
     'notes': 'Hosts a mesh app: a licensed ham transmitter for the '
              'public broadcast core, MULTIPLE HaLow units to ingest '
              'high-bandwidth mesh traffic from several routes at '
              'once (units multiply capacity on distinct channels).'},
    {'name': 'bandwidth-backbone',
     'display_name': 'Bandwidth backbone',
     'devices_json': json.dumps({'wifi-halow': 4}),
     'intent': 'backbone',
     'notes': 'A relay-capacity node: four HaLow units carrying '
              'other people\'s traffic on distinct channels.'},
]
