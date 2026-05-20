"""
Keycloak admin-API client for the PRF backend.

Single responsibility: authenticate as the `polari-backend` service-account
client (client_credentials grant) and expose a small surface that the
permissions system needs — listing realm roles today, with room to grow
(group lookups, user role-mapping) later.

Configuration is read from environment variables that the PRF setup
scripts already plumb (`staging-setup.sh`, `prod-setup.sh`):

    POLARI_KEYCLOAK_ADMIN_URL          e.g. http://prf-keycloak:8080
    POLARI_KEYCLOAK_REALM              e.g. Polari
    POLARI_KEYCLOAK_ADMIN_CLIENT_ID    e.g. polari-backend
    KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET

The service-account token is cached in-process until 30s before expiry —
keeps us off Keycloak's `/token` endpoint on every API call without
risking 401s from clock skew.
"""

import os
import time
import threading
from typing import List, Dict, Optional

import requests


class KeycloakClientError(RuntimeError):
    """Raised when the admin client can't talk to Keycloak."""


class KeycloakClient:
    _instance: Optional["KeycloakClient"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get(cls) -> "KeycloakClient":
        """Process-wide singleton — Falcon middleware reuses one instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = KeycloakClient()
        return cls._instance

    def __init__(self):
        self.admin_url = (os.environ.get('POLARI_KEYCLOAK_ADMIN_URL') or '').rstrip('/')
        self.realm = os.environ.get('POLARI_KEYCLOAK_REALM') or 'Polari'
        self.client_id = os.environ.get('POLARI_KEYCLOAK_ADMIN_CLIENT_ID') or 'polari-backend'
        self.client_secret = os.environ.get('KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET') or ''

        self._token: Optional[str] = None
        self._token_expiry_epoch: float = 0.0
        self._token_lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.admin_url and self.client_secret)

    def _fetch_token(self) -> str:
        if not self.configured:
            raise KeycloakClientError(
                "KeycloakClient not configured — POLARI_KEYCLOAK_ADMIN_URL or "
                "KEYCLOAK_POLARI_BACKEND_CLIENT_SECRET missing from env"
            )
        url = f"{self.admin_url}/realms/{self.realm}/protocol/openid-connect/token"
        try:
            resp = requests.post(
                url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                },
                timeout=10,
            )
        except requests.RequestException as e:
            raise KeycloakClientError(f"Could not reach Keycloak token endpoint: {e}") from e
        if resp.status_code != 200:
            raise KeycloakClientError(
                f"Keycloak token request failed (HTTP {resp.status_code}): {resp.text[:200]}"
            )
        body = resp.json()
        token = body.get('access_token')
        expires_in = int(body.get('expires_in', 60))
        if not token:
            raise KeycloakClientError("Keycloak token response missing access_token")
        # 30s safety buffer — refresh before the token actually expires.
        self._token = token
        self._token_expiry_epoch = time.time() + max(expires_in - 30, 10)
        return token

    def _get_token(self) -> str:
        with self._token_lock:
            if self._token and time.time() < self._token_expiry_epoch:
                return self._token
            return self._fetch_token()

    def list_realm_roles(self) -> List[Dict]:
        """Return the realm's roles as Keycloak gives them — list of dicts
        with at least `name`, `description`, `composite`, `id`. Filters out
        Keycloak's internal default roles (`offline_access`, `uma_authorization`,
        `default-roles-<realm>`) since they're not meaningful to permission
        assignment in Polari."""
        token = self._get_token()
        url = f"{self.admin_url}/admin/realms/{self.realm}/roles"
        try:
            resp = requests.get(
                url,
                headers={'Authorization': f'Bearer {token}'},
                timeout=10,
            )
        except requests.RequestException as e:
            raise KeycloakClientError(f"Could not list realm roles: {e}") from e
        if resp.status_code != 200:
            raise KeycloakClientError(
                f"Keycloak role list failed (HTTP {resp.status_code}): {resp.text[:200]}"
            )
        builtin = {'offline_access', 'uma_authorization', f'default-roles-{self.realm.lower()}'}
        return [r for r in resp.json() if r.get('name') not in builtin]

    def list_groups(self) -> List[Dict]:
        """Return the realm's top-level groups with their realm role mappings
        attached. Description is pulled from KC's group attributes (KC stores
        it under `attributes.description[0]` historically; some realms put a
        top-level `description` field — we surface both).

        Shape per group:
            {
              'id': str,
              'name': str,
              'path': str,
              'description': str,
              'attributes': dict,
              'realmRoles': [role_name, ...],   # populated via per-group role-mapping fetch
              'memberCount': int | None,        # None if KC didn't return it
            }
        """
        token = self._get_token()
        headers = {'Authorization': f'Bearer {token}'}
        # briefRepresentation=false → returns attributes + subGroups.
        # Realm role mappings still need a separate call per group.
        list_url = f"{self.admin_url}/admin/realms/{self.realm}/groups?briefRepresentation=false"
        try:
            resp = requests.get(list_url, headers=headers, timeout=10)
        except requests.RequestException as e:
            raise KeycloakClientError(f"Could not list groups: {e}") from e
        if resp.status_code != 200:
            raise KeycloakClientError(
                f"Keycloak group list failed (HTTP {resp.status_code}): {resp.text[:200]}"
            )

        groups: List[Dict] = []
        for raw in resp.json():
            gid = raw.get('id')
            if not gid:
                continue
            attributes = raw.get('attributes') or {}
            # Description can live in either the top-level field or the
            # `description` attribute (KC's UI puts it on the top-level
            # field, but some realm-import JSONs use the attribute).
            description = raw.get('description') or ''
            if not description:
                attr_desc = attributes.get('description')
                if isinstance(attr_desc, list) and attr_desc:
                    description = str(attr_desc[0])
                elif isinstance(attr_desc, str):
                    description = attr_desc

            realm_roles: List[str] = []
            try:
                role_url = f"{self.admin_url}/admin/realms/{self.realm}/groups/{gid}/role-mappings/realm"
                role_resp = requests.get(role_url, headers=headers, timeout=10)
                if role_resp.status_code == 200:
                    realm_roles = [r.get('name') for r in role_resp.json() if r.get('name')]
            except requests.RequestException:
                # Don't bring the whole listing down for one group's
                # role-mapping fetch — UI will just show no roles for it.
                pass

            groups.append({
                'id': gid,
                'name': raw.get('name', ''),
                'path': raw.get('path', ''),
                'description': description,
                'attributes': attributes,
                'realmRoles': realm_roles,
                # KC's `subGroupCount` is sometimes present; membership
                # count is not — we surface what we have, no extra calls.
                'memberCount': raw.get('membersCount'),
            })
        return groups
