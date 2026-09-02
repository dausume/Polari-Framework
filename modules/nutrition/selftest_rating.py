"""
@module nutrition.selftest_rating

mpb-8 selftest — ratings into ranking: averages per template and
variation, the person's own history outranks the household's,
unrated templates sit neutral and labeled, out-of-range ratings
are ignored, and nothing is ever hidden by a low score.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_rating
"""

from types import SimpleNamespace

from nutrition.rating_basis import SEED_MEAL_RATINGS
from nutrition.rating_analysis import rank_templates, rating_summary

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


RATINGS = list(SEED_MEAL_RATINGS) + [
    # a housemate hates the bowl; alex has no rating for it… wait,
    # alex rates it 4 in the seeds — dana's 1 must NOT change
    # alex's own ranking.
    {'name': 'dana-bowl-r1', 'person_name': 'test-dana',
     'template_name': 'chicken-bowl-dinner',
     'variation_name': 'chicken-bowl-dinner-tofu', 'rating': 1,
     'note': 'not for me', 'date': '2026-09-01',
     'intake_record_name': '', 'is_prior': False},
    # garbage rating ignored
    {'name': 'bad-r', 'person_name': 'test-dana',
     'template_name': 'omelet-breakfast', 'variation_name': '',
     'rating': 11, 'note': '', 'date': '', 'intake_record_name':
     '', 'is_prior': False},
]

MANAGER = SimpleNamespace(objectTables={
    'MealRating': _rows(RATINGS),
})

print('mpb-8: ratings into ranking')

own = rating_summary(MANAGER, 'demo-alex')
check('per-person summary computes', own.get('ok')
      and own['ratingCount'] == 2)
check('sorted best-first with variation averages',
      own['templates'][0]['template'] == 'omelet-breakfast'
      and own['templates'][1]['variations']
      ['chicken-bowl-dinner-base'] == 4.0)
check('out-of-range ratings ignored (11 stars is not a rating)',
      rating_summary(MANAGER, 'test-dana')['ratingCount'] == 1)

everyone = rating_summary(MANAGER)
bowl = [t for t in everyone['templates']
        if t['template'] == 'chicken-bowl-dinner'][0]
check('household average blends raters (4 and 1 → 2.5)',
      bowl['avg'] == 2.5)

rank = rank_templates(MANAGER, 'demo-alex',
                      ['chicken-bowl-dinner', 'omelet-breakfast',
                       'mystery-meal'])
check('own ratings outrank the household blend (alex bowl = 4, '
      'not 2.5)',
      [e for e in rank['ranked']
       if e['template'] == 'chicken-bowl-dinner'][0]['score']
      == 4.0)
check('unrated template sits neutral and labeled',
      [e for e in rank['ranked']
       if e['template'] == 'mystery-meal'][0]['basis']
      == 'unrated (neutral)')
check('nothing hidden: every candidate returned',
      len(rank['ranked']) == 3
      and 'hidden' in rank['honesty'] or 'blocked'
      in rank['honesty'])
dana = rank_templates(MANAGER, 'test-dana',
                      ['chicken-bowl-dinner'])
check('a housemate\'s own 1-star ranks low for THEM',
      dana['ranked'][0]['score'] == 1.0
      and dana['ranked'][0]['basis'] == 'your ratings')

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpb-8 ratings hold together')
