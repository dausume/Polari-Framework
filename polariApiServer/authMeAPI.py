"""
Auth diagnostic endpoints for the Permissions section.

GET /auth/me           — returns identity extracted from the Bearer token,
                          or `authenticated: false` for anonymous requests.
GET /auth/jwks-health  — independent of the caller's token; reports whether
                          Polari's backend can fetch & parse the realm JWKS.
                          Lets the Auth Diagnostics page distinguish
                          "JWKS unreachable" from "token rejected".

Both are non-gating. Anonymous requests get HTTP 200 (Phase 1).
"""

import os
import time

import requests
from objectTreeDecorators import *
import falcon


class AuthMeAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/auth/me'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        info = getattr(request.context, 'user_info', None)
        roles = getattr(request.context, 'roles', []) or []
        if info is None:
            response.media = {
                'success': True,
                'data': {
                    'authenticated': False,
                    'roles': [],
                },
            }
            response.status = falcon.HTTP_200
            return
        response.media = {
            'success': True,
            'data': {
                'authenticated': True,
                'sub': info.get('sub'),
                'username': info.get('username'),
                'email': info.get('email'),
                'roles': roles,
            },
        }
        response.status = falcon.HTTP_200


class AuthJwksHealthAPI(treeObject):
    """GET /auth/jwks-health — does the backend's view of Keycloak's JWKS work?

    Response shape:
        {
          success: true,
          data: {
            configured: bool,          # POLARI_KEYCLOAK_JWKS_URI / _ISSUER_URI present
            jwksUri: str | null,
            issuer: str | null,
            reachable: bool,
            httpStatus: int | null,
            keyCount: int | null,
            kids: [str, ...] | null,   # signing-key IDs the backend would accept
            latencyMs: int | null,
            error: str | null,
          }
        }
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/auth/jwks-health'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        jwks_uri = os.environ.get('POLARI_KEYCLOAK_JWKS_URI') or ''
        issuer = os.environ.get('POLARI_KEYCLOAK_ISSUER_URI') or ''
        out = {
            'configured': bool(jwks_uri and issuer),
            'jwksUri': jwks_uri or None,
            'issuer': issuer or None,
            'reachable': False,
            'httpStatus': None,
            'keyCount': None,
            'kids': None,
            'latencyMs': None,
            'error': None,
        }
        if not jwks_uri:
            out['error'] = 'POLARI_KEYCLOAK_JWKS_URI is not set'
            response.media = {'success': True, 'data': out}
            response.status = falcon.HTTP_200
            return
        try:
            t0 = time.time()
            resp = requests.get(jwks_uri, timeout=5)
            out['latencyMs'] = int((time.time() - t0) * 1000)
            out['httpStatus'] = resp.status_code
            if resp.status_code == 200:
                body = resp.json()
                keys = body.get('keys') or []
                out['reachable'] = True
                out['keyCount'] = len(keys)
                out['kids'] = [k.get('kid') for k in keys if k.get('kid')]
            else:
                out['error'] = f'JWKS endpoint returned HTTP {resp.status_code}'
        except requests.RequestException as e:
            out['error'] = f'Could not reach JWKS endpoint: {e}'
        except ValueError as e:
            out['error'] = f'JWKS response was not valid JSON: {e}'
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200
