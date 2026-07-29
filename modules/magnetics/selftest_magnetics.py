"""
@module magnetics.selftest_magnetics

Section-A selftests (mag-2/2r/2t): realization gates, derived role
viability (the soft/hard split enforced by predicates, Earnshaw and
copper-gap honesty notes traveling, unassessed-not-assumed), the one
vol<->wt conversion, the analytic composite predictors vs the msci
FEM datum, cost-if-real gating, and the laddered answer.

Run from polari-framework/: python3 -m magnetics.selftest_magnetics
"""

import types

from magnetics.magnet_analysis import (
    bruggeman, composite_predict, gates_for, laddered_answer,
    maxwell_garnett, role_viability, viability_matrix, vol_from_wt,
    wt_from_vol, _named,
)
from magnetics.magnet_seed import (
    SEED_MAGNETIC_POWDERS, SEED_MATERIAL_OPTIONS, SEED_USE_ROLES,
)
from supplychain.sourcing_seed import (
    SEED_PRICE_CITATIONS, SEED_PRODUCT_FORMULAS,
    SEED_PRODUCT_REQUIREMENTS, SEED_SOURCE_POLICIES,
    SEED_SUPPLY_SOURCES,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _mgr():
    m = types.SimpleNamespace()

    def table(seed):
        return {s['name']: types.SimpleNamespace(**s) for s in seed}
    m.objectTables = {
        'MaterialUseRole': table(SEED_USE_ROLES),
        'MagneticMaterialOption': table(SEED_MATERIAL_OPTIONS),
        'MagneticPowderDefinition': table(SEED_MAGNETIC_POWDERS),
        'SupplySourceProfile': table(SEED_SUPPLY_SOURCES),
        'PriceCitation': table(SEED_PRICE_CITATIONS),
        'ProductInputRequirement': table(SEED_PRODUCT_REQUIREMENTS),
        'ProductFormula': table(SEED_PRODUCT_FORMULAS),
        'SourcePreferencePolicy': table(SEED_SOURCE_POLICIES),
    }
    return m


mgr = _mgr()


def opt(name):
    return _named(mgr, 'MagneticMaterialOption', name)


def role(name):
    return _named(mgr, 'MaterialUseRole', name)


print('== suite: seed shape ==')
check('10 use roles seeded', len(SEED_USE_ROLES) == 10,
      extra=str(len(SEED_USE_ROLES)))
check('7 powder definitions (5 real + 2 theoretical)',
      len(SEED_MAGNETIC_POWDERS) == 7
      and sum(1 for p in SEED_MAGNETIC_POWDERS
              if p['is_theoretical']) == 2)
check('31 catalog options across 5 families',
      len(SEED_MATERIAL_OPTIONS) == 31
      and len({o['family'] for o in SEED_MATERIAL_OPTIONS}) == 5,
      extra=str(len(SEED_MATERIAL_OPTIONS)))
check('every option realization level is on the ladder',
      all(o['realization_level'] in
          ('theoretical', 'literature-demonstrated',
           'recipe-seeded', 'made-and-measured')
          for o in SEED_MATERIAL_OPTIONS))

print('== suite: realization gates ==')
g = gates_for(mgr, opt('opt-magnetite-powder'))
check('magnetite: cited AND recipe-seeded -> costing allowed, '
      'business refused (not made-and-measured)',
      g['buyableCited'] and g['recipeSeeded']
      and g['costing']['allowed'] and not g['business']['allowed'])
g = gates_for(mgr, opt('opt-fe16n2'))
check('theoretical Fe16N2: simulation OPEN with watermark, costing '
      'refused with the sourcing ask',
      g['simulation']['allowed']
      and 'theoretical' in g['simulation']['watermark']
      and not g['costing']['allowed']
      and 'suggestion' in g['costing'])
g = gates_for(mgr, opt('opt-copper-magnet-wire'))
check('commodity magnet wire: made-and-measured -> ALL gates open',
      g['simulation']['allowed'] and g['costing']['allowed']
      and g['business']['allowed'])
g = gates_for(mgr, opt('opt-srfe12o19'))
check('hexaferrite: recipe-seeded (mag-1) -> costable even though '
      'buy-side is quote-only... ',
      g['recipeSeeded'] and g['costing']['allowed'])
check('...and buyableCited True via the GBP quote-gap row (a '
      'citation EXISTS; normalization refuses separately)',
      g['buyableCited'])

print('== suite: derived role viability (the taxonomy enforces '
      'physics) ==')
v = role_viability(mgr, opt('opt-magnetite-powder'),
                   role('torque-magnet'))
check('magnetite FAILS torque-magnet (soft — H_c 8 < 100)',
      v['verdict'] == 'unviable' and v['via'] == 'derived')
v = role_viability(mgr, opt('opt-srfe12o19'), role('torque-magnet'))
check('SrFe12O19 passes torque-magnet (B_r 0.40, H_c 250)',
      v['verdict'] == 'viable')
v = role_viability(mgr, opt('opt-alnico'), role('torque-magnet'))
check('alnico honestly excluded (H_c 50 fails >=100 — demag risk '
      'knob)', v['verdict'] == 'unviable')
v = role_viability(mgr, opt('opt-aligned-magnetite-chains'),
                   role('torque-magnet'))
check('aligned chains fail torque-magnet BY DESIGN (weak ceiling)',
      v['verdict'] == 'unviable')
v = role_viability(mgr, opt('opt-hexaferrite-pm-ring'),
                   role('magnetic-bearing'))
check('PM ring viable for bearing WITH Earnshaw note traveling',
      v['verdict'] == 'viable' and 'EARNSHAW' in v['honestyNote'])
v = role_viability(mgr, opt('opt-ferrite-cnt-composite'),
                   role('electric-conductor-power'))
check('ferrite-CNT fails POWER conduction (227 S/m << 1e7)',
      v['verdict'] == 'unviable')
v = role_viability(mgr, opt('opt-ferrite-cnt-composite'),
                   role('electric-conductor-signal'))
check('...but passes SIGNAL grade, copper-gap note attached',
      v['verdict'] == 'viable' and 'copper' in
      v['honestyNote'].lower() or 'power' in v['honestyNote'].lower())
v = role_viability(mgr, opt('opt-maghemite'),
                   role('magnetic-conductor'))
check('maghemite = UNASSESSED (missing mu/H_c) + the measurement '
      'ask — never assumed viable',
      v['verdict'] == 'unassessed' and 'suggestion' in v)
v = role_viability(mgr, opt('opt-plain-geopolymer'),
                   role('structural-containment'))
check('plain geopolymer fails structural predicate (4 < 5 MPa '
      'literature order) — honesty over optimism',
      v['verdict'] == 'unviable')
v = role_viability(mgr, opt('opt-solgel-ferrite'),
                   role('mortar-joint'))
check('sol-gel-ferrite mortar = flux-continuity mechanism tagged',
      v['verdict'] == 'viable'
      and v.get('mechanism') == 'flux-continuity')
v = role_viability(mgr, opt('opt-plain-solgel-mortar'),
                   role('mortar-joint'))
check('plain sol-gel mortar = deliberate-gap mechanism tagged',
      v['verdict'] == 'viable'
      and v.get('mechanism') == 'deliberate-gap')
v = role_viability(mgr, opt('opt-geopolymer-ferrite'),
                   role('mortar-joint'))
check('geopolymer-ferrite is NOT a mortar (form axis excludes it)',
      v['verdict'] == 'unviable' and v['via'] == 'form')

print('== suite: casual search (role+form -> viable list with '
      'numbers) ==')
out = viability_matrix(mgr, 'magnetic-conductor', 'mortar')
viable = [r for r in out['rows'] if r['verdict'] == 'viable']
check('"mortar, magnetic-conductor" -> sol-gel-ferrite leads the '
      'viable list with deciding numbers',
      out['ok'] and any(r['option'] == 'opt-solgel-ferrite'
                        for r in viable)
      and all(r['deciding'] for r in viable))
out = viability_matrix(mgr, 'torque-magnet')
check('torque-magnet matrix counts add up and reference rows are '
      'flagged',
      out['ok'] and out['counts']['viable'] >= 5
      and any(r['referenceOnly'] and r['option'] == 'opt-ndfeb'
              for r in out['rows']))

print('== suite: vol<->wt (the ONE conversion) ==')
wt = wt_from_vol(0.35, 5200.0, 2000.0)
check('35 vol% magnetite in geopolymer = 58.3 wt% (the mag-1 '
      'number)', abs(wt - 0.5834) < 0.001, extra=str(wt))
check('round-trips', abs(vol_from_wt(wt, 5200.0, 2000.0)
                         - 0.35) < 0.001)
check('refuses without densities (never guesses)',
      wt_from_vol(0.35, None, 2000.0) is None
      and vol_from_wt(0.5, 5200.0, 0) is None)

print('== suite: composite predictors vs the msci FEM datum ==')
mg = maxwell_garnett(1.0, 800.0, 0.35)
check('MG @35vol% mu_i=800 lands ~2.07 (FEM said 2.196 — analytic '
      'within ~6%, the confirmation-run pattern)',
      abs(mg - 2.0707) < 0.01, extra=str(mg))
br = bruggeman(1.0, 800.0, 0.35)
check('Bruggeman exceeds MG past its 1/3 percolation threshold '
      '(stated, not hidden)', br > mg, extra=str(br))
out = composite_predict(mgr, 'magnetite-powder-def', 'geopolymer',
                        0.35)
check('magnetite/geopolymer 35vol predicts + COSTS (~6.1/kg '
      'matches the mag-1 cascade)',
      out['ok'] and out['costing']['allowed']
      and 5.5 < out['costing']['usdPerKg'] < 6.5
      and abs(out['wtFraction'] - 0.5834) < 0.001,
      extra=str(out.get('costing')))
check('...with the FEM confirmation-run pointer riding along',
      out['confirmationRun']['engine']
      == 'fem-effective-permeability')
out = composite_predict(mgr, 'fe16n2-theoretical', 'geopolymer',
                        0.35)
check('theoretical powder: predicts WITH watermark, costing '
      'refused naming the hunt',
      out['ok'] and 'THEORETICAL' in out['watermark']
      and not out['costing']['allowed']
      and 'suggestion' in out['costing'])
out = composite_predict(mgr, 'magnetite-powder-def', 'granite', 0.3)
check('unknown matrix refused', not out['ok'])
out = composite_predict(mgr, 'magnetite-powder-def', 'wax', 0.30)
check('wax matrix: 30vol -> ~70.6 wt% (heavy loading visible)',
      out['ok'] and abs(out['wtFraction'] - 0.7056) < 0.001,
      extra=str(out.get('wtFraction')))

print('== suite: laddered answer (best per rung, watermarked) ==')
out = laddered_answer(mgr, 'torque-magnet')
levels = {r['level']: r for r in out['ladder']}
check('torque-magnet ladder answers with multiple rungs',
      out['ok'] and len(out['ladder']) >= 3)
check('recipe-seeded rung = SrFe12O19 (the build TODAY)',
      levels.get('recipe-seeded', {}).get('option')
      == 'opt-srfe12o19')
check('theoretical rung = Fe16N2 (the research target) — one '
      'report, both horizons',
      levels.get('theoretical', {}).get('option') == 'opt-fe16n2')
check('literature rung is NdFeB and it is FLAGGED reference-only '
      '(parity benchmark, not our route)',
      levels.get('literature-demonstrated', {}).get('option')
      == 'opt-ndfeb'
      and levels['literature-demonstrated']['referenceOnly'])

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
