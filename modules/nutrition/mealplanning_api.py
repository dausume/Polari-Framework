"""
@cross-cutting
@module nutrition.mealplanning_api
@tags @xc:bindings

mpa-5 — the meal-planning APP's read surface, one route per display
panel (MEAL_PLANNING_APP_PLAN.md; every page is pure data over
these):

  GET /api/mealplanning/me                         who am I here
  GET /api/mealplanning/users/{person}/dashboard   the front door
  GET /api/mealplanning/users/{person}/day/{date}  one day rolled up
  GET /api/mealplanning/users/{person}/series      metrics over time
  GET /api/mealplanning/plans/{name}/cost          plan $ estimate
  GET /api/mealplanning/plans/{name}/availability  plan vs pantry
  GET /api/mealplanning/plans/{name}/shopping-list priced gap
  GET /api/mealplanning/plans/{name}/suggestions   stock-aware swaps
  GET /api/mealplanning/prices                     price compare
  GET /api/mealplanning/pantry/{household}         what's on hand
  GET /api/mealplanning/purchase-preview           weight+nutrition
                                                   for a purchase
  GET /api/mealplanning/templates/{name}/acidity   meal acidity
  GET /api/mealplanning/templates/{name}/state-chain
                                                   the fsp-2 PSPP
                                                   chain behind the
                                                   meal

Writes stay on the generic CRUDE surface (PantryItem /
PriceObservation / IntakeRecord / UserAccountLink rows) — this API
is the derived-view layer, not a second write path.

@consumers
  - polariServer (route registration, gated on nutrition)
  - the /display/mealplan* pages (mealplanning_pages_seed)
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-5
"""

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.acidity_analysis import template_acidity
from nutrition.market_analysis import (price_report,
                                       purchased_item_report)
from nutrition.meal_analysis import _named
from nutrition.pantry_analysis import (
    availability_suggestions, pantry_stock, plan_cost,
    plan_vs_pantry, shopping_list,
)
from nutrition.person_analysis import _rows
from nutrition.tracking_analysis import (
    intake_day, resolve_me, tracking_series,
)


def _plan_household(manager, plan, request):
    return (request.params.get('household')
            or getattr(plan, 'household_name', '')
            or 'demo-household')


