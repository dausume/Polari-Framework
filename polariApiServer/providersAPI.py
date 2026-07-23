#    Copyright (C) 2020  Dustin Etts
#    GNU GPLv3 — see LICENSE.

"""Reasoning-provider management endpoint (Phase 4).

GET  /ai/providers                 -> status of every provider (ready?, needs?)
POST /ai/providers {action: ...}
     action "select"   {provider, settings?}   -> set the active provider
     action "set_auth" {provider, secret}      -> store a secret locally (600)
     action "validate" {provider}              -> probe the provider

Automates provider selection + authentication: detection of installed SDKs and
credentials, a persisted active choice, and validation. Secrets are write-only —
never returned by any response, never logged. `set_auth` is meant for a human /
the settings UI, not the AI channel (a secret in an AI tool call would land in
the audit log); the AI uses select + validate + status only.
"""

from objectTreeDecorators import *
import falcon

from polariApiServer import reasoning_config
from polariApiServer.reasoning_provider import build_provider


class providersAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/ai/providers'
        if polServer != None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        response.media = reasoning_config.all_status()
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')

    def on_post(self, request, response):
        try:
            body = request.get_media() or {}
        except Exception as err:
            response.status = falcon.HTTP_400
            response.media = {"error": f"expected JSON body: {err}"}
            response.set_header('Powered-By', 'Polari')
            return
        action = body.get('action')
        provider = body.get('provider')
        try:
            if action == 'select':
                result = reasoning_config.set_active(provider, body.get('settings'))
            elif action == 'set_auth':
                secret = body.get('secret')
                if not secret:
                    raise ValueError("set_auth requires a 'secret'")
                # Returns status only — the secret is never echoed back.
                result = reasoning_config.set_secret(provider, secret)
            elif action == 'validate':
                result = reasoning_config.validate(provider, build_provider)
            else:
                response.status = falcon.HTTP_400
                response.media = {"error": "action must be one of: select, set_auth, validate"}
                response.set_header('Powered-By', 'Polari')
                return
        except ValueError as err:
            response.status = falcon.HTTP_400
            response.media = {"error": str(err)}
            response.set_header('Powered-By', 'Polari')
            return
        response.media = result
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')
