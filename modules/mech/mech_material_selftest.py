"""
@module mech.mech_material_selftest

mxc-1 material selftests. Everything asserted here is HAND-COMPUTED
first, from the registry files in custom/registry/ and the property
table in custom/registry/material_properties.py:

  registry: 51 materials in the econ-core collab registry
    (24 polari_preferred / 9 polari_acceptable / 18 legacy_harmful)
    + 2 wood rows mech added (birch_plywood, mdf; both
    polari_acceptable, formaldehyde glue IARC 1) = 53 options,
    24 / 11 / 18. 35 part roles -> 35 preferences, unique slugs.
  Group 1 among polari_preferred: NONE. The one row whose feedstock
    note mentions IARC 1 and is still preferred is anodise — its
    sulfuric acid is tagged 'none' because strong-inorganic-acid
    MISTS are the IARC 1 agent (an occupational control, not in the
    part); the note says so.
  neoprene_cr: legacy_harmful, worst feedstock '1' (1,3-butadiene),
    replaced_by tpu_mdi, tpc_et, cm, epdm_peroxide.
  deep_groove_ball_bearing: default 'steel_carbon (52100) +
    steel_carbon shield (ZZ)' -> default_ids [steel_carbon] (dedup),
    legacy [nbr_hnbr] (the 2RS seal).
  uhmwpe density 940 kg/m3 'textbook-prior'; UHMWPE-on-aluminium
    plan knob 0.1-0.2 -> headline friction_coefficient 0.15; ball
    slide 0.01-0.03 -> steel_carbon@rolling mu_kinetic 0.02;
    wood-on-wood 0.25-0.5 -> 0.35; PTFE 0.04-0.1 -> 0.05.
  low_friction_slider_pad (the drawer slide's nearest registry key:
    the printed UHMWPE runner of D-mxc-5) plays sliding +
    static-structural -> needs friction_coefficient + tensile_mpa;
    uhmwpe states both -> viable. profile_rail_carriage (the steel
    slide) -> steel_carbon viable the same way.
  deep_groove_ball_bearing plays moving + colliding -> needs
    fatigue_class, tensile_mpa, hardness_hv >= 100: steel_carbon
    (ductile-endurance-limit, 440, 130 HV) viable; the aem seal
    alternative states none of them -> unassessed, not a pass.
  magnet -> torque-magnet-active: ndfeb b_r 1.2 T >= 0.05,
    h_c 900 kA/m >= 100 -> viable.

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m
mech.mech_material_selftest
"""

import contextlib
import io
import json
import types

