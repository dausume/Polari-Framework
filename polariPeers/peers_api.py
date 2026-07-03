"""
@cross-cutting
@module polariPeers.peers_api
@tags @xc:bindings

Peers + Modules API — the twin-Polari handshake surface.

Endpoints:
  GET  /api/peers                     — known peers, live-pinged
  POST /api/peers/register            — {name, baseUrl, token}; shared-token gated
  GET  /api/peers/ping                — THIS instance's identity (+ moduleCount)
  GET  /api/peers/{peer_name}/simulations
                                      — probe a peer's SimulationDefinitions
  GET  /api/modules                   — modules installed/installing here
  GET  /api/modules/{module_name}     — a module's manifest/bundle (Track 3
                                        fills bundles; a clear 404 until then)

Identity + token resolution (works WITHOUT recreating a running
container): env POLARI_INSTANCE_ID / POLARI_INSTANCE_NAME /
POLARI_PEER_TOKEN, with /app/data/peer_token as the token fallback so an
already-running instance can be enrolled via a file drop into its data
volume.

Peer HTTP calls use short timeouts and return structured errors — a dead
peer degrades a field to 'unreachable', never a 500.

@consumers
  - polariServer (route registration)
  - twin-polari-build.sh (registration handshake)
@see /OVERLAP_MAP.md
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import falcon

from objectTreeDecorators import treeObject, treeObjectInit

PEER_HTTP_TIMEOUT_S = 4
TOKEN_FILE = '/app/data/peer_token'


def instance_identity() -> Dict[str, Any]:
    iid = (os.environ.get('POLARI_INSTANCE_ID') or 'a').strip()
    name = (os.environ.get('POLARI_INSTANCE_NAME') or f'polari-{iid}').strip()
    return {'instanceId': iid, 'instanceName': name, 'framework': 'polari'}


def peer_token() -> str:
    tok = (os.environ.get('POLARI_PEER_TOKEN') or '').strip()
    if tok:
        return tok
    try:
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    except OSError:
        return ''


def _http_get_json(url: str) -> Dict[str, Any]:
    """GET a JSON document with a short timeout; structured error on
    failure ({'_error': msg})."""
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=PEER_HTTP_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {'_error': f'{type(exc).__name__}: {exc}'}


class PeersAPI(treeObject):
    """Peer + module handshake endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/peers'
        if polServer is not None:
            polServer.falconServer.add_route('/api/peers', self)
            polServer.falconServer.add_route(
                '/api/peers/register', self, suffix='register')
            polServer.falconServer.add_route(
                '/api/peers/ping', self, suffix='ping')
            polServer.falconServer.add_route(
                '/api/peers/{peer_name}/simulations', self,
                suffix='peer_simulations')
            polServer.falconServer.add_route(
                '/api/modules', self, suffix='modules')
            polServer.falconServer.add_route(
                '/api/modules/{module_name}', self, suffix='module_one')

    # ------------------------------------------------------------------
    # GET /api/peers — known peers, live-pinged.
    # ------------------------------------------------------------------
    def on_get(self, request, response):
        out: List[Dict[str, Any]] = []
        for peer in self._peer_rows():
            base = getattr(peer, 'base_url', '')
            ping = _http_get_json(f'{base}/api/peers/ping') if base else \
                {'_error': 'no base_url'}
            alive = '_error' not in ping
            peer.status = 'alive' if alive else 'unreachable'
            if alive:
                peer.last_seen = datetime.now(timezone.utc).isoformat()
                peer.identity_json = json.dumps(ping.get('data') or ping)
                self._persist(peer)
            out.append({
                'name': getattr(peer, 'name', ''),
                'baseUrl': base,
                'status': peer.status,
                'lastSeen': getattr(peer, 'last_seen', ''),
                'identity': _parse(getattr(peer, 'identity_json', '{}')),
                'error': ping.get('_error'),
            })
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # POST /api/peers/register — shared-token gated upsert.
    # ------------------------------------------------------------------
    def on_post_register(self, request, response):
        try:
            body = request.media or {}
        except Exception:
            body = {}
        expected = peer_token()
        if not expected:
            response.status = falcon.HTTP_403
            response.media = {
                'success': False,
                'error': ('This instance has no peer token configured '
                          '(POLARI_PEER_TOKEN or /app/data/peer_token) — '
                          'peer registration is disabled.'),
            }
            return
        if (body.get('token') or '') != expected:
            response.status = falcon.HTTP_403
            response.media = {'success': False, 'error': 'Invalid peer token.'}
            return
        name = (body.get('name') or '').strip()
        base_url = (body.get('baseUrl') or '').strip().rstrip('/')
        if not name or not base_url:
            response.status = falcon.HTTP_400
            response.media = {'success': False,
                              'error': "'name' and 'baseUrl' are required."}
            return
        peer = self._find_peer(name)
        if peer is None:
            from polariPeers.peer_node import PeerNode
            peer = PeerNode(name=name, base_url=base_url, status='unknown',
                            manager=self.manager)
        else:
            peer.base_url = base_url
        self._persist(peer)
        response.media = {'success': True,
                          'data': {'name': name, 'baseUrl': base_url}}
        response.status = falcon.HTTP_201

    # ------------------------------------------------------------------
    # GET /api/peers/ping — this instance's identity.
    # ------------------------------------------------------------------
    def on_get_ping(self, request, response):
        ident = instance_identity()
        ident['moduleCount'] = len(self._module_rows())
        ident['peersKnown'] = len(self._peer_rows())
        sims = self.manager.objectTables.get('SimulationDefinition', {}) or {}
        ident['simulationCount'] = len(sims)
        response.media = {'success': True, 'data': ident}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/peers/{peer_name}/simulations — probe a peer's sim defs.
    # ------------------------------------------------------------------
    def on_get_peer_simulations(self, request, response, peer_name):
        peer = self._find_peer(peer_name)
        if peer is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'Peer "{peer_name}" is not registered.'}
            return
        base = getattr(peer, 'base_url', '')
        payload = _http_get_json(f'{base}/SimulationDefinition')
        if '_error' in payload:
            response.status = falcon.HTTP_502
            response.media = {'success': False,
                              'error': f'Peer unreachable: {payload["_error"]}'}
            return
        sims = _parse_crude_rows(payload, 'SimulationDefinition')
        summaries = [{
            'name': r.get('name', ''),
            'intent': r.get('intent', 'observe'),
            'description': (r.get('description') or '')[:200],
        } for r in sims]
        response.media = {'success': True,
                          'data': {'peer': peer_name, 'simulations': summaries}}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/modules — what this instance has installed / is installing.
    # ------------------------------------------------------------------
    def on_get_modules(self, request, response):
        out = [{
            'name': getattr(m, 'name', ''),
            'version': getattr(m, 'version', ''),
            'sourceKind': getattr(m, 'source_kind', ''),
            'sourceRef': getattr(m, 'source_ref', ''),
            'status': getattr(m, 'status', ''),
            'manifest': _parse(getattr(m, 'manifest_json', '{}')),
        } for m in self._module_rows()]
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/modules/{module_name} — manifest + bundle when present.
    # ------------------------------------------------------------------
    def on_get_module_one(self, request, response, module_name):
        row = next((m for m in self._module_rows()
                    if getattr(m, 'name', '') == module_name), None)
        if row is None:
            response.status = falcon.HTTP_404
            response.media = {
                'success': False,
                'error': (f'No module named "{module_name}" on this '
                          f'instance. (The module exporter/loader arrives '
                          f'with Track 3 — this registry and API are its '
                          f'handshake skeleton.)'),
            }
            return
        bundle_raw = getattr(row, 'bundle_json', '') or ''
        response.media = {
            'success': True,
            'data': {
                'name': module_name,
                'version': getattr(row, 'version', ''),
                'status': getattr(row, 'status', ''),
                'manifest': _parse(getattr(row, 'manifest_json', '{}')),
                'bundle': _parse(bundle_raw) if bundle_raw else None,
            },
        }
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _peer_rows(self) -> List:
        return list((self.manager.objectTables.get('PeerNode', {}) or {}).values())

    def _module_rows(self) -> List:
        return list((self.manager.objectTables.get('PolariModule', {}) or {}).values())

    def _find_peer(self, name: str):
        for p in self._peer_rows():
            if getattr(p, 'name', '') == name:
                return p
        return None

    def _persist(self, inst) -> None:
        db = getattr(self.manager, 'db', None)
        if db is not None:
            try:
                db.saveInstanceInDB(inst)
            except Exception:
                pass


def _parse(text: str) -> Any:
    try:
        return json.loads(text) if text else {}
    except (ValueError, TypeError):
        return {}


def _parse_crude_rows(payload: Any, class_name: str) -> List[Dict[str, Any]]:
    """Unwrap the generic CRUDE list envelope:
    [{ClassName: [{data: [{...row...}, ...]}]}] → row dicts."""
    try:
        for entry in payload if isinstance(payload, list) else []:
            block = entry.get(class_name)
            if isinstance(block, list):
                out: List[Dict[str, Any]] = []
                for seg in block:
                    for row in (seg.get('data') or []):
                        if isinstance(row, dict):
                            out.append(row)
                return out
    except AttributeError:
        pass
    return []
