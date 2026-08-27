"""
@module cntfet.cnt_kwant

F3 — the Kwant NEGF kernel behind a D14 knob: the heavy stack
(kwant + numpy<2) lives in its OWN virtualenv
(~/tools/kwant-venv, built 2026-08-21 because kwant 1.5.0's
pregenerated Cython C is incompatible with numpy 2.x) and is
driven by SUBPROCESS through kwant_worker.py — never imported by
the polari process. Absent venv = honest refusal, reported by the
capability endpoint.

What F3 adds over F2 (recorded per run): S/D tunneling through
the eq.(5) barrier (F2 is thermionic-only) and the second subband
(T -> 4) at high energy (F1/F2 are single-subband). Sanity pins
from the atomistic model itself: TB gap == compact-model Eg by
construction; T == 2 valleys just above the edge — independently
confirming the (4q/h) degeneracy the closed forms assume.

D13 (2026-08-25): scf=True upgrades the kernel to a
self-consistent 1D cylindrical Poisson <-> NEGF-charge loop —
the eq.(5) barrier is exactly the zero-charge (Laplace) solution
of the solved equation, so the fixed mode is the SCF's own
degenerate limit and the worker's poisson-pin mode asserts that
identity on the discrete grid. Building the pin also CAUGHT a
latent a1/a2 coefficient swap in the original eq.(5)
implementation (the interior ramp was mirrored, leaving ~vd-sized
steps at the gate edges); both modes now ride the corrected
profile, so fixed-mode F3 numbers shift slightly vs the S5-era
rows.

Honest limits riding every result: coherent-only (no phonons),
zigzag (n,0) tubes only; fixed mode: FIXED eq.(5) potential; scf
mode: electron-band propagating-state charge in the transport
window only (no valence/hole charge — VDD < Eg regime; quasi-
bound well states flagged, not counted), 1D cylindrical Poisson
through eq.(7) lambda + eq.(1) Cox, abrupt-junction donor
profile.

@consumers
  - cntfet.cnt_api ({action: f3-oracle})
  - cntfet.cnt_capability (live probe)
  - cntfet.selftest_cntfet (honest-skip leg)
"""

import json
import os
import subprocess
from datetime import datetime, timezone

from cntfet.cnt_constants import lit_value
from cntfet.cnt_derive import resolve_components

F3_LIMITS = ['coherent-only (no phonon scattering)',
             'fixed eq.(5) potential (Laplace limit — pass '
             'scf: true for the self-consistent Poisson solve, '
             'D13 built 2026-08-25)',
             'zigzag (n,0) tubes only',
             'F3 sees the second subband (T->4); F1/F2 are '
             'single-subband — expect divergence at high '
             'overdrive']

F3_SCF_LIMITS = [
    'coherent-only (no phonon scattering)',
    'self-consistent 1D cylindrical Poisson (D13): eq.(7) '
    'lambda + eq.(1) Cox coupling, mode-space — not a 3D solve',
    'electron-band charge over the transport window only — no '
    'valence/hole charge (VDD < Eg regime, labeled not fitted)',
    'propagating-state charge only: quasi-bound well states '
    'below both lead edges are not counted (flagged per point '
    'as wellFormed)',
    'abrupt-junction donor profile: lead density for |x| > '
    'Lg/2, undoped channel inside',
    'zigzag (n,0) tubes only',
    'F3 sees the second subband (T->4); F1/F2 are '
    'single-subband — expect divergence at high overdrive']

_WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'kwant_worker.py')


def find_kwant_python():
    """The kwant executor per the dist ladder (cnt_remote.resolve):
    the CNTFET_ENGINES_URL worker wins, else a local venv
    interpreter, else the topology's cnt-engines provider.
    (path | 'remote', detail) or (None, why)."""
    from cntfet.cnt_remote import resolve
    return resolve('kwant', _find_kwant_python_local)


