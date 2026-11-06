"""
@module mech.mech_catalog_selftest

mxc-1 selftests. Everything asserted here is HAND-COMPUTED first, from
the upstream tables kept verbatim under custom/upstream/:

  ISO 4762 (FsData/iso4762def.csv, sections ISO4762length + ISO4762range)
    nominal length series: 2.5 3 4 5 6 8 10 12 14 16 20 25 30 35 40 45
      50 55 60 65 70 75 80 100 ...
    M2 range 3..20  -> 3 4 5 6 8 10 12 14 16 20              = 10 lengths
    M8 range 10..80 -> 10 12 14 16 20 25 30 35 40 45 50 55 60 65 70 75 80
                                                              = 17 lengths
    M2.5 4..25 = 10, M3 5..30 = 10, M4 6..40 = 11, M5 8..50 = 12,
    M6 8..60 = 14   -> 10+10+10+11+12+14+17 = 84 variants
    M5 row: P 0.8, b 22, dk_max 8.5, k 5, s_mean 4.06 (ISO 4762 s = 4)
  NopSCADlib extrusions.scad
    E2020 = W 20, H 20, d1 -4.2, cw 6, cwi 12, t 2  -> 4 slots, slot-B6/20
    E2040 = W 20, H 40                -> 1x2 cells -> 2*(1+2) = 6 slots
    E3030 cw 8 -> slot-B8/30 ; E4040 cw 10 -> slot-B10/40
    centre bore 4.2 = 5 - 0.8 -> tap M5
  NopSCADlib nuts.scad
    M5_sliding_t_nut: width 6, thickness 3.7, total height 4.7 -> rides
      slot-B6/20, thread M5x0.8 female, engagement 4.7
    M6_sliding_t_nut: width 8 -> slot-B8/30 (refused in a B6/20 slot)
  gridfinity-rebuilt standard.scad
    grid 42, base top 41.5 (gap 0.5), BASE_HEIGHT 7 (the height unit)
    2x2x6 bin: 2*42 - 0.5 = 83.5 square, 6*7 = 42 high; 4 bases x 4
      magnet sockets (6.5 x 2) = 16; magnet at 21 - 8 = 13 from centre
  engagement knobs: 1.0 d steel, 2.0 d aluminium, 2.5 d plastic
    M5 in 4.7 mm steel: 4.7 < 5.0 -> refused by the knob (advisory)
    M5 tapped 10 mm into aluminium: 10 >= 10 -> ok ; 8 mm -> refused

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m
mech.mech_catalog_selftest
"""

import hashlib
import json
import os
import types

