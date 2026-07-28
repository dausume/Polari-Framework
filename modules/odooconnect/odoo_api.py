"""
@module odooconnect.odoo_api

/api/odoo/* — status + config catalog (od-3). Read-only surface; the
write path arrives with od-4 bindings and stays knob+confirm-gated in
the client layer regardless of transport.

@consumers polariServer (constructed when _feature_available('odooconnect'))
"""

from objectTreeDecorators import treeObject, treeObjectInit

from odooconnect.odoo_analysis import odoo_configs, odoo_status


class OdooConnectAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/odoo'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/odoo/status', self, suffix='status')
            add('/api/odoo/configs', self, suffix='configs')

    def on_get_status(self, request, response):
        response.media = odoo_status(self.manager)

    def on_get_configs(self, request, response):
        response.media = odoo_configs(self.manager)
