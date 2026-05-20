"""
Bearer-token validation for incoming HTTP requests.

Verifies Keycloak access tokens against the realm's JWKS endpoint and
extracts the principal info the rest of the auth stack needs (sub,
username, email, realm + client roles).

The JWKS keys are fetched lazily by PyJWT's PyJWKClient and cached
in-process; KC rotates keys infrequently so this is fine. If the JWKS
endpoint is unreachable (e.g. Keycloak isn't up yet during boot), we
fail closed — validate() returns None rather than raising, so the
middleware treats the caller as unauthenticated.

Config from env:
    POLARI_KEYCLOAK_JWKS_URI    (e.g. http://prf-keycloak:8080/realms/Polari/protocol/openid-connect/certs)
    POLARI_KEYCLOAK_ISSUER_URI  (e.g. https://auth.prf.<host>/realms/Polari)
"""

import os
import threading
from typing import Optional, Dict, List

import jwt
from jwt import PyJWKClient, PyJWTError


class JwtValidator:
    _instance: Optional["JwtValidator"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get(cls) -> "JwtValidator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = JwtValidator()
        return cls._instance

    def __init__(self):
        self.jwks_uri = os.environ.get('POLARI_KEYCLOAK_JWKS_URI') or ''
        self.issuer = os.environ.get('POLARI_KEYCLOAK_ISSUER_URI') or ''
        self.client_id = os.environ.get('POLARI_KEYCLOAK_FRONTEND_CLIENT_ID') or 'polari-frontend'

        self._jwks_client: Optional[PyJWKClient] = None
        if self.jwks_uri:
            # PyJWKClient handles caching + key rotation transparently.
            self._jwks_client = PyJWKClient(self.jwks_uri, cache_keys=True)

    @property
    def configured(self) -> bool:
        return bool(self.jwks_uri and self.issuer)

    def validate(self, token: str) -> Optional[Dict]:
        """Return a principal dict on a valid token, None on any failure
        (missing config, bad signature, expired, wrong issuer, ...).

        Principal shape:
            {
              'sub': str,            # Keycloak user UUID
              'username': str,       # preferred_username
              'email': str | None,
              'roles': [str, ...],   # realm_access.roles UNION resource_access[client].roles
              'raw_claims': dict,    # full decoded JWT — for debugging only
            }
        """
        if not self.configured or not self._jwks_client or not token:
            return None
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                issuer=self.issuer,
                # Keycloak's default `aud` claim is `account`, not the client_id —
                # skipping audience validation matches what the official
                # keycloak-client libraries do for resource-server flows.
                options={'verify_aud': False},
            )
        except PyJWTError:
            return None
        except Exception:
            # JWKS fetch failures, malformed tokens, etc. — fail closed.
            return None

        realm_roles: List[str] = (claims.get('realm_access') or {}).get('roles') or []
        client_roles: List[str] = (
            (claims.get('resource_access') or {}).get(self.client_id) or {}
        ).get('roles') or []
        roles = list({*realm_roles, *client_roles})

        return {
            'sub': claims.get('sub', ''),
            'username': claims.get('preferred_username') or claims.get('email') or '',
            'email': claims.get('email'),
            'roles': roles,
            'raw_claims': claims,
        }
