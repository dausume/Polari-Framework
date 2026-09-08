"""
@module bizops.custom.bizops_deals

biz-5 / scenario-3 (static half): TRANSFER-PRICE DISCOVERY for
partnership deals. For every flow on a PartnershipAgreement the
viable window is bounded by data already on record:

  floor   = supplier's cheapest seeded make-cost for the item,
            marked up by min_margin_pct (nobody supplies at cost
            forever); no seeded recipe (byproducts, shaped goods)
            -> floor 0 WITH the note — the supplier must confirm.
  ceiling = the buyer's best cited alternative (the flow's
            alternative_item_ref, defaulting to the item itself at
            retail) — above that the buyer just buys retail.

Window empty or unboundable -> honest refusal per bound, with the
citation ask. The suggested price is the midpoint, and it is a
SUGGESTION with evidence — terms change only when humans edit the
deal row. The dynamic half (running the odoo scenario engine over a
price sweep) stays a plan-first suggestion in the report.

@consumers bizops.bizops_api (/api/bizops/deal-pricing/{deal})
"""

import re

from bizops.custom.bizops_flows import _loads, _named, _rows
from supplychain.custom.formula_analysis import (
    effective_unit_price, make_cost,
)


def _current_term_price(terms_note):
    """Best-effort read of a number already in the terms note
    ('transfer price 3.50/kg ...') — None when not parseable;
    shown next to the window so a human compares, never acted on."""
    match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(kg|unit)',
                      terms_note or '')
    return float(match.group(1)) if match else None


def _flow_window(manager, flow, min_margin_pct):
    item = flow.get('item_ref', '')
    alternative = flow.get('alternative_item_ref') or item
    out = {'item': item, 'from': flow.get('from', ''),
           'to': flow.get('to', ''),
           'alternativeItem': alternative,
           'currentTermPrice': _current_term_price(
               flow.get('terms_note', ''))}

    made = make_cost(manager, item)
    if made is not None:
        floor = round(made['usdPerKg']
                      * (1.0 + min_margin_pct / 100.0), 4)
        out['floorUsdPerKg'] = floor
        out['floorBasis'] = (f'make-cost {made["usdPerKg"]}/kg via '
                             f'{made["formula"]} '
                             f'+ {min_margin_pct:g}% margin')
        out['floorEstimate'] = bool(made.get('anyEstimate'))
    else:
        floor = 0.0
        out['floorUsdPerKg'] = 0.0
        out['floorBasis'] = ('no seeded recipe for the item '
                             '(byproduct or shaped good) — floor '
                             'set at 0; the SUPPLIER must confirm '
                             'their real cost before agreeing')

    alt = effective_unit_price(manager, alternative)
    ceiling = (alt or {}).get('normalized')
    if ceiling is not None:
        out['ceilingUsdPerKg'] = ceiling
        out['ceilingBasis'] = (f'buyer\'s alternative: '
                               f'{alternative} at {ceiling}/kg '
                               f'({(alt or {}).get("via", "?")}, '
                               f'{(alt or {}).get("source", "?")})')
        out['ceilingEstimate'] = bool((alt or {}).get('isEstimate'))
    else:
        out['ceilingUsdPerKg'] = None
        out['ceilingBasis'] = (f'no citation prices "{alternative}" '
                               '— the ceiling is unknowable until '
                               'one lands')
        out['ask'] = (f'cite a retail/commercial price for '
                      f'"{alternative}" (PriceCitation row) to '
                      'bound this flow')

    if ceiling is None:
        out['viable'] = None
        out['note'] = 'unbounded above — window not computable'
        return out
    if ceiling <= floor:
        out['viable'] = False
        out['note'] = (f'EMPTY window: the buyer buys retail at '
                       f'{ceiling}/kg for less than the supplier '
                       f'can make it ({floor}/kg incl. margin) — '
                       'this deal only works on byproduct/scale '
                       'economics the rows do not show yet')
        return out
    midpoint = round((floor + ceiling) / 2.0, 2)
    out['viable'] = True
    out['suggestedUsdPerKg'] = midpoint
    out['buyerSavingPct'] = round(
        100.0 * (ceiling - midpoint) / ceiling, 1)
    out['supplierMarkupNote'] = (
        f'midpoint {midpoint}/kg sits {round(midpoint - floor, 2)} '
        'above the floor — split the surplus, argue from there')
    return out


def deal_price_window(manager, deal_name, min_margin_pct=10.0):
    """The discovery report for one deal: a bounded window per flow,
    every bound carrying its basis and estimate flags."""
    deal = _named(manager, 'PartnershipAgreement', deal_name)
    if deal is None:
        return {'ok': False,
                'refusal': f'no PartnershipAgreement named '
                           f'"{deal_name}"'}
    flows = [_flow_window(manager, f, min_margin_pct)
             for f in _loads(deal, 'flows_json', [])]
    return {
        'ok': True, 'deal': deal_name,
        'displayName': getattr(deal, 'display_name', ''),
        'minMarginPct': min_margin_pct,
        'flows': flows,
        'suggestion': {
            'evidence': 'bounds derive from seeded make-costs and '
                        'cited prices — every basis is on the flow',
            'knob': f'PartnershipAgreement[{deal_name}].flows_json '
                    '(terms_note per flow)',
            'action': 'edit the deal terms to a price inside the '
                      'window if both parties agree — suggestion, '
                      'never auto-applied'},
        'dynamicHalf': 'to VALIDATE a chosen price end-to-end, run '
                       'the odoo scenario engine with the price '
                       'repinned (hydroponic-wax-farm-v1 seed) — '
                       'plan-first via /api/odoo/scenario/plan',
        'units': 'USD/kg throughout — per-unit flows (pots) refuse '
                 'their bounds until priced per kg or cited '
                 'per-unit (dimension honesty)'}


def deal_pricing_catalog(manager, min_margin_pct=10.0):
    """Windows for every seeded deal — the partnerships board feed."""
    deals = _rows(manager, 'PartnershipAgreement')
    if not deals:
        return {'ok': False,
                'refusal': 'no PartnershipAgreement rows seeded'}
    return {'ok': True,
            'deals': [deal_price_window(manager,
                                        getattr(d, 'name', ''),
                                        min_margin_pct)
                      for d in deals]}
