"""
@cross-cutting
@module polariPeers.peer_node
@tags @xc:bindings

PeerNode — another Polari instance this one knows about. The first
primitive of node integration (framework trajectory step 3): peers
register with a shared token, get pinged for liveness, and expose their
definitions + modules for probing (see polariPeers.peers_api).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - polariPeers.peers_api
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PeerNode(treeObject):
    """One known peer Polari instance. Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Base URL this instance uses to reach the peer's API, e.g.
        # 'http://prf-b-backend:3000' over the polari-link network.
        base_url: str = '',
        # 'alive' | 'unreachable' | 'unknown' — updated on liveness pings.
        status: str = 'unknown',
        # ISO timestamp of the last successful ping.
        last_seen: str = '',
        # Peer-reported identity from its /api/peers/ping (instance name,
        # module count, ...) — cached JSON for display.
        identity_json: str = '{}',
        manager=None,
    ):
        self.name = name
        self.base_url = base_url
        self.status = status
        self.last_seen = last_seen
        self.identity_json = identity_json
