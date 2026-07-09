"""
Selftest — biomine-1: bioextraction yield, refinement pathways, and
nutrient-recovery transfer across the specialized variants.

Run from polari-framework/:
    python3 -m biomining.selftest_biomining

Covers: extraction scales with agent biomass, selectivity, and days;
supply bounds the yield (can't pull more than is available) + flags an
over-provisioned culture; the cap bounds it further; product mass =
element × yield; iron→ferrite and carbon→CNT pathways resolve to REAL
materialsScience material rows; steel/phosphate pathways honestly report
no material row; nutrient-recovery transfer reports the recovered nutrient
+ its supplement target and flags uncapped parent depletion; refusals.
"""

from types import SimpleNamespace

from biomining.biomining_analysis import (
    extraction_yield, recovery_transfer, refinement_pathway,
)
from biomining.biomining_seed import (
    SEED_BIOEXTRACTION_AGENTS, SEED_BIOMINERAL_PRODUCTS,
    SEED_BIOMINE_SYSTEMS,
)
from biomining.optical_seed import (
    SEED_OPTICAL_AGENTS, SEED_OPTICAL_BIOMINE_SYSTEMS,
    SEED_OPTICAL_PRODUCTS,
)
from materialsScience.dielectric_optics_seed import (
    SEED_DIELECTRIC_MATERIALS, SEED_DIELECTRIC_PROPERTY_MEANINGS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


# Stand-in for the real materialsScience rows the products link to
# (ferrite + CNT for biomine-1; the dielectric rows for the optical set).
MATERIALS = ([{'name': 'ferrite'}, {'name': 'carbon-nanotube'}]
             + SEED_DIELECTRIC_MATERIALS)


def _mgr(systems=None):
    return SimpleNamespace(objectTables={
        'BioextractionAgent': _rows(
            SEED_BIOEXTRACTION_AGENTS + SEED_OPTICAL_AGENTS),
        'BiomineralProduct': _rows(
            SEED_BIOMINERAL_PRODUCTS + SEED_OPTICAL_PRODUCTS),
        'BiomineSystemDefinition': _rows(
            systems if systems is not None
            else SEED_BIOMINE_SYSTEMS + SEED_OPTICAL_BIOMINE_SYSTEMS),
        'MaterialsScienceMaterial': _rows(MATERIALS),
    })


if __name__ == '__main__':
    manager = _mgr()

    print('iron → ferrite extraction')
    y = extraction_yield(manager, 'iron-ferrite-biomine', days=30.0)
    check('yield ok + targets Fe', y['ok'] and y['targetElement'] == 'Fe')
    # magnetotactic 30×20×0.9=540 + iron-ox 45×15×0.8=540 -> 1080 mg/day
    check('potential = Σ uptake×biomass×selectivity (~1080)',
          abs(y['potentialUptakeMgPerDay'] - 1080.0) < 1.0,
          extra=str(y['potentialUptakeMgPerDay']))
    check('bounded by feedstock supply (1500) — not supply-limited here',
          y['effectiveExtractionMgPerDay'] == 1080.0)
    check('refined ferrite = element × 1.38 yield',
          abs(y['refinedProductMgPerDay'] - 1080.0 * 1.38) < 1.0)
    check('30-day element recovered = 30× daily',
          abs(y['elementRecoveredMg']
              - y['effectiveExtractionMgPerDay'] * 30) < 1.0)

    print('supply + cap bounds')
    low_supply = extraction_yield(manager, 'iron-ferrite-biomine',
                                  days=30.0, supply_override=500.0)
    check('scarce supply bounds extraction + flags over-provisioning',
          low_supply['effectiveExtractionMgPerDay'] == 500.0
          and 'over-provisioned' in (low_supply['riskFactor'] or ''))
    capped = _mgr(systems=[dict(SEED_BIOMINE_SYSTEMS[0],
                                extraction_cap_mg_per_day=300.0)])
    cy = extraction_yield(capped, 'iron-ferrite-biomine', days=30.0)
    check('extraction cap bounds the draw',
          cy['effectiveExtractionMgPerDay'] == 300.0)

    print('refinement pathways link to real materials')
    fp = refinement_pathway(manager, 'ferrite-magnet-feedstock')
    check('iron pathway resolves to the ferrite material',
          fp['ok'] and fp['materialResolved']
          and fp['materialRef'] == 'ferrite' and len(fp['steps']) >= 4)
    cp = refinement_pathway(manager, 'cnt-carbon-feedstock')
    check('carbon pathway resolves to the carbon-nanotube material',
          cp['materialResolved']
          and cp['materialRef'] == 'carbon-nanotube')
    sp = refinement_pathway(manager, 'steel-feedstock')
    check('steel pathway honestly reports no material row',
          not sp['materialResolved'] and sp['materialRef'] == '')

    print('nutrient recovery + transfer to a lacking system')
    t = recovery_transfer(manager, 'phosphate-recovery-biomine',
                          days=30.0, supply_override=600.0)
    check('recovery transfer ok + names the nutrient (P)',
          t['ok'] and t['nutrientElement'] == 'P')
    # PAO 25×25×0.85=531 potential, cap 300 -> effective 300
    check('capped recovery <= cap (protects the parent)',
          t['recoveredMgPerDay'] <= 300.0)
    check('can supplement the target lacking system',
          t['canSupplement']
          and 'household-hydroponic-reservoir'
          in t['supplementTargetSystem'])
    # Uncapped recovery drawing beyond surplus -> flagged.
    uncapped = _mgr(systems=[dict(SEED_BIOMINE_SYSTEMS[3],
                                  extraction_cap_mg_per_day=0.0)])
    ut = recovery_transfer(uncapped, 'phosphate-recovery-biomine',
                           days=30.0, supply_override=100.0)
    check('uncapped recovery beyond surplus flags parent depletion',
          'cap the extraction' in (ut['riskFactor'] or ''))
    check('non-recovery variant refuses transfer',
          not recovery_transfer(manager,
                                'iron-ferrite-biomine').get('ok'))

    print('optical-dielectric variants (fully bio-derivable)')
    # Every optical product's material_ref must resolve to a seeded
    # dielectric material.
    dielectric_names = {m['name'] for m in SEED_DIELECTRIC_MATERIALS}
    refs = {p['material_ref'] for p in SEED_OPTICAL_PRODUCTS}
    check('every optical product links a real dielectric material',
          refs <= dielectric_names,
          extra=str(sorted(refs - dielectric_names)))
    # KDP electro-optic chain: K + phosphate -> KDP crystal.
    kdp = extraction_yield(manager, 'kdp-electro-optic-biomine',
                           days=30.0)
    check('KDP biomine yields crystal + links kdp-electro-optic',
          kdp['ok'] and kdp['refinedProductMgPerDay'] > 0
          and kdp['product'] == 'kdp-crystal')
    kfp = refinement_pathway(manager, 'kdp-crystal')
    check('KDP pathway resolves to the kdp-electro-optic material',
          kfp['materialResolved']
          and kfp['materialRef'] == 'kdp-electro-optic')
    # Rochelle salt: wine tartar + potash + salt (fully community-common).
    rs = refinement_pathway(manager, 'rochelle-salt-crystal')
    check('Rochelle salt links rochelle-salt material + names solution '
          'growth',
          rs['materialResolved']
          and any('solution' in s for s in rs['steps']))
    # Bio-silica -> fused silica.
    fs = refinement_pathway(manager, 'fused-silica-optic')
    check('fused-silica links bio-fused-silica material',
          fs['materialResolved']
          and fs['materialRef'] == 'bio-fused-silica')
    # ZnO high-index coating partner.
    zn = refinement_pathway(manager, 'zinc-oxide-coating')
    check('ZnO coating links bio-zinc-oxide material',
          zn['materialResolved'] and zn['materialRef'] == 'bio-zinc-oxide')
    # All optical variants carry the optical-dielectric variant tag.
    check('all optical systems are the optical-dielectric variant',
          all(s['variant'] == 'optical-dielectric'
              for s in SEED_OPTICAL_BIOMINE_SYSTEMS))
    # Dielectric property vocabulary present.
    meaning_names = {m['name'] for m in SEED_DIELECTRIC_PROPERTY_MEANINGS}
    check('dielectric property meanings defined (permittivity/EO/index/'
          'loss/piezo)',
          {'relativePermittivity', 'electroOpticCoefficient',
           'refractiveIndex', 'opticalLoss',
           'piezoelectricCoefficient'} <= meaning_names)

    print('honest refusals')
    check('unknown system refuses',
          not extraction_yield(manager, 'nope').get('ok'))
    no_agents = _mgr(systems=[dict(SEED_BIOMINE_SYSTEMS[0],
                                   agent_stock_json='{}')])
    check('system with no agents refuses with the knob',
          not extraction_yield(no_agents,
                               'iron-ferrite-biomine').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
