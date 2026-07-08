"""
@cross-cutting
@module aquaponics.atmosphere_api
@tags @xc:bindings

HTTP surface for atmospheric conditions + gas exchange (aqp-5):

  GET /api/aquaponics/atmospheres/{name}/state   VPD, CO2 density,
                                                 light, findings
  GET /api/aquaponics/atmospheres/{name}/exchange?plant=...
                                                 plant↔air CO2/O2
                                                 coupling verdict

@consumers
  - aquaponics frontend (later) / aqp-6
@see /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.atmosphere_analysis import (
    atmosphere_state, environment_gas_exchange,
)


class AquaponicsAtmosphereAPI(treeObject):
    """Atmospheric condition + gas-exchange endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/atmospheres'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/atmospheres/{name}/state', self,
                suffix='state')
            polServer.falconServer.add_route(
                '/api/aquaponics/atmospheres/{name}/exchange', self,
                suffix='exchange')

    def on_get_state(self, request, response, name):
        report = atmosphere_state(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_exchange(self, request, response, name):
        plant = request.get_param('plant') or ''
        if not plant:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "query param 'plant' is "
                                       'required'}
            return
        report = environment_gas_exchange(self.manager, plant, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
