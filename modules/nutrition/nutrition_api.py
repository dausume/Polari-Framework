"""
@cross-cutting
@module nutrition.nutrition_api
@tags @xc:bindings

HTTP surface for nut-1/3/4 (person + household nutrition):

  GET  /api/nutrition/nutrients
        the dietary-nutrient vocabulary + plant availability.
  GET  /api/nutrition/persons/{name}/bmr
        BMR + TDEE + calorie target (with any safety warning).
  POST /api/nutrition/persons/{name}/needs
        body {period: day|week|month} -> per-nutrient needs.
  GET  /api/nutrition/households/{name}/needs?period=week
        aggregate household demand + per-member breakdown.
  GET  /api/nutrition/persons/{name}/obesity          (nmp-1)
        BMI band / body-fat classification + honest caveats.
  GET  /api/nutrition/persons/{name}/envelope         (nmp-1)
        the healthy daily-calorie band + per-slot split.
  GET  /api/nutrition/persons/{name}/thresholds?period=day  (nmp-1)
        per-nutrient min/target/max with derivations + overrides.

Profiles are edited through standard CRUDE on DietaryNutrient /
NutrientReference / PersonProfile / HouseholdProfile rows
(object-coherence).

@consumers
  - nutrition frontend (later); nut-5 fulfillment
@see /HOUSEHOLD_NUTRITION_PLAN.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from nutrition.person_analysis import (
    bmr, calorie_target, nutrient_needs, tdee,
)
from nutrition.household_analysis import household_needs
from nutrition.threshold_analysis import (
    calorie_envelope, obesity_classification, person_thresholds,
)
from nutrition.tolerance_analysis import (
    evaluate_tolerances, meal_glycemic_load,
)
from nutrition.recipe_analysis import (
    recipe_nutrition, retention_candidates,
)
from nutrition.meal_analysis import (
    plan_rollup, template_rollup, validate_template,
)
from nutrition.activity_analysis import (
    day_timeline, fasted_exercise_facts, weekly_summary,
)
from nutrition.weight_trajectory import observed_vs_projected
from nutrition.fulfillment_analysis import coverage, suggest_plantings
from nutrition.workflow_analysis import (
    derive_week_plan, resolve_method, tool_advisor,
)


class NutritionAPI(treeObject):
    """nut-1/3/4 endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/nutrition'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/nutrition/nutrients', self, suffix='nutrients')
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/bmr', self, suffix='bmr')
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/needs', self,
                suffix='needs')
            polServer.falconServer.add_route(
                '/api/nutrition/households/{name}/needs', self,
                suffix='household')
            # nmp-1: the threshold layer
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/obesity', self,
                suffix='obesity')
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/envelope', self,
                suffix='envelope')
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/thresholds', self,
                suffix='thresholds')
            # nmp-2: the tolerance table
            polServer.falconServer.add_route(
                '/api/nutrition/tolerances', self,
                suffix='tolerances')
            polServer.falconServer.add_route(
                '/api/nutrition/tolerance-check', self,
                suffix='tolerance_check')
            polServer.falconServer.add_route(
                '/api/nutrition/meal-gl', self, suffix='meal_gl')
            # nmp-3: the recipe rollup engine
            polServer.falconServer.add_route(
                '/api/nutrition/recipes/{name}/nutrition', self,
                suffix='recipe_nutrition')
            polServer.falconServer.add_route(
                '/api/nutrition/retention-search', self,
                suffix='retention_search')
            # nmp-4: templates + plans
            polServer.falconServer.add_route(
                '/api/nutrition/templates/{name}/validate', self,
                suffix='template_validate')
            polServer.falconServer.add_route(
                '/api/nutrition/templates/{name}/rollup', self,
                suffix='template_rollup')
            polServer.falconServer.add_route(
                '/api/nutrition/plans/{name}/rollup', self,
                suffix='plan_rollup')
            # nmp-5/5b: activity + timing
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/activity-week', self,
                suffix='activity_week')
            polServer.falconServer.add_route(
                '/api/nutrition/plans/{name}/timeline', self,
                suffix='timeline')
            polServer.falconServer.add_route(
                '/api/nutrition/fasted-exercise', self,
                suffix='fasted')
            # nmp-6: the Hall weight trajectory
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/trajectory', self,
                suffix='trajectory')
            # nmp-7: the garden loop (nut-5, meal-plan-aware)
            polServer.falconServer.add_route(
                '/api/nutrition/garden-plans/{name}/coverage', self,
                suffix='garden_coverage')
            polServer.falconServer.add_route(
                '/api/nutrition/garden-plans/{name}/suggest', self,
                suffix='garden_suggest')
            # nmp-10: the prep scheduler
            polServer.falconServer.add_route(
                '/api/nutrition/plans/{name}/prep-schedule', self,
                suffix='prep_schedule')
            polServer.falconServer.add_route(
                '/api/nutrition/plans/{name}/tool-advisor', self,
                suffix='tool_advice')
            polServer.falconServer.add_route(
                '/api/nutrition/method-resolve', self,
                suffix='method_resolve')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def _named(self, class_name, name):
        for row in self._rows(class_name):
            if getattr(row, 'name', '') == name:
                return row
        return None

    def on_get_nutrients(self, request, response):
        out = []
        for n in self._rows('DietaryNutrient'):
            out.append({
                'name': getattr(n, 'name', ''),
                'displayName': getattr(n, 'display_name', ''),
                'category': getattr(n, 'category', ''),
                'unit': getattr(n, 'unit', ''),
                'role': getattr(n, 'role', ''),
                'plantAvailability': getattr(n, 'plant_availability', ''),
                'alternateSource': getattr(n, 'alternate_source', '')})
        response.media = {'ok': True, 'nutrients': out,
                          'count': len(out)}

    def on_get_bmr(self, request, response, name):
        person = self._named('PersonProfile', name)
        if person is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no PersonProfile named '{name}'"}
            return
        response.media = {'ok': True, 'person': name,
                          'bmr': bmr(person), 'tdee': tdee(person),
                          'calorieTarget': calorie_target(person)}

    def on_post_needs(self, request, response, name):
        try:
            body = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        person = self._named('PersonProfile', name)
        if person is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no PersonProfile named '{name}'"}
            return
        result = nutrient_needs(self.manager, person,
                                period=body.get('period', 'day'))
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def _person_or_404(self, response, name):
        person = self._named('PersonProfile', name)
        if person is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no PersonProfile named '{name}'"}
        return person

    def on_get_obesity(self, request, response, name):
        person = self._person_or_404(response, name)
        if person is None:
            return
        result = obesity_classification(person)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_envelope(self, request, response, name):
        person = self._person_or_404(response, name)
        if person is None:
            return
        response.media = calorie_envelope(self.manager, person)

    def on_get_thresholds(self, request, response, name):
        person = self._person_or_404(response, name)
        if person is None:
            return
        period = (request.params or {}).get('period', 'day')
        result = person_thresholds(self.manager, person, period=period)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_tolerances(self, request, response):
        out = []
        for t in self._rows('ToleranceThreshold'):
            out.append({
                'name': getattr(t, 'name', ''),
                'substance': getattr(t, 'substance', ''),
                'period': getattr(t, 'period', ''),
                'thresholdAmount': getattr(t, 'threshold_amount', 0.0),
                'unit': getattr(t, 'unit', ''),
                'perKgBodyMass': bool(
                    getattr(t, 'per_kg_body_mass', False)),
                'symptom': getattr(t, 'symptom', ''),
                'citation': getattr(t, 'citation', ''),
                'confidence': getattr(t, 'confidence', ''),
                'qualifier': getattr(t, 'qualifier', '')})
        response.media = {'ok': True, 'tolerances': out,
                          'count': len(out)}

    def _json_body(self, request, response):
        try:
            return json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return None

    def on_post_tolerance_check(self, request, response):
        body = self._json_body(request, response)
        if body is None:
            return
        person = None
        if body.get('person'):
            person = self._named('PersonProfile', body['person'])
        result = evaluate_tolerances(
            self.manager, body.get('intake', {}) or {},
            body.get('period', 'day'), person=person)
        response.media = result

    def on_post_meal_gl(self, request, response):
        body = self._json_body(request, response)
        if body is None:
            return
        response.media = meal_glycemic_load(
            self.manager, body.get('portions', []) or [])

    def on_get_recipe_nutrition(self, request, response, name):
        recipe = self._named('Recipe', name)
        if recipe is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no Recipe named '{name}'"}
            return
        result = recipe_nutrition(self.manager, recipe)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_retention_search(self, request, response):
        q = (request.params or {}).get('q', '')
        if not q:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': 'q= required'}
            return
        hits = retention_candidates(q)
        response.media = {'ok': True, 'query': q, 'candidates': hits,
                          'count': len(hits)}

    def on_get_template_validate(self, request, response, name):
        t = self._named('MealTemplate', name)
        if t is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no MealTemplate named '{name}'"}
            return
        response.media = validate_template(self.manager, t)

    def on_get_template_rollup(self, request, response, name):
        t = self._named('MealTemplate', name)
        if t is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no MealTemplate named '{name}'"}
            return
        params = request.params or {}
        variation = None
        if params.get('variation'):
            variation = self._named('VariationDefinition',
                                    params['variation'])
        try:
            scale = float(params.get('scale', 1.0))
        except ValueError:
            scale = 1.0
        result = template_rollup(self.manager, t, variation, scale)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_plan_rollup(self, request, response, name):
        plan = self._named('MealPlanDefinition', name)
        if plan is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no MealPlanDefinition named '{name}'"}
            return
        result = plan_rollup(self.manager, plan)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_activity_week(self, request, response, name):
        person = self._person_or_404(response, name)
        if person is None:
            return
        response.media = weekly_summary(self.manager, person)

    def on_get_timeline(self, request, response, name):
        plan = self._named('MealPlanDefinition', name)
        if plan is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no MealPlanDefinition named '{name}'"}
            return
        try:
            day = int((request.params or {}).get('day', 1))
        except ValueError:
            day = 1
        response.media = day_timeline(self.manager, plan, day)

    def on_get_fasted(self, request, response):
        response.media = fasted_exercise_facts()

    def on_get_trajectory(self, request, response, name):
        person = self._person_or_404(response, name)
        if person is None:
            return
        params = request.params or {}
        from nutrition.threshold_analysis import calorie_envelope
        try:
            intake = float(params.get('daily_kcal', 0) or 0)
        except ValueError:
            intake = 0.0
        if intake <= 0:
            # default: the person's envelope target (their plan's
            # honest daily number)
            intake = calorie_envelope(
                self.manager, person)['targetDailyKcal']
        try:
            horizon = int(params.get('horizon_weeks', 0) or 0) or None
        except ValueError:
            horizon = None
        result = observed_vs_projected(self.manager, person,
                                       intake, horizon)
        if result.get('ok') and str(
                params.get('naive', '')).lower() in ('1', 'true'):
            from nutrition.weight_trajectory import project_weight
            naive = project_weight(person, intake, horizon,
                                   include_naive=True)
            result['naive3500Kg'] = naive.get('naive3500Kg')
            result['naive3500Label'] = naive.get('naive3500Label')
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_garden_coverage(self, request, response, name):
        period = (request.params or {}).get('period', 'week')
        result = coverage(self.manager, name, period)
        if not result.get('ok'):
            response.status = '404 Not Found' \
                if 'no GardenPlanDefinition' in str(
                    result.get('error', '')) else '400 Bad Request'
        response.media = result

    def on_get_garden_suggest(self, request, response, name):
        period = (request.params or {}).get('period', 'week')
        result = suggest_plantings(self.manager, name, period)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def _plan_or_404(self, response, name):
        plan = self._named('MealPlanDefinition', name)
        if plan is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no MealPlanDefinition named '{name}'"}
        return plan

    def on_get_prep_schedule(self, request, response, name):
        plan = self._plan_or_404(response, name)
        if plan is None:
            return
        params = request.params or {}
        result = derive_week_plan(
            self.manager, plan,
            household=params.get('household', ''),
            skill=params.get('skill', 'intermediate'))
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_tool_advice(self, request, response, name):
        plan = self._plan_or_404(response, name)
        if plan is None:
            return
        params = request.params or {}
        response.media = tool_advisor(
            self.manager, plan,
            household=params.get('household', ''),
            skill=params.get('skill', 'intermediate'))

    def on_post_method_resolve(self, request, response):
        body = self._json_body(request, response)
        if body is None:
            return
        result = resolve_method(
            self.manager, body.get('task_kind', ''),
            float(body.get('grams', 0.0) or 0.0),
            household=body.get('household', ''),
            skill=body.get('skill', 'intermediate'))
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_household(self, request, response, name):
        period = (request.params or {}).get('period', 'week')
        result = household_needs(self.manager, name, period=period)
        if not result.get('ok'):
            response.status = '404 Not Found' \
                if 'no HouseholdProfile' in str(result.get('error', '')) \
                else '400 Bad Request'
        response.media = result
