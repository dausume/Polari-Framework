"""
@cross-cutting
@module reticulum.reticulum_basis
@tags @xc:bindings

Reticulum transport core (ret-1, RETICULUM_TRANSPORT_PLAN §4): the
object model for mesh transport over Reticulum — the third module born
manifest-first on the dyn-1 machinery (scanning, collab walked first).

The one hard architectural line (plan ret-8, inherited VERBATIM from
LiveKit §2), stated here because this module is where it would be
easiest to violate:

    NOTHING ARRIVING FROM ANOTHER ISLE OVER RETICULUM MAY MUTATE
    POLARI STATE. Inbound app data becomes a PROPOSAL through the
    ordinary ai_actions path; applying stays a confirmed act.

Licence: the RNS stack is pinned to the last MIT releases
(rns==0.9.4 + lxmf==0.6.3, RETICULUM_LICENCE_GATE.md) — pins are
LICENCE pins, never `>=`. This module itself never imports RNS: the
stack lives in the pol-reticulum sidecar (plan §5k); rows here are
facts ABOUT the mesh.

Six treeObjects (auto-CRUDE + persisted — object-coherence):

  ReticulumIdentity     an identity we hold or trust. Keycloak stays
                        the authority for PEOPLE (mtg-2 lesson);
                        this row BINDS a KC subject / an instance to
                        an RNS identity. PRIVATE KEYS NEVER LAND IN
                        A ROW — only the hash and where the key lives.
  ReticulumDestination  name ⇄ destination hash, aspects, scope,
                        direction, destination type (single|plain|…).
  ReticulumInterface    one physical/logical link and its DECLARED
                        parameters, with MEASURED facts kept separate
                        (fidelity — the resources-module idiom). Also
                        carries the regulatory domain and rx/tx
                        direction as DEVICE FACTS (§5g/§5i).
  TransportBinding      "this app endpoint reaches that destination"
                        + the admission POLICY (encoding, size, rate,
                        FEC, snapshot mode) — ret-3's detection as
                        data rather than code.
  LinkMeasurement       measured facts PER PATH, not per interface
                        (§5e: latency is a property of the path);
                        every fact carries a timestamp — stale
                        measurements are not measurements.
  AirtimeBudget         duty-cycle accounting per interface: the
                        netledger analogue for spectrum. Airtime is
                        ledgered, never assumed.

@consumers
  - polariApiServer.polariServer.defClassList (auto-CRUDE + persistence)
  - reticulum.reticulum_api (capability, arch listing, inbound seam)
@see modules/reticulum/rns_remote.py (the resolution ladder),
     modules/collab/collab_basis.py (the pattern this walks),
     RETICULUM_TRANSPORT_PLAN.md (decisions ledger — do not relitigate)
"""

import json
import re

from objectTreeDecorators import treeObject, treeObjectInit

#: Identity kinds. 'instance' is the DEFAULT binding level (§6
#: assumption 2026-08-13): one RNS identity per Polari instance, users
#: authorized behind it by ordinary KC auth. 'operator' exists for the
#: per-user case (e.g. a HAM operator's own identity) so the schema
#: never needs to change if Dustin flips the assumption.
IDENTITY_KIND_VALUES = ('instance', 'operator')

#: Destination types, mirroring RNS. 'plain' is the §5g hinge — the
#: UNENCRYPTED mode a lawful amateur path needs (existence verified in
#: ret-0, 2026-08-13, rns 0.9.4).
DESTINATION_TYPE_VALUES = ('single', 'group', 'plain')

#: Reachability scope vocabulary — LAN vs mesh vs internet are
#: DISTINCT surfaces (the lan-access lesson).
DESTINATION_SCOPE_VALUES = ('local', 'mesh', 'web')

#: Traffic direction on a destination or binding.
DIRECTION_VALUES = ('in', 'out', 'both')

#: Bearers (§5d): LoRa is ONE bearer, not THE bearer. Nothing above
#: the interface row may assume LoRa's constraints.
BEARER_VALUES = ('tcp', 'udp', 'serial-kiss', 'rnode-lora', 'lorawan',
                 'wifi', 'wifi-halow', 'ethernet')

#: Regulatory domain is a DECLARED interface fact (§5f HAM block):
#: the gateway refuses encrypted payloads on 'amateur' by name, with
#: the rule cited. 'none' = wired/virtual links with no RF at all.
REGULATORY_DOMAIN_VALUES = ('none', 'ism', 'amateur', 'licensed-other')

