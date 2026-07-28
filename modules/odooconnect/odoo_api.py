"""
@module odooconnect.odoo_api

/api/odoo/* — status + configs (od-3), bindings + pull/push + receipts
(od-4). The write path stays knob+confirm-gated in the CLIENT layer,
so this transport can never widen permissions: /push just forwards the
caller's confirm string into the same guards.

@consumers polariServer (constructed when _feature_available('odooconnect'))
"""

from objectTreeDecorators import treeObject, treeObjectInit

from odooconnect.odoo_analysis import odoo_configs, odoo_status
from odooconnect.odoo_sync import (
    bindings_catalog, pull, push, receipts_catalog,
)


class OdooConnectAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/odoo'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/odoo/status', self, suffix='status')
            add('/api/odoo/configs', self, suffix='configs')
            add('/api/odoo/bindings', self, suffix='bindings')
            add('/api/odoo/pull', self, suffix='pull')
            add('/api/odoo/push', self, suffix='push')
            add('/api/odoo/receipts', self, suffix='receipts')

    def _binding_named(self, name):
        table = getattr(self.manager, 'objectTables', {}).get(
            'OdooModelBinding', {})
        for row in table.values():
            if getattr(row, 'name', None) == name:
                return row
        return None

    def on_get_status(self, request, response):
        response.media = odoo_status(self.manager)

    def on_get_configs(self, request, response):
        response.media = odoo_configs(self.manager)

    def on_get_bindings(self, request, response):
        response.media = bindings_catalog(self.manager)

    def on_get_receipts(self, request, response):
        response.media = receipts_catalog(self.manager)

    def on_post_pull(self, request, response):
        body = request.media if request.content_length else {}
        binding = self._binding_named(body.get('binding', ''))
        if binding is None:
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'refusal': f'no OdooModelBinding named '
                           f'"{body.get("binding", "")}"'}
            return
        response.media = pull(self.manager, binding)

    def on_post_push(self, request, response):
        body = request.media if request.content_length else {}
        binding = self._binding_named(body.get('binding', ''))
        if binding is None:
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'refusal': f'no OdooModelBinding named '
                           f'"{body.get("binding", "")}"'}
            return
        response.media = push(
            self.manager, binding,
            row_names=body.get('rowNames') or [],
            confirm=body.get('confirm', ''))