def _find_kwant_python_local():
    """The venv interpreter that can import kwant, or (None, why)."""
    candidates = [os.environ.get('CNTFET_KWANT_PYTHON', ''),
                  os.path.expanduser(
                      '~/tools/kwant-venv/bin/python'),
                  'python3']
    for cand in candidates:
        if not cand:
            continue
        try:
            probe = subprocess.run(
                [cand, '-c', 'import kwant'],
                capture_output=True, timeout=60)
            if probe.returncode == 0:
                return cand, ''
        except Exception:
            continue
    return None, ('no python with kwant importable (checked '
                  'CNTFET_KWANT_PYTHON, ~/tools/kwant-venv, '
                  'python3); kwant 1.5.0 needs numpy<2 — build '
                  'the venv per cnt_kwant docstring')


def _run_worker(python_path, job, timeout_s=1200):
    from cntfet.cnt_remote import REMOTE, RemoteError, remote_post
    if python_path == REMOTE:
        try:
            return remote_post('/kwant/run',
                               {'job': job, 'timeout': timeout_s},
                               timeout=timeout_s + 60)
        except RemoteError as exc:
            return {'ok': False, 'error': 'kwant worker unreachable',
                    'stderr': str(exc)}
    run = subprocess.run(
        [python_path, _WORKER], input=json.dumps(job),
        capture_output=True, text=True, timeout=timeout_s)
    if run.returncode != 0:
        return {'ok': False, 'error': 'kwant worker failed',
                'stderr': run.stderr[-1200:]}
    try:
        return json.loads(run.stdout)
    except Exception:
        return {'ok': False, 'error': 'worker emitted no JSON',
                'stdout': run.stdout[-500:],
                'stderr': run.stderr[-500:]}


def sanity(python_path=None):
    """Pristine-tube pins: gap + valley count."""
    python_path = python_path or find_kwant_python()[0]
    if python_path is None:
        return {'ok': False, 'refusal': find_kwant_python()[1]}
    return _run_worker(python_path, {
        'mode': 'sanity', 'n': 16,
        'a_cc_nm': lit_value('a_cc_nm'),
        'ep_ev': lit_value('Ep_eV')}, timeout_s=300)


def poisson_pin(manager, device, vg_v=0.3, vd_v=0.6):
    """The D13 identity pin: the discrete Poisson solve at zero
    charge must reproduce the analytic eq.(5) profile to
    discretization error (~1e-4 eV on the ring grid). Pure numpy
    in the worker — no NEGF solve involved."""
    python_path, why = find_kwant_python()
    if python_path is None:
        return {'ok': False, 'refusal': why}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}'}
    mat, geo = rows['material'], rows['geometry']
    gate, transport = rows['gate_stack'], rows['transport']
    return _run_worker(python_path, {
        'mode': 'poisson-pin', 'n': mat.chirality_n,
        'a_cc_nm': lit_value('a_cc_nm'),
        'ep_ev': lit_value('Ep_eV'),
        'lg_nm': geo.lg_nm,
        'lof_nm': lit_value('lof_over_tox') * gate.t_ox_nm,
        'lambda_nm': transport.lambda_nm,
        'efsd_ev': transport.efsd_ev,
        'vt0_v': transport.vt0_v,
        'temperature_k': device.temperature_k,
        'bias_points': [{'vg_v': vg_v, 'vd_v': vd_v}],
    }, timeout_s=300)


def _default_bias_points(manager, device):
    """The latest triangle row's worst-disagreement points (the
    adaptive-oracle discipline: F3 spend goes where F1/F2
    disagree), plus one on-state point. Falls back to a fixed
    trio."""
    tables = getattr(manager, 'objectTables', None) or {}
    best_row, best_time = None, ''
    for row in (tables.get('CNTFETSimResult') or {}).values():
        if (getattr(row, 'kind', '') == 'validation-triangle'
                and getattr(row, 'device', '') == device.name
                and getattr(row, 'ran_at', '') > best_time):
            best_row, best_time = row, row.ran_at
    if best_row is not None:
        try:
            points = json.loads(best_row.series_json)
            scored = [p for p in points
                      if p.get('intrinsicEdgeDex') is not None]
            scored.sort(key=lambda p: -p['intrinsicEdgeDex'])
            picks = [{'vg_v': p['vg_v'], 'vd_v': p['vd_v']}
                     for p in scored[:3]]
            picks.append({'vg_v': 0.6, 'vd_v': 0.6})
            return picks, f'top-3 disagreement points of ' \
                          f'{best_row.name} + on-state'
        except Exception:
            pass
    return ([{'vg_v': 0.0, 'vd_v': 0.6},
             {'vg_v': 0.3, 'vd_v': 0.6},
             {'vg_v': 0.6, 'vd_v': 0.6}],
            'default trio (no triangle run found)')


