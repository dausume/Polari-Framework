#    Copyright (C) 2020  Dustin Etts
#    GNU GPLv3 — see LICENSE.

"""Endpoints for the in-app AI action loop (Phase 4 keystone).

POST /ai/act        { proposal_id, confirm }  -> gate + execute a proposal
GET  /ai/provenance [?limit=N]                -> the JSON audit trail

Proposals are created by /ai/chat (command grammar or, with a real model, tool
calls) and executed here only after the user confirms — the gate refuses
anything above the auth threshold. Behavior mirrors the MCP server's authority
kernel so the two surfaces are consistent.
"""

from objectTreeDecorators import *
import falcon

from polariApiServer.ai_actions import kernel


class aiActionsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/ai/act'
        if polServer != None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route('/ai/provenance', self, suffix='provenance')

    def on_post(self, request, response):
        try:
            body = request.get_media() or {}
        except Exception as err:
            response.status = falcon.HTTP_400
            response.media = {"error": f"expected JSON body: {err}"}
            response.set_header('Powered-By', 'Polari')
            return
        proposal_id = body.get('proposal_id')
        confirm = bool(body.get('confirm', False))
        if not proposal_id:
            response.status = falcon.HTTP_400
            response.media = {"error": "missing 'proposal_id'"}
            response.set_header('Powered-By', 'Polari')
            return
        response.media = kernel.execute(proposal_id, confirm)
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')

    def on_get_provenance(self, request, response):
        try:
            limit = int(request.get_param('limit') or 50)
        except (TypeError, ValueError):
            limit = 50
        response.media = {"provenance": kernel.provenance(limit=limit)}
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')