#: rx/tx capability is a DEVICE FACT, not a preference (§5i): an
#: RTL-SDR is 'rx' because it cannot be anything else. A device that
#: cannot transmit never offers a transmit control.
INTERFACE_DIRECTION_VALUES = ('rx', 'tx', 'both')

#: Mesh encodings (DECIDED row 4): TWO formats cross the mesh — gRPC
#: (protobuf bodies, HTTP/2 terminated at each end) and JSON (honestly
#: labelled the expensive one). CBOR stays available as the middle
#: option if ret-4 measurements demand it. STOMP is OUT (stays LAN).
ENCODING_VALUES = ('grpc', 'json', 'cbor')

#: FEC / snapshot policies resolve per binding against the MEASURED
#: path (§5b/§5e) — 'auto' means "the path decides, and the row
#: records which it chose", never a silent global default.
FEC_MODE_VALUES = ('auto', 'off', 'on')
SNAPSHOT_MODE_VALUES = ('auto', 'snapshot', 'delta')

#: Declared-vs-measured split (resources idiom): every fact row says
#: which it is, and VM-flattered numbers are labelled as such (§5h).
FIDELITY_VALUES = ('declared', 'measured-vm', 'measured-real')

#: Names travel into config files, DNS labels and provenance lines:
#: one safe segment (the collab safe_room_name idiom).
_SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')


def safe_mesh_name(name):
    """True when *name* is a single safe name segment."""
    return bool(_SAFE_NAME_RE.match(name or '')) and '..' not in name


def measurement_fresh(measured_at_ms, now_ms, horizon_ms=900_000):
    """§5e: stale measurements are not measurements. Past the
    freshness horizon (default 15 min) the honest answer is 'unknown,
    measure first', not the last good number."""
    if not measured_at_ms:
        return False
    return (now_ms - measured_at_ms) <= horizon_ms


def derive_timeout_ms(measured_rtt_ms, margin_factor=4.0, floor_ms=2000):
    """§5e: timeouts must be DERIVED, never constant. Returns None when
    there is no measurement to derive from — the caller must refuse
    (with the reason) rather than invent a constant."""
    if not measured_rtt_ms or measured_rtt_ms <= 0:
        return None
    return max(int(measured_rtt_ms * margin_factor), floor_ms)


def airtime_ms(payload_bytes, bitrate_bps, overhead_bytes=40):
    """Airtime a payload will cost on a bearer, in ms. An ESTIMATE for
    admission arithmetic — ret-6 measures the real thing. Returns None
    (refuse, don't guess) when the bitrate is unknown."""
    if not bitrate_bps or bitrate_bps <= 0:
        return None
    return int(((payload_bytes + overhead_bytes) * 8 * 1000) / bitrate_bps)


def budget_admits(consumed_ms, budget_ms, cost_ms):
    """Whether an airtime budget has room for one more send. A budget
    of 0/None means 'no budget declared' — on a duty-cycled bearer
    that is a refusal, not a free pass (callers pass the bearer)."""
    if cost_ms is None:
        return False
    if not budget_ms:
        return False
    return (consumed_ms + cost_ms) <= budget_ms


def tx_permitted(iface):
    """The TX legality gate as a pure rule: an RF interface may key
    up ONLY when it is enabled, tx-capable, and carries the
    operator's own legality confirmation (with its basis). Wired
    links (regulatory_domain 'none') pass on enabled+direction alone.
    Returns (True, None) or (False, {evidence, knob, action}).
    Config-mode/receive paths never consult this — RX is always
    ungated (§5i)."""
    if not iface.get('enabled'):
        return (False, {
            'evidence': 'interface is not enabled',
            'knob': 'ReticulumInterface.enabled',
            'action': 'enable the interface deliberately',
        })
    if iface.get('direction') not in ('tx', 'both'):
        return (False, {
            'evidence': 'interface direction is %r — this device '
                        'cannot or may not transmit'
                        % iface.get('direction'),
            'knob': 'ReticulumInterface.direction (a device FACT)',
            'action': 'use an rx path, or attach tx-capable hardware',
        })
    if iface.get('regulatory_domain', 'none') == 'none':
        return (True, None)
    if not iface.get('tx_legal_confirmed'):
        return (False, {
            'evidence': 'no operator legality confirmation on file '
                        'for this RF interface (radios SHIP with '
                        'unlawful defaults — the SH-L1A pair arrived '
                        'on 873.125 MHz, outside US ISM)',
            'knob': 'ReticulumInterface.tx_legal_confirmed + '
                    'tx_legal_basis (the operator\'s own assertion, '
                    'never a software legal claim)',
            'action': 'read the device\'s ACTUAL configured '
                      'frequency/power, confirm them against your '
                      'jurisdiction, record the confirmation, then '
                      'transmit',
        })
    return (True, None)


