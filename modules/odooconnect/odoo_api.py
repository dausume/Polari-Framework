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
from odooconnect.odoo_scenario_engine import (
    scenario_archive_status, scenario_create_status, scenario_harvest,
    scenario_plan, scenario_run, scenario_seed, scenarios_catalog,
)
from odooconnect.odoo_orders import pull_orders
from odooconnect.odoo_sync import (
    _named_row, bindings_catalog, pull, push, receipts_catalog,
)

SCENARIO_VERBS = {
    'plan': scenario_plan,
    'create': scenario_create_status,
    'seed': scenario_seed,
    'run': scenario_run,
    'harvest': scenario_harvest,
    'archive': scenario_archive_status,
}


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
            add('/api/odoo/pull-orders', self, suffix='pull_orders')
            add('/api/odoo/push', self, suffix='push')
            add('/api/odoo/receipts', self, suffix='receipts')
            add('/api/odoo/scenarios', self, suffix='scenarios')
            add('/api/odoo/scenario/{verb}', self, suffix='scenario')

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

    def on_post_pull_orders(self, request, response):
        body = request.media if request.content_length else {}
        binding = self._binding_named(body.get('binding',
                                               'sim-sale-orders'))
        if binding is None:
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'refusal': f'no OdooModelBinding named '
                           f'"{body.get("binding", "sim-sale-orders")}"'}
            return
        response.media = pull_orders(self.manager, binding)

    def on_get_scenarios(self, request, response):
        response.media = scenarios_catalog(self.manager)

    def on_post_scenario(self, request, response, verb):
        fn = SCENARIO_VERBS.get(verb)
        if fn is None:
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'refusal': f'unknown scenario verb "{verb}" — one of '
                           f'{sorted(SCENARIO_VERBS)}'}
            return
        body = request.media if request.content_length else {}
        scenario = _named_row(self.manager,
                              'BusinessScenarioDefinition',
                              body.get('scenario', ''))
        if scenario is None:
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'refusal': f'no BusinessScenarioDefinition named '
                           f'"{body.get("scenario", "")}"'}
            return
        response.media = fn(self.manager, scenario)

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
