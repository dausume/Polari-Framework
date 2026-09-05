"""
@module reticulum.meshapp_basis

THE APP ACCESS LADDER (ret-1c, plan §5n, DECIDED rows 20/21 — Dustin
2026-08-13): the reserved isle-mesh suffixes, per-app knobs
defaulting to the most restrictive.

  isle   (.isle)  reachable only on its own isle (the default).
  arch   (.arch)  archipelago-accessible: apps inside the .arch talk
                  as their own network. The farmer's market — vendors
                  mesh their isles so customers move between stalls
                  as one.
  mesh   (.mesh)  the ZERO-TRUST wider mesh: beyond the archipelago
                  is water that belongs to no one. Arbitrary
                  consumers connect to a LIGHTHOUSE (MeshAppRelay)
                  that broadcasts the app's current (and optionally
                  prior) state; consumers are pseudonymous — tracked
                  SOLELY by Reticulum identity — and nothing they
                  send mutates state except through the ret-8
                  proposal seam, like everyone else.
  web             the internet, with its various possible endpoints
                  (the EXTERNAL_APPS story) — outermost, distinct
                  from the mesh (the standing local-vs-web split).

An app may hold exposures at SEVERAL levels at once (one row per
level, each its own enable) — "multiple different definition levels"
are rows, not a single field.

Three treeObjects:

  AppArchExposure  the knob row: app ⇄ scope ⇄ which archipelago ⇄
                   OUR ROLE for that app at that level (server /
                   relay-only / user / observer). Enable/disable at
                   will; disabled and isle-scoped are
                   indistinguishable to the outside, which is the
                   point.
  MeshAppRelay     the lighthouse for one app: fans out a
                   WatchedObject's state (§5f verbatim — parent/
                   child versions, keyframes mandatory), cadence
                   adaptively adjusted between bounds, expected user
                   count for the census.
  MeshConsumer     one consumer, named BY its RNS identity hash.
                   kc_subject stays '' unless the consumer opted in
                   under the relay's kc_link_mode — and 'required'
                   DOES NOT EXIST as a mode: a zero-trust tier that
                   demands enrolment is not zero-trust.

Inter-archipelago: each arch holds FULL state (keyframes land at the
arch, so local consumers get wholeness locally); BETWEEN archs only
deltas travel, gRPC/protobuf-encoded (§2/ret-5).
ObjectStateVersion.source_arch_name already keys versions per arch;
the delta algebra is replication_basis's.

@consumers reticulum.reticulum_api, the relay daemon (sidecar,
           ret-5/ret-7)
@see modules/reticulum/replication_basis.py (the state machinery this
     reuses), plan §5n
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: The ladder — the reserved isle-mesh suffixes plus the internet.
#: Order matters: each rung includes the ones below it for ORIGIN
#: checks (an isle-local caller may use an arch-scoped app; a .mesh
#: consumer may not reach an arch-scoped one; web is outermost).
APP_SCOPE_VALUES = ('isle', 'arch', 'mesh', 'web')

#: What WE are for an app at a level (Dustin 2026-08-13): the node's
#: ROLE, not the app's nature. Default 'observer' — receive-only
#: presence, the §5i posture; being a server is declared, never
#: assumed.
MESH_APP_ROLE_VALUES = ('observer', 'user', 'relay-only', 'server')

#: KC linkage on the mesh tier: disabled (default) or optional.
#: 'required' is deliberately absent (DECIDED row 20) — the option
#: not existing is how the promise is kept.
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


class AppArchExposure(treeObject):
    """One app's participation at ONE level: scope + which
    archipelago + our ROLE there. An app may hold several exposure
    rows (one per level). Default isle + observer + disabled —
    raising a rung, or claiming a bigger role, is always a
    deliberate act."""

    @treeObjectInit
    def __init__(self, name='', app_name='', scope='isle',
                 arch_name='', role='observer', enabled=False,
                 exposed_by='', exposed_at='', notes='',
                 manager=None):
        self.name = name
        self.app_name = app_name
        self.scope = scope
        # WHICH archipelago carries it at 'arch' scope and above —
        # a farmer's market is a specific market, not all markets.
        self.arch_name = arch_name
        # what WE are for this app at this level: observer (receive-
        # only presence), user (submits under the data rules),
        # relay-only (forwards state, holds no authority), server
        # (the app's authoritative core — the lighthouse keeper).
        self.role = role
        self.enabled = enabled
        # who raised the rung, and when — exposure is provenance.
        self.exposed_by = exposed_by
        self.exposed_at = exposed_at
        self.notes = notes


class MeshAppRelay(treeObject):
    """The lighthouse: broadcasts one app's state to the open sea.
    Reuses the §5f machinery wholesale — watched_name points at the
    WatchedObject whose parent/child versions and keyframes carry
    the actual state."""

    @treeObjectInit
    def __init__(self, name='', app_name='', exposure_name='',
                 watched_name='', cadence_seconds=60,
                 min_cadence_seconds=10, max_cadence_seconds=600,
                 prior_states_kept=1, expected_users=0,
                 kc_link_mode='disabled', enabled=False, notes='',
                 manager=None):
        self.name = name
        self.app_name = app_name
        self.exposure_name = exposure_name
        self.watched_name = watched_name
        # current cadence — adaptive_cadence() moves it between the
        # bounds; the floor answers to the airtime budget (row 19).
        self.cadence_seconds = cadence_seconds
        self.min_cadence_seconds = min_cadence_seconds
        self.max_cadence_seconds = max_cadence_seconds
        # current + N prior states ride each keyframe window.
        self.prior_states_kept = prior_states_kept
        self.expected_users = expected_users
        self.kc_link_mode = kc_link_mode
        self.enabled = enabled
        self.notes = notes


class KitProfile(treeObject):
    """A named per-person equipment CONFIGURATION (§5q, Dustin
    2026-08-13): counts of devices one person carries — the unit the
    population sims count PEOPLE by. Percentages are analytics;
    counts of people per profile are the configuration."""

    @treeObjectInit
    def __init__(self, name='', display_name='', devices_json='{}',
                 intent='custom', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        # {'lora': 1, 'ham-rx': 1, 'wifi-halow': 1} — builds from the
        # population vocabulary, counts per person.
        self.devices_json = devices_json
        # everyday | broadcaster | backbone | custom — what this kit
        # is FOR, so a planner reads intent, not just parts.
        self.intent = intent
        self.notes = notes


#: Dustin's three worked examples (2026-08-13), verbatim.
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


class MeshConsumer(treeObject):
    """One mesh consumer. Its NAME is its Reticulum identity
    hash — the pseudonym IS the identity, and that is enough."""

    @treeObjectInit
    def __init__(self, name='', relay_name='', first_seen_ms=0,
                 last_seen_ms=0, last_return_interval_s=0.0,
                 returns_in_window=0, kc_subject='', kc_signed=False,
                 notes='', manager=None):
        self.name = name
        self.relay_name = relay_name
        self.first_seen_ms = first_seen_ms
        self.last_seen_ms = last_seen_ms
        # the feedback adaptive_cadence() aggregates.
        self.last_return_interval_s = last_return_interval_s
        self.returns_in_window = returns_in_window
        # '' unless the consumer OPTED IN under kc_link_mode
        # 'optional'; kc_signed says whether the linked identity is
        # signed or anonymous on the mesh-app's local Keycloak.
        self.kc_subject = kc_subject
        self.kc_signed = kc_signed
        self.notes = notes
