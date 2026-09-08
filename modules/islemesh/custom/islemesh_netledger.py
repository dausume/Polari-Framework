"""
@module islemesh.custom.islemesh_netledger

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

Four resource kinds: CIDR pools, single published ports (proto
'tcp' unless stated — 80/tcp and 80/udp are different resources),
UDP port RANGES (mtg-0: a WebRTC media server owns a range, not a
port; LiveKit is the first tenant), and SYNTHETIC-IP pools (ret-3:
addresses a resolver hands out for mesh names — never real hosts,
so they must overlap NEITHER each other NOR any docker pool on the
host, or the resolver answers with an address docker also routes).

@consumers
  - islemesh.custom.islemesh_coherence (per-device pools/ports + conflicts)
  - islemesh.islemesh_api (/api/islemesh/coherence)
  - islemesh.islemesh_selftest
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
    """Host ports published more than once. ports: [{port,proto?,...}].
    proto defaults 'tcp' — 80/tcp and 80/udp are DIFFERENT resources,
    so the key is (port, proto). tcp dups stay the bare port value
    (pre-udp callers keep their shape); others render 'port/proto'."""
    seen, dup = set(), []
    for p in ports:
        key = (p.get('port'), (p.get('proto') or 'tcp').lower())
        if key in seen and key not in dup:
            dup.append(key)
        seen.add(key)
    return (sorted(pt for pt, proto in dup if proto == 'tcp')
            + sorted('%s/%s' % (pt, proto)
                     for pt, proto in dup if proto != 'tcp'))


def _as_range(r):
    """(lo, hi) ints for a range row {lo, hi} or None if unusable."""
    try:
        lo, hi = int(r.get('lo')), int(r.get('hi'))
    except (TypeError, ValueError):
        return None
    if not (0 < lo <= hi <= 65535):
        return None
    return (lo, hi)


def udp_range_conflicts(udp_ranges, ports=None):
    """UDP port-RANGE collisions on ONE host — the media-server
    resource kind (a WebRTC server owns a range, not a port).
    udp_ranges: [{name, lo, hi}, ...]; ports (optional) are the
    single published ports, whose udp rows also collide with a range.
    Returns [{a, b, range_a, range_b}, ...] with ranges as 'lo-hi'
    (a single port renders as 'p/udp')."""
    out = []
    items = [(r.get('name', '?'), _as_range(r))
             for r in (udp_ranges or [])]
    items = [(n, r) for n, r in items if r]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (na, (alo, ahi)), (nb, (blo, bhi)) = items[i], items[j]
            if alo <= bhi and blo <= ahi:
                out.append({'a': na, 'b': nb,
                            'range_a': '%d-%d' % (alo, ahi),
                            'range_b': '%d-%d' % (blo, bhi)})
    for p in (ports or []):
        if (p.get('proto') or 'tcp').lower() != 'udp':
            continue
        try:
            pt = int(p.get('port'))
        except (TypeError, ValueError):
            continue
        for n, (lo, hi) in items:
            if lo <= pt <= hi:
                out.append({'a': p.get('container', '?'), 'b': n,
                            'range_a': '%d/udp' % pt,
                            'range_b': '%d-%d' % (lo, hi)})
    return out


def free_udp_range(udp_ranges, ports=None, width=100,
                   lo=50000, hi=60999):
    """Suggest a UDP range of `width` ports colliding with no
    registered range/udp port (WebRTC media space by default).
    Deterministic scan — the allocator's hint, like free_port."""
    taken = [r for r in [_as_range(x) for x in (udp_ranges or [])] if r]
    for p in (ports or []):
        if (p.get('proto') or 'tcp').lower() != 'udp':
            continue
        try:
            pt = int(p.get('port'))
        except (TypeError, ValueError):
            continue
        taken.append((pt, pt))
    start = lo
    while start + width - 1 <= hi:
        end = start + width - 1
        clash = next((t for t in taken
                      if t[0] <= end and start <= t[1]), None)
        if clash is None:
            return {'lo': start, 'hi': end}
        start = clash[1] + 1
    return None


def synthetic_pool_conflicts(synthetic_pools, pools=None):
    """Synthetic-IP pool collisions on ONE host (ret-3): a synthetic
    pool is a CIDR the mesh resolver answers from for *.rns.isle /
    .arch names — routed to the gateway, never a real network. It
    therefore collides with OTHER synthetic pools AND with any real
    docker pool on the host. Returns the pool_conflicts shape with a
    'kind' key naming which collision it is."""
    out = []
    for c in pool_conflicts(synthetic_pools or []):
        out.append(dict(c, kind='synthetic-vs-synthetic'))
    for s in (synthetic_pools or []):
        if not s.get('cidr'):
            continue
        for p in (pools or []):
            if p.get('cidr') and cidrs_overlap(s['cidr'], p['cidr']):
                out.append({'a': s.get('name', '?'),
                            'b': p.get('name', '?'),
                            'cidr_a': s['cidr'], 'cidr_b': p['cidr'],
                            'kind': 'synthetic-vs-real'})
    return out


def free_synthetic_pool(pools, synthetic_pools=None, prefix='10.77',
                        third_lo=0, third_hi=250):
    """Suggest a /24 for the mesh resolver that overlaps no docker
    pool and no other synthetic pool. 10.77.x.0/24 by default —
    deliberately far from docker's 172.16/12 habit and the RFC1918
    space isle-mesh hands out, but STILL checked against everything
    registered (a habit is not a reservation)."""
    taken = [p for p in (pools or []) if p.get('cidr')] \
        + [p for p in (synthetic_pools or []) if p.get('cidr')]
    for third in range(third_lo, third_hi):
        cand = '%s.%d.0/24' % (prefix, third)
        if not any(cidrs_overlap(cand, p['cidr']) for p in taken):
            return cand
    return None


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
        for c in udp_range_conflicts(d.get('udp_ranges') or [],
                                     d.get('ports') or []):
            out.append({
                'level': 'warn', 'code': 'udp-range-conflict',
                'message': '%s: UDP ranges collide — %s (%s) vs '
                           '%s (%s). Media servers on this host '
                           'will fight over ports.' % (
                               name, c['a'], c['range_a'],
                               c['b'], c['range_b'])})
        for c in synthetic_pool_conflicts(
                d.get('synthetic_pools') or [], d.get('pools') or []):
            out.append({
                'level': 'warn', 'code': 'synthetic-pool-conflict',
                'message': '%s: synthetic-IP pool collides (%s) — %s '
                           '(%s) vs %s (%s). The mesh resolver would '
                           'hand out addresses %s.' % (
                               name, c['kind'], c['a'], c['cidr_a'],
                               c['b'], c['cidr_b'],
                               'docker also routes'
                               if c['kind'] == 'synthetic-vs-real'
                               else 'two resolvers both claim')})
    return out
