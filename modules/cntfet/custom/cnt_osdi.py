"""
@module cntfet.custom.cnt_osdi

S1d half 2: OpenVAF -> .osdi -> ngspice `pre_osdi`, plus the
MANDATORY D3 numerical-equivalence regression: the Python reference
and the compiled OSDI twin evaluated over a grid of {Vg, Vd, Lg,
diameter, T, Rc} variants with EXPLICIT tolerances. A model card is
never trusted because it compiled — only because it matched.

Toolchain honesty: everything here refuses loudly when a tool is
absent (capability endpoint reports the same). Known host gotcha
(2026-08-21): OpenVAF-Reloaded binaries need glibc >= 2.36 — on
older hosts the original openvaf 23.5.0 (OSDI 0.3) is the fallback;
ngspice >= 42 loads either (0.3+0.4 since 44, our image carries 46).

Run bundles (D3): each regression leaves osdi + netlist +
parameter-manifest.json (value/unit/role per parameter + a sha256
over the sorted set) + provenance.json — .model cards stay
non-opaque.

@consumers
  - cntfet.cnt_api ({action: equivalence}, capability)
  - cntfet.cntfet_selftest (honest-skip when tools absent)
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import types
import tempfile
from datetime import datetime, timezone

from cntfet.custom.cnt_constants import EQUATION_REVISION, MODEL_LABEL
from cntfet.cnt_verilog_a_endpoints import construct_gate_check, generate_va
from cntfet.cnt_remote import REMOTE, RemoteError, active_url, \
    remote_post
from cntfet.custom.cnt_vs_model import vs_terminal_current

# Explicit regression tolerances (D3): ngspice solves KCL to its own
# reltol; we set it tight and demand this much agreement.
TOL_REL = 1e-4
TOL_ABS = 1e-12  # amps


def _probe(cmd):
    try:
        run = subprocess.run([cmd, '--version'],
                             capture_output=True, timeout=20)
        return run.returncode == 0
    except Exception:
        return False


def find_openvaf():
    """First runnable compiler: CNTFET_ENGINES_URL worker (knob wins),
    env knob CNTFET_OPENVAF, PATH (reloaded first), ~/tools/openvaf,
    then a topology-resolved worker. Returns (path | 'remote',
    flavor) or (None, why) — cnt_remote.resolve is the ladder."""
    from cntfet.cnt_remote import resolve
    return resolve('openvaf', _find_openvaf_local)


def _find_openvaf_local():
    home = os.path.expanduser('~')
    candidates = []
    env = os.environ.get('CNTFET_OPENVAF', '')
    if env:
        candidates.append(env)
    for name in ('openvaf-r', 'openvaf'):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    candidates += [os.path.join(home, 'tools', 'openvaf', 'openvaf-r'),
                   os.path.join(home, 'tools', 'openvaf', 'openvaf')]
    for cand in candidates:
        if os.path.isfile(cand) and _probe(cand):
            flavor = ('openvaf-reloaded (OSDI 0.4)'
                      if cand.endswith('openvaf-r')
                      else 'openvaf 23.5.0 (OSDI 0.3)')
            return cand, flavor
    return None, ('no runnable OpenVAF (tried PATH + ~/tools/'
                  'openvaf; note: Reloaded binaries need glibc '
                  '>= 2.36)')


def find_ngspice():
    """ngspice per the dist ladder (see find_openvaf)."""
    from cntfet.cnt_remote import resolve
    return resolve('ngspice', _find_ngspice_local)


def _find_ngspice_local():
    home = os.path.expanduser('~')
    for cand in (shutil.which('ngspice'),
                 os.path.join(home, 'tools', 'ngspice', 'bin',
                              'ngspice')):
        if cand and os.path.isfile(cand) and _probe(cand):
            return cand, ''
    return None, 'no runnable ngspice (PATH + ~/tools/ngspice)'


def run_ngspice(ngspice_path, workdir, netlist_path, timeout=600):
    """Run ONE netlist file (already written under workdir) locally
    or on the cnt-engines worker; either way the outputs the netlist
    writes (wrdata .dat) land in workdir and the return object
    carries returncode/stdout/stderr like subprocess.run. Remote
    transport failure = returncode -1 with the reason in stderr, so
    callers' 'produced no output' branches report it."""
    if ngspice_path != REMOTE:
        return subprocess.run([ngspice_path, '-b', netlist_path],
                              capture_output=True, text=True,
                              timeout=timeout, cwd=workdir)
    with open(netlist_path) as fh:
        text = fh.read()
    m = re.search(r'pre_osdi\s+remote://(\S+)', text)
    payload = {'name': os.path.basename(netlist_path), 'netlist': text,
               'timeout': timeout}
    if m:
        payload['osdiId'] = m.group(1)
    try:
        rep = remote_post('/ngspice/run', payload, timeout=timeout + 60)
    except RemoteError as exc:
        return types.SimpleNamespace(returncode=-1, stdout='',
                                     stderr=f'cnt-engines: {exc}')
    if not rep.get('ok'):
        return types.SimpleNamespace(
            returncode=-1, stdout='',
            stderr=f'cnt-engines: {rep.get("error", rep)}')
    for name, content in rep.get('files', {}).items():
        with open(os.path.join(workdir, os.path.basename(name)),
                  'w') as fh:
            fh.write(content)
    return types.SimpleNamespace(returncode=rep.get('returncode', 0),
                                 stdout=rep.get('stdout', ''),
                                 stderr=rep.get('stderr', ''))


