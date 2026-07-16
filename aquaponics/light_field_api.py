"""
@cross-cutting
@module aquaponics.light_field_api
@tags @xc:bindings

HTTP surface for plant-growth-sim phase 8 (2026-07-15) — the direct-
light field engine (aquaponics/light_field.py). Read-only diagnostics;
the actual growth-rate effect happens automatically inside
advance_growth() when a planting's bound PotSystemDefinition names a
light_source_name — these endpoints are for INSPECTING that
computation, not triggering it.

  GET  /api/aquaponics/plantings/{name}/light-absorption
        the full per-bone + per-part absorbed-PPFD breakdown for a
        planting, against its own bound system's light source (or an
        explicit override via ?lightSource=<name>).
  GET  /api/aquaponics/light-spectra/{name}/ppfd
        a spectrum's real computed PPFD at a given broadband
        intensity — the "how much usable light does this spectrum
        actually deliver" diagnostic. Query: ?intensityWm2=<n>
        (default 1000, roughly full outdoor sun).

@consumers
  - aquaponics frontend (a future light-source editor / diagnostic
    view, not yet built)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 8
"""

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.light_field import _named, per_part_absorption, spectrum_ppfd


def _not_found_or_bad(result):
    error = str(result.get('error', ''))
    return '404 Not Found' if error.startswith('no ') \
        else '400 Bad Request'


class AquaponicsLightFieldAPI(treeObject):
    """Plant-growth-sim phase 8 diagnostic endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/light-field'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/plantings/{name}/light-absorption',
                self, suffix='light_absorption')
            polServer.falconServer.add_route(
                '/api/aquaponics/light-spectra/{name}/ppfd', self,
                suffix='ppfd')

    def on_get_light_absorption(self, request, response, name):
        params = request.params or {}
        light_source = params.get('lightSource')
        if not light_source:
            planting = _named(self.manager, 'PotPlanting', name)
            if planting is None:
                response.status = '404 Not Found'
                response.media = {
                    'ok': False,
                    'error': f"no PotPlanting named '{name}'"}
                return
            system = _named(self.manager, 'PotSystemDefinition',
                            getattr(planting, 'system_name', ''))
            light_source = getattr(system, 'light_source_name', '') \
                if system is not None else ''
            if not light_source:
                response.media = {
                    'ok': True, 'planting': name,
                    'partAbsorptionPpfd': {},
                    'note': 'no light source bound (directly, or via '
                            "the planting's PotSystemDefinition."
                            'light_source_name) — pass '
                            '?lightSource=<name> to evaluate one '
                            'explicitly.'}
                return
        result = per_part_absorption(self.manager, name, light_source)
        if not result.get('ok'):
            response.status = _not_found_or_bad(result)
        response.media = result

    def on_get_ppfd(self, request, response, name):
        spectrum = _named(self.manager, 'LightSpectrumDefinition', name)
        if spectrum is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no LightSpectrumDefinition named '{name}'"}
            return
        params = request.params or {}
        intensity = float(params.get('intensityWm2', 1000.0) or 1000.0)
        result = spectrum_ppfd(intensity, spectrum)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        result['intensityWm2'] = intensity
        response.media = result
