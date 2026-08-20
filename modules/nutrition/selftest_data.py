"""
@module nutrition.selftest_data

nmp-0 selftest — the vendored data + transcriptions hold together:
vendor CSVs parse and carry the expected shapes/counts, the DRI
table covers every nutrient with sane band structure, the FDC seed
rows reference only known nutrients/foods, spot values match the
published numbers they claim to be.

Run from polari-framework/:  python3 -m nutrition.selftest_data
Stdlib-only; no manager, no DB, no server.
"""

from nutrition.dga_limits import AMDR, DGA_EDITION, DGA_LIMITS
from nutrition.dri_seed import SEED_DRI_REFERENCES
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.nutrient_seed import SEED_DIETARY_NUTRIENTS
from nutrition import vendor_data

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def main():
    nutrients = {n['name'] for n in SEED_DIETARY_NUTRIENTS}

    print('nmp-0 vendor files')
    r6 = vendor_data.retention_factors()
    check('retention factors: 7018 rows', len(r6) == 7018,
          f'got {len(r6)}')
    # some source rows carry a BLANK factor (missing upstream —
    # honest absence, kept verbatim); numeric ones must be 0-100
    check('retention percent parses 0-100 where present',
          all(0 <= float(r['retention_percent']) <= 100
              for r in r6 if r['retention_percent'].strip()))
    mets = vendor_data.compendium_mets()
    check('compendium: 1111 activities', len(mets) == 1111,
          f'got {len(mets)}')
    check('compendium: 22 categories',
          len({r['category'] for r in mets}) == 22)
    check('MET values parse and are plausible (0.9-25)',
          all(0.9 <= float(r['met_value']) <= 25 for r in mets))
    yields = vendor_data.cooking_yields()
    ynum = [r for r in yields
            if len(r) > 4 and r[4].replace('.', '', 1).isdigit()]
    check('cooking yields: >=150 numeric rows', len(ynum) >= 150,
          f'got {len(ynum)}')

    print('nmp-0 FDC subset -> seed rows')
    check('49 starter foods', len(SEED_FDC_FOOD_ITEMS) == 49,
          f'got {len(SEED_FDC_FOOD_ITEMS)}')
    check('949 content rows',
          len(SEED_FDC_NUTRIENT_CONTENTS) == 949,
          f'got {len(SEED_FDC_NUTRIENT_CONTENTS)}')
    check('every content row names a known nutrient',
          all(c['nutrient_name'] in nutrients
              for c in SEED_FDC_NUTRIENT_CONTENTS))
    slugs = {f['name'] for f in SEED_FDC_FOOD_ITEMS}
    check('every content row names a known food',
          all(c['food_name'] in slugs
              for c in SEED_FDC_NUTRIENT_CONTENTS))
    check('every food pins an fdc_id',
          all(f['fdc_id'] > 0 for f in SEED_FDC_FOOD_ITEMS))
    by_key = {c['name']: c for c in SEED_FDC_NUTRIENT_CONTENTS}
    # spot values straight off the vendored CSV's cited FDC rows
    check('salt sodium = 38700 mg/100g',
          by_key['salt-iodized-sodium']['amount_per_100g'] == 38700.0)
    check('banana potassium = 326 mg/100g',
          by_key['banana-raw-potassium']['amount_per_100g'] == 326.0)
    check('copper rows are in ug (unit conversion applied)',
          by_key['almonds-raw-copper']['unit'] == 'ug'
          and by_key['almonds-raw-copper']['amount_per_100g'] > 100)

    print('nmp-0 DRI transcription')
    ref_nutrients = {r['nutrient_name'] for r in SEED_DRI_REFERENCES}
    check('every nutrient has >=1 DRI row',
          nutrients <= ref_nutrients,
          f'missing: {sorted(nutrients - ref_nutrients)}')
    names = [r['name'] for r in SEED_DRI_REFERENCES]
    check('row names unique', len(names) == len(set(names)))
    check('life-stage rows present (pregnancy + lactation)',
          {r['life_stage'] for r in SEED_DRI_REFERENCES} >=
          {'', 'pregnancy', 'lactation'})
    check('every row carries jurisdiction + edition',
          all(r['jurisdiction'] and r['edition']
              for r in SEED_DRI_REFERENCES))
    # spot checks against the NASEM tables the header cites
    def row(name):
        return next(r for r in SEED_DRI_REFERENCES
                    if r['name'] == name)
    check('male iron RDA 8 / EAR 6 / UL 45',
          (row('iron-male-19-120')['rda_per_day'],
           row('iron-male-19-120')['ear_per_day'],
           row('iron-male-19-120')['upper_limit_per_day'])
          == (8.0, 6.0, 45.0))
    check('female 19-50 iron RDA 18',
          row('iron-female-19-51')['rda_per_day'] == 18.0)
    check('pregnancy iron RDA 27',
          row('iron-female-pregnancy-19-50')['rda_per_day'] == 27.0)
    check('vitamin D 71+ RDA 20 ug',
          row('vitamin-d-any-71-120')['rda_per_day'] == 20.0)
    check('sodium max carries the CDRR note',
          'CDRR' in row('sodium-any-19-120')['notes']
          and row('sodium-any-19-120')['upper_limit_per_day'] == 2300.0)
    check('AI rows carry no EAR (none exists by definition)',
          all(r['ear_per_day'] == 0 for r in SEED_DRI_REFERENCES
              if r['value_type'] == 'ai'))
    check('firm RDA rows are non-prior; AI/prior rows flagged',
          all((r['value_type'] == 'rda') == (not r['is_prior'])
              for r in SEED_DRI_REFERENCES))
    # boundary-age rule: within a nutrient+sex+stage, higher bands
    # must be seeded first (person_analysis first-match)
    seen = {}
    ordered = True
    for r in SEED_DRI_REFERENCES:
        key = (r['nutrient_name'], r['sex'], r['life_stage'])
        if key in seen and r['age_min'] > seen[key]:
            ordered = False
        seen[key] = r['age_min']
    check('bands seeded higher-first per (nutrient, sex, stage)',
          ordered)

    print('nmp-0 DGA limits')
    check('edition tagged 2020-2025', DGA_EDITION == '2020-2025')
    check('3 limits + 3 AMDR bands',
          len(DGA_LIMITS) == 3 and len(AMDR) == 3)
    check('AMDR fractions sane',
          all(0 < a['min_fraction'] < a['max_fraction'] <= 0.65
              for a in AMDR))

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-0 data adoption holds together')


if __name__ == '__main__':
    main()
