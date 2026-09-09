"""
@module polariApiServer.module_health

The unified module health check over the registrar
(moduleService.module_registrar):

  GET  /api/modules/health                 ok + counts by state + every record
  GET  /api/modules/health/{module}        one record
  POST /api/modules/health/{module}/verify re-check the module against the live server now
  POST /api/modules/health/{module}/confirm {piece, ok, detail}
                                           an external confirmation (selftest results land here)

`ok` is false while any module is degraded, failed, blocked or invalid —
a module that loaded but does not have every declared piece live is
not healthy, whatever the loader said. (/api/health stays the
boot-phase check; this is the per-module functionality check.)
"""
import falcon


class ModuleHealthEndpoint:
    def __init__(self, polServer):
        self.polServer = polServer
        app = polServer.falconServer
        app.add_route('/api/modules/health', self)
        app.add_route('/api/modules/health/{module}', self, suffix='module')
        app.add_route('/api/modules/health/{module}/verify', self, suffix='verify')
        app.add_route('/api/modules/health/{module}/confirm', self, suffix='confirm')

    @property
    def registrar(self):
        return getattr(self.polServer, 'moduleRegistrar', None)

    def on_get(self, request, response):
        reg = self.registrar
        if reg is None:
            response.media = {'ok': False, 'error': 'registrar absent'}
            response.status = falcon.HTTP_503
            return
        snap = reg.snapshot()
        if request.get_param_as_bool('brief'):
            snap['modules'] = {m: {'state': r['state'], 'error': r['error']}
                               for m, r in snap['modules'].items()}
        response.media = snap

    def on_get_module(self, request, response, module):
        reg = self.registrar
        row = reg.get(module) if reg else None
        if row is None:
            response.media = {'ok': False, 'module': module,
                              'error': 'not declared on this instance'}
            response.status = falcon.HTTP_404
            return
        response.media = {'ok': row['state'] == 'online', **row}

    def on_post_verify(self, request, response, module):
        reg = self.registrar
        if reg is None or reg.get(module) is None:
            reg.declare(module) if reg else None
        if reg is None or reg.get(module) is None:
            response.media = {'ok': False, 'module': module,
                              'error': 'not declared on this instance'}
            response.status = falcon.HTTP_404
            return
        row = reg.verify(module)
        response.media = {'ok': row['state'] == 'online', **row}

    def on_post_confirm(self, request, response, module):
        reg = self.registrar
        body = request.get_media() or {}
        piece = str(body.get('piece', 'selftest'))
        if reg is None or reg.get(module) is None:
            response.media = {'ok': False, 'module': module,
                              'error': 'not declared on this instance'}
            response.status = falcon.HTTP_404
            return
        row = reg.confirm(module, piece, ok=bool(body.get('ok', True)),
                          detail=body.get('detail', ''))
        response.media = {'ok': True, 'piece': piece, **row}
