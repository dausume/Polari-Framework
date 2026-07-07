"""
@module simulations.profile_api

HTTP surface for MultiScaleSimulationProfile conformance (PeersAPI
pattern — self-registering falcon routes; separate module so
simulation_api.py stays at its current size):

  GET /api/simulations/multi-scale/{msim_name}/profile-conformance
      Run the family conformance checker against the msim's
      profile_ref. Honest gaps: 404-with-reason when the msim or its
      profile row is missing, and an explicit no-profile-declared
      response (not an error) when profile_ref is empty.
"""

from objectTreeDecorators import treeObject, treeObjectInit
from simulations.multi_scale_profile_conformance import (
    check_profile_conformance,
)


def _row_by_name(manager, class_name, name):
    table = manager.objectTables.get(class_name, {}) or {}
    return next((r for r in table.values()
                 if getattr(r, 'name', '') == name), None)


class ProfileAPI(treeObject):
    """Multi-scale family conformance endpoint."""

    @treeObjectInit
    def __init__(self, polServer):
        # self.manager arrives via the manager= kwarg treeObjectInit
        # consumes (same idiom as ScaleExecutionAPI).
        self.polServer = polServer
        self.apiName = '/api/simulations'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/simulations/multi-scale/{msim_name}/profile-conformance',
                self, suffix='conformance')

    def on_get_conformance(self, request, response, msim_name):
        msim = _row_by_name(
            self.manager, 'MultiScaleSimulationDefinition', msim_name)
        if msim is None:
            response.status = '404 Not Found'
            response.media = {
                'success': False,
                'error': f'MultiScaleSimulationDefinition "{msim_name}" '
                         'not found'}
            return
        profile_ref = getattr(msim, 'profile_ref', '') or ''
        if not profile_ref:
            # An honest gap, not an error: the msim declares no family.
            response.media = {
                'success': True,
                'data': {
                    'conforms': None,
                    'profile': '',
                    'msim': msim_name,
                    'findings': [],
                    'suggestions': [{
                        'action': f'Set profile_ref on "{msim_name}" to a '
                                  'MultiScaleSimulationProfile name',
                        'reason': 'No family declared — conformance cannot '
                                  'be checked',
                        'evidence': {'profile_ref': ''},
                    }],
                }}
            return
        profile = _row_by_name(
            self.manager, 'MultiScaleSimulationProfile', profile_ref)
        if profile is None:
            response.status = '404 Not Found'
            response.media = {
                'success': False,
                'error': f'msim "{msim_name}" declares profile_ref='
                         f'"{profile_ref}" but no such '
                         'MultiScaleSimulationProfile row exists'}
            return
        response.media = {
            'success': True,
            'data': check_profile_conformance(self.manager, msim, profile),
        }