class MealPlanningAPI(treeObject):
    """The meal-planning app's derived-view routes."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/mealplanning'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/mealplanning/me', self, suffix='me')
            add('/api/mealplanning/users/{person}/dashboard', self,
                suffix='dashboard')
            add('/api/mealplanning/users/{person}/day/{day}', self,
                suffix='day')
            add('/api/mealplanning/users/{person}/series', self,
                suffix='series')
            add('/api/mealplanning/plans/{name}/cost', self,
                suffix='plan_cost')
            add('/api/mealplanning/plans/{name}/availability', self,
                suffix='availability')
            add('/api/mealplanning/plans/{name}/shopping-list', self,
                suffix='shopping')
            add('/api/mealplanning/plans/{name}/suggestions', self,
                suffix='suggestions')
            add('/api/mealplanning/prices', self, suffix='prices')
            add('/api/mealplanning/pantry/{household}', self,
                suffix='pantry')
            add('/api/mealplanning/purchase-preview', self,
                suffix='purchase_preview')
            add('/api/mealplanning/templates/{name}/acidity', self,
                suffix='template_acidity')
            add('/api/mealplanning/templates/{name}/state-chain',
                self, suffix='state_chain')

    # ── identity ─────────────────────────────────────────
    def on_get_me(self, request, response):
        info = getattr(request.context, 'user_info', None)
        me = resolve_me(self.manager, info)
        if me.get('ok'):
            person = me['person']
            me['plans'] = sorted(
                getattr(p, 'name', '') for p in
                _rows(self.manager, 'MealPlanDefinition')
                if getattr(p, 'person_name', '') == person
                or (me['household'] and getattr(
                    p, 'household_name', '') == me['household']))
            me['nextSteps'] = {
                'dashboard': f'/api/mealplanning/users/{person}'
                             f'/dashboard',
                'series': f'/api/mealplanning/users/{person}/series',
            }
        response.media = me

    def on_get_dashboard(self, request, response, person):
        manager = self.manager
        profile = _named(manager, 'PersonProfile', person)
        link = None
        for row in _rows(manager, 'UserAccountLink'):
            if getattr(row, 'person_name', '') == person:
                link = row
                break
        household = (request.params.get('household')
                     or (getattr(link, 'household_name', '')
                         if link else '') or 'demo-household')
        dates = sorted({
            getattr(r, 'date', '') for r in
            _rows(manager, 'IntakeRecord')
            if getattr(r, 'person_name', '') == person
            and getattr(r, 'date', '')})
        latest = intake_day(manager, person, dates[-1]) if dates \
            else {'ok': False, 'error': 'no intake logged yet'}
        plans = sorted(
            getattr(p, 'name', '') for p in
            _rows(manager, 'MealPlanDefinition')
            if getattr(p, 'person_name', '') == person
            or getattr(p, 'household_name', '') == household)
        stock = pantry_stock(manager, household)
        response.media = {
            'ok': True, 'schema': 'mealplan-dashboard/1',
            'person': person,
            'profileExists': profile is not None,
            'household': household,
            'plans': plans,
            'latestDay': latest,
            'pantryFoods': len(stock['stockG']),
            'pantryUnresolved': len(stock['unresolved']),
            'links': {
                'day': f'/api/mealplanning/users/{person}/day/'
                       + (dates[-1] if dates else 'YYYY-MM-DD'),
                'series': f'/api/mealplanning/users/{person}/series',
                'pantry': f'/api/mealplanning/pantry/{household}',
                'prices': '/api/mealplanning/prices',
            },
        }

    def on_get_day(self, request, response, person, day):
        response.media = intake_day(self.manager, person, day)

    def on_get_series(self, request, response, person):
        nutrients = None
        if request.params.get('nutrients'):
            nutrients = [n.strip() for n in
                         request.params['nutrients'].split(',')
                         if n.strip()]
        # persist=True: reading the series refreshes the
        # DailyIntakeMetric cache rows the trend charts read
        # (derive-on-demand + cached, idempotent upsert).
        response.media = tracking_series(
            self.manager, person,
            start_date=request.params.get('start'),
            end_date=request.params.get('end'),
            nutrients=nutrients,
            persist=request.params.get('persist', '1') != '0')

    # ── plans vs pantry vs market ────────────────────────
    def _plan(self, name, response):
        plan = _named(self.manager, 'MealPlanDefinition', name)
        if plan is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'no MealPlanDefinition '
                                       f'"{name}"'}
        return plan

    def on_get_plan_cost(self, request, response, name):
        plan = self._plan(name, response)
        if plan is not None:
            response.media = plan_cost(self.manager, plan)

    def on_get_availability(self, request, response, name):
        plan = self._plan(name, response)
        if plan is not None:
            response.media = plan_vs_pantry(
                self.manager, plan,
                _plan_household(self.manager, plan, request))

    def on_get_shopping(self, request, response, name):
        plan = self._plan(name, response)
        if plan is not None:
            response.media = shopping_list(
                self.manager, plan,
                _plan_household(self.manager, plan, request))

    def on_get_suggestions(self, request, response, name):
        plan = self._plan(name, response)
        if plan is not None:
            response.media = availability_suggestions(
                self.manager, plan,
                _plan_household(self.manager, plan, request))

    # ── market + pantry ──────────────────────────────────
    def on_get_prices(self, request, response):
        response.media = price_report(
            self.manager, request.params.get('food') or None)

    def on_get_pantry(self, request, response, household):
        response.media = pantry_stock(self.manager, household)

    def on_get_purchase_preview(self, request, response):
        params = request.params
        food = params.get('food', '')
        if not food:
            response.media = {
                'ok': False,
                'error': 'purchase-preview?food=<slug>&quantity=N'
                         '&unit=<g|kg|lb|oz|each|cup|…>'}
            return
        try:
            quantity = float(params.get('quantity', '1'))
        except ValueError:
            response.media = {'ok': False,
                              'error': 'quantity must be a number'}
            return
        response.media = purchased_item_report(
            self.manager, food, quantity,
            params.get('unit', 'each'),
            params.get('household', ''))

    # ── the PSPP seam ────────────────────────────────────
    def on_get_template_acidity(self, request, response, name):
        template = _named(self.manager, 'MealTemplate', name)
        if template is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'no MealTemplate "{name}"'}
            return
        variation = None
        if request.params.get('variation'):
            variation = _named(self.manager, 'VariationDefinition',
                               request.params['variation'])
        try:
            scale = float(request.params.get('scale', '1'))
        except ValueError:
            scale = 1.0
        response.media = template_acidity(
            self.manager, template, variation, scale)

    def on_get_state_chain(self, request, response, name):
        try:
            from foodstate.food_transforms import (
                template_state_chain,
            )
        except ImportError as exc:
            response.media = {
                'ok': False,
                'error': f'foodstate module not available ({exc}) — '
                         f'the PSPP state chain needs it enabled'}
            return
        response.media = template_state_chain(self.manager, name)
