#    Copyright (C) 2020  Dustin Etts
#    GNU GPLv3 — see LICENSE.

"""In-app AI assistant endpoint (Phase 4).

POST /ai/chat  { "message": str, "history"?: [{role, content}] }
    -> { provider, mode, reply, node_context, capabilities }

The endpoint is the backend the in-app AI panel (text + voice, incl. WebXR)
talks to. It builds a node-context snapshot from the object tree and routes the
message through the provider-agnostic reasoning layer (reasoning_provider.py).
With no LLM configured it returns a deterministic, node-aware reply; with a
provider configured it returns real model output. Either way, interface
mutations still flow through the gated MCP capability + provenance log — this
endpoint is the conversation surface, not a mutation bypass.
"""

from objectTreeDecorators import *
import falcon

from polariApiServer.reasoning_provider import get_provider

_AWARENESS_CLASSES = (
    "PolariModule", "DisplayDefinition", "SolutionDefinition",
    "SimulationRun", "ServiceConnection", "TopologyDefinition",
)


class aiChatAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/ai/chat'
        if polServer != None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.apiName + '/stream', self, suffix='stream')

    def _node_context(self):
        """A small, human-readable snapshot of the running node for the AI."""
        manager = self.manager
        counts = {}
        tables = getattr(manager, 'objectTables', {}) or {}
        for cls in _AWARENESS_CLASSES:
            tbl = tables.get(cls)
            try:
                counts[cls] = len(tbl) if tbl is not None else 0
            except TypeError:
                counts[cls] = 0
        return {
            "class_counts": counts,
            "object_types": len(getattr(manager, 'objectTypingDict', {}) or {}),
        }

    def on_get(self, request, response):
        """Health / contract for the endpoint."""
        response.media = {
            "endpoint": "/ai/chat",
            "method": "POST",
            "provider": get_provider().name,
            "expects": {"message": "string", "history": "optional [{role, content}]"},
        }
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')

    def on_post_stream(self, request, response):
        """SSE stream of the reply. Emits {type:'delta',text} chunks then a
        {type:'done', provider, mode, proposals, node_context} event. The reply
        is computed (a real model runs its tool loop) and streamed in chunks;
        proposals ride the done event and become confirmation cards."""
        import json as _json
        try:
            body = request.get_media() or {}
        except Exception:
            body = {}
        message = (body or {}).get('message', '')
        history = (body or {}).get('history', [])
        node_context = self._node_context()

        def gen():
            if not message or not isinstance(message, str):
                yield f"data: {_json.dumps({'type': 'done', 'reply': '', 'proposals': [], 'error': 'missing message'})}\n\n".encode()
                return
            if message.strip().startswith('/act'):
                from polariApiServer.ai_actions import parse_command
                proposal = parse_command(message)
                if proposal.get('error'):
                    reply, proposals = f"Couldn't prepare that action: {proposal['error']}", []
                else:
                    reply, proposals = "I've prepared this action. Review and confirm to apply it.", [proposal]
                provider_name, mode, model = "action", "command", None
            else:
                provider = get_provider()
                try:
                    result = provider.respond(message, node_context, history)
                except Exception as exc:  # noqa: BLE001
                    yield f"data: {_json.dumps({'type': 'done', 'reply': '', 'proposals': [], 'error': str(exc)})}\n\n".encode()
                    return
                reply = result.get('reply', '') or ''
                proposals = result.get('proposals', [])
                provider_name, mode, model = provider.name, result.get('mode'), result.get('model')
            words = reply.split(' ')
            for i, wd in enumerate(words):
                chunk = wd + ('' if i == len(words) - 1 else ' ')
                yield f"data: {_json.dumps({'type': 'delta', 'text': chunk})}\n\n".encode()
            done = {'type': 'done', 'provider': provider_name, 'mode': mode,
                    'proposals': proposals, 'node_context': node_context}
            if model:
                done['model'] = model
            yield f"data: {_json.dumps(done)}\n\n".encode()

        response.content_type = 'text/event-stream'
        response.set_header('Cache-Control', 'no-cache')
        response.set_header('X-Accel-Buffering', 'no')
        response.set_header('Powered-By', 'Polari')
        response.stream = gen()

    def on_post(self, request, response):
        try:
            body = request.get_media()
        except Exception as err:
            response.status = falcon.HTTP_400
            response.media = {"error": f"expected JSON body: {err}"}
            response.set_header('Powered-By', 'Polari')
            return
        message = (body or {}).get('message', '')
        if not message or not isinstance(message, str):
            response.status = falcon.HTTP_400
            response.media = {"error": "missing 'message' (string) in request body"}
            response.set_header('Powered-By', 'Polari')
            return
        history = (body or {}).get('history', [])
        node_context = self._node_context()

        # Action grammar: a message that proposes a gated change comes back as a
        # dry-run proposal the user confirms via /ai/act — the assistant never
        # applies a change without confirmation. (A real model produces the same
        # proposal shape through tool-calling.)
        if message.strip().startswith('/act'):
            from polariApiServer.ai_actions import parse_command
            proposal = parse_command(message)
            if proposal.get('error'):
                response.media = {"provider": "action", "mode": "command",
                                  "reply": f"Couldn't prepare that action: {proposal['error']}",
                                  "node_context": node_context, "proposals": []}
            else:
                response.media = {
                    "provider": "action", "mode": "command",
                    "reply": "I've prepared this action. Review and confirm to apply it.",
                    "node_context": node_context, "proposals": [proposal],
                }
            response.status = falcon.HTTP_200
            response.set_header('Powered-By', 'Polari')
            return
        try:
            provider = get_provider()
            result = provider.respond(message, node_context, history)
        except Exception as err:  # never 500 — refuse honestly
            response.status = falcon.HTTP_400
            response.media = {"error": f"reasoning provider failed: {err}"}
            response.set_header('Powered-By', 'Polari')
            return
        response.media = {
            "provider": provider.name,
            "mode": result.get("mode"),
            "reply": result.get("reply"),
            "capabilities": result.get("capabilities"),
            "proposals": result.get("proposals", []),
            "node_context": node_context,
            **({"provider_note": result["provider_note"]} if "provider_note" in result else {}),
            **({"model": result["model"]} if "model" in result else {}),
        }
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')
