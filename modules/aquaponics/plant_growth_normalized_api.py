"""
@cross-cutting
@module aquaponics.plant_growth_normalized_api
@tags @xc:bindings

HTTP surface for plant-growth-sim phase 1 (2026-07-15) — the
free-soil/constrained-limits stages, the per-part PotPlanting instance
state, and the animation-bones skeleton generator. Read endpoints only
except /advance (the one state-mutating action, matching aqp-8's own
grow/advance-style POST convention) — everything else is a pure
derived read over plant_growth_normalized.py / plant_skeleton.py, no
new business logic here.

  GET  /api/aquaponics/plants/{name}/free-soil-constants
        Stage 1 — species' unconfined reference maximums, per part.
  GET  /api/aquaponics/pots/{name}/plants/{plant_name}/constrained-limits
        Stage 2 — Stage 1 run through this pot's real geometry;
        the survives/declines verdict + a per-part ceiling.
  GET  /api/aquaponics/plantings/{name}
        one PotPlanting's current state: overall + per-part
        normalized growth, and both SHAPE-equation profiles
        (current_root_profile / current_canopy_profile).
  POST /api/aquaponics/plantings/{name}/advance
        {"dtDays", "waterSupplyFactor"?, "soilSupplyFactor"?} ->
        advances every part's normalized growth by dtDays of real
        time and persists it (the one mutating action here).
  GET  /api/aquaponics/plantings/{name}/skeleton
        the animation-bones vector graph (plant_skeleton.
        generate_skeleton) — ready to feed a future pot-plant
        SimSpace geometry, same "live-computed" pattern as
        aquaponics.custom.hydraulics.water_slice_mesh. Query:
        ?maxGenerations=<n>&maxBones=<n>
  GET  /api/aquaponics/plantings/{name}/stress
        phase 7 — every part's per-stress-type breakdown (Liebig's-
        Law-combined) against the planting's bound PotSystemDefinition
        (PotPlanting.system_name) — the diagnostic view for "how are
        these equations behaving for this part, right now."
  GET  /api/aquaponics/stress-curves/{name}/sweep
        phase 7 — Tier-A trapezoid curves only: samples factor-vs-
        input across the curve's own [min, max] range, independent of
        any live data row — the "look through and evaluate how these
        are functioning" curve-shape diagnostic. Query:
        ?steps=<n> (default 20). Tier-B (equation_ref set) curves
        refuse here — sweep those via the no-code matrix-equation
        editor's own run-overlay instead (see plant_stress.sweep_curve
        docstring for why this isn't duplicated).

@consumers
  - aquaponics frontend (a future pot-plant SimSpace geometry view,
    not yet built)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 6
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.plant_growth_normalized_basis import (
    _named, advance_growth, constrained_limits, current_canopy_profile,
    current_root_profile, free_soil_constants, overall_normalized_growth,
)
from aquaponics.custom.plant_skeleton import (
    DEFAULT_MAX_BONES, DEFAULT_MAX_GENERATIONS, generate_skeleton,
)
from aquaponics.plant_stress_basis import (
    combined_stress_factor, part_stress_factors, sweep_curve,
)


def _not_found_or_bad(result):
    error = str(result.get('error', ''))
    return '404 Not Found' if error.startswith('no ') \
        else '400 Bad Request'


class AquaponicsPlantGrowthNormalizedAPI(treeObject):
    """Plant-growth-sim phase 1 endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/plant-growth-normalized'
        if polServer is not None:
            # Falcon's compiled router requires the SAME field name for
            # every route sharing a trie node — 'plants/{name}/...' and
            # 'pots/{name}/...' already exist (plant_api.py, pot_api.py,
            # hydraulics_api.py), so both outer segments here MUST also
            # be {name}, not {plant_name}/{pot_name}, or add_route raises
            # falcon.routing.compiled.UnacceptableRouteError at boot.
            polServer.falconServer.add_route(
                '/api/aquaponics/plants/{name}/'
                'free-soil-constants', self, suffix='free_soil')
            polServer.falconServer.add_route(
                '/api/aquaponics/pots/{name}/plants/{plant_name}/'
                'constrained-limits', self, suffix='constrained')
            polServer.falconServer.add_route(
                '/api/aquaponics/plantings/{name}', self,
                suffix='planting')
            polServer.falconServer.add_route(
                '/api/aquaponics/plantings/{name}/advance', self,
                suffix='advance')
            polServer.falconServer.add_route(
                '/api/aquaponics/plantings/{name}/skeleton', self,
                suffix='skeleton')
            polServer.falconServer.add_route(
                '/api/aquaponics/plantings/{name}/stress', self,
                suffix='stress')
            polServer.falconServer.add_route(
                '/api/aquaponics/stress-curves/{name}/sweep', self,
                suffix='sweep')

    def on_get_free_soil(self, request, response, name):
        result = free_soil_constants(self.manager, name)
        if not result.get('ok'):
            response.status = _not_found_or_bad(result)
        response.media = result

    def on_get_constrained(self, request, response, name, plant_name):
        result = constrained_limits(self.manager, name, plant_name)
        if not result.get('ok'):
            response.status = _not_found_or_bad(result)
        response.media = result

    def on_get_planting(self, request, response, name):
        overall = overall_normalized_growth(self.manager, name)
        if not overall.get('ok'):
            response.status = _not_found_or_bad(overall)
            response.media = overall
            return
        root = current_root_profile(self.manager, name)
        canopy = current_canopy_profile(self.manager, name)
        response.media = {
            'ok': True, 'planting': name,
            'overall': overall,
            'rootProfile': root,
            'canopyProfile': canopy,
        }

    def on_post_advance(self, request, response, name):
        try:
            body = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        if 'dtDays' not in body:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': "'dtDays' is required"}
            return
        # Omitted waterSupplyFactor/soilSupplyFactor (the default) lets
        # advance_growth auto-compute PER-PART stress factors from the
        # planting's bound PotSystemDefinition (phase 7) — passing
        # either explicitly overrides that with the old manual,
        # uniform-across-parts behavior.
        water_factor = body.get('waterSupplyFactor')
        soil_factor = body.get('soilSupplyFactor')
        result = advance_growth(
            self.manager, name, dt_days=float(body['dtDays']),
            water_supply_factor=(
                float(water_factor) if water_factor is not None else None),
            soil_supply_factor=(
                float(soil_factor) if soil_factor is not None else None))
        if not result.get('ok'):
            response.status = _not_found_or_bad(result)
        response.media = result

    def on_get_skeleton(self, request, response, name):
        params = request.params or {}
        max_generations = int(
            params.get('maxGenerations', DEFAULT_MAX_GENERATIONS)
            or DEFAULT_MAX_GENERATIONS)
        max_bones = int(
            params.get('maxBones', DEFAULT_MAX_BONES) or DEFAULT_MAX_BONES)
        result = generate_skeleton(
            self.manager, name, max_generations=max_generations,
            max_bones=max_bones)
        if not result.get('ok'):
            response.status = _not_found_or_bad(result)
        response.media = result

    def on_get_stress(self, request, response, name):
        planting = _named(self.manager, 'PotPlanting', name)
        if planting is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no PotPlanting named '{name}'"}
            return
        if not getattr(planting, 'system_name', ''):
            response.media = {
                'ok': True, 'planting': name, 'mode': 'no-linkage',
                'parts': {},
                'note': 'PotPlanting.system_name is empty — no '
                        'PotSystemDefinition bound, so no atmosphere/'
                        'water/soil rows to evaluate stress curves '
                        'against (advance_growth uses factor 1.0 for '
                        'every part in this case).'}
            return
        system = _named(self.manager, 'PotSystemDefinition',
                        planting.system_name)
        if system is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"PotPlanting '{name}' names system "
                         f"'{planting.system_name}' but no "
                         'PotSystemDefinition with that name exists'}
            return
        limits = constrained_limits(self.manager, planting.pot_name,
                                    planting.plant_name)
        if not limits.get('ok'):
            response.status = _not_found_or_bad(limits)
            response.media = limits
            return
        parts_report = {}
        for part_name in limits['partCeilings']:
            by_type = part_stress_factors(
                self.manager, planting.plant_name, part_name,
                system.atmosphere_name, system.water_name,
                system.soil_name)
            factor, limiting_type, ok_factors = combined_stress_factor(
                by_type)
            parts_report[part_name] = {
                'combinedFactor': round(factor, 4),
                'limitingStressType': limiting_type,
                'byStressType': by_type,
            }
        response.media = {
            'ok': True, 'planting': name, 'system': planting.system_name,
            'mode': 'stress-equations', 'parts': parts_report,
            'note': "combinedFactor is Liebig's-Law-of-the-Minimum "
                    'across whatever stress-type curves exist for that '
                    'part — see byStressType for the full per-type '
                    'breakdown this diagnostic is for.',
        }

    def on_get_sweep(self, request, response, name):
        curve = _named(self.manager, 'StressResponseCurve', name)
        if curve is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no StressResponseCurve named '{name}'"}
            return
        params = request.params or {}
        steps = int(params.get('steps', 20) or 20)
        result = sweep_curve(curve, sample_count=steps)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result
