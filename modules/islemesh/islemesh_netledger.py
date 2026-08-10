"""
@module islemesh.islemesh_netledger

The NETWORK RESOURCE LEDGER (Dustin 2026-08-09): track the subnets/
pools and published ports each device has allocated, so a
near-arbitrary number of apps/engines can be added to the isle-mesh
WITHOUT collision. Pure functions over plain rows — the allocator
and the conflict assessments both read these; nothing here acts.

A pool collision (the econ-core case: the isle agent's fixed
172.20/16 vs the odoo suite's network on the same pool) is a
per-HOST fact — two docker networks on one host cannot overlap.
Ports are likewise per-host. This module makes both VISIBLE and
CHECKABLE.

@consumers
  - islemesh.islemesh_coherence (per-device pools/ports + conflicts)
  - islemesh.islemesh_api (/api/islemesh/coherence)
  - islemesh.selftest_islemesh
"""


def _ip_to_int(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return None
    try:
        a, b, c, d = (int(x) for x in parts)
    except ValueError:
        return None
    if not all(0 <= x <= 255 for x in (a, b, c, d)):
        return None
    return (a << 24) | (b << 16) | (c << 8) | d


def _cidr_range(cidr):
    """(net_int, mask_int) for 'A.B.C.D/N', or None if unparseable."""
    if '/' not in cidr:
        return None
    ip, bits = cidr.split('/', 1)
    base = _ip_to_int(ip)
    try:
        n = int(bits)
    except ValueError:
        return None
    if base is None or not (0 <= n <= 32):
        return None
    mask = 0 if n == 0 else ((0xFFFFFFFF << (32 - n)) & 0xFFFFFFFF)
    return (base & mask, mask)


def cidrs_overlap(a, b):
    """Do two CIDR strings share any address?"""
    ra, rb = _cidr_range(a), _cidr_range(b)
    if ra is None or rb is None:
        return False
    (na, ma), (nb, mb) = ra, rb
    mask = ma & mb  # the shorter (coarser) mask
    return (na & mask) == (nb & mask)


def pool_conflicts(pools):
    """Overlapping pools within ONE host's list.
    pools: [{name, cidr}, ...] → [{a, b, cidr_a, cidr_b}, ...]."""
    out = []
    items = [p for p in pools if p.get('cidr')]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if cidrs_overlap(items[i]['cidr'], items[j]['cidr']):
                out.append({
                    'a': items[i].get('name', '?'),
                    'b': items[j].get('name', '?'),
                    'cidr_a': items[i]['cidr'],
                    'cidr_b': items[j]['cidr']})
    return out


def port_conflicts(ports):
    """Host ports published more than once. ports: [{port,...}]."""
    seen, dup = set(), set()
    for p in ports:
        pt = p.get('port')
        if pt in seen:
            dup.add(pt)
        seen.add(pt)
    return sorted(dup)


def free_subnet(pools, prefix='172', second_lo=22, second_hi=250):
    """Suggest a /24 that overlaps none of `pools` (docker-bridge
    space by default). Deterministic scan — the allocator's hint."""
    for second in range(second_lo, second_hi):
        cand = '%s.%d.0.0/24' % (prefix, second)
        if not any(cidrs_overlap(cand, p['cidr'])
                   for p in pools if p.get('cidr')):
            return cand
    return None


def free_port(ports, lo=18080, hi=18999):
    """Suggest a host port not already published. The expose hint."""
    taken = {p.get('port') for p in ports}
    for pt in range(lo, hi):
        if pt not in taken:
            return pt
    return None


def assess_resources(devices):
    """Per-device pool/port conflict assessments (suggest-only).
    devices: [{name, pools:[{name,cidr}], ports:[{port,container}],
               is_mock}, ...]."""
    out = []
    for d in devices:
        if d.get('is_mock'):
            continue
        name = d.get('name', '')
        for c in pool_conflicts(d.get('pools') or []):
            out.append({
                'level': 'warn', 'code': 'pool-overlap',
                'message': '%s: docker pools overlap — %s (%s) vs '
                           '%s (%s). New networks on this host may '
                           'fail to allocate.' % (
                               name, c['a'], c['cidr_a'],
                               c['b'], c['cidr_b'])})
        dup = port_conflicts(d.get('ports') or [])
        if dup:
            out.append({
                'level': 'warn', 'code': 'port-conflict',
                'message': '%s: host port(s) %s published more than '
                           'once' % (name, ', '.join(map(str, dup)))})
    return out