def f3_oracle(manager, device, bias_points=None, energy_points=60,
              result_factory=None, scf=None):
    """Evaluate the F3 kernel at the oracle targets and lay it
    beside F1/F2 at the same alignment — the triangle's third
    vertex. scf truthy (True or an options dict: damping, tol_ev,
    max_iter, charge_energy_points) runs the D13 self-consistent
    Poisson loop instead of the fixed eq.(5) potential."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    python_path, why = find_kwant_python()
    if python_path is None:
        return {'ok': False, 'refusal': why}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}'}
    mat, geo = rows['material'], rows['geometry']
    gate, transport = rows['gate_stack'], rows['transport']
    if mat.chirality_m != 0:
        return {'ok': False,
                'refusal': f'F3 worker is zigzag-only; '
                           f'({mat.chirality_n},{mat.chirality_m}) '
                           'is not (n,0) — chiral tubes are a '
                           'worker extension, not a silent '
                           'approximation'}
    picked, picked_why = (bias_points, 'caller-supplied') \
        if bias_points else _default_bias_points(manager, device)
    job = {
        'mode': 'iv', 'n': mat.chirality_n,
        'a_cc_nm': lit_value('a_cc_nm'),
        'ep_ev': lit_value('Ep_eV'),
        'lg_nm': geo.lg_nm,
        'lof_nm': lit_value('lof_over_tox') * gate.t_ox_nm,
        'lambda_nm': transport.lambda_nm,
        'efsd_ev': transport.efsd_ev,
        'vt0_v': transport.vt0_v,
        'temperature_k': device.temperature_k,
        'energy_points': energy_points,
        'bias_points': picked,
    }
    timeout_s = 1200
    scf_opts = None
    if scf:
        scf_opts = dict(scf) if isinstance(scf, dict) else {}
        max_iter = int(scf_opts.get('max_iter', 30))
        job['scf'] = {
            'enabled': True,
            'damping': float(scf_opts.get('damping', 0.35)),
            'tol_ev': float(scf_opts.get('tol_ev', 2e-3)),
            'max_iter': max_iter,
            'charge_energy_points': scf_opts.get(
                'charge_energy_points'),
        }
        job['cox_f_per_m'] = gate.cox_f_per_m
        # The plan's budget prior is min–tens-of-min PER POINT for
        # SCF NEGF — scale the subprocess timeout with the work
        # instead of letting 1200 s bind first.
        timeout_s = 600 + len(picked) * max_iter * 40
    result = _run_worker(python_path, job, timeout_s=timeout_s)
    if not result.get('ok'):
        return result
    # F1/F2 at the same alignment, per point.
    from cntfet.cnt_tob import tob_operating_point
    from cntfet.cnt_vs_model import (
        build_vs_params, vs_terminal_current,
    )
    contact = rows['contact']
    p_vs = build_vs_params(
        {'diameter_nm': mat.diameter_nm, 'eg_ev': mat.eg_ev},
        {'lg_nm': geo.lg_nm},
        {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
        {'rc_ohm': 0.0},  # intrinsic edge — F3 has no contacts
        {'vt0_v': transport.vt0_v, 'efsd_ev': transport.efsd_ev},
        device.temperature_k)
    p_tob = {'eg_ev': mat.eg_ev, 'vf_m_per_s': mat.vf_m_per_s,
             'lg_nm': geo.lg_nm, 'cox_f_per_m': gate.cox_f_per_m,
             'temperature_k': device.temperature_k,
             'eta0_ev': transport.vt0_v,
             'cd_over_cg': transport.dibl_v_per_v,
             'transmission_mode': 'ballistic'}
    comparison = []
    profiles = []
    unconverged = []
    for point in result['points']:
        vg, vd = point['vg_v'], point['vd_v']
        i_f1 = vs_terminal_current(vg, vd, p_vs)['id_a']
        i_f2 = tob_operating_point(vg, vd, p_tob)['id_a']
        entry = {
            'vg_v': vg, 'vd_v': vd,
            'f3_negf_a': point['id_a'],
            'f2_tob_a': i_f2, 'f1_vs_intrinsic_a': i_f1,
            'ecTop_ev': point['ec_top_ev'],
            'tMax': point['t_max']}
        scf_rep = point.get('scf')
        if scf_rep is not None:
            entry.update({
                'scfConverged': scf_rep['converged'],
                'scfIterations': scf_rep['iterations'],
                'scfResidual_ev': scf_rep['residual_ev'],
                'ecTopLaplace_ev': scf_rep['ec_top_laplace_ev'],
                'deltaEcTop_ev': (point['ec_top_ev']
                                  - scf_rep['ec_top_laplace_ev']),
                'wellFormed': scf_rep['wellFormed'],
                'sourceDensityRatio':
                    scf_rep['source_density_ratio'],
                'ldosPinRel': scf_rep['ldos_pin_rel'],
            })
            profiles.append({'vg_v': vg, 'vd_v': vd,
                             **scf_rep['profile']})
            if not scf_rep['converged']:
                unconverged.append(
                    {'vg_v': vg, 'vd_v': vd,
                     'residual_ev': scf_rep['residual_ev'],
                     'iterations': scf_rep['iterations']})
        comparison.append(entry)
    scf_ran = bool(result.get('scf_enabled'))
    limits = F3_SCF_LIMITS if scf_ran else F3_LIMITS
    engine = ('kwant (subprocess venv, coherent NEGF, '
              'self-consistent 1D Poisson)' if scf_ran else
              'kwant (subprocess venv, coherent NEGF)')
    stamp = datetime.now(timezone.utc).isoformat()
    report = {
        'ok': True, 'device': device.name,
        'biasPointsFrom': picked_why,
        'atoms': result['atoms'], 'cells': result['cells'],
        'egTb_ev': result['eg_tb_ev'],
        'comparison': comparison,
        'limits': limits,
        'engine': engine,
    }
    if scf_ran:
        report['scf'] = job['scf']
        report['profiles'] = profiles
        if unconverged:
            # Non-convergence is a per-point flag the caller must
            # see — never absorbed into a plausible-looking number.
            report['unconverged'] = unconverged
    if result_factory is None:
        from cntfet.cnt_basis import CNTFETSimResult
        result_factory = CNTFETSimResult
    tag = 'f3scf' if scf_ran else 'f3'
    verdict = 'triangle-third-vertex-recorded'
    if unconverged:
        verdict = 'scf-unconverged-points-flagged'
    metrics = {'atoms': result['atoms'],
               'egTb_ev': result['eg_tb_ev']}
    if scf_ran:
        metrics['scf'] = job['scf']
        metrics['profiles'] = profiles
    row = result_factory(
        name=f'{device.name}-{tag}-'
             f'{stamp[11:19].replace(":", "")}',
        device=device.name, kind='f3-oracle',
        engine=report['engine'],
        physics_fidelity='F3_NEGF_SCF' if scf_ran else 'F3_NEGF',
        inputs_json=json.dumps({'biasPoints': picked,
                                'energyPoints': energy_points,
                                'from': picked_why,
                                'scf': job.get('scf')}),
        series_json=json.dumps(comparison),
        metrics_json=json.dumps(metrics),
        verdict=verdict, ran_at=stamp,
        notes='; '.join(limits), manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report
