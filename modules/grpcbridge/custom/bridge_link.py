"""
@module grpcbridge.custom.bridge_link

How a Polari Hardware Bridge reaches its Polari node, read from its PolariBridgeInstance row. It is the same for a cabled board and for its twin:
the far end (a serial port, or a twin session's line) is the only difference. The bridge's structs map to the node's objects through the
instance's `maps` (StructObjectMap names) and its `bridge_definition` (the HardwareBridgeDefinition whose project is generated). The bridge
pushes to the node's own gRPC name on the isle, over TLS checked against the isle trust bundle. No address is written by hand.

    grpc_name(node)          -> 'grpc.<node>.isle'   the node's gRPC name, beside its api name 'api.<node>.isle' (bridge_paths.node_url).
                                The isle's agent carries it to the backend's gRPC port; see AI-Notes/plans/ISLE_GRPC_ROUTE_REQUEST.md.
    grpc_target(node)        -> 'grpc.<node>.isle:443'
    instance(manager, name)  -> the PolariBridgeInstance as a dict: the server's row, else the seed (bridge_paths.SEED_POLARI_BRIDGES)
    link(row)                -> {'instance', 'node', 'node_url', 'target', 'tls', 'definition', 'maps', 'mode', 'hardware_id', 'why'}
                                Raises LinkRefused (words + an HTTP status) when check_bridge does not say `bound` or the instance has no
                                bridge_definition.

A plaintext link (`grpc.tls=plaintext`, the backend's own :3002 on a dev stack) stays possible only as an explicit grpc_target given by hand.
It never comes from an instance.
"""
from grpcbridge.custom import bridge_paths as BP

CLASS = 'PolariBridgeInstance'
GRPC_PORT_ON_ISLE = 443     # the agent's one TLS port; the name, not the port, picks the service
TLS = 'verified'
_FIELDS = ('name', 'hardware_id', 'polari_node', 'polari_node_url', 'mode', 'path', 'bench', 'pins', 'maps', 'bridge_definition', 'basis', 'notes')


class LinkRefused(RuntimeError):
    def __init__(self, why, status=409):
        super().__init__(why)
        self.status = status


def grpc_name(node):
    return 'grpc.%s.isle' % node


def grpc_target(node):
    return '%s:%d' % (grpc_name(node), GRPC_PORT_ON_ISLE)


def _get(o, k):
    return o.get(k, '') if isinstance(o, dict) else getattr(o, k, '')


def instance(manager, name):
    """The instance row as a dict: the server's PolariBridgeInstance table first, else the seed of that name."""
    tabs = getattr(manager, 'objectTables', None) or {}
    rows = [r for r in (tabs.get(CLASS) or {}).values() if _get(r, 'name') == name]
    if not rows:
        rows = [r for r in BP.SEED_POLARI_BRIDGES if r['name'] == name]
    if not rows:
        known = sorted({_get(r, 'name') for r in (tabs.get(CLASS) or {}).values()} | {r['name'] for r in BP.SEED_POLARI_BRIDGES})
        raise LinkRefused('no Polari bridge instance %r (known: %s; GET /api/grpc/bench-bridges/<bench> lists them)' % (name, ', '.join(known) or 'none'), 404)
    return {k: _get(rows[0], k) for k in _FIELDS}


def link(row):
    status, why = BP.check_bridge(row)   # the node, its isle url, the mode, the hardware id; the cable path is the bench view's question, not the link's
    if status != 'bound':
        raise LinkRefused('the bridge instance %s is not bound, so it has no Polari node to push to: %s' % (row.get('name', '?'), why), 409)
    definition = (row.get('bridge_definition') or '').strip()
    if not definition:
        raise LinkRefused('the bridge instance %s names no bridge_definition: nothing says which structs it carries or which objects they become'
                          % row['name'], 422)
    node = row['polari_node'].strip()
    return {'instance': row['name'], 'node': node, 'node_url': BP.node_url(node), 'target': grpc_target(node), 'tls': TLS, 'definition': definition,
            'maps': row.get('maps') or '', 'mode': row.get('mode') or 'serial', 'hardware_id': row.get('hardware_id') or '',
            'why': 'bridge %s -> Polari node %s at %s (gRPC, TLS checked against the isle trust bundle); its structs map by %s'
                   % (row['name'], node, grpc_name(node), row.get('maps') or '(no StructObjectMap named)')}
