"""
Self-test for pspp-2 material states: canonical resolution (invariant
I1), the implicit-canonical idiom, a two-branch DAG round trip with
branch-scoped claims, and legacy scale rows resolving through
canonical with zero call-site edits.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.selftest_material_states
"""

import sys
from types import SimpleNamespace

from pspp.material_states import (
    CANONICAL_STATE, SEED_PROCESSING_STAGES,
)
from pspp.state_resolution import (
    branch_lineage, material_states, resolve_state,
    scale_definitions_for_state, state_key,
)
from pspp.claims import claims_for_subject

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


def _state(name, material, state, parents='[]', **kw):
    return SimpleNamespace(
        name=name, material_name=material, state_name=state,
        is_canonical=(state == CANONICAL_STATE),
        processing_stage=kw.get('stage', ''),
        thermodynamic_phase=kw.get('phase', ''),
        composition_snapshot_json='{}',
        environmental_snapshot_json='{}',
        parent_state_ids_json=parents,
        producing_execution_id='', validation_status='unvalidated',
        provenance_id='', notes='')


def _manager():
    """A metakaolin geopolymer with the plan's two-branch DAG:
    cured → carbonated | heat-treated. Plus legacy beeswax with a
    pre-pspp scale row (no state_key attribute at all)."""
    gp = 'metakaolin-geopolymer'
    states = {
        f'{gp}#cured-solid': _state(
            f'{gp}#cured-solid', gp, 'cured-solid',
            stage='cured-solid', phase='solid'),
        f'{gp}#carbonated': _state(
            f'{gp}#carbonated', gp, 'carbonated',
            parents=f'["{gp}#cured-solid"]', stage='carbonated',
            phase='solid'),
        f'{gp}#heat-treated': _state(
            f'{gp}#heat-treated', gp, 'heat-treated',
            parents=f'["{gp}#cured-solid"]',
            stage='heat-treated-ceramic', phase='solid'),
    }
    claims = {
        'c1': SimpleNamespace(
            name='c1', subject_state_key=f'{gp}#carbonated',
            property_meaning_name='compressiveStrength', scale_level=0,
            value=32.0, value_json='', units='MPa',
            evidence_method='measured', assumptions_json='[]',
            validity_json='{}', source_execution_id='x1',
            confidence_json='', provenance_id='lab', notes=''),
        'c2': SimpleNamespace(
            name='c2', subject_state_key=f'{gp}#heat-treated',
            property_meaning_name='compressiveStrength', scale_level=0,
            value=18.0, value_json='', units='MPa',
            evidence_method='measured', assumptions_json='[]',
            validity_json='{}', source_execution_id='x2',
            confidence_json='', provenance_id='lab', notes=''),
    }
    scale_rows = {
        # Legacy row: NO state_key attribute at all (pre-pspp shape).
        'beeswax@L0': SimpleNamespace(
            name='beeswax@L0', material_name='beeswax', scale_level=0,
            status='defined'),
        # State-scoped row on the carbonated branch.
        f'{gp}@L0-carbonated': SimpleNamespace(
            name=f'{gp}@L0-carbonated', material_name=gp,
            scale_level=0, status='defined',
            state_key=f'{gp}#carbonated'),
        # Canonical-state row for the same material.
        f'{gp}@L0': SimpleNamespace(
            name=f'{gp}@L0', material_name=gp, scale_level=0,
            status='defined', state_key=''),
    }
    return SimpleNamespace(objectTables={
        'MaterialsScienceMaterial': {
            gp: SimpleNamespace(name=gp),
            'beeswax': SimpleNamespace(name='beeswax'),
        },
        'MaterialState': states,
        'PropertyClaim': claims,
        'MaterialScaleDefinition': scale_rows,
    }), gp


def test_stage_vocabulary():
    print('[processing stages]')
    names = [s['name'] for s in SEED_PROCESSING_STAGES]
    check('geopolymer route seeded raw-powder → carbonated', all(
        n in names for n in ('activated-slurry', 'percolating-gel',
                             'set-gel', 'cured-solid', 'carbonated')))
    check('wax route seeded (pspp-11 mapping target)', all(
        n in names for n in ('wax-solid', 'wax-melt',
                             'wax-superheated')))
    check('names unique', len(set(names)) == len(names))


def test_canonical_resolution():
    print('[canonical resolution — invariant I1]')
    manager, gp = _manager()
    r = resolve_state(manager, 'beeswax')
    check('name-only lookup resolves to the canonical state',
          r['ok'] and r['stateKey'] == 'beeswax#as-defined'
          and r['state']['isCanonical'])
    check('canonical is implicit (virtual) until written',
          r['state']['virtual'] is True)
    check('unknown material refused',
          resolve_state(manager, 'mystery-goo')['ok'] is False)
    missing = resolve_state(manager, gp, '28-day-cure')
    check('unknown state refused listing the available states',
          missing['ok'] is False
          and 'cured-solid' in missing['available'])
    check('state_key helper matches the convention',
          state_key('beeswax') == 'beeswax#as-defined'
          and state_key(gp, 'carbonated') == f'{gp}#carbonated')


def test_dag_and_branch_scoping():
    print('[two-branch DAG + branch-scoped queries]')
    manager, gp = _manager()
    states = material_states(manager, gp)
    check('material lists implicit canonical + 3 explicit states',
          len(states) == 4 and states[0]['virtual'])

    carb = resolve_state(manager, gp, 'carbonated')
    heat = resolve_state(manager, gp, 'heat-treated')
    check('both branches resolve', carb['ok'] and heat['ok'])
    check('branches share the cured parent',
          carb['state']['parents'] == [f'{gp}#cured-solid']
          and heat['state']['parents'] == [f'{gp}#cured-solid'])
    check('lineage walks branch → parent',
          branch_lineage(manager, f'{gp}#carbonated')
          == [f'{gp}#carbonated', f'{gp}#cured-solid'])

    carbClaims = claims_for_subject(manager, f'{gp}#carbonated')
    heatClaims = claims_for_subject(manager, f'{gp}#heat-treated')
    check('property query returns ONLY its branch (32 vs 18 MPa '
          'never mix)',
          [c['value'] for c in carbClaims] == [32.0]
          and [c['value'] for c in heatClaims] == [18.0])


def test_legacy_scale_rows():
    print('[legacy scale rows resolve through canonical]')
    manager, gp = _manager()
    legacy = scale_definitions_for_state(manager, 'beeswax')
    check('pre-pspp row (no state_key attribute) belongs to canonical',
          [r.name for r in legacy] == ['beeswax@L0'])
    canon = scale_definitions_for_state(manager, gp)
    check("canonical query sees only ''-keyed rows, not branch rows",
          [r.name for r in canon] == [f'{gp}@L0'])
    branch = scale_definitions_for_state(manager, gp, 'carbonated')
    check('branch query sees only its own rows',
          [r.name for r in branch] == [f'{gp}@L0-carbonated'])


def main():
    test_stage_vocabulary()
    test_canonical_resolution()
    test_dag_and_branch_scoping()
    test_legacy_scale_rows()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
