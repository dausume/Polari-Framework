"""
@module magnetics.field_views_selftest

mag-fv selftests: analytic primitives vs hand values (dipole
axial/equatorial factor-2, wire 1/d), deterministic dispersion
sampling with threshold gating, user-drawn shape fit metrics
(precision/recall — the sphere-vs-dipole compromise measured),
flux tubes from the mag-4 layout, group alternation, and the
refusal ladder (fem-2d, unknown primitive, missing bands/region).

Run from polari-framework/:
    python3 -m magnetics.field_views_selftest
"""

import math
import types

from magnetics.field_view_basis import (
    SEED_FIELD_BANDS, SEED_FIELD_GROUPS, SEED_FIELD_VIEWS,
)
from magnetics.custom.field_views import (
    dipole_field, dispersion_payload, group_payload, shapes_payload,
    view_payload, wire_field,
)
from magnetics.magnet_block_basis import (
    SEED_BLOCK_LAYOUTS, SEED_BLOCK_PLACEMENTS, SEED_BLOCK_VARIANTS,
    SEED_JOINT_MORTARS,
)
from magnetics.magnet_seed import SEED_MATERIAL_OPTIONS

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
        'FieldViewDefinition': table(SEED_FIELD_VIEWS),
        'FieldThresholdBand': table(SEED_FIELD_BANDS),
        'FieldViewGroup': table(SEED_FIELD_GROUPS),
        'MagneticMaterialOption': table(SEED_MATERIAL_OPTIONS),
        'BlockSizeVariant': table(SEED_BLOCK_VARIANTS),
        'BlockLayoutDefinition': table(SEED_BLOCK_LAYOUTS),
        'BlockPlacement': table(SEED_BLOCK_PLACEMENTS),
        'JointMortarAssignment': table(SEED_JOINT_MORTARS),
    }
    return m


mgr = _mgr()
DIPOLE = {'moment_a_m2': 1.0, 'center': [0, 0, 0],
          'axis': [0, 0, 1]}

print('== suite: analytic primitives (exact hand values) ==')
axial = dipole_field([0, 0, 0.05], DIPOLE)
check('dipole axial |B| at 5 cm = 1.6e-3 T, along +z',
      abs(axial[2] - 1.6e-3) < 1e-9 and abs(axial[0]) < 1e-12,
      extra=str(axial))
equat = dipole_field([0.05, 0, 0], DIPOLE)
check('dipole equatorial |B| = HALF the axial (8e-4 T), along -z '
      '(the factor-2 anisotropy)',
      abs(equat[2] + 8e-4) < 1e-9 and abs(equat[0]) < 1e-12)
wire = wire_field([0.02, 0, 0.3],
                  {'amps': 5.0, 'point': [0, 0, 0],
                   'direction': [0, 0, 1]})
check('wire |B| at 2 cm from 5 A = 5e-5 T, tangential (+y at +x)',
      abs(wire[1] - 5e-5) < 1e-10 and abs(wire[0]) < 1e-12
      and abs(wire[2]) < 1e-12, extra=str(wire))
check('dipole at its own center = None (excluded, not infinity)',
      dipole_field([0, 0, 0], DIPOLE) is None)

print('== suite: threshold-gated vector dispersion ==')
out = dispersion_payload(mgr, 'dipole-b-dispersion')
check('dispersion answers: 512 sampled, some kept, some below '
      'threshold',
      out['ok'] and out['sampled'] == 512
      and 0 < len(out['vectors']) < 512
      and out['outsideBands'] > 0,
      extra=f"kept {len(out.get('vectors', []))}")
mags_ok = all(
    (2e-3 <= v['magnitude'] or 5e-4 <= v['magnitude'] < 2e-3)
    for v in out['vectors'])
check('EVERY kept vector sits inside a band — the dispersion IS '
      'the gate', mags_ok)
check('band colors + alphas ride each vector',
      all(v['color'] and 0 < v['alpha'] <= 1
          for v in out['vectors']))
check('absence-note + watermark present (below threshold != zero '
      'field; exact-closed-form source named)',
      'below' in out['note'] and 'EXACT' in out['watermark'])
out2 = dispersion_payload(mgr, 'dipole-b-dispersion')
check('deterministic: same jitter_seed -> identical dispersion',
      out2['vectors'] == out['vectors'])

