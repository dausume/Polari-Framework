"""@module reticulum.objects.reticulum._shared — what the reticulum row classes share (constants, seeds, helpers); split from reticulum_basis.py (sap-2c)."""
import json
import re

IDENTITY_KIND_VALUES = ('instance', 'operator')
DESTINATION_TYPE_VALUES = ('single', 'group', 'plain')
DESTINATION_SCOPE_VALUES = ('local', 'mesh', 'web')
DIRECTION_VALUES = ('in', 'out', 'both')
BEARER_VALUES = ('tcp', 'udp', 'serial-kiss', 'rnode-lora', 'lorawan',
                 'wifi', 'wifi-halow', 'ethernet')
REGULATORY_DOMAIN_VALUES = ('none', 'ism', 'amateur', 'licensed-other')
INTERFACE_DIRECTION_VALUES = ('rx', 'tx', 'both')
ENCODING_VALUES = ('grpc', 'json', 'cbor')
FEC_MODE_VALUES = ('auto', 'off', 'on')
SNAPSHOT_MODE_VALUES = ('auto', 'snapshot', 'delta')
FIDELITY_VALUES = ('declared', 'measured-vm', 'measured-real')
IDLE_POLICY_VALUES = ('silent', 'rx-hold', 'hold-open')
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
def interface_may_attach(iface, active_uses=0):
    """DECIDED row 19: whether an interface may be attached to the
    running stack AT ALL. Wired links attach freely; an RF interface
    with idle_policy 'silent' attaches only while something is
    actively declared to use it — detached is the only state that
    GUARANTEES dark. Returns (bool, reason)."""
    if not iface.get('enabled'):
        return (False, 'interface not enabled')
    if iface.get('regulatory_domain', 'none') == 'none':
        return (True, '')
    policy = iface.get('idle_policy', 'silent')
    if policy == 'silent' and not active_uses:
        return (False,
                'idle_policy silent and no active use — the radio '
                'stays detached (set rx-hold to listen while idle, '
                'hold-open to stay reachable; both are deliberate)')
    return (True, '')
def may_announce(iface, active_uses=0):
    """Announces ARE transmissions: on an RF interface they happen
    only for an active declared use, or under the operator's explicit
    hold-open. An idle radio does not introduce itself."""
    if iface.get('regulatory_domain', 'none') == 'none':
        return True
    if not tx_permitted(iface)[0]:
        return False
    if iface.get('idle_policy', 'silent') == 'hold-open':
        return True
    return active_uses > 0
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