def compile_osdi(workdir):
    """Write the generated .va (gate-checked) and compile it."""
    gate = construct_gate_check(generate_va())
    if not gate['ok']:
        return {'ok': False, 'error': 'construct gate FAILED: '
                                      f'{gate["violations"]}'}
    compiler, flavor = find_openvaf()
    if compiler is None:
        return {'ok': False, 'refusal': flavor}
    va_path = os.path.join(workdir, 'cntfet_vs_s1.va')
    with open(va_path, 'w') as fh:
        fh.write(generate_va())
    if compiler == REMOTE:
        # the worker compiles + caches by content hash; the pseudo
        # path travels through every netlist's `pre_osdi` line and
        # run_ngspice hands the id back to the same worker
        try:
            rep = remote_post('/osdi/compile', {'va': generate_va()},
                              timeout=300)
        except RemoteError as exc:
            return {'ok': False, 'refusal': f'cnt-engines: {exc}'}
        if not rep.get('ok'):
            return {'ok': False, 'error': 'remote openvaf failed',
                    'stderr': rep.get('error', '')[-2000:]}
        return {'ok': True, 'osdiPath': f'remote://{rep["osdiId"]}',
                'vaPath': va_path,
                'compiler': f'{rep.get("compiler")} @ {active_url()}'}
    run = subprocess.run([compiler, va_path], capture_output=True,
                         text=True, timeout=300, cwd=workdir)
    osdi_path = os.path.join(workdir, 'cntfet_vs_s1.osdi')
    if run.returncode != 0 or not os.path.isfile(osdi_path):
        return {'ok': False, 'error': 'openvaf failed',
                'stderr': run.stderr[-2000:]}
    return {'ok': True, 'osdiPath': osdi_path, 'vaPath': va_path,
            'compiler': flavor}


def _model_card(p):
    """.model line from a vs-params dict (same names as the .va)."""
    vals = {'lg_m': p['lg_m'], 'cinv': p['cinv_f_per_m'],
            'vxo': p['vxo_m_per_s'], 'mu': p['mu_m2_per_vs'],
            'vt0': p['vt0_v'], 'dvt': p['dvt_v'],
            'dibl': p['dibl_v_per_v'], 'nss': p['n_ss'],
            'alpha': p['alpha'], 'beta': p['beta'],
            'rs': p['rs_ohm'], 'rd': p['rd_ohm'],
            'tdev': p['temperature_k'],
            'ptype': float(p.get('ptype', 0)),
            'cinvb': p.get('cinvb_f_per_m', 1.0e-10),
            'vtbq': p.get('vtb_v', 0.6)}
    text = ' '.join(f'{k}={v:.10g}' for k, v in vals.items())
    return f'.model cntmod cntfet_vs_s1 {text}', vals


def run_osdi_grid(osdi_path, p, vg_list, vd_list, workdir,
                  ngspice_path):
    """One ngspice batch run: DC-sweep vd per vg, wrdata out.
    Returns {(vg, vd): id_a} with Id = current into the drain."""
    card, _ = _model_card(p)
    # signed sweep (p-type grids run negative)
    vd_start, vd_stop = vd_list[0], vd_list[-1]
    vd_step = (vd_list[1] - vd_list[0]) if len(vd_list) > 1 else 0.1
    lines = [
        '* cntfet S1 OSDI equivalence harness', card,
        'N1 dpin gpin 0 cntmod',
        'vg gpin 0 0.0',
        'vd dhi 0 0.0',
        'vids dhi dpin 0',
        '.options reltol=1e-9 abstol=1e-18 vntol=1e-9',
        '.control',
        f'pre_osdi {osdi_path}',
    ]
    for i, vg in enumerate(vg_list):
        lines += [f'alter vg {vg:.10g}',
                  f'dc vd {vd_start:.10g} {vd_stop:.10g} '
                  f'{vd_step:.10g}',
                  f'wrdata sweep_{i}.dat i(vids)']
    lines += ['quit', '.endc', '.end']
    netlist = os.path.join(workdir, 'device-model.sp')
    with open(netlist, 'w') as fh:
        fh.write('\n'.join(lines) + '\n')
    run = run_ngspice(ngspice_path, workdir, netlist, timeout=600)
    out = {}
    for i, vg in enumerate(vg_list):
        path = os.path.join(workdir, f'sweep_{i}.dat')
        if not os.path.isfile(path):
            return {'ok': False, 'error': f'missing sweep output '
                    f'for vg={vg}',
                    'stderr': run.stderr[-1500:],
                    'stdout': run.stdout[-1500:]}
        with open(path) as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2:
                    vd = float(parts[0])
                    out[(round(vg, 6), round(vd, 6))] = float(
                        parts[1])
    return {'ok': True, 'points': out}