def may_route(publication_class, regulatory_domain, encrypted):
    """§5f/§5g: the two refusals that make the mesh lawful to operate,
    as one pure rule. Returns (True, '') or (False, reason-by-name).
    NOT legal advice — conservative DEFAULTS the operator can knob
    (the plan states no legal conclusions)."""
    if regulatory_domain == 'amateur':
        if encrypted:
            return (False,
                    'refused: encrypted payload on an amateur-domain '
                    'interface (conservative default: amateur bands '
                    'prohibit obscured meaning; knob: interface '
                    'regulatory_domain / binding encoding)')
        if publication_class != 'public':
            return (False,
                    'refused: publication_class %r on an amateur-domain '
                    'interface — the HAM segment is a PUBLIC, PERMANENT '
                    'broadcast; only rows explicitly marked public may '
                    'cross it' % (publication_class,))
    return (True, '')


def admit_binding(policy, path_fact, payload_bytes, now_ms,
                  horizon_ms=900_000):
    """The gateway's admission decision for one send, as a pure rule:
    policy = dict from a TransportBinding row, path_fact = dict from a
    LinkMeasurement row (or None). Returns (True, None) or (False,
    refusal) where refusal carries the standing three keys
    {evidence, knob, action} — every refusal names its evidence.
    """
    max_bytes = policy.get('max_message_bytes') or 0
    if max_bytes and payload_bytes > max_bytes:
        return (False, {
            'evidence': 'payload %d B exceeds binding max %d B'
                        % (payload_bytes, max_bytes),
            'knob': 'TransportBinding.max_message_bytes',
            'action': 'raise the binding limit or shrink the message',
        })
    if path_fact is None:
        return (False, {
            'evidence': 'no LinkMeasurement for this path — unknown, '
                        'measure first (stale/absent facts are not '
                        'facts)',
            'knob': 'LinkMeasurement rows (ret-6 battery)',
            'action': 'measure the path, then retry',
        })
    if not measurement_fresh(path_fact.get('measured_at_ms', 0), now_ms,
                             horizon_ms):
        return (False, {
            'evidence': 'path measurement is stale (measured_at_ms=%s, '
                        'horizon %d ms)' % (
                            path_fact.get('measured_at_ms'), horizon_ms),
            'knob': 'freshness horizon (admit_binding horizon_ms)',
            'action': 're-measure the path, then retry',
        })
    cost = airtime_ms(payload_bytes, path_fact.get('throughput_bps', 0))
    if cost is None:
        return (False, {
            'evidence': 'path throughput unknown — airtime cost cannot '
                        'be computed',
            'knob': 'LinkMeasurement.throughput_bps',
            'action': 'measure throughput on this path',
        })
    budget = path_fact.get('budget_ms', None)
    consumed = path_fact.get('consumed_ms', 0)
    if budget is not None and not budget_admits(consumed, budget, cost):
        return (False, {
            'evidence': 'airtime budget would be exceeded: consumed %s '
                        'ms + cost %s ms > budget %s ms'
                        % (consumed, cost, budget),
            'knob': 'AirtimeBudget on the interface',
            'action': 'queue (store-and-forward, ret-7) or defer to a '
                      'cheaper bearer',
        })
    return (True, None)


