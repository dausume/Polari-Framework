"""
@module cntfet.cnt_capability

D14 accountability: the per-module dependency/capability ledger as
DATA, and the honest capability report — which fidelities THIS
instance can evaluate right now, which it must refuse, and which
external tools + licenses each capability pulls in. Refusal, never
silent fallback.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/capability)
  - cntfet.selftest_cntfet
"""

from cntfet.cnt_osdi import find_ngspice, find_openvaf

# The D14 ledger — what this module provides and what each
# capability depends on (queryable, tech-tree data_dependencies
# style).
MODULE_LEDGER = {
    'module': 'cntfet',
    'provides': {
        'F0-analytical': 'bandstructure/electrostatics derivation '
                         '(cnt_bandstructure) — pure python, '
                         'always present',
        'F1-VS-compact': 'VS-CNFET-derived DC compact model '
                         '(cnt_vs_model) — python + numpy, always '
                         'present; profile VS_MINIMAL',
        'F2-ToB': 'top-of-the-barrier quasi-ballistic reference '
                  '(cnt_tob) — python + numpy, always present',
        'verilog-a-generation': 'clean-room .va twin generation + '
                                'construct gate (cnt_verilog_a) — '
                                'always present',
        'osdi-compile': 'OpenVAF compile of the twin (cnt_osdi) — '
                        'OPTIONAL, needs an openvaf binary',
        'ngspice-equivalence': 'D3 numerical-equivalence '
                               'regression (cnt_osdi) — OPTIONAL, '
                               'needs openvaf + ngspice >= 42',
        'S2-validation': 'metric family + F1-vs-F2 triangle + '
                         'digitized-curve residuals (cnt_metrics/'
                         'cnt_triangle/cnt_calibration) — always '
                         'present',
        'S3-montecarlo': 'process-object distributions + Monte '
                         'Carlo populations (cnt_process_basis/'
                         'cnt_montecarlo) — always present; '
                         'refuses without a bound process set',
        'S4a-inverter': 'complementary inverter VTC through the '
                        'OSDI twin (cnt_inverter) — OPTIONAL, '
                        'needs openvaf + ngspice',
    },
    'provides-optional': {
        'F3-NEGF': 'kwant NEGF oracle (cnt_kwant/kwant_worker) — '
                   'OPTIONAL, needs the kwant venv (numpy<2, '
                   'subprocess-isolated, D14); fixed eq.(5) '
                   'potential AND D13 self-consistent 1D Poisson '
                   '(scf: true) modes',
    },
    'absent_by_design': {
        'F4-atomistic': 'S2+',
        'multi-tube-aggregation': 'the array-device arc (pitch/'
                                  'count distributions already '
                                  'ride the process objects)',
        'cells/Liberty/delay-energy': 'S4b+/S5 (needs the charge '
                                      'model for transients)',
    },
    'external_tools': {
        'openvaf': {'license': 'GPL-3.0', 'role': 'build tool '
                    '(compiles the GPLv3 model; compiler license '
                    'does not constrain the model)',
                    'gotcha': 'Reloaded binaries need glibc >= '
                              '2.36; original 23.5.0 (OSDI 0.3) '
                              'is the older-host fallback'},
        'ngspice': {'license': 'BSD-ish (ngspice license)',
                    'role': 'OSDI runtime, >= 42 for OSDI'},
        'kwant': {'license': 'BSD-2-Clause (S0-gated '
                             'incorporable; dausume/kwant '
                             'fork-pin)',
                  'role': 'F3 NEGF kernel — subprocess venv only '
                          '(kwant 1.5 needs numpy<2), never a '
                          'polari-process import',
                  'gotcha': 'venv at ~/tools/kwant-venv or '
                            'CNTFET_KWANT_PYTHON'},
    },
    'python_deps': ['numpy'],
    'polari_deps': ['electrodevice (device_validator judge '
                    'machinery only)'],
}


def capability():
    """The honest live report: fidelity -> present | refusing."""
    openvaf_path, openvaf_why = find_openvaf()
    ngspice_path, ngspice_why = find_ngspice()
    from cntfet.cnt_kwant import find_kwant_python
    kwant_python, kwant_why = find_kwant_python()
    fidelities = {
        'F0-analytical': {'present': True},
        'F1-VS-compact': {'present': True,
                          'profile': 'VS_MINIMAL'},
        'F2-ToB': {'present': True},
        'F3-NEGF': (
            {'present': True, 'worker': kwant_python,
             'limits': 'coherent-only, fixed eq.(5) potential '
                       '(Laplace limit), zigzag tubes '
                       '(subprocess venv — D14)'}
            if kwant_python else
            {'present': False, 'refusal': kwant_why}),
        'F3-NEGF-SCF': (
            {'present': True, 'worker': kwant_python,
             'limits': 'coherent-only, D13 self-consistent 1D '
                       'cylindrical Poisson (eq.(7) lambda + '
                       'eq.(1) Cox), electron-band propagating-'
                       'state charge only, abrupt-junction donor '
                       'profile, zigzag tubes ({action: '
                       'f3-oracle, scf: true})'}
            if kwant_python else
            {'present': False, 'refusal': kwant_why}),
        'verilog-a-generation': {'present': True},
        'osdi-compile': (
            {'present': True, 'compiler': openvaf_path}
            if openvaf_path else
            {'present': False, 'refusal': openvaf_why}),
        'ngspice-equivalence': (
            {'present': True, 'ngspice': ngspice_path}
            if (openvaf_path and ngspice_path) else
            {'present': False,
             'refusal': (openvaf_why if not openvaf_path
                         else ngspice_why)}),
        'S2-validation': {'present': True},
        'S3-montecarlo': {'present': True,
                          'note': 'refuses without a bound, '
                                  'regime-coherent process set'},
        'S4a-inverter': (
            {'present': True}
            if (openvaf_path and ngspice_path) else
            {'present': False,
             'refusal': (openvaf_why if not openvaf_path
                         else ngspice_why)}),
    }
    return {'ok': True, 'module': 'cntfet',
            'fidelities': fidelities, 'ledger': MODULE_LEDGER}
