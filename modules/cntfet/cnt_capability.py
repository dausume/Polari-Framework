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
    },
    'absent_by_design': {
        'F3-NEGF': 'Kwant-based NEGF kernel — S2+ (D13/D15: '
                   'dausume/kwant fork-pin on a worker, never a '
                   'hard import here)',
        'F4-atomistic': 'S2+',
        'variability': 'S3 (Monte Carlo over process objects)',
        'multi-tube/cells/Liberty': 'S4/S5 arcs',
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
    },
    'python_deps': ['numpy'],
    'polari_deps': ['electrodevice (device_validator judge '
                    'machinery only)'],
}


def capability():
    """The honest live report: fidelity -> present | refusing."""
    openvaf_path, openvaf_why = find_openvaf()
    ngspice_path, ngspice_why = find_ngspice()
    fidelities = {
        'F0-analytical': {'present': True},
        'F1-VS-compact': {'present': True,
                          'profile': 'VS_MINIMAL'},
        'F2-ToB': {'present': True},
        'F3-NEGF': {'present': False,
                    'refusal': 'not built at S1 (S2+; D14 keeps '
                               'heavy kernels off thin instances)'},
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
    }
    return {'ok': True, 'module': 'cntfet',
            'fidelities': fidelities, 'ledger': MODULE_LEDGER}