def capability_for_path(path_fact, now_ms, horizon_ms=900_000):
    """§5e: capability is answered PER PEER with evidence — 'gRPC
    unary: yes; streaming: no, this path is 1.2 kbps at 4 hops'.
    Returns a dict of honest answers; 'unknown' when facts are stale."""
    if path_fact is None or not measurement_fresh(
            path_fact.get('measured_at_ms', 0), now_ms, horizon_ms):
        return {'known': False,
                'reason': 'unknown, measure first — no fresh '
                          'measurement for this path'}
    bps = path_fact.get('throughput_bps', 0) or 0
    rtt = path_fact.get('rtt_ms', 0) or 0
    return {
        'known': True,
        'grpc_unary': bps >= 300,
        'grpc_streaming': bps >= 100_000,
        'grpc_streaming_reason': (
            '' if bps >= 100_000 else
            'path is %d bps at %s hops — streaming assumes a fat pipe'
            % (bps, path_fact.get('hop_count', '?'))),
        'json_max_bytes': max(int(bps / 8), 256) if bps else 0,
        'derived_timeout_ms': derive_timeout_ms(rtt),
        'evidence': {'throughput_bps': bps, 'rtt_ms': rtt,
                     'hop_count': path_fact.get('hop_count'),
                     'worst_hop_bearer':
                         path_fact.get('worst_hop_bearer', ''),
                     'fidelity': path_fact.get('fidelity', 'declared')},
    }


class ReticulumIdentity(treeObject):
    """An RNS identity we hold or trust. Binds an INSTANCE (default,
    §6 assumption) or a KC subject to an identity hash. Private keys
    never land in a row — key_location is a label naming where the
    sidecar keeps it, not material."""

    @treeObjectInit
    def __init__(self, name='', kind='instance', instance_name='',
                 kc_subject='', identity_hash='', key_location='',
                 held=False, source='', notes='', manager=None):
        self.name = name
        self.kind = kind
        self.instance_name = instance_name
        # NULLABLE by design: instance-level is the default binding;
        # a per-user (operator) identity fills this in.
        self.kc_subject = kc_subject
        self.identity_hash = identity_hash
        self.key_location = key_location
        # Whether WE hold the private key (vs. a trusted remote peer).
        self.held = held
        # How this identity entered the rows — evidence, never bare.
        self.source = source
        self.notes = notes


class ReticulumDestination(treeObject):
    """name ⇄ RNS destination hash. The row §3's name registry is made
    of: the gateway refuses unmapped addresses BY NAME."""

    @treeObjectInit
    def __init__(self, name='', identity_name='', app_name='polari',
                 aspects='', dest_hash='', dest_type='single',
                 scope='local', direction='both', notes='',
                 manager=None):
        self.name = name
        self.identity_name = identity_name
        self.app_name = app_name
        # Dot-joined aspect list ('ret0.gossip') — scalar on purpose.
        self.aspects = aspects
        self.dest_hash = dest_hash
        self.dest_type = dest_type
        self.scope = scope
        self.direction = direction
        self.notes = notes


class ReticulumInterface(treeObject):
    """One physical/logical link. Declared parameters and measured
    facts kept SEPARATE (fidelity); regulatory domain and rx/tx
    direction are device facts every surface must read."""

    @treeObjectInit
    def __init__(self, name='', bearer='tcp', platform='linux',
                 regulatory_domain='none', direction='both',
                 declared_params_json='{}', measured_facts_json='{}',
                 fidelity='declared', device_link_name='',
                 enabled=False, tx_legal_confirmed=False,
                 tx_legal_basis='', tx_legal_confirmed_by='',
                 tx_legal_confirmed_at='', notes='', manager=None):
        self.name = name
        self.bearer = bearer
        # 'linux' (Ubuntu default target, §5j) | 'openwrt' (the router
        # CASE, isle-core's work) — platform-specific behaviour lives
        # behind this field, never in code assumptions.
        self.platform = platform
        self.regulatory_domain = regulatory_domain
        self.direction = direction
        self.declared_params_json = declared_params_json
        self.measured_facts_json = measured_facts_json
        self.fidelity = fidelity
        # The DeviceLink row backing this interface, when hardware.
        self.device_link_name = device_link_name
        self.enabled = enabled
        # THE TX LEGALITY GATE (Dustin 2026-08-13: "never transmit
        # anything without confirming it is legal first" — earned the
        # same day: the SH-L1A pair SHIPPED on 873.125 MHz, outside US
        # ISM). The software records the OPERATOR's confirmation with
        # its basis and refuses TX without it; it makes no legal
        # claims itself (§5f framing). RF-domain interfaces only —
        # wired links (regulatory_domain 'none') are not gated.
        self.tx_legal_confirmed = tx_legal_confirmed
        # e.g. '915.125 MHz @ 22 dBm, US 902-928 ISM' — WHAT was
        # confirmed, so a later config change visibly invalidates it.
        self.tx_legal_basis = tx_legal_basis
        self.tx_legal_confirmed_by = tx_legal_confirmed_by
        self.tx_legal_confirmed_at = tx_legal_confirmed_at
        self.notes = notes


