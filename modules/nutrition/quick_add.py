"""
@cross-cutting
@module nutrition.quick_add
@tags @xc:bindings

mpb-9 — quick-add text entry (the adoption seam: prices, pantry
and intake die if entry is tedious). A DETERMINISTIC grammar —
refuses rather than guesses; every parse returns a PROPOSAL the
human applies through CRUDE, never a silent write.

Grammar (one line):
  price:   <qty> <unit> <food words> <price> [@ <location>]
           "2 lb chicken breast 11.98 @ demo-grocery"
  pantry:  <qty> <unit> <food words> [pantry|fridge|freezer]
           "3 each banana fridge"
  intake:  ate <template words> [<slot>] [on <YYYY-MM-DD>]
           "ate chicken bowl dinner on 2026-09-02"

Food/template resolution is token containment against the seeded
names — ambiguity REFUSES listing the candidates (never picks one
silently); unknown words refuse naming what was understood.

@consumers
  - nutrition.mealplanning_api (quick-add preview route)
  - nutrition.selftest_quickadd
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-9
"""

import re

from nutrition.market_basis import EXACT_UNIT_GRAMS
from nutrition.person_analysis import _rows

_COUNT_UNITS = ('each', 'dozen', 'bunch', 'head', 'cup', 'tbsp',
                'clove', 'stalk', 'oz-slice', 'lb', 'oz', 'kg', 'g')
_STORAGES = ('pantry', 'fridge', 'freezer')
_SLOTS = ('breakfast', 'lunch', 'dinner', 'brunch', 'linner',
          'snack')


def _resolve(tokens, names, kind):
    """Token-containment match of free words against seeded names.
    Exactly one candidate or a refusal naming the options."""
    if not tokens:
        return None, f'no {kind} words to resolve'
    joined = '-'.join(t.lower() for t in tokens)
    candidates = [n for n in names
                  if all(t.lower() in n for t in tokens)]
    exact = [n for n in candidates if n == joined]
    if exact:
        return exact[0], ''
    if len(candidates) == 1:
        return candidates[0], ''
    if not candidates:
        return None, (f'no {kind} matches "{" ".join(tokens)}" — '
                      f'nothing is guessed; check the name')
    return None, (f'"{" ".join(tokens)}" is ambiguous between '
                  f'{sorted(candidates)[:6]} — say more of the '
                  f'name')


def parse_quick_add(manager, text):
    """One line → one typed PROPOSAL (never a write)."""
    text = (text or '').strip()
    if not text:
        return {'ok': False, 'error': 'empty line'}
    foods = sorted(getattr(f, 'name', '')
                   for f in _rows(manager, 'FoodItem'))
    templates = sorted(getattr(t, 'name', '')
                       for t in _rows(manager, 'MealTemplate'))
    locations = sorted(getattr(l, 'name', '')
                       for l in _rows(manager, 'SourceLocation'))

    # ── intake: "ate <template words> [slot] [on date]" ──
    m = re.match(r'^ate\s+(.*)$', text, re.IGNORECASE)
    if m:
        rest = m.group(1)
        date = ''
        dm = re.search(r'\bon\s+(\d{4}-\d{2}-\d{2})\s*$', rest)
        if dm:
            date = dm.group(1)
            rest = rest[:dm.start()].strip()
        tokens = rest.split()
        slot = ''
        if tokens and tokens[-1].lower() in _SLOTS:
            slot = tokens[-1].lower()
            tokens = tokens[:-1]
        template, why = _resolve(tokens, templates, 'meal template')
        if template is None:
            return {'ok': False, 'error': why}
        return {'ok': True, 'schema': 'quick-add/1',
                'kind': 'intake',
                'proposal': {'template_name': template,
                             'slot': slot or 'dinner',
                             'date': date,
                             'source': 'logged'},
                'appliedBy': 'you — this is a proposal; apply it '
                             'as an IntakeRecord row'}

    # ── price / pantry: "<qty> <unit> <words> [...]" ─────
    m = re.match(r'^(\d+(?:\.\d+)?)\s+(\S+)\s+(.*)$', text)
    if not m:
        return {'ok': False,
                'error': 'unparsed — expected "<qty> <unit> '
                         '<food> [...]", "ate <template> [...]"; '
                         'nothing is guessed'}
    qty = float(m.group(1))
    unit = m.group(2).lower()
    if unit not in _COUNT_UNITS and unit not in EXACT_UNIT_GRAMS:
        return {'ok': False,
                'error': f'unknown unit "{unit}" — known: '
                         f'{sorted(set(_COUNT_UNITS) | set(EXACT_UNIT_GRAMS))}'}
    rest = m.group(3)
    location = ''
    lm = re.search(r'@\s*(\S+)\s*$', rest)
    if lm:
        location = lm.group(1)
        rest = rest[:lm.start()].strip()
        if location not in locations:
            return {'ok': False,
                    'error': f'unknown location "{location}" — '
                             f'known: {locations}; add the '
                             f'SourceLocation row first'}
    tokens = rest.split()
    storage = ''
    if tokens and tokens[-1].lower() in _STORAGES:
        storage = tokens[-1].lower()
        tokens = tokens[:-1]
    price = None
    if tokens and re.fullmatch(r'\d+(?:\.\d+)?', tokens[-1]):
        price = float(tokens[-1])
        tokens = tokens[:-1]
    food, why = _resolve(tokens, foods, 'food')
    if food is None:
        return {'ok': False, 'error': why}
    if price is not None:
        if storage:
            return {'ok': False,
                    'error': 'a line cannot be both a price '
                             'observation and a pantry lot — '
                             'drop the storage word or the price'}
        return {'ok': True, 'schema': 'quick-add/1',
                'kind': 'price',
                'proposal': {'food_name': food, 'price': price,
                             'package_quantity': qty,
                             'package_unit': unit,
                             'location_name': location},
                'note': ('' if location else
                         'no @location — add one or the '
                         'observation stays unplaced'),
                'appliedBy': 'you — apply as a PriceObservation '
                             'row'}
    return {'ok': True, 'schema': 'quick-add/1',
            'kind': 'pantry',
            'proposal': {'food_name': food, 'quantity': qty,
                         'unit': unit,
                         'storage_state': storage or 'pantry'},
            'appliedBy': 'you — apply as a PantryItem row'}
