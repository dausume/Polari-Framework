"""
Self-test for the reaction-network schema: species inventory
(Q-species as dynamic motifs, competing framework families), rules as
graph-rewrite data with declared hypothesis status, and the
kinetics-free refusal (invariant I5).

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.reaction_network_selftest
"""

import sys

from pspp.reaction_network_basis import (
    REACTION_STAGES, SEED_CHEMICAL_SPECIES, SEED_REACTION_RULES,
    rule_rate, validate_rule,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_species():
    print('[species inventory]')
    names = [s['name'] for s in SEED_CHEMICAL_SPECIES]
    check('names unique', len(set(names)) == len(names))
    check('Q0..Q4 present as motifs with qn set',
          all(f'siloxonate-q{n}' in names for n in range(5)) and all(
              s['qn'] == n for n, s in enumerate(
                  s for s in SEED_CHEMICAL_SPECIES
                  if s['name'].startswith('siloxonate-q'))))
    check('competing framework families coexist (F4 — never one '
          'framework)', all(f'framework-{f}' in names for f in
                            ('nepheline', 'phillipsite', 'albite',
                             'leucite', 'kalsilite', 'amorphous-gel')))
    check('Na and K are distinct explicit species (F11)',
          'sodium-ion' in names and 'potassium-ion' in names)


def test_rules():
    print('[reaction rules]')
    check('the reusable common stages exist (F7)',
          REACTION_STAGES[:5] == (
              'activation', 'dissolution', 'ortho-sialate-generation',
              'branch-selection', 'framework-growth'))
    for rule in SEED_REACTION_RULES:
        check(f"seed rule {rule['name']!r} validates",
              validate_rule(rule)['ok'])
    hydrolysis = next(r for r in SEED_REACTION_RULES
                      if r['name'] == 'siloxane-hydrolysis')
    check('hydrolysis is book-supported with the p.84/p.90 citation',
          hydrolysis['hypothesis_status'] == 'book-supported'
          and '5.3.1' in hydrolysis['source_reference'])
    condensation = next(r for r in SEED_REACTION_RULES
                        if r['name'] == 'sialate-condensation')
    check('condensation is a PROPOSAL naming its Loewenstein-'
          'conflicting rival',
          condensation['hypothesis_status'] == 'mechanistic-proposal'
          and 'al-o-al' in condensation['competing_with_json'])

    ghost = dict(condensation, reactants_json='["unobtainium"]')
    check('rule naming unknown species refused',
          validate_rule(ghost)['ok'] is False)
    badStage = dict(condensation, stage='magic')
    check('unknown stage refused', validate_rule(badStage)['ok'] is False)
    noHyp = dict(condensation, hypothesis_status='')
    check('undeclared hypothesis status refused (competing '
          'hypotheses, never truth)',
          validate_rule(noHyp)['ok'] is False)


def test_two_phase_branch():
    print('[pp.184-187: transport-selected branching (Fig 8.21)]')
    rules = {r['name']: r for r in SEED_REACTION_RULES}
    check('both phases share the ortho-sialate generation stage (F7)',
          rules['ortho-sialate-formation']['stage']
          == 'ortho-sialate-generation')
    albite = rules['albite-pathway-condensation']
    nepheline = rules['nepheline-pathway-condensation']
    check('Phase 1 is surface-only (needs waterglass siloxonates)',
          albite['site_constraint'] == 'surface-only'
          and 'di-siloxonate' in albite['reactants_json'])
    check('Phase 2 is interior-only (ions penetrate, siloxonates '
          'cannot)', nepheline['site_constraint'] == 'interior-only')
    check('the branches grow DIFFERENT frameworks (albite vs '
          'nepheline — never one framework, F4)',
          'framework-albite' in
          rules['albite-framework-polycondensation']['products_json']
          and 'framework-nepheline' in
          rules['nepheline-framework-polycondensation']
          ['products_json'])
    check('both condensations regenerate NaOH (alkali reacts again)',
          all('sodium-hydroxide' in r['products_json']
              for r in (albite, nepheline)))
    badSite = dict(albite, site_constraint='underwater')
    check('unknown site constraint refused',
          validate_rule(badSite)['ok'] is False)


def test_kinetics_refusal():
    print('[invariant I5: no invented kinetics]')
    for rule in SEED_REACTION_RULES:
        r = rule_rate(rule)
        check(f"rate query on {rule['name']!r} refuses (no "
              'calibration)', r['ok'] is False
              and 'kinetics' in r['refusal'])


def main():
    test_species()
    test_rules()
    test_two_phase_branch()
    test_kinetics_refusal()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
