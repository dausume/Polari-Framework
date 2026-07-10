"""
@cross-cutting
@module polariRefs.refs_api

HTTP surface for the ONE reference ladder (xsim-3):

  POST /api/refs/resolve   {ref: {kind:'objectRef', ...}, path?: bool}
      → {'ok', 'value'|'fields', 'provenance'} or the honest refusal.
        Read-only by construction — the resolver hands back values and
        GenericRemoteObject field dicts, never live write handles.

@consumers
  - live verification + the later frontend ref-inspector
@see /CROSS_INSTANCE_SIM_PLAN.md
"""

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from polariRefs.resolver import resolve_ref, walk_path


def _serializable(obj):
    from polariRefs.remote_hydration import GenericRemoteObject
    from polariRefs.resolver import RowView
    if isinstance(obj, GenericRemoteObject):
        return {'fields': obj.polariRefFields}
    if isinstance(obj, RowView):
        return {'fields': {k: v for k, v in obj.__dict__.items()
                           if not k.startswith('_')
                           and not k.startswith('polariRef')}}
    # a live local tree object: identifying surface only (read-only
    # endpoint — full objects stay on their CRUDE surface)
    return {'fields': {'id': getattr(obj, 'id', None),
                       'name': getattr(obj, 'name', None),
                       'className': type(obj).__name__},
            'note': 'local tree object — full body via its CRUDE '
                    'endpoint'}


class PolariRefsAPI(treeObject):
    """Reference-resolution endpoint."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/refs'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/refs/resolve', self, suffix='resolve')

    def on_post_resolve(self, request, response):
        try:
            body = request.get_media() or {}
        except Exception:
            body = {}
        ref = body.get('ref')
        if not isinstance(ref, dict):
            response.status = falcon.HTTP_400
            response.media = {'ok': False,
                              'error': "body needs {'ref': {...}}"}
            return
        result = resolve_ref(self.manager, ref)
        if not result['ok']:
            response.status = falcon.HTTP_404
            response.media = {'ok': False,
                              'refusal': result['refusal']}
            return
        media = {'ok': True, 'provenance': result['provenance']}
        path = str(ref.get('path', '') or '')
        if path:
            ok, value, refusal = walk_path(result['object'], path)
            if not ok:
                response.status = falcon.HTTP_404
                response.media = {'ok': False, 'refusal': refusal,
                                  'provenance': result['provenance']}
                return
            media['value'] = value
        else:
            media.update(_serializable(result['object']))
        response.media = media