print('== suite: user-drawn threshold shapes (fit metrics) ==')
out = shapes_payload(mgr, 'dipole-b-shells')
inner = next(s for s in out['shapes']
             if s['band'] == 'shell-band-inner')
check('shells answer with shape + color + alpha per band',
      out['ok'] and inner['shape']['kind'] == 'sphere'
      and inner['alpha'] == 0.35)
fit = inner['fit']
check('fit metrics computed (precision + recall in (0,1])',
      fit['precision'] is not None and fit['recall'] is not None
      and 0.5 < fit['precision'] <= 1.0
      and 0.5 < fit['recall'] <= 1.0, extra=str(fit))
check('the sphere-vs-dipole compromise is MEASURED, not hidden '
      '(precision < 1: the sphere over-covers the equator)',
      fit['precision'] < 1.0, extra=str(fit))
check('honesty note: the shape is your drawing, not the field',
      'not the field' in fit['note'])
check('mathshapes seam named as the follow-up',
      'mathshapes' in out['mathshapesSeam'])
band = mgr.objectTables['FieldThresholdBand']['shell-band-outer']
saved = band.shape_json
band.shape_json = '{}'
out = shapes_payload(mgr, 'dipole-b-shells')
outer = next(s for s in out['shapes']
             if s['band'] == 'shell-band-outer')
check('a band with no shape drawn = fit refusal naming the ask',
      'no shape drawn' in outer['fit']['refusal'])
band.shape_json = saved

print('== suite: flux tubes from the mag-4 layout ==')
out = view_payload(mgr, 'ring-core-flux-tubes')
by_el = {t['element']: t for t in out['tubes']}
check('tubes payload from the layout solve (16 elements)',
      out['ok'] and out['displayMode'] == 'flux-tubes'
      and len(out['tubes']) == 16)
check('carrying elements banded green; the dead-end seat mortar '
      'gets NO band (B ~ 0)',
      by_el['ring-joint-10-11-mortar']['band'] == 'tube-band-active'
      and by_el['ring-joint-seat-mortar']['band'] is None)
check('1D-per-path watermark travels',
      'NO off-path field' in out['watermark'])

print('== suite: alternation group ==')
out = group_payload(mgr, 'dipole-and-ring-group')
check('group carries all three views IN ORDER, each rendered by '
      'its own mode',
      out['ok'] and out['order'] == ['dipole-b-dispersion',
                                     'dipole-b-shells',
                                     'ring-core-flux-tubes']
      and [v['payload']['displayMode'] for v in out['views']]
      == ['vector-dispersion', 'threshold-shapes', 'flux-tubes'])

check('every seed ROW\'s display_mode matches its payload mode '
      '(the list route must never disagree with the payload — '
      'the ring-core row said vector-dispersion until mag-7)',
      [s['display_mode'] for s in SEED_FIELD_VIEWS]
      == ['vector-dispersion', 'threshold-shapes', 'flux-tubes'])

print('== suite: refusal ladder ==')
view = mgr.objectTables['FieldViewDefinition']['dipole-b-dispersion']
saved_kind = view.source_kind
view.source_kind = 'fem-2d'
out = dispersion_payload(mgr, 'dipole-b-dispersion')
check('fem-2d refuses naming the follow-up (no faked field maps)',
      not out['ok'] and 'follow-up' in out['refusal'])
view.source_kind = saved_kind
saved_params = view.source_params_json
view.source_params_json = '{"primitive": "solenoid"}'
out = dispersion_payload(mgr, 'dipole-b-dispersion')
check('unknown primitive refuses with the v1 vocabulary',
      not out['ok'] and 'dipole' in out['refusal'])
view.source_params_json = saved_params
saved_sample = view.sample_json
view.sample_json = '{}'
out = dispersion_payload(mgr, 'dipole-b-dispersion')
check('missing sample region refuses (bounds are not guessed)',
      not out['ok'] and 'region' in out['refusal'])
view.sample_json = saved_sample
for b in list(mgr.objectTables['FieldThresholdBand'].values()):
    if b.view_ref == 'dipole-b-dispersion':
        b.view_ref = '__parked__'
out = dispersion_payload(mgr, 'dipole-b-dispersion')
check('a view with no bands refuses — thresholds ARE the gate',
      not out['ok'] and 'band' in out['refusal'].lower())
for b in list(mgr.objectTables['FieldThresholdBand'].values()):
    if b.view_ref == '__parked__':
        b.view_ref = 'dipole-b-dispersion'

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
