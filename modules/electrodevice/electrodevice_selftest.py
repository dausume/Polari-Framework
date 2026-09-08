"""
Selftest for electrodevice (materials -> device -> SPICE -> circuit).

Run from polari-framework/:
  python3 -m electrodevice.electrodevice_selftest

Fake manager + injected executor for derivation math; the ngspice leg
runs the REAL binary when available (honest skip otherwise): the
0xA5A5 grid must show 8 lit branches with LED-range currents and 8
dark ones, and an implausible geometry must yield the
current-out-of-range verdict + a knob suggestion.
"""

import json
import sys
import types

from electrodevice.custom import device_derive as dd
from electrodevice import device_validator_basis as dv
from electrodevice import semiconductor_basis as sc
from electrodevice.custom import spice_run as sr

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
        'CircuitRunResult': {}, 'SemiconductorProfile': {},
        'DeviceValidationReport': {},
        'MaterialScaleDefinition': {}}, db=None)


def _profile(**over):
    base = dict(name='cnt-n-doped', material='n-doped-cnt',
                variant='n', sim_model='doped-cnt-fragment-energy',
                reference_model='cnt-fragment-energy', homo_ev=0.0,
                lumo_ev=0.0, gap_ev=0.0, level_shift_ev=0.0,
                carrier_type='', derived_at='', provenance_json='{}',
                notes='')
    base.update(over)
    return types.SimpleNamespace(**base)


def _dft_executor(frontiers):
    def execute(manager, name):
        homo, lumo = frontiers[name]
        return {'ok': True, 'engine': 'dft.molecular-energy',
                'result': {'homoEv': homo, 'lumoEv': lumo,
                           'gapEv': lumo - homo,
                           'frontierNote': 'Kohn-Sham approx'}}
    return execute


FRONTIERS = {  # from the LIVE staging runs 2026-07-10
    'cnt-fragment-energy': (-6.765, 0.124),
    'doped-cnt-fragment-energy': (-6.529, -0.829),
    'p-doped-cnt-fragment-energy': (-5.978, -2.742),
}