from composition.custom import data_refs
from composition.custom.data_refs import material_prop
from composition.custom.part_roles import ROLE_REQUIREMENTS
from mech.custom.material_registry import (
    PREFERENCE_ROLE_REFS, legacy_comparison, options_from_registry,
    preference, preference_check, preferences_from_registry,
)
from mech.mech_material_basis import (
    IARC_GROUPS, MATERIAL_CLASSES, REALIZATION_LEVELS, STATUSES,
    MechMaterialOption, MechMaterialPreference,
)
from mech.mech_material_seed import (
    SEED_MECH_MATERIAL_OPTIONS, SEED_MECH_MATERIAL_PREFERENCES,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _table(seed):
    return {s['name']: types.SimpleNamespace(**s) for s in seed}


def _mgr(magnetic_rows=()):
    m = types.SimpleNamespace(objectTables={
        'MechMaterialOption': _table(SEED_MECH_MATERIAL_OPTIONS),
        'MechMaterialPreference': _table(SEED_MECH_MATERIAL_PREFERENCES),
        'MagneticMaterialOption': _table(magnetic_rows),
    })
    m.objectTypingDict = {k: object() for k in m.objectTables}
    return m


mgr = _mgr()
OPTS = {o['name']: o for o in SEED_MECH_MATERIAL_OPTIONS}
PREFS = {p['name']: p for p in SEED_MECH_MATERIAL_PREFERENCES}
J = json.loads

print('== suite: the registry is seeded as rows ==')
check('53 options seeded = 51 collab registry rows + 2 mech wood rows',
      len(SEED_MECH_MATERIAL_OPTIONS) == 53
      and sum(o['source'] == 'collab-mech-parts'
              for o in SEED_MECH_MATERIAL_OPTIONS) == 51
      and sorted(o['name'] for o in SEED_MECH_MATERIAL_OPTIONS
                 if o['source'] == 'mech-mxc-1')
      == ['birch_plywood', 'mdf'],
      extra=str(len(SEED_MECH_MATERIAL_OPTIONS)))
check('status split 24 preferred / 11 acceptable / 18 legacy (collab '
      '24/9/18 + the two acceptable wood rows)',
      [sum(o['status'] == s for o in SEED_MECH_MATERIAL_OPTIONS)
       for s in STATUSES] == [24, 11, 18])
check('35 preferences seeded, one per registry part role, unique names',
      len(SEED_MECH_MATERIAL_PREFERENCES) == 35
      and len(PREFS) == 35)
check('the seed is what the registry builds (seed == '
      'options_from_registry / preferences_from_registry)',
      options_from_registry() == SEED_MECH_MATERIAL_OPTIONS
      and preferences_from_registry() == SEED_MECH_MATERIAL_PREFERENCES)
check('every option name is unique and every status / class / '
      'confidence is in the vocabulary',
      len(OPTS) == 53
      and all(o['status'] in STATUSES
              and o['material_class'] in MATERIAL_CLASSES
              and o['confidence'] in ('good', 'check')
              and o['realization_level'] in REALIZATION_LEVELS
              for o in SEED_MECH_MATERIAL_OPTIONS))
check("the registry's 'plastic' lands as 'polymer' (uhmwpe, pla), "
      "'wood' is a class of its own",
      OPTS['uhmwpe']['material_class'] == 'polymer'
      and OPTS['pla']['material_class'] == 'polymer'
      and OPTS['birch_plywood']['material_class'] == 'wood')
_all_ids = set()
for p in SEED_MECH_MATERIAL_PREFERENCES:
    for key in ('default_ids_json', 'alternative_ids_json',
                'legacy_ids_json'):
        _all_ids |= set(J(p[key]))
check('every id a preference references is a seeded option',
      _all_ids and _all_ids <= set(OPTS),
      extra=str(sorted(_all_ids - set(OPTS))))
check('every replaced_by id is a seeded option, and none of them is '
      'itself legacy_harmful',
      all(r in OPTS and OPTS[r]['status'] != 'legacy_harmful'
          for o in SEED_MECH_MATERIAL_OPTIONS
          for r in J(o['replaced_by_json'])))
check('every legacy_harmful option names at least one replacement '
      '(except the coatings/additives the registry leaves bare: none)',
      all(J(o['replaced_by_json'])
          for o in SEED_MECH_MATERIAL_OPTIONS
          if o['status'] == 'legacy_harmful'),
      extra=str([o['name'] for o in SEED_MECH_MATERIAL_OPTIONS
                 if o['status'] == 'legacy_harmful'
                 and not J(o['replaced_by_json'])]))
check('every feedstock IARC group is in IARC_GROUPS and '
      'worst_feedstock_iarc is the worst of them (neoprene 1, '
      'uhmwpe 3, pla none, aem check)',
      all(f['iarc'] in IARC_GROUPS
          for o in SEED_MECH_MATERIAL_OPTIONS
          for f in J(o['feedstocks_json']))
      and [OPTS[n]['worst_feedstock_iarc']
           for n in ('neoprene_cr', 'uhmwpe', 'pla', 'aem')]
      == ['1', '3', 'none', 'check'])

print('\n== suite: the IARC discipline ==')
_pref_g1 = [o['name'] for o in SEED_MECH_MATERIAL_OPTIONS
            if o['status'] == 'polari_preferred'
            and any(f['iarc'] == '1' for f in J(o['feedstocks_json']))]
check('no polari_preferred option has a Group-1 IARC feedstock',
      _pref_g1 == [], extra=str(_pref_g1))
_anod = J(OPTS['anodise']['feedstocks_json'])
check("the one preferred row that MENTIONS IARC 1 is anodise: sulfuric "
      "acid tagged 'none' with the note that acid MISTS are the Group-1 "
      "agent (occupational control, not in the part)",
      OPTS['anodise']['status'] == 'polari_preferred'
      and _anod[0]['iarc'] == 'none'
      and 'IARC 1' in _anod[0]['note']
      and 'occupational' in _anod[0]['note'])
check('the wood rows carry their formaldehyde glue as IARC 1 and are '
      'therefore polari_acceptable with confidence=check, not preferred',
      all(OPTS[w]['status'] == 'polari_acceptable'
          and OPTS[w]['worst_feedstock_iarc'] == '1'
          and OPTS[w]['confidence'] == 'check'
          for w in ('birch_plywood', 'mdf')))
check('neoprene is legacy_harmful (chloroprene 2B, butadiene 1) with '
      'replaced_by naming TPU, TPC-ET, CM and EPDM',
      OPTS['neoprene_cr']['status'] == 'legacy_harmful'
      and OPTS['neoprene_cr']['is_reference_only'] is True
      and J(OPTS['neoprene_cr']['replaced_by_json'])
      == ['tpu_mdi', 'tpc_et', 'cm', 'epdm_peroxide'])
check('nitrile (NBR/HNBR) is legacy_harmful on acrylonitrile Group 1 '
      '(the 2024 upgrade) and butadiene Group 1',
      OPTS['nbr_hnbr']['status'] == 'legacy_harmful'
      and sorted(f['iarc'] for f in J(OPTS['nbr_hnbr']['feedstocks_json']))
      == ['1', '1'])
check("AEM is the registry's own 'check' row (methyl acrylate class to "
      "confirm) — confidence travels on the row",
      OPTS['aem']['confidence'] == 'check'
      and sum(o['confidence'] == 'check'
              for o in SEED_MECH_MATERIAL_OPTIONS
              if o['source'] == 'collab-mech-parts') == 1)
check('legacy rows are reference-only, every other row is not',
      all((o['status'] == 'legacy_harmful') == o['is_reference_only']
          for o in SEED_MECH_MATERIAL_OPTIONS))

print('\n== suite: preferences ==')
_b = PREFS['deep_groove_ball_bearing']
check("the bearing's default is steel + ZZ steel shield (no elastomer): "
      "default_ids [steel_carbon], the combination string names ZZ",
      J(_b['default_ids_json']) == ['steel_carbon']
      and 'ZZ' in J(_b['polari_default_json'])[0]
      and 'steel_carbon shield' in J(_b['polari_default_json'])[0])
check("the bearing's legacy list is the NBR 2RS seal; EPDM is NOT an "
      "alternative (swells in grease — the registry note says so)",
      J(_b['legacy_ids_json']) == ['nbr_hnbr']
      and 'epdm_peroxide' not in J(_b['alternative_ids_json'])
      and 'EPDM' in _b['notes'])
check('belts default to MDI polyurethane, inserts to lead-free brass, '
      'the heat-set insert legacy is leaded brass (plan section 7)',
      J(PREFS['timing_belt_body']['default_ids_json']) == ['tpu_mdi']
      and J(PREFS['heat_set_insert']['default_ids_json'])
      == ['brass_lead_free']
      and J(PREFS['heat_set_insert']['legacy_ids_json'])
      == ['brass_leaded'])
check('flattened id lists deduplicate (the bearing names steel_carbon '
      'twice) and keep order (screw: black oxide steel before '
      'stainless)',
      J(PREFS['socket_cap_button_countersunk_set']['default_ids_json'])
      == ['steel_carbon', 'black_oxide', 'stainless_a2_a4'])
check('every preference names ONLY composition roles '
      '(ROLE_REQUIREMENTS keys), and every preference has a mapping',
      all(set(J(p['role_refs_json'])) <= set(ROLE_REQUIREMENTS)
          for p in SEED_MECH_MATERIAL_PREFERENCES)
      and set(PREFERENCE_ROLE_REFS) == set(PREFS))
check('a slide plays sliding + static-structural, a screw '
      'static-structural, a seal sliding (section 9.1 examples)',
      J(PREFS['low_friction_slider_pad']['role_refs_json'])
      == ['sliding', 'static-structural']
      and J(PREFS['socket_cap_button_countersunk_set']['role_refs_json'])
      == ['static-structural']
      and J(PREFS['gasket_seal']['role_refs_json']) == ['sliding'])
check('categories repeat (linear x5, frame_joint x3) so the part slug '
      'is the key',
      sum(p['category'] == 'linear'
          for p in SEED_MECH_MATERIAL_PREFERENCES) == 5
      and sum(p['category'] == 'frame_joint'
              for p in SEED_MECH_MATERIAL_PREFERENCES) == 3)

print('\n== suite: no fourth material identity — composition reads it ==')
check('MechMaterialOption is registered in composition.data_refs.'
      'MATERIAL_PROPERTY_CLASSES AFTER MagneticMaterialOption',
      data_refs.MATERIAL_PROPERTY_CLASSES
      == ('MagneticMaterialOption', 'MechMaterialOption'))
check('the realization ladder is composition\'s (and magnetics agrees)',
      tuple(REALIZATION_LEVELS)
      == tuple(__import__('magnetics.magnet_basis', fromlist=['x'])
               .REALIZATION_LEVELS))
check("material_prop finds UHMWPE's density through composition's "
      "lookup: 940 kg/m3, textbook-prior",
      material_prop(mgr, 'uhmwpe', 'density_kg_m3')
      == (940.0, 'textbook-prior'))
_coll = _mgr(magnetic_rows=[{
    'name': 'uhmwpe', 'properties_json': json.dumps({
        'density_kg_m3': {'value': 1.0, 'unit': 'kg/m3',
                          'provenance': 'collision-test'}})}])
check('a magnetics row of the same name wins — magnetics is searched '
      'FIRST, mech second',
      material_prop(_coll, 'uhmwpe', 'density_kg_m3')
      == (1.0, 'collision-test'))
check('no seeded mech name collides with a seeded magnetics option '
      'name (magnetics names are opt-*)',
      not ({o['name'] for o in SEED_MECH_MATERIAL_OPTIONS}
           & {o['name'] for o in __import__(
               'magnetics.magnet_seed', fromlist=['x'])
              .SEED_MATERIAL_OPTIONS}))
check('a property nobody stated is (None, "") — ppd6 has no row in '
      'the property table at all',
      material_prop(mgr, 'ppd6', 'density_kg_m3') == (None, ''))
check('every properties_json entry carries value / unit / provenance, '
      'and provenance is textbook-prior or plan-knob',
      all(set(e) >= {'value', 'unit', 'provenance'}
          and e['provenance'] in ('textbook-prior', 'plan-knob')
          for o in SEED_MECH_MATERIAL_OPTIONS
          for e in J(o['properties_json']).values()))
_steel = J(OPTS['steel_carbon']['properties_json'])
_uh = J(OPTS['uhmwpe']['properties_json'])
_ply = J(OPTS['birch_plywood']['properties_json'])
_ptfe = J(OPTS['ptfe']['properties_json'])
check("the plan's friction knobs are on the rows: ball slide 0.02 "
      "(steel_carbon@rolling), UHMWPE-on-Al 0.15, wood-on-wood 0.35, "
      "PTFE 0.05 — each tagged plan-knob",
      _steel['friction_json']['value']['steel_carbon@rolling']
      == {'mu_static': 0.03, 'mu_kinetic': 0.02, 'basis': 'plan-knob',
          'note': 'ball slide 0.01-0.03: steel ball in steel raceway'}
      and _uh['friction_json']['value']['al_6063']['mu_kinetic'] == 0.15
      and _uh['friction_json']['value']['al_6063']['basis'] == 'plan-knob'
      and _ply['friction_json']['value']['birch_plywood']['mu_kinetic']
      == 0.35
      and _ptfe['friction_json']['value']['steel_carbon']['mu_kinetic']
      == 0.05)
check('friction_json entries are {mu_static, mu_kinetic, basis} keyed '
      'by a registry id (or id@rolling)',
      all(set(e) >= {'mu_static', 'mu_kinetic', 'basis'}
          and k.split('@')[0] in OPTS
          for o in SEED_MECH_MATERIAL_OPTIONS
          for k, e in J(o['properties_json'])
          .get('friction_json', {}).get('value', {}).items()))
check('the headline friction_coefficient is the mu_kinetic of the '
      'named pair (uhmwpe 0.15 vs al_6063; ptfe 0.05 vs steel)',
      _uh['friction_coefficient']['value'] == 0.15
      and 'al_6063' in _uh['friction_coefficient']['note']
      and _ptfe['friction_coefficient']['value'] == 0.05)
check('6063-T5: 2700 kg/m3, E 68.9 GPa, nu 0.33, yield 145, '
      'tensile 185; 1018: 7850, 200, 0.29, 370, 440, 130 HV',
      [J(OPTS['al_6063']['properties_json'])[k]['value']
       for k in ('density_kg_m3', 'youngs_modulus_gpa', 'poisson_ratio',
                 'yield_mpa', 'tensile_mpa')]
      == [2700.0, 68.9, 0.33, 145.0, 185.0]
      and [_steel[k]['value']
           for k in ('density_kg_m3', 'youngs_modulus_gpa',
                     'poisson_ratio', 'yield_mpa', 'tensile_mpa',
                     'hardness_hv')]
      == [7850.0, 200.0, 0.29, 370.0, 440.0, 130.0])
check('-1 marks a number not held (TPU has no yield point) and '
      'hardness names its scale (TPU Shore A, PLA Shore D, PA66 '
      'Rockwell R, steel HV)',
      J(OPTS['tpu_mdi']['properties_json'])['yield_mpa']['value'] == -1
      and 'hardness_shore_a' in J(OPTS['tpu_mdi']['properties_json'])
      and 'hardness_shore_d' in J(OPTS['pla']['properties_json'])
      and 'hardness_rockwell_r' in J(OPTS['pa66']['properties_json'])
      and 'hardness_hv' in _steel)

print('\n== suite: preference_check runs role_viability ==')
_slide = preference_check(mgr, 'low_friction_slider_pad')
check("'drawer slide' is not a registry key: the refusal names the "
      "nearest (low_friction_slider_pad / profile_rail_carriage)",
      preference(mgr, 'drawer slide')[1]['kind'] == 'no-such-row'
      and not preference_check(mgr, 'drawer slide')['ok']
      and set(preference(mgr, 'drawer slide')[1]['nearest'])
      >= {'low_friction_slider_pad'})
check('the printed-runner slide (low_friction_slider_pad): default '
      'uhmwpe VIABLE — friction_coefficient present for sliding, '
      'tensile_mpa present for static-structural',
      _slide['ok'] and _slide['registered']
      and _slide['ids']['uhmwpe']['tier'] == 'default'
      and _slide['ids']['uhmwpe']['viable'] is True
      and _slide['ids']['uhmwpe']['missing_props'] == []
      and _slide['ids']['uhmwpe']['failed_predicates'] == []
      and {(c['role'], c['property'], c['verdict'])
           for c in _slide['ids']['uhmwpe']['checks']}
      == {('sliding', 'friction_coefficient', 'pass'),
          ('static-structural', 'tensile_mpa', 'pass')},
      extra=str(_slide['ids'].get('uhmwpe')))
check('its alternatives pa11 and peek are viable too; viable_ids lists '
      'all three',
      sorted(_slide['viable_ids']) == ['pa11', 'peek', 'uhmwpe'])
_rail = preference_check(mgr, 'profile_rail_carriage')
check('the steel slide (profile_rail_carriage): steel_carbon and '
      'stainless viable on the same two properties',
      _rail['ids']['steel_carbon']['viable']
      and _rail['ids']['stainless_a2_a4']['viable'])
_bear = preference_check(mgr, 'deep_groove_ball_bearing')
check('bearing (moving + colliding): steel_carbon viable — '
      'fatigue_class ductile-endurance-limit, tensile 440, 130 HV >= 100',
      _bear['ids']['steel_carbon']['viable']
      and _bear['roles'] == ['moving', 'colliding'],
      extra=str(_bear['ids']['steel_carbon']))
check('the AEM seal alternative is UNASSESSED, not viable: it states '
      'no fatigue_class and no hardness_hv',
      _bear['ids']['aem']['verdict'] == 'unassessed'
      and _bear['ids']['aem']['viable'] is False
      and _bear['ids']['aem']['missing_props']
      == ['fatigue_class', 'hardness_hv']
      and 'UNASSESSED' in _bear['note'])
_gear = preference_check(mgr, 'spur_gear')
check('spur gear: steel viable; PA66 unassessed on hardness_hv and '
      'fatigue_class (a polymer states Rockwell R, not HV — no silent '
      'conversion)',
      _gear['ids']['steel_carbon']['viable']
      and _gear['ids']['pa66']['verdict'] == 'unassessed'
      and 'hardness_hv' in _gear['ids']['pa66']['missing_props'])
_mag = preference_check(mgr, 'magnet')
check('magnet (torque-magnet-active): ndfeb viable on b_r 1.2 T and '
      'h_c 900 kA/m',
      _mag['ids']['ndfeb']['viable'])
check('a preference with no roles (cable insulation) checks nothing '
      'and every id is trivially viable',
      preference_check(mgr, 'cable_insulation_tubing')['roles'] == []
      and all(r['viable'] for r in
              preference_check(mgr, 'cable_insulation_tubing')['ids']
              .values()))
_saved = data_refs.MATERIAL_PROPERTY_CLASSES
data_refs.MATERIAL_PROPERTY_CLASSES = ('MagneticMaterialOption',)
_unreg = preference_check(mgr, 'low_friction_slider_pad')
data_refs.MATERIAL_PROPERTY_CLASSES = _saved
check('with mech NOT registered in MATERIAL_PROPERTY_CLASSES every id '
      'reads unassessed and the result says why — the registration '
      'line is load-bearing',
      _unreg['registered'] is False and 'warning' in _unreg
      and _unreg['ids']['uhmwpe']['verdict'] == 'unassessed')

print('\n== suite: legacy_comparison ==')
_seal = legacy_comparison(mgr, 'gasket_seal')
check('gasket/seal: defaults [epdm], legacy neoprene + nitrile + FKM '
      'each with a reason',
      _seal['ok']
      and [d['id'] for d in _seal['defaults']] == ['epdm_peroxide']
      and [l['id'] for l in _seal['legacy']]
      == ['neoprene_cr', 'nbr_hnbr', 'fkm']
      and all(l['reason'] for l in _seal['legacy']))
_nbr = next(l for l in _seal['legacy'] if l['id'] == 'nbr_hnbr')
check("nitrile's reason names acrylonitrile IARC 1 and its "
      "replacements aem, tpu_mdi exist as rows",
      'acrylonitrile' in _nbr['reason'] and 'IARC 1' in _nbr['reason']
      and _nbr['polari_replacements'] == ['aem', 'tpu_mdi'])
_bc = legacy_comparison(mgr, 'deep_groove_ball_bearing')
check("the bearing comparison keeps the combination strings: "
      "'nbr_hnbr (2RS seal)' legacy vs the ZZ default",
      _bc['legacy_combinations'] == ['nbr_hnbr (2RS seal)']
      and 'ZZ' in _bc['default_combinations'][0])
check('an unknown preference refuses honestly',
      not legacy_comparison(mgr, 'nope')['ok'])

print('\n== suite: the row classes construct from the seed ==')
with contextlib.redirect_stdout(io.StringIO()):
    _o = MechMaterialOption(**OPTS['uhmwpe'])
    _l = MechMaterialOption(**OPTS['neoprene_cr'])
    _p = MechMaterialPreference(**PREFS['deep_groove_ball_bearing'])
check('MechMaterialOption(**seed) keeps name / class / status and '
      'recomputes worst_feedstock_iarc from feedstocks_json',
      _o.name == 'uhmwpe' and _o.material_class == 'polymer'
      and _o.status == 'polari_preferred'
      and _o.worst_feedstock_iarc == '3'
      and _l.worst_feedstock_iarc == '1' and _l.is_reference_only)
check('MechMaterialPreference(**seed) keeps the id lists and roles',
      _p.name == 'deep_groove_ball_bearing'
      and J(_p.legacy_ids_json) == ['nbr_hnbr']
      and J(_p.role_refs_json) == ['moving', 'colliding'])
check('the field set mirrors MagneticMaterialOption (name, '
      'display_name, realization_level, item_ref, msci_material_ref, '
      'forms_json, properties_json, role_overrides_json, '
      'is_reference_only, is_prior, provenance_id, notes)',
      {'name', 'display_name', 'realization_level', 'item_ref',
       'msci_material_ref', 'forms_json', 'properties_json',
       'role_overrides_json', 'is_reference_only', 'is_prior',
       'provenance_id', 'notes'} <= set(vars(_o)))

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