class TransportBinding(treeObject):
    """'This app endpoint reaches that destination' + the admission
    policy — what makes ret-3's detection DATA rather than code."""

    @treeObjectInit
    def __init__(self, name='', app_protocol='', endpoint='',
                 destination_name='', encoding='grpc',
                 max_message_bytes=4096, max_rate_per_min=60,
                 priority=5, fec_mode='auto', snapshot_mode='auto',
                 direction='both', enabled=False, notes='',
                 manager=None):
        self.name = name
        # e.g. 'grpc-unary', 'http-get', 'json-message' — the named
        # handful; truly arbitrary IP is a promise the physics cannot
        # keep (plan §6, assumed as written).
        self.app_protocol = app_protocol
        self.endpoint = endpoint
        self.destination_name = destination_name
        self.encoding = encoding
        self.max_message_bytes = max_message_bytes
        self.max_rate_per_min = max_rate_per_min
        self.priority = priority
        self.fec_mode = fec_mode
        self.snapshot_mode = snapshot_mode
        self.direction = direction
        self.enabled = enabled
        self.notes = notes


class LinkMeasurement(treeObject):
    """Measured facts PER PATH (destination + bearer path), §5e — a
    fast local interface says nothing about a peer three hops away
    whose last hop is LoRa. Turns §2's placeholders into facts; the
    fidelity field says HOW the number was obtained (a VM number must
    never decide an encoding/FEC choice, §5h)."""

    @treeObjectInit
    def __init__(self, name='', destination_name='',
                 bearer_path_json='[]', hop_count=0,
                 worst_hop_bearer='', throughput_bps=0, rtt_ms=0,
                 loss_rate=0.0, airtime_ms_consumed=0,
                 measured_at_ms=0, fidelity='declared', notes='',
                 manager=None):
        self.name = name
        self.destination_name = destination_name
        # Ordered bearer list for the path, worst hop named beside it.
        self.bearer_path_json = bearer_path_json
        self.hop_count = hop_count
        self.worst_hop_bearer = worst_hop_bearer
        self.throughput_bps = throughput_bps
        self.rtt_ms = rtt_ms
        self.loss_rate = loss_rate
        self.airtime_ms_consumed = airtime_ms_consumed
        self.measured_at_ms = measured_at_ms
        self.fidelity = fidelity
        self.notes = notes


class AirtimeBudget(treeObject):
    """Duty-cycle accounting per interface — the netledger analogue
    for spectrum. In some bands the budget is 1%; it is a hard budget,
    not a guideline, so it is LEDGERED."""

    @treeObjectInit
    def __init__(self, name='', interface_name='', window_seconds=3600,
                 budget_ms=0, consumed_ms=0, duty_cycle_pct=0.0,
                 window_started_ms=0, notes='', manager=None):
        self.name = name
        self.interface_name = interface_name
        self.window_seconds = window_seconds
        self.budget_ms = budget_ms
        self.consumed_ms = consumed_ms
        self.duty_cycle_pct = duty_cycle_pct
        self.window_started_ms = window_started_ms
        self.notes = notes


#: Seed: the ret-0 shape as a row — a wired/virtual TCP interface,
#: disabled until the sidecar exists (declaring is not enabling, the
#: collab scope precedent). No radio is seeded: hardware rows come
#: from real udev facts (§5j), never from hopeful defaults.
SEED_RNS_INTERFACES = [
    {
        'name': 'local-tcp',
        'bearer': 'tcp',
        'platform': 'linux',
        'regulatory_domain': 'none',
        'direction': 'both',
        'declared_params_json': json.dumps(
            {'listen_ip': '0.0.0.0', 'listen_port': 4242,
             'proven': 'ret-0 2026-08-13 (containers, default bridge)'}),
        'fidelity': 'declared',
        'enabled': False,
        'notes': 'The ret-0 proof shape: Reticulum TCP interface on '
                 'the LAN. Enable via pol compose reticulum (ret-2).',
    },
]