def _fet_executor(manager, name):
    return {'ok': True, 'engine': 'analytic.percolation-conductivity',
            'inputs': {'matrixSigma': 1e-12},
            'result': {'effectiveSigma': 227.267,
                       'matrixSigma': 1e-12,
                       'validity': 'idealized'}}


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

    # --- semiconductor section + validator + transistor ladder ------
    mgr2 = _mgr()
    nprof = _profile()
    rep = sc.derive_semiconductor(mgr2, nprof,
                                  executor=_dft_executor(FRONTIERS))
    check('semiconductor: N-fragment honestly classifies p (mu '
          'shifts down — the data does not demonstrate donor '
          'character at this fragment size)',
          rep['ok'] and rep['carrierType'] == 'p'
          and abs(rep['gapEv'] - 5.7) < 0.01, str(rep)[:200])
    pprof = _profile(name='cnt-p-doped', variant='p',
                     sim_model='p-doped-cnt-fragment-energy')
    rep = sc.derive_semiconductor(mgr2, pprof,
                                  executor=_dft_executor(FRONTIERS))
    check('semiconductor: B-doped classified p (mu down 1.04 eV)',
          rep['ok'] and rep['carrierType'] == 'p'
          and rep['levelShiftEv'] < -0.9)
    mgr2.objectTables['SemiconductorProfile'] = {
        nprof.name: nprof, pprof.name: pprof}

    findings = dv.validate_profile(pprof)
    check('validator: consistent derived profile passes clean',
          dv._verdict(findings) == 'valid-semiconductor-device',
          str(findings))
    findings = dv.validate_profile(nprof)
    check('validator: claimed n but the sim demonstrates p -> '
          'not-valid with evidence (the standards gate WORKING)',
          dv._verdict(findings) == 'not-valid'
          and any(f['criterion'] == 'carrier-consistent'
                  and f['status'] == 'fail' for f in findings))

    nfet = _device(name='cnt-nfet-led-switch', device_type='nfet',
                   semiconductor_profile='cnt-n-doped',
                   dielectric_material='bio-fused-silica',
                   dielectric_thickness_m=1e-7,
                   length_m=2e-5, cross_section_m2=1.4e-8,
                   threshold_v=0.0, kp_a_per_v2=0.0, r_on_ohm=0.0,
                   r_off_ohm=0.0)
    rep = dd.derive_device(mgr2, nfet, executor=_fet_executor)
    check('transistor: VTO=+gap/4, Ron/Roff from on/off sigmas',
          rep['ok'] and abs(rep['threshold_v'] - 5.7 / 4) < 0.01
          and rep['onOffRatio'] > 1e10, str(rep)[:200])
    findings = dv.validate_transistor(mgr2, nfet)
    check('validator: nfet on the inconsistent profile -> not-valid',
          dv._verdict(findings) == 'not-valid', str(findings)[:200])
    pfet_probe = _device(name='pfet-probe', device_type='pfet',
                         semiconductor_profile='cnt-p-doped',
                         dielectric_material='bio-fused-silica',
                         dielectric_thickness_m=1e-7,
                         length_m=2e-5, cross_section_m2=1.4e-8,
                         threshold_v=0.0, kp_a_per_v2=0.0,
                         r_on_ohm=0.0, r_off_ohm=0.0)
    dd.derive_device(mgr2, pfet_probe, executor=_fet_executor)
    findings = dv.validate_transistor(mgr2, pfet_probe)
    check('validator: pfet conditionally-valid (dielectric '
          'literature fallback flagged, profile clean)',
          dv._verdict(findings) == 'conditionally-valid'
          and any(f['criterion'] == 'dielectric-sourced'
                  and f['status'] == 'warn' for f in findings),
          str(findings)[:300])

    # With a real permittivity material row (Chandrashekhar & Shafer
    # data), the dielectric warn is EARNED away -> fully valid.
    mgr2.objectTables['MaterialScaleDefinition'] = {
        'sol-gel-silica@L0': _factory(
            name='sol-gel-silica@L0',
            material_name='sol-gel-silica',
            parameters_json=json.dumps({'relativePermittivity': {
                'value': 3.9, 'frequency_hz': 1e6,
                'temperature_c': 25,
                'measurement_method': 'literature',
                'confidence': 'medium'}}))}
    pfet_probe.dielectric_material = 'sol-gel-silica'
    dd.derive_device(mgr2, pfet_probe, executor=_fet_executor)
    findings = dv.validate_transistor(mgr2, pfet_probe)
    check('validator: structured permittivity record -> dielectric '
          'pass with measurement context in evidence -> fully valid',
          dv._verdict(findings) == 'valid-semiconductor-device'
          and any('confidence medium' in f['evidence']
                  for f in findings
                  if f['criterion'] == 'dielectric-sourced'),
          str(findings)[:300])
    prov = json.loads(pfet_probe.provenance_json)
    check('derive: measurement context rides device provenance',
          prov['dielectric']['measurementContext']
          .get('frequency_hz') == 1e6
          and prov['dielectric']['epsilonR'] == 3.9)

    pfet = _device(name='cnt-pfet-inverter', device_type='pfet',
                   semiconductor_profile='cnt-p-doped',
                   dielectric_material='bio-fused-silica',
                   dielectric_thickness_m=1e-7,
                   length_m=2e-5, cross_section_m2=1.4e-8,
                   threshold_v=0.0, kp_a_per_v2=0.0, r_on_ohm=0.0,
                   r_off_ohm=0.0)
    dd.derive_device(mgr2, pfet, executor=_fet_executor)
    if sr.ngspice_bin() is not None:
        run = sr.run_led_switch(mgr2, nfet, pfet, nfet, dev,
                                result_factory=_factory)
        tt = run['outputs']['truthTable']
        check('micro-circuit: truth table LED=NOT(pin), on-current '
              'in LED range',
              run['verdict'] == 'switch-works'
              and tt['pin-low']['ledCurrent_mA'] > 1.0
              and abs(tt['pin-high']['ledCurrent_mA']) < 0.01,
              json.dumps(run['outputs'])[:250])

    # --- physical size + state-space switching -----------------------
    from electrodevice.custom import switching as sw
    nfet.film_thickness_m = 1e-6
    nfet.dielectric_thickness_m = 1e-7
    geo = sw.device_geometry(nfet)
    check('geometry: width = A/t with landmark comparison',
          abs(geo['width_m'] - 0.014) < 1e-6
          and 'fingernail' in geo['widthScale'])
    ana = sw.state_space_switching(
        nfet, {'epsilonR': 3.9,
               'measurementContext': {'frequency_hz': 1e6}})
    lam = ana['stateSpace']['eigenvalues_on']
    check('state-space: triangular A eigenvalues = phase rates; '
          'delays + f_max derived',
          lam[0] < 0 and lam[1] < 0
          and ana['delays_s']['turnOn'] < ana['delays_s']['turnOff']
          and ana['maxToggle_Hz'] > 1e6)
    check('state-space: honest frequency-context note (f_max beyond '
          'the eps_r measurement frequency)',
          'EXCEEDS' in ana['frequencyContextNote'])

    # --- photo: tuning ladder + orientation + solar optimizer --------
    from electrodevice.custom import photo_derive as ph
    gaps = {'a': 6.9, 'b': 4.8, 'c': 3.3, 'd': 2.76, 'e': 2.1}
    def photo_exec(mgr_, name):
        return {'ok': True, 'engine': 'fake',
                'result': {'gapEv': gaps[name],
                           'frontierNote': 'KS approx'}}
    absorber = _factory(
        name='blue-sensor', target_wavelength_nm=450.0,
        candidates_json=json.dumps(
            [{'name': k + '-frag', 'simModel': k} for k in gaps]),
        orientation='aligned', polarization_angle_deg=0.0,
        chosen_candidate='', chosen_gap_ev=0.0,
        absorption_edge_nm=0.0, match_error_nm=0.0,
        orientation_factor=0.0, derived_at='', provenance_json='{}')
    rep = ph.tune_absorber(mgr2, absorber, executor=photo_exec)
    check('photo: tune picks the gap whose edge best matches 450 nm '
          '(2.76 eV -> 449 nm)',
          rep['ok'] and rep['chosen'] == 'd-frag'
          and abs(rep['absorptionEdge_nm'] - 449.2) < 1)
    check('photo: aligned orientation couples cos^2(0)=1; random '
          'averages 1/3',
          rep['orientationFactor'] == 1.0
          and abs(ph.orientation_factor('random', 0) - 1 / 3) < 1e-9)

    u11 = ph.ultimate_efficiency(1.1)
    check('solar: blackbody ultimate efficiency peaks near 1.1 eV '
          '(~0.44) and falls off both ways',
          0.40 < u11 < 0.48
          and ph.ultimate_efficiency(3.3) < u11
          and ph.ultimate_efficiency(0.3) < u11, str(u11))
    sq13 = ph.detailed_balance_efficiency(1.3)
    check('solar: detailed-balance (SQ) limit ~31% at 1.3 eV — '
          'BELOW single-junction physical limits, unlike ultimate',
          0.28 < sq13 < 0.33 and sq13 < u11
          and ph.detailed_balance_efficiency(2.1) < sq13, str(sq13))
    stack = _factory(
        name='panel', absorber_candidates_json=json.dumps([
            {'name': 'cu2o', 'gapRecord': {'value': 2.1},
             'demonstrated': {'value': 0.081}},
            {'name': 'pyrite', 'gapRecord': {'value': 0.95},
             'demonstrated': {'value': 0.028},
             'caveats': [{'kind': 'voc-deficit', 'note': 'x'}]},
            {'name': 'zno', 'gapRecord': {'value': 3.3}}]),
        selection_policy='sq-limit',
        chosen_absorber='', chosen_gap_ev=0.0,
        ultimate_efficiency=0.0, derived_at='',
        provenance_json='{}')
    mgr2.objectTables['SolarLayerDefinition'] = {}
    rep = ph.optimize_stack(mgr2, stack, executor=photo_exec)
    check('solar: optimizer ranks by the SQ limit (pyrite > Cu2O > '
          'ZnO) and reports BOTH ceilings',
          rep['ok'] and rep['chosen'] == 'pyrite'
          and [c['candidate'] for c in rep['ranking']]
          == ['pyrite', 'cu2o', 'zno']
          and all(c['sqLimit'] < c['ultimateEfficiency']
                  for c in rep['ranking']))
    check('solar: physics-vs-demonstrated disagreement -> the '
          'policy-knob suggestion, caveats ride the ranking',
          rep.get('suggestion', {}).get('knob', '').count(
              'selection_policy')
          and 'cu2o' in rep['suggestion']['why']
          and any(c.get('caveats') for c in rep['ranking']))
    stack.selection_policy = 'demonstrated'
    rep = ph.optimize_stack(mgr2, stack, executor=photo_exec)
    check('solar: demonstrated policy picks Cu2O (what has actually '
          'made power)',
          rep['chosen'] == 'cu2o'
          and rep['selectionPolicy'] == 'demonstrated')

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
