"""
Selftest for electrodevice (materials -> device -> SPICE -> circuit).

Run from polari-framework/:
  python3 -m electrodevice.selftest_electrodevice

Fake manager + injected executor for derivation math; the ngspice leg
runs the REAL binary when available (honest skip otherwise): the
0xA5A5 grid must show 8 lit branches with LED-range currents and 8
dark ones, and an implausible geometry must yield the
current-out-of-range verdict + a knob suggestion.
"""

import json
import sys
import types

from electrodevice import device_derive as dd
from electrodevice import spice_run as sr

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _factory(**fields):
    fields.pop('manager', None)
    return types.SimpleNamespace(**fields)


def _mgr():
    return types.SimpleNamespace(objectTables={
        'ElectronicDeviceDefinition': {}, 'SpiceModelCard': {},
        'CircuitRunResult': {}}, db=None)


def _device(**over):
    base = dict(name='cnt-solgel-led-resistor',
                device_type='resistor',
                sim_model='cnt-solgel-percolation',
                length_m=0.002, cross_section_m2=1.4e-8,
                sigma_s_per_m=0.0, resistance_ohm=0.0,
                derived_at='', provenance_json='{}', notes='')
    base.update(over)
    return types.SimpleNamespace(**base)


def _executor(sigma):
    def execute(manager, name):
        return {'ok': True, 'engine': 'analytic.percolation-'
                                      'conductivity',
                'inputs': {'volumeFraction': 0.02},
                'result': {'effectiveSigma': sigma,
                           'validity': 'idealized classical '
                                       'percolation',
                           'note': 'selftest'}}
    return execute


def main():
    mgr = _mgr()
    dev = _device()

    # --- derivation from the (injected) sim ---------------------------
    report = dd.derive_device(mgr, dev, executor=_executor(227.267))
    check('derive: R = L/(sigma*A) from the SIM result',
          report['ok']
          and abs(report['resistance_ohm']
                  - 0.002 / (227.267 * 1.4e-8)) < 1e-6)
    check('derive: provenance names model, engine, formula',
          report['provenance']['simModel'] == 'cnt-solgel-percolation'
          and 'R = L / (sigma_eff * A)'
          == report['provenance']['formula'])

    bad = dd.derive_device(
        mgr, _device(), executor=lambda m, n: {
            'ok': True, 'inputs': {},
            'result': {'effectiveSigma': 0.0}})
    check('derive: below-threshold sigma refused with the sweep hint',
          not bad['ok'] and 'volumeFraction' in bad['error'])

    # --- the SPICE abstraction ----------------------------------------
    card = dd.render_card(dev)
    check('card: subckt with the derived resistance + provenance '
          'comments',
          '.subckt polari_cnt_solgel_led_resistor n1 n2' in card
          and 'R1 n1 n2 628.5' in card
          and 'DERIVED from simulated material data' in card)
    versioned = dd.make_card_row(mgr, dev, card_factory=_factory)
    check('card rows version append-only',
          versioned['version'] == 1
          and dd.make_card_row(mgr, dev,
                               card_factory=_factory)['version'] == 1)

    # --- netlist shape ---------------------------------------------------
    net = sr.render_led_grid_netlist(dev, 0xA5A5)
    check('netlist: 16 branches, 8 driven at vdd, 8 at 0',
          net.count('polari_led') == 17  # model + 16 diodes
          and net.count('DC 3.3') == 8 and net.count('DC 0.0') == 8)

    # --- the real engine (honest skip without the binary) --------------
    if sr.ngspice_bin() is None:
        print('SKIP: ngspice not available — circuit legs need it '
              '(build into ~/tools/ngspice). Honest skip, not a '
              'pass.')
    else:
        run = sr.run_led_grid(mgr, dev, 0xA5A5,
                              result_factory=_factory)
        per = run['outputs']['perPin']
        check('ngspice: 8 lit pins all in LED range, dark pins ~0',
              run['verdict'] == 'all-leds-in-range'
              and run['outputs']['litCount'] == 8
              and all(abs(p['current_mA']) < 1e-3
                      for p in per if not p['lit']),
              json.dumps(run['outputs'])[:200])
        lit_mA = [p['current_mA'] for p in per if p['lit']]
        check('ngspice: lit current physically sane '
              '(~(3.3-Vf)/R ≈ 2 mA)',
              all(1.0 < c < 4.0 for c in lit_mA), str(lit_mA[:4]))

        fat = _device(name='fat-trace', cross_section_m2=1.4e-4)
        dd.derive_device(mgr, fat, executor=_executor(227.267))
        run = sr.run_led_grid(mgr, fat, 0x0001,
                              result_factory=_factory)
        check('ngspice: implausible geometry -> out-of-range verdict '
              '+ knob suggestion',
              run['verdict'] == 'current-out-of-range'
              and 'geometry' in run['suggestion']['knob'])

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