def _manifest(p, roles_note):
    ordered = sorted(_model_card(p)[1].items())
    digest = hashlib.sha256(
        json.dumps(ordered).encode()).hexdigest()
    return {'equationRevision': EQUATION_REVISION,
            'modelLabel': MODEL_LABEL, 'parameters': dict(ordered),
            'rolesNote': roles_note, 'sha256': digest}


def equivalence_regression(variants, vg_list=None, vd_list=None,
                           workdir=None, keep_bundle=True):
    """THE D3 regression. variants: {label: vs-params dict} — the
    caller supplies the {Lg, d, T, Rc} spread (cnt_api builds it
    from the device rows). Compares Python reference vs OSDI at
    every grid point with explicit tolerances."""
    vg_list = vg_list or [0.0, 0.2, 0.4, 0.6]
    vd_list = vd_list or [0.05 * i for i in range(11)]
    ngspice_path, why_ng = find_ngspice()
    if ngspice_path is None:
        return {'ok': False, 'refusal': why_ng}
    workdir = workdir or tempfile.mkdtemp(prefix='cntfet-osdi-')
    os.makedirs(workdir, exist_ok=True)
    compiled = compile_osdi(workdir)
    if not compiled.get('ok'):
        return compiled
    worst = {'relErr': 0.0, 'absErr': 0.0, 'at': None}
    checked = 0
    failures = []
    for label, p in variants.items():
        got = run_osdi_grid(compiled['osdiPath'], p, vg_list,
                            vd_list, workdir, ngspice_path)
        if not got.get('ok'):
            got['variant'] = label
            return got
        for (vg, vd), id_osdi in got['points'].items():
            id_py = vs_terminal_current(vg, vd, p)['id_a']
            abs_err = abs(id_py - id_osdi)
            denom = max(abs(id_py), abs(id_osdi))
            rel_err = abs_err / denom if denom > TOL_ABS else 0.0
            checked += 1
            if abs_err > worst['absErr']:
                worst['absErr'] = abs_err
            if rel_err > worst['relErr']:
                worst.update(relErr=rel_err,
                             at={'variant': label, 'vg': vg,
                                 'vd': vd, 'python': id_py,
                                 'osdi': id_osdi})
            if rel_err > TOL_REL and abs_err > TOL_ABS:
                failures.append({'variant': label, 'vg': vg,
                                 'vd': vd, 'python': id_py,
                                 'osdi': id_osdi,
                                 'relErr': rel_err})
    ok = not failures
    stamp = datetime.now(timezone.utc).isoformat()
    provenance = {
        'ranAt': stamp, 'compiler': compiled['compiler'],
        'ngspice': ngspice_path,
        'toleranceRel': TOL_REL, 'toleranceAbs': TOL_ABS,
        'grid': {'vg': vg_list, 'vd': vd_list,
                 'variants': list(variants)},
        'pointsChecked': checked, 'failures': failures[:20],
        'worst': worst, 'verdict': 'EQUIVALENT' if ok
        else 'NOT EQUIVALENT'}
    if keep_bundle:
        with open(os.path.join(workdir,
                               'parameter-manifest.json'),
                  'w') as fh:
            json.dump({label: _manifest(p, 'roles ride the '
                       'CNTFETParameterRow rows per device')
                       for label, p in variants.items()}, fh,
                      indent=1)
        with open(os.path.join(workdir, 'provenance.json'),
                  'w') as fh:
            json.dump(provenance, fh, indent=1)
    return {'ok': ok, 'pointsChecked': checked, 'worst': worst,
            'failures': failures[:20],
            'toleranceRel': TOL_REL, 'toleranceAbs': TOL_ABS,
            'compiler': compiled['compiler'],
            'bundleDir': workdir if keep_bundle else '',
            'verdict': provenance['verdict']}