from mech.custom.compatibility import (
    ENGAGEMENT_FACTORS, ROLE_PAIRS, check_pairing, features_compatible,
    pairings_for, thread_engagement,
)
from mech.mech_catalog_basis import (
    BASES, CATEGORIES, FEATURE_KINDS, FEATURE_ROLES,
)
from mech.mech_catalog_seed import (
    SEED_DIMENSION_SOURCES, SEED_FEATURES, SEED_PART_FAMILIES,
    SEED_PART_VARIANTS,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []
MECH_DIR = os.path.dirname(os.path.abspath(__file__))


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _mgr():
    def table(seed):
        return {s['name']: types.SimpleNamespace(**s) for s in seed}
    return types.SimpleNamespace(objectTables={
        'DimensionSource': table(SEED_DIMENSION_SOURCES),
        'MechPartFamily': table(SEED_PART_FAMILIES),
        'MechPartVariant': table(SEED_PART_VARIANTS),
        'MechFeature': table(SEED_FEATURES),
    })


mgr = _mgr()
T = mgr.objectTables
FAM, VAR, FEAT, SRC = (T['MechPartFamily'], T['MechPartVariant'],
                       T['MechFeature'], T['DimensionSource'])


def J(row, field):
    return json.loads(getattr(row, field))


def variants_of(fam):
    return [v for v in VAR.values() if v.family_ref == fam]


def feats_of(vname):
    return [FEAT[n] for n in J(VAR[vname], 'interfaces_json')]


print('== suite: what was seeded (counts stated, not assumed) ==')
check('21 dimension sources, 25 families, 401 variants, 1277 features',
      (len(SRC), len(FAM), len(VAR), len(FEAT)) == (21, 25, 401, 1277),
      extra=str((len(SRC), len(FAM), len(VAR), len(FEAT))))
CONTRACT = ['iso4762', 'iso7380-1', 'iso10642', 'iso4026', 'iso4032',
            'iso4035', 'iso7089', 'iso7093', 'din508', 'tnut-sliding',
            'tnut-hammer', 'extrusion', 'bracket-inner', 'bracket-corner',
            'bearing-ball', 'lm-bushing', 'rail-mgn', 'rod', 'leadscrew-tr8',
            'belt-gt2', 'pulley-gt2', 'gridfinity-bin', 'gridfinity-baseplate',
            'gridfinity-lid', 'drawer-slide']
check('every family of the naming contract exists, and nothing else',
      sorted(FAM) == sorted(CONTRACT), extra=str(sorted(set(FAM) ^ set(CONTRACT))))
CONTRACT_VARIANTS = ['iso4762-M5x10', 'iso4032-M5', 'extrusion-2020-L300',
                     'tnut-sliding-slot6-M5', 'bearing-ball-608',
                     'rail-mgn-9H-L300', 'gridfinity-bin-2x2x6',
                     'gridfinity-baseplate-2x2', 'drawer-slide-L300']
check('the contract\'s example variant names all resolve',
      all(v in VAR for v in CONTRACT_VARIANTS),
      extra=str([v for v in CONTRACT_VARIANTS if v not in VAR]))
check('vocabularies hold: every family category, feature kind, role and '
      'basis is in catalog._shared',
      all(f.category in CATEGORIES for f in FAM.values())
      and all(f.kind in FEATURE_KINDS and f.role in FEATURE_ROLES
              and f.basis in BASES for f in FEAT.values()))

print('== suite: ISO 4762 against the WB range table (hand-counted) ==')
m2 = sorted(v.length_mm for v in variants_of('iso4762') if v.size_key == 'M2')
m8 = sorted(v.length_mm for v in variants_of('iso4762') if v.size_key == 'M8')
check('M2: lengths 3..20 of the series = 3 4 5 6 8 10 12 14 16 20 (10)',
      m2 == [3, 4, 5, 6, 8, 10, 12, 14, 16, 20], extra=str(m2))
check('M8: lengths 10..80 of the series = 17 (10 12 14 16 20 25 ... 80)',
      m8 == [10, 12, 14, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80],
      extra=str(m8))
check('ISO 4762 variants total 84 = 10+10+10+11+12+14+17 (M2 M2.5 M3 M4 M5 M6 M8)',
      len(variants_of('iso4762')) == 84, extra=str(len(variants_of('iso4762'))))
check('M2-M8 only: no (M3.5), nothing above M8, no variant outside its range',
      {v.size_key for v in variants_of('iso4762')}
      == {'M2', 'M2.5', 'M3', 'M4', 'M5', 'M6', 'M8'}
      and all(J(FAM['iso4762'], 'length_rule_json')['per_size'][v.size_key][0]
              <= v.length_mm
              <= J(FAM['iso4762'], 'length_rule_json')['per_size'][v.size_key][1]
              for v in variants_of('iso4762')))
d5 = J(VAR['iso4762-M5x10'], 'dims_json')
check('M5 head: dk 8.5, k 5, s 4 (s_mean 4.06), P 0.8, b 22 per ISO 4762',
      d5['dk_max'] == 8.5 and d5['k'] == 5 and abs(d5['s_mean'] - 4) < 0.1
      and d5['P'] == 0.8 and d5['b'] == 22, extra=str(d5))
th = FEAT['iso4762-M5x10:thread']
check('iso4762-M5x10 exposes thread M5x0.8 male, 10 mm of it (L 10 < b 22), '
      'along -z from the head seat',
      th.key == 'M5x0.8' and th.role == 'male' and th.extent_mm == 10
      and J(th, 'axis_json') == [0, 0, -1]
      and FEAT['iso4762-M5x10:head-seat'].role == 'plane')
th50 = FEAT['iso4762-M5x50:thread']
check('iso4762-M5x50 has only b = 22 of thread (partial), said in the axis value',
      th50.extent_mm == 22 and J(VAR['iso4762-M5x50'], 'axis_values_json')['thread_extent'] == 'partial')
check('set screws (ISO 4026) have no head seat; nuts offer m as engagement '
      '(ISO 4032 M5 m = 4.7, s 8)',
      len(feats_of('iso4026-M5x10')) == 1
      and J(FEAT['iso4032-M5:thread'], 'dims_json')['engagement_available_mm'] == 4.7
      and J(VAR['iso4032-M5'], 'dims_json')['s_nom'] == 8)
check('washers: ISO 7089 M5 d1 5.3 / d2 10 / h 1, keyed to the M5x0.8 screw as a socket',
      J(VAR['iso7089-M5'], 'dims_json')['d1_min'] == 5.3
      and J(VAR['iso7089-M5'], 'dims_json')['d2_max'] == 10
      and FEAT['iso7089-M5:bore'].key == 'M5x0.8'
      and FEAT['iso7089-M5:bore'].role == 'socket')

print('== suite: extrusions from the NopSCADlib tuples (stated) ==')
e = J(FAM['extrusion'], 'dimension_table_json')
check('E2020: slot opening cw 6, inner width 12, wall 2, centre bore 4.2 (tap M5), 4 slots',
      e['2020']['cw'] == 6 and e['2020']['cwi'] == 12 and e['2020']['t'] == 2
      and e['2020']['d1'] == -4.2 and e['2020']['centre_bore_tap'] == 5
      and e['2020']['slot_count'] == 4, extra=str(e['2020']))
check('E2040 = 1x2 cells -> 6 slots; E2080 -> 10; E4080 (40-series 1x2) -> 6',
      e['2040']['slot_count'] == 6 and e['2080']['slot_count'] == 10
      and e['4080']['slot_count'] == 6)
s2020 = [f for f in feats_of('extrusion-2020-L300') if f.kind == 'slot']
s2040 = [f for f in feats_of('extrusion-2040-L300') if f.kind == 'slot']
check('extrusion-2020-L300 carries 4 slot-B6/20 channels of extent 300 along +z; 2040 carries 6',
      len(s2020) == 4 and all(f.key == 'slot-B6/20' and f.role == 'channel'
                              and f.extent_mm == 300 for f in s2020)
      and len(s2040) == 6)
check('slot keys follow the series: 3030 -> slot-B8/30, 4040 -> slot-B10/40, 1515 -> slot-B6/15',
      {f.key for f in feats_of('extrusion-3030-L300') if f.kind == 'slot'} == {'slot-B8/30'}
      and {f.key for f in feats_of('extrusion-4040-L300') if f.kind == 'slot'} == {'slot-B10/40'}
      and {f.key for f in feats_of('extrusion-1515-L300') if f.kind == 'slot'} == {'slot-B6/15'})
lr = J(FAM['extrusion'], 'length_rule_json')
check('length rule continuous 100..1000 step 100; only L300 and L500 seeded (8 sizes x 2 = 16)',
      lr == {'kind': 'continuous', 'min': 100, 'max': 1000, 'step': 100, 'notes': lr.get('notes')}
      and sorted({v.length_mm for v in variants_of('extrusion')}) == [300, 500]
      and len(variants_of('extrusion')) == 16)
check('the 2020 centre bore is a bore-4.2 socket at both ends, noted as the M5 tap drill',
      FEAT['extrusion-2020-L300:bore:0:end0'].key == 'bore-4.2'
      and 'M5' in FEAT['extrusion-2020-L300:bore:0:end0'].notes
      and FEAT['extrusion-2020-L300:bore:0:endL'].role == 'socket')

print('== suite: the T-nut / slot / screw lookup (plan §3.2 example) ==')
r1 = check_pairing(mgr, 'tnut-sliding-slot6-M5', 'slot', 'extrusion-2020-L300', 'slot:+x:0')
check('T-nut slot6-M5 rider pairs with the 2020 slot-B6/20 channel; common DOF = tz (slides)',
      r1['ok'] and r1['key'] == 'slot-B6/20' and r1['dofCommon'] == ['tz'], extra=str(r1))
r2 = check_pairing(mgr, 'tnut-sliding-slot6-M5', 'thread', 'iso4762-M5x10', 'thread')
check('T-nut M5x0.8 female pairs with the ISO 4762 M5x10 male',
      r2['ok'] and r2['key'] == 'M5x0.8' and r2['roles'] == ['female', 'male'], extra=str(r2))
check('engagement reported beside it: M5 steel needs 1.0 x 5 = 5.0, the nut offers 4.7 -> '
      'the knob refuses, basis knob, and `ok` stays the lookup verdict',
      r2['engagement']['required_mm'] == 5.0 and r2['engagement']['available_mm'] == 4.7
      and r2['engagement']['ok'] is False and r2['engagement']['basis'] == 'knob'
      and r2['ok'] is True, extra=str(r2['engagement']))
r3 = check_pairing(mgr, 'tnut-sliding-slot8-M6', 'slot', 'extrusion-2020-L300', 'slot:+x:0')
check('an M6 T-nut (slot-B8/30 rider) in a B6/20 slot is REFUSED, both keys in the reason',
      not r3['ok'] and 'slot-B8/30' in r3['reason'] and 'slot-B6/20' in r3['reason'],
      extra=str(r3))
r4 = check_pairing(mgr, 'iso4762-M5x10', 'thread', 'iso7380-1-M5x10', 'thread')
check('two male threads on the same key do not pair (roles named in the reason)',
      not r4['ok'] and 'roles do not pair' in r4['reason'])
r5 = check_pairing(mgr, 'tnut-sliding-slot6-M5', 'thread', 'iso4762-M6x10', 'thread')
check('M6 screw in an M5 nut: key mismatch M5x0.8 vs M6x1',
      not r5['ok'] and 'M5x0.8' in r5['reason'] and 'M6x1' in r5['reason'])
p = pairings_for(mgr, 'tnut-sliding-slot6-M5')
slot_hits = p['tnut-sliding-slot6-M5:slot']
thread_hits = p['tnut-sliding-slot6-M5:thread']
check('pairings_for the T-nut: its slot finds every 20-series profile (1515 and 30/40 excluded), '
      'its thread finds the M5 screws and nothing M6',
      set(slot_hits) == {v.name for v in variants_of('extrusion') if v.size_key.startswith('20')}
      and 'iso4762-M5x10' in thread_hits and 'iso7380-1-M5x10' in thread_hits
      and 'iso4762-M6x10' not in thread_hits
      and 'extrusion-1515-L300' not in slot_hits, extra=str(sorted(slot_hits)))
check('features_compatible is symmetric and ROLE_PAIRS has the five pairs of the contract',
      features_compatible(FEAT['iso4762-M5x10:thread'], FEAT['iso4032-M5:thread'])
      and features_compatible(FEAT['iso4032-M5:thread'], FEAT['iso4762-M5x10:thread'])
      and set(ROLE_PAIRS) == {('male', 'female'), ('rider', 'channel'), ('cell', 'cell'),
                              ('socket', 'male'), ('plane', 'plane')})
check('the inner bracket rides two slot-B6/20 channels and takes M4 screws; the washer '
      'socket takes the M5 screw male',
      {f.key for f in feats_of('bracket-inner-20') if f.kind == 'slot'} == {'slot-B6/20'}
      and {f.key for f in feats_of('bracket-inner-20') if f.kind == 'bore'} == {'M4x0.7'}
      and check_pairing(mgr, 'iso7089-M5', 'bore', 'iso4762-M5x10', 'thread')['ok'])

print('== suite: thread engagement knobs (hand-computed) ==')
check('knobs are the plan\'s: steel 1.0 d, aluminium 2.0 d, plastic 2.5 d',
      ENGAGEMENT_FACTORS == {'steel': 1.0, 'aluminium': 2.0, 'plastic': 2.5})
check('M5 tapped 10 mm into aluminium: 10 >= 2 x 5 ok; 8 mm refused with the numbers',
      thread_engagement(5, 10, 'aluminium')['ok'] is True
      and thread_engagement(5, 8, 'aluminium')['ok'] is False
      and '8 mm < 10 mm' in thread_engagement(5, 8, 'aluminium')['reason'])
check('M3 in plastic needs 7.5 (2.5 x 3): 7.5 ok exactly, 7.4 refused; unknown class -> undetermined',
      thread_engagement(3, 7.5, 'plastic')['ok'] is True
      and thread_engagement(3, 7.4, 'plastic')['ok'] is False
      and thread_engagement(3, 7.5, 'wood')['ok'] is None)

print('== suite: Gridfinity from the rebuilt constants ==')
g = J(FAM['gridfinity-bin'], 'dimension_table_json')['unit']
check('constants read: grid 42, base top 41.5, gap 0.5, height unit 7, base profile 4.75, '
      'lip 4.4, magnet 6.5 x 2 (hole 2.4), screw 3, holes 8 from the side',
      g['grid'] == 42 and g['base_top'] == 41.5 and g['base_gap'] == 0.5
      and g['height_unit'] == 7 and g['base_profile_h'] == 4.75 and g['lip_h'] == 4.4
      and g['magnet_d'] == 6.5 and g['magnet_h'] == 2 and g['magnet_hole_depth'] == 2.4
      and g['screw_d'] == 3 and g['hole_from_side'] == 8, extra=str(g))
b226 = J(VAR['gridfinity-bin-2x2x6'], 'dims_json')
check('gridfinity-bin-2x2x6: footprint 83.5 x 83.5 (2 x 42 - 0.5), height 42 (6 x 7)',
      b226['footprint_x'] == 83.5 and b226['footprint_y'] == 83.5 and b226['height'] == 42,
      extra=str(b226))
bf = feats_of('gridfinity-bin-2x2x6')
check('its bottom: 4 grid-42 cells at (0,0) (42,0) (0,42) (42,42), 16 magnet-6.5x2 sockets at '
      '+-13 from each centre, 16 counterbore-M3; its top: 4 lip cells at z = 42',
      [J(f, 'origin_json') for f in bf if f.kind == 'grid_cell'] == [[0, 0, 0], [42, 0, 0], [0, 42, 0], [42, 42, 0]]
      and sum(1 for f in bf if f.key == 'magnet-6.5x2') == 16
      and J(FEAT['gridfinity-bin-2x2x6:magnet:0,0:ne'], 'origin_json') == [13, 13, 0]
      and sum(1 for f in bf if f.key == 'counterbore-M3') == 16
      and [J(f, 'origin_json')[2] for f in bf if f.kind == 'lip'] == [42, 42, 42, 42])
check('a bin cell pairs with a baseplate cell (cell <-> cell); baseplate 2x2 is 84 exactly (no gap)',
      check_pairing(mgr, 'gridfinity-bin-2x2x6', 'cell:0,0', 'gridfinity-baseplate-2x2', 'cell:0,0')['ok']
      and J(VAR['gridfinity-baseplate-2x2'], 'dims_json')['footprint_x'] == 84)
check('the lid is hand-derived and says so: knob basis on its features, a note on the variant',
      all(f.basis == 'knob' for f in feats_of('gridfinity-lid-2x2'))
      and 'hand-derived' in VAR['gridfinity-lid-2x2'].notes
      and 'HAND-DERIVED' in FAM['gridfinity-lid'].notes)

print('== suite: bearings, rods, rails, belts, slides ==')
check('bearing-ball-608: id 8 / od 22 / w 7; its bore-8H7 socket takes the rod-8 shaft male, '
      'the LM8UU bore does too; two bearings do not pair (socket vs male on different keys)',
      J(VAR['bearing-ball-608'], 'dims_json')['od'] == 22
      and check_pairing(mgr, 'bearing-ball-608', 'bore', 'rod-8-L300', 'shaft')['ok']
      and check_pairing(mgr, 'lm-bushing-LM8UU', 'bore', 'rod-8-L300', 'shaft')['ok']
      and not check_pairing(mgr, 'bearing-ball-608', 'bore', 'bearing-ball-608', 'outer')['ok'])
check('625 is derived from F625 and 6000/6001 were not invented',
      J(VAR['bearing-ball-625'], 'dims_json') | {} == J(VAR['bearing-ball-625'], 'dims_json')
      and FEAT['bearing-ball-625:bore'].basis == 'derived'
      and 'bearing-ball-6000' not in VAR and 'bearing-ball-6200' in VAR)
rf = feats_of('rail-mgn-9H-L300')
check('rail-mgn-9H-L300: rail channel + carriage rider on rail-MGN9, rail W 9, carriage MGN9H L 39.9, '
      'holes M3 at pitch 20',
      {(f.role) for f in rf if f.key == 'rail-MGN9'} == {'channel', 'rider'}
      and J(VAR['rail-mgn-9H-L300'], 'dims_json')['rail_W'] == 9
      and J(VAR['rail-mgn-9H-L300'], 'dims_json')['carriage_L'] == 39.9
      and J(FEAT['rail-mgn-9H-L300:rail-holes'], 'dims_json')['pitch'] == 20
      and FEAT['rail-mgn-9H-L300:rail-holes'].key == 'M3x0.5')
check('GT2 belt 6 (rider) runs on the 16T bore-5 pulley (channel); the 9 mm belt is refused',
      check_pairing(mgr, 'belt-gt2-6-L1000', 'teeth', 'pulley-gt2-16T-b5', 'teeth')['ok']
      and not check_pairing(mgr, 'belt-gt2-9-L1000', 'teeth', 'pulley-gt2-16T-b5', 'teeth')['ok']
      and J(VAR['belt-gt2-6-L1000'], 'dims_json')['teeth'] == 500)
check('TR8x8 from the LSN8x8 nut tuple: pitch 2, lead 8, 4 starts; TR8x4 is a hand-entered knob',
      J(VAR['leadscrew-tr8-TR8x8-L300'], 'dims_json')['starts'] == 4
      and FEAT['leadscrew-tr8-TR8x4-L300:thread'].basis == 'knob')
sl = variants_of('drawer-slide')
check('drawer slides: 8 lengths 250..600 step 50, 45 high, 12.7 per side, rated load a knob '
      '(45 kg per pair -> 220.7 N per slide shear)',
      sorted(v.length_mm for v in sl) == list(range(250, 601, 50))
      and J(VAR['drawer-slide-L300'], 'dims_json')['height'] == 45
      and J(VAR['drawer-slide-L300'], 'dims_json')['thickness_per_side'] == 12.7
      and J(FEAT['drawer-slide-L300:drawer'], 'load_rating_json')['basis'] == 'knob'
      and J(FEAT['drawer-slide-L300:drawer'], 'load_rating_json')['shear_n'] == 220.7
      and check_pairing(mgr, 'drawer-slide-L300', 'drawer', 'drawer-slide-L300', 'cabinet')['ok'])
check('the bore-8 pulleys are hand-entered knobs and say so; the bore-5 ones are cited',
      FEAT['pulley-gt2-16T-b8:bore'].basis == 'knob' and 'verify' in VAR['pulley-gt2-16T-b8'].notes
      and FEAT['pulley-gt2-16T-b5:bore'].basis == 'cited')

print('== suite: provenance — every family cited, every sha true, every ref resolves ==')
check('every family names a DimensionSource that exists',
      all(f.dimension_source_ref in SRC for f in FAM.values()),
      extra=str([f.name for f in FAM.values() if f.dimension_source_ref not in SRC]))
check('every DimensionSource states a licence (SPDX not NONE) in the publisher\'s words, '
      'with a verification method',
      all(s.license_spdx not in ('', 'NONE') and s.license_statement
          and s.verification_method in ('file', 'header') for s in SRC.values()))
check('the three upstream licences are what the plan expects: GPL-2.0 (Fasteners WB), '
      'GPL-3.0-or-later (NopSCADlib), MIT (gridfinity-rebuilt)',
      SRC['fasteners-wb:iso4762def.csv'].license_spdx == 'GPL-2.0-only'
      and SRC['nopscadlib:extrusions.scad'].license_spdx == 'GPL-3.0-or-later'
      and SRC['gridfinity-rebuilt:standard.scad'].license_spdx == 'MIT')


def _sha_ok(s):
    p = os.path.join(MECH_DIR, s.path)
    if not os.path.exists(p):
        return False
    b = open(p, 'rb').read()
    return hashlib.sha256(b).hexdigest() == s.sha256 and len(b) == s.bytes


fetched = [s for s in SRC.values() if s.path]
check('every fetched source\'s sha256 + bytes match the verbatim file on disk (%d files), '
      'and each names its commit' % len(fetched),
      all(_sha_ok(s) and len(s.commit) == 40 for s in fetched),
      extra=str([s.name for s in fetched if not _sha_ok(s)]))
check('hand-entered sources (rod, drawer-slide) have no sha and say where their numbers come from',
      all(s.sha256 == '' and 'plan' in s.url.lower() or 'AI-Notes' in s.url
          for s in SRC.values() if not s.path)
      and {s.name for s in SRC.values() if not s.path} == {'hand:rod', 'hand:drawer-slide'})
check('every variant\'s family resolves; every feature\'s variant resolves',
      all(v.family_ref in FAM for v in VAR.values())
      and all(f.variant_ref in VAR for f in FEAT.values()))
check('every variant\'s interfaces_json resolves to MechFeature rows of that variant, '
      'and every feature is listed by its variant (no orphans)',
      all(all(n in FEAT and FEAT[n].variant_ref == v.name for n in J(v, 'interfaces_json'))
          for v in VAR.values())
      and sum(len(J(v, 'interfaces_json')) for v in VAR.values()) == len(FEAT))
check('no family without material roles: default ids on every family, all strings',
      all(J(f, 'material_default_ids_json') and
          all(isinstance(m, str) for m in J(f, 'material_default_ids_json'))
          for f in FAM.values()))
check('every family carries an archetype_ref (composition PartArchetypeDefinition name, at-*) '
      'and an empty generator (nothing draws a part before mxc-3b)',
      all(f.archetype_ref.startswith('at-') and f.generator == '' for f in FAM.values()))
check('every number names its basis: feature basis in BASES; load ratings carry a basis '
      'wherever given',
      all(('basis' in J(f, 'load_rating_json')) for f in FEAT.values()
          if J(f, 'load_rating_json')))
check('variant names follow <family>-<size key> and feature names <variant>:<tag>',
      all(v.name.startswith(v.family_ref + '-') for v in VAR.values())
      and all(f.name.startswith(f.variant_ref + ':') for f in FEAT.values()))

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
