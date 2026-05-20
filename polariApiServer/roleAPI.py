"""
Endpoints for the Phase-2 Permissions hub.

GET /api/roles                 list all Role objects (triggers KC sync)
GET /api/roles/{name}          single role with parsed grants
GET /api/roles/{name}/grants   reverse query: classes + ops this role grants
GET /api/me/permissions        the caller's effective CRUDE matrix
                               (transient, keyed by `sub`, no PII stored)

PII / storage posture:
    The UserPermissionMatrix is cached in-process only, keyed by the
    Keycloak `sub` UUID. Username, email, and any other identifying
    fields are never written to the cache or to disk — they're read
    fresh from the JWT on every request and used purely for the
    response payload's display fields.
"""

import json
import time
import threading
from typing import Dict, List

from objectTreeDecorators import treeObject, treeObjectInit
import falcon

from accessControl.role import Role
from accessControl.keycloak_client import KeycloakClient, KeycloakClientError


# How often we re-pull the realm role list from Keycloak. 60s is a
# tradeoff: a new KC role appears in Polari within a minute, and we
# only pay one `/admin/realms/{}/roles` round-trip per minute under load.
_KC_SYNC_INTERVAL_SECONDS = 60


class RoleAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self._last_sync_epoch = 0.0
        self._sync_lock = threading.Lock()
        # sub -> (computed_matrix, computed_epoch). Recomputed when the
        # token's role list differs from what produced the cache entry,
        # so role grants applied at runtime take effect on next call.
        self._user_matrix_cache: Dict[str, Dict] = {}
        self._user_matrix_lock = threading.Lock()

        if polServer is not None:
            base = '/api/roles'
            polServer.falconServer.add_route(base, self)
            polServer.falconServer.add_route(base + '/sync-health', self, suffix='sync_health')
            polServer.falconServer.add_route(base + '/{name}', self, suffix='one')
            polServer.falconServer.add_route(base + '/{name}/grants', self, suffix='grants')
            polServer.falconServer.add_route(
                base + '/{name}/grants/{class_name}', self, suffix='grant_write'
            )
            polServer.falconServer.add_route('/api/me/permissions', self, suffix='me')
            polServer.falconServer.add_route('/api/groups', self, suffix='groups_list')
            # `apiName` is used for overlap-tracking; pick the base path.
            self.apiName = base

    # ---------------------------------------------------------------------
    # GET /api/roles
    # ---------------------------------------------------------------------
    def on_get(self, request, response):
        try:
            self._sync_with_keycloak_if_stale()
        except KeycloakClientError as e:
            # Sync failures shouldn't blank the role list — we still
            # serve whatever's already in the local table, but flag it.
            response.media = {
                'success': True,
                'data': self._all_roles_payload(),
                'syncWarning': str(e),
            }
            response.status = falcon.HTTP_200
            return
        response.media = {'success': True, 'data': self._all_roles_payload()}
        response.status = falcon.HTTP_200

    def on_get_one(self, request, response, name):
        role = self._find_role(name)
        if role is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'Role "{name}" not found'}
            return
        response.media = {'success': True, 'data': self._role_to_payload(role)}
        response.status = falcon.HTTP_200

    def on_get_grants(self, request, response, name):
        """Reverse-query: '[{className, ops}, ...]' for one role."""
        role = self._find_role(name)
        if role is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'Role "{name}" not found'}
            return
        grants = self._parse_grants(role.grants_by_class_json)
        items = [{'className': cn, 'ops': sorted(ops)} for cn, ops in grants.items() if ops]
        items.sort(key=lambda x: x['className'])
        response.media = {
            'success': True,
            'data': {'role': name, 'grants': items},
        }
        response.status = falcon.HTTP_200

    # ---------------------------------------------------------------------
    # GET /api/groups
    # Live-fetches the realm's groups from Keycloak (no local persistence
    # — groups are an admin/ops concern, not a Polari-stored concept).
    # Powers the Permissions → Admin tab where users see existing groups
    # and can deep-link into Keycloak to manage membership.
    # ---------------------------------------------------------------------
    def on_get_groups_list(self, request, response):
        kc = KeycloakClient.get()
        if not kc.configured:
            response.media = {
                'success': True,
                'data': [],
                'syncWarning': 'KeycloakClient not configured — set '
                               'KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET '
                               'on the backend container.',
            }
            response.status = falcon.HTTP_200
            return
        try:
            groups = kc.list_groups()
        except KeycloakClientError as e:
            response.media = {'success': False, 'error': str(e)}
            response.status = falcon.HTTP_502
            return
        response.media = {'success': True, 'data': groups}
        response.status = falcon.HTTP_200

    # ---------------------------------------------------------------------
    # GET /api/roles/sync-health
    # Independent of any caller token — probes the backend's ability to
    # authenticate as the service account and list realm roles. Mirrors
    # /auth/jwks-health so the diagnostics page can distinguish:
    #   - secret missing      (configured=false)
    #   - token endpoint down (tokenOk=false)
    #   - admin API rejected  (listOk=false, with HTTP status)
    #   - happy path          (configured/tokenOk/listOk all true, role count)
    # ---------------------------------------------------------------------
    def on_get_sync_health(self, request, response):
        kc = KeycloakClient.get()
        t0 = time.time()
        out = {
            'configured': kc.configured,
            'adminUrl': kc.admin_url or None,
            'realm': kc.realm or None,
            'clientId': kc.client_id or None,
            'secretPresent': bool(kc.client_secret),
            'tokenOk': False,
            'listOk': False,
            'roleCount': None,
            'roleNames': None,
            'localRoleCount': len(self.manager.objectTables.get('Role', {}) or {}),
            'latencyMs': None,
            'error': None,
        }
        if not kc.configured:
            out['error'] = ('KeycloakClient not configured — '
                            'POLARI_KEYCLOAK_ADMIN_URL or '
                            'KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET missing')
            response.media = {'success': True, 'data': out}
            response.status = falcon.HTTP_200
            return
        try:
            # _get_token + list_realm_roles together hit the two endpoints
            # we'd be relying on for sync. If either fails, we surface a
            # specific reason rather than the generic "no roles" symptom.
            roles = kc.list_realm_roles()
            out['tokenOk'] = True
            out['listOk'] = True
            out['roleCount'] = len(roles)
            out['roleNames'] = [r.get('name') for r in roles if r.get('name')]
        except KeycloakClientError as e:
            msg = str(e)
            out['error'] = msg
            # Heuristic: "token" in the message → token-endpoint failed.
            if 'token' in msg.lower():
                out['tokenOk'] = False
            else:
                out['tokenOk'] = True
        except Exception as e:
            out['error'] = f'Unexpected error: {e}'
        out['latencyMs'] = int((time.time() - t0) * 1000)
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    # ---------------------------------------------------------------------
    # PUT /api/roles/{name}/grants/{class_name}
    # Body: { "ops": ["C","R","U","D","E"] }    — full replacement
    # An empty array clears the grant entirely.
    # ---------------------------------------------------------------------
    def on_put_grant_write(self, request, response, name, class_name):
        role = self._find_role(name)
        if role is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'Role "{name}" not found'}
            return
        try:
            body = request.media or {}
        except Exception:
            body = {}
        ops_raw = body.get('ops')
        if not isinstance(ops_raw, list):
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Body must include "ops": [...]'}
            return
        valid_ops = sorted({o for o in ops_raw if o in {'C', 'R', 'U', 'D', 'E'}})

        current = self._parse_grants(role.grants_by_class_json)
        if valid_ops:
            current[class_name] = set(valid_ops)
        else:
            current.pop(class_name, None)
        # Re-serialize. Stored as sorted lists so diffs stay stable.
        serialized = {cn: sorted(ops) for cn, ops in current.items()}
        role.grants_by_class_json = json.dumps(serialized)

        # Persist if a DB is wired up.
        try:
            if self.manager.db is not None:
                self.manager.db.saveInstanceInDB(role)
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'DB save failed: {e}'}
            return

        # Invalidate the per-user matrix cache — any user holding this
        # role should see the new grants on their next /api/me/permissions.
        with self._user_matrix_lock:
            self._user_matrix_cache.clear()

        response.media = {'success': True, 'data': self._role_to_payload(role)}
        response.status = falcon.HTTP_200

    # ---------------------------------------------------------------------
    # GET /api/me/permissions
    # ---------------------------------------------------------------------
    def on_get_me(self, request, response):
        info = getattr(request.context, 'user_info', None)
        roles = list(getattr(request.context, 'roles', []) or [])
        if info is None:
            response.media = {
                'success': True,
                'data': {
                    'authenticated': False,
                    'sub': None,
                    'roles': [],
                    'effectivePermissions': [],
                    'sourceRoles': {},
                },
            }
            response.status = falcon.HTTP_200
            return

        sub = info.get('sub') or ''
        matrix = self._compute_user_matrix(sub, roles)
        response.media = {
            'success': True,
            'data': {
                'authenticated': True,
                # Identity fields come straight from the token; we don't
                # cache them anywhere — keeps the backend free of PII.
                'sub': sub,
                'username': info.get('username'),
                'roles': roles,
                # effectivePermissions: list of {className, ops}
                'effectivePermissions': matrix['effective'],
                # sourceRoles: per-(className, op) which roles granted it.
                # Useful in the UI to show "you can DELETE Datasets via
                # the polari-admin role" — disambiguates aggregated views.
                'sourceRoles': matrix['source_roles'],
            },
        }
        response.status = falcon.HTTP_200

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _sync_with_keycloak_if_stale(self):
        with self._sync_lock:
            if time.time() - self._last_sync_epoch < _KC_SYNC_INTERVAL_SECONDS:
                return
            kc = KeycloakClient.get()
            if not kc.configured:
                # No KC creds — leave whatever's in the table alone, but
                # log loudly. The most common cause is the backend not
                # being given KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET; the
                # symptom is an empty Roles tab with no other signal.
                print('[RoleAPI] sync skipped — KeycloakClient not configured. '
                      'Check the backend env vars POLARI_KEYCLOAK_ADMIN_URL '
                      'and KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET.', flush=True)
                self._last_sync_epoch = time.time()
                return
            kc_roles = kc.list_realm_roles()
            print(f'[RoleAPI] synced from Keycloak — {len(kc_roles)} realm role(s)', flush=True)
            self._reconcile_roles(kc_roles)
            self._last_sync_epoch = time.time()

    def _reconcile_roles(self, kc_roles: List[Dict]):
        """Create local Role objects for new KC roles. Mark missing ones
        as orphaned (source='orphaned') without deleting — preserves any
        grants the admin set against a role that was later removed in KC.
        """
        from datetime import datetime, timezone
        manager = self.manager
        existing = manager.objectTables.get('Role', {}) or {}
        # Build lookups by name (the natural identity).
        existing_by_name = {}
        for r in existing.values():
            n = getattr(r, 'name', None)
            if n:
                existing_by_name[n] = r

        kc_names = set()
        now_iso = datetime.now(timezone.utc).isoformat()
        for kc_role in kc_roles:
            n = kc_role.get('name')
            if not n:
                continue
            kc_names.add(n)
            local = existing_by_name.get(n)
            if local is None:
                Role(
                    name=n,
                    description=kc_role.get('description', '') or '',
                    source='keycloak-realm',
                    synced_at=now_iso,
                    grants_by_class_json='{}',
                    manager=manager,
                )
            else:
                # Refresh description and ensure source is current.
                local.description = kc_role.get('description', '') or local.description
                local.source = 'keycloak-realm'
                local.synced_at = now_iso

        # Orphan check: anything local but no longer in KC.
        for n, r in existing_by_name.items():
            if n not in kc_names and getattr(r, 'source', '') == 'keycloak-realm':
                r.source = 'orphaned'

    def _all_roles_payload(self) -> List[Dict]:
        roles = self.manager.objectTables.get('Role', {}) or {}
        out = [self._role_to_payload(r) for r in roles.values()]
        out.sort(key=lambda x: x['name'])
        return out

    def _role_to_payload(self, role) -> Dict:
        grants = self._parse_grants(role.grants_by_class_json)
        return {
            'name': role.name,
            'description': role.description,
            'source': role.source,
            'syncedAt': role.synced_at,
            'grants': [
                {'className': cn, 'ops': sorted(ops)}
                for cn, ops in sorted(grants.items())
            ],
        }

    def _find_role(self, name: str):
        roles = self.manager.objectTables.get('Role', {}) or {}
        for r in roles.values():
            if getattr(r, 'name', '') == name:
                return r
        return None

    @staticmethod
    def _parse_grants(grants_json: str) -> Dict[str, set]:
        try:
            raw = json.loads(grants_json or '{}')
        except (ValueError, TypeError):
            return {}
        out: Dict[str, set] = {}
        for class_name, ops in (raw.items() if isinstance(raw, dict) else []):
            if not isinstance(ops, list):
                continue
            valid = {op for op in ops if op in {'C', 'R', 'U', 'D', 'E'}}
            if valid:
                out[class_name] = valid
        return out

    def _compute_user_matrix(self, sub: str, roles: List[str]) -> Dict:
        """Build the per-class effective CRUDE matrix for the caller.

        Cached in-process by (sub, frozenset(roles)) so a token refresh
        with the same roles is free, but a role change forces a recompute
        on next call. Cache is never written to disk.
        """
        cache_key = (sub, frozenset(roles))
        with self._user_matrix_lock:
            cached = self._user_matrix_cache.get(sub)
            if cached and cached.get('key') == cache_key:
                return cached['value']

        # Walk every local Role the caller has, unioning grants.
        per_class_ops: Dict[str, set] = {}
        # source_roles[className][op] = [role_name, ...]
        source_roles: Dict[str, Dict[str, List[str]]] = {}

        all_roles = self.manager.objectTables.get('Role', {}) or {}
        roles_by_name = {getattr(r, 'name', ''): r for r in all_roles.values()}
        for role_name in roles:
            local = roles_by_name.get(role_name)
            if local is None:
                continue
            grants = self._parse_grants(local.grants_by_class_json)
            for class_name, ops in grants.items():
                per_class_ops.setdefault(class_name, set()).update(ops)
                source_roles.setdefault(class_name, {})
                for op in ops:
                    source_roles[class_name].setdefault(op, []).append(role_name)

        effective = [
            {'className': cn, 'ops': sorted(ops)}
            for cn, ops in sorted(per_class_ops.items())
        ]
        value = {'effective': effective, 'source_roles': source_roles}

        with self._user_matrix_lock:
            self._user_matrix_cache[sub] = {'key': cache_key, 'value': value}
        return value
