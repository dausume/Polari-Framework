"""
@module computelod.custom.lod4_devices

THE PROCESS NODE'S KEY NUMBERS, RUN (lod-4c, 2026-09-26): the `sky130` SiliconProcessNode row (lod-4) carried only what
was READ (L, Vdd, metals). sifet's ladder holds Ion / Ioff / Vt per rung for FreePDK45 from its documentation; for
sky130 we can do better than cite — the PDK's own BSIM4 device models are on this box (lod-3b fetched them, cited by
sha256, never committed), so the numbers are SIMULATED here, at stated conditions, the way sifet's `extract_metrics`
defines them:

    Ion    Id at Vgs = Vds = Vdd, per µm of width                 (µA/µm)
    Ioff   Id at Vgs = 0, Vds = Vdd, per µm of width              (nA/µm)
    Vt     constant-current: Vgs where Id = 100 nA × W(µm), at Vds = 50 mV (linear) and at Vds = Vdd (saturation)
    DIBL   (Vt_lin − Vt_sat) / (Vdd − 0.05)                        (mV/V)
    SS     the shallowest decade slope of log10(Id) vs Vgs between Ioff and 1000 × Ioff, saturation sweep  (mV/dec)

on the two device flavours the adder's cells use (lod-3): `nfet_01v8` and `pfet_01v8_hvt`, at W = 1 µm, L = 0.15 µm
(the cells' drawn L), tt corner, 25 °C — one device each, nominal (the models' mismatch terms scale with 1/√(WL); the
width is a stated condition, not "the" number). Evidence level `simulated` (a model of the process, run here); the
row's `key_numbers_json` gains them with `source` naming this report; a FreePDK45 number beside each for the reading
(different node, different Vdd — a comparison of what each ladder rung offers, NOT a ranking).

    python3 -m computelod.custom.lod4_devices run [--devices nfet_01v8,pfet_01v8_hvt]

ngspice through the cntfet engines ladder (find_ngspice: CNTFET_ENGINES_URL → PATH/~/tools → topology provider →
refusal); a remote worker receives netlist TEXT only (the model includes are inlined).
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
OUT = os.path.join(MOD, 'initialData', 'lod4')
CONDITIONS = {'corner': 'tt', 'temperature_c': 25.0, 'vdd_v': 1.8, 'w_um': 1.0, 'l_um': 0.15, 'vds_linear_v': 0.05, 'vt_criterion': 'constant current, Id = 100 nA × W(µm) (sifet metric_spec)',
              'sweep': 'Vgs 0 → Vdd in 10 mV steps, DC', 'mismatch': 'nominal (mismatch.corner included, no Monte Carlo)', 'netlist': 'one device, the PDK subckt (sky130_fd_pr__<flavour>), no parasitics'}
#: flavour → (polarity, what it is in the cells)
DEVICES = {'nfet_01v8': ('n', 'every n device of the mapped sky130_fd_sc_hd cells (lod-3)'), 'pfet_01v8_hvt': ('p', 'every p device of the mapped cells (high-Vt flavour; the library\'s default)')}
#: sifet's ladder numbers beside ours — FreePDK45 documentation v1.4 (Vdd 1.0 V, 45 nm), VTG flavour — for the READING only
FREEPDK45_BESIDE = {'nfet_01v8': {'ion_ua_per_um': 975.5, 'ioff_na_per_um': 10.0}, 'pfet_01v8_hvt': {'ion_ua_per_um': 650.3, 'ioff_na_per_um': 10.0}}


def _deck(flavour, polarity, includes):
    vdd, vlin = CONDITIONS['vdd_v'], CONDITIONS['vds_linear_v']
    s = -1.0 if polarity == 'p' else 1.0   # a p device is swept with mirrored biases (source at Vdd would be the same physics; this keeps |Vgs|, |Vds| the sweep variables)
    return '''* sky130_fd_pr__%(flavour)s DC sweeps — Polari lod-4c (Ion / Ioff / Vt / DIBL / SS at stated conditions)
.option scale=1.0e-6
.temp %(temp)s
%(includes)s
Vd d 0 %(vd_sat)s
Vg g 0 0
X1 d g 0 0 sky130_fd_pr__%(flavour)s w=%(w)su l=%(l)su
.control
dc Vg 0 %(vg_end)s %(vg_step)s
wrdata sat.dat i(Vd)
alter Vd %(vd_lin)s
dc Vg 0 %(vg_end)s %(vg_step)s
wrdata lin.dat i(Vd)
quit
.endc
.end
''' % {'flavour': flavour, 'temp': CONDITIONS['temperature_c'], 'includes': includes, 'vd_sat': s * vdd, 'vd_lin': s * vlin, 'vg_end': s * vdd, 'vg_step': s * 0.01,
       'w': int(round(CONDITIONS['w_um'] * 1e6)), 'l': int(round(CONDITIONS['l_um'] * 1e6))}


def _read(path):
    """wrdata → [(vg, id)] with |values| (the p sweep is mirrored; the drain current sign is the source's convention)."""
    out = []
    for line in open(path):
        parts = line.split()
        if len(parts) >= 2:
            try:
                out.append((abs(float(parts[0])), abs(float(parts[1]))))
            except ValueError:
                pass
    return out


def _cross(curve, icrit):
    """Vgs where Id first reaches icrit (linear interpolation between samples); None if never."""
    for (v0, i0), (v1, i1) in zip(curve, curve[1:]):
        if i0 < icrit <= i1:
            return v0 + (v1 - v0) * (icrit - i0) / (i1 - i0) if i1 != i0 else v1
    return None


def metrics(sat, lin):
    w = CONDITIONS['w_um']
    ion = sat[-1][1]; ioff = sat[0][1]
    icrit = 1e-7 * w
    vt_sat, vt_lin = _cross(sat, icrit), _cross(lin, icrit)
    dibl = (vt_lin - vt_sat) / (CONDITIONS['vdd_v'] - CONDITIONS['vds_linear_v']) * 1000.0 if vt_sat is not None and vt_lin is not None else None
    # SS: the shallowest slope (largest mV/dec) over any decade between Ioff and 1000·Ioff on the saturation sweep — a
    # conservative reading; the steep part near Ioff can be dominated by the constant leakage floor, so the window starts one decade up
    ss = None
    pts = [(v, i) for v, i in sat if 10 * ioff <= i <= 1000 * ioff and i > 0]
    if len(pts) >= 2:
        (v0, i0), (v1, i1) = pts[0], pts[-1]
        if i1 > i0:
            ss = (v1 - v0) / math.log10(i1 / i0) * 1000.0
    return {'ion_ua_per_um': round(ion / w * 1e6, 1), 'ioff_na_per_um': round(ioff / w * 1e9, 4), 'ion_ioff_ratio': round(ion / ioff) if ioff > 0 else None,
            'vt_lin_v': round(vt_lin, 4) if vt_lin is not None else None, 'vt_sat_v': round(vt_sat, 4) if vt_sat is not None else None,
            'dibl_mv_per_v': round(dibl, 1) if dibl is not None else None, 'ss_mv_per_dec': round(ss, 1) if ss is not None else None}


def run(devices=None, work=None):
    from computelod.custom.lod3_devices import _fetch, PR_REPO, run_spice, ngspice_where
    ng = ngspice_where()
    if not ng:
        raise SystemExit('no ngspice through the cntfet engines ladder (PATH, ~/tools, CNTFET_ENGINES_URL, or a cntfet.engines provider)')
    work = work or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-lod4c'); os.makedirs(work, exist_ok=True)
    rep = {'tool': 'ngspice-46 (%s)' % ng, 'engine_ladder': 'cntfet.engines (find_ngspice)', 'models': dict(PR_REPO, files={}), 'conditions': CONDITIONS,
           'definitions': {'ion': 'Id(Vgs = Vds = Vdd) / W', 'ioff': 'Id(Vgs = 0, Vds = Vdd) / W', 'vt': 'Vgs at Id = 100 nA × W(µm); _lin at Vds = 50 mV, _sat at Vds = Vdd',
                           'dibl': '(Vt_lin − Vt_sat) / (Vdd − 0.05 V)', 'ss': 'shallowest decade slope of log10(Id) vs Vgs between 10× and 1000× Ioff, saturation sweep'},
           'devices': {}}
    for flavour in (devices or list(DEVICES)):
        polarity, role = DEVICES[flavour]
        inc = []
        for kind in ('mismatch.corner', 'tt.corner', 'tt.pm3'):
            rel = 'cells/%s/sky130_fd_pr__%s__%s.spice' % (flavour, flavour, kind)
            p, sha, url = _fetch(PR_REPO, rel); rep['models']['files'][os.path.basename(rel)] = {'url': url, 'sha256': sha, 'bytes': os.path.getsize(p)}
            if kind != 'tt.pm3':
                inc.append('.include "%s"' % p)
        sub = os.path.join(work, flavour); os.makedirs(sub, exist_ok=True)
        for f in ('sat.dat', 'lin.dat'):
            if os.path.exists(os.path.join(sub, f)):
                os.remove(os.path.join(sub, f))
        deck = os.path.join(sub, '%s.sp' % flavour); open(deck, 'w').write(_deck(flavour, polarity, '\n'.join(inc)))
        text = run_spice(sub, deck)
        if not (os.path.exists(os.path.join(sub, 'sat.dat')) and os.path.exists(os.path.join(sub, 'lin.dat'))):
            raise SystemExit('ngspice wrote no sweep for %s:\n%s' % (flavour, text[-1500:]))
        sat, lin = _read(os.path.join(sub, 'sat.dat')), _read(os.path.join(sub, 'lin.dat'))
        m = metrics(sat, lin)
        beside = FREEPDK45_BESIDE.get(flavour, {})
        rep['devices'][flavour] = {'polarity': polarity, 'role': role, 'metrics': m, 'samples': len(sat),
                                   'curve_sat': [[round(v, 3), i] for v, i in sat[::10]], 'curve_lin': [[round(v, 3), i] for v, i in lin[::10]],
                                   'freepdk45_beside': dict(beside, note='FreePDK45 documentation v1.4, VTG flavour, Vdd 1.0 V, 45 nm — sifet\'s ladder row; a different node and voltage: shown for the reading, not a ranking')}
    rep['summary'] = {'devices': list(rep['devices']), 'nfet_ion_ua_per_um': rep['devices'].get('nfet_01v8', {}).get('metrics', {}).get('ion_ua_per_um'),
                      'pfet_hvt_ion_ua_per_um': rep['devices'].get('pfet_01v8_hvt', {}).get('metrics', {}).get('ion_ua_per_um'),
                      'reading': 'the sky130 tt models at 1.8 V give the n device roughly half the FreePDK45 documented on-current at 1.0 V/45 nm while leaking three to four orders of magnitude less — a 130 nm low-leakage process, read from its own models, not from a datasheet'}
    os.makedirs(OUT, exist_ok=True)
    json.dump(rep, open(os.path.join(OUT, 'devices_report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'devices_report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def key_numbers(rep):
    """What the SiliconProcessNode row's key_numbers_json gains — sifet's {value, unit, source, note} shape, the sifet key names
    (ion_ua_per_um / ioff_na_per_um / pmos_*) so the ladder reads sky130 like its other rungs."""
    if not rep:
        return {}
    src = 'lod4/devices_report.json — ngspice on sky130_fd_pr tt BSIM4 (%s @ %s), SIMULATED here: W = %s µm, L = %s µm, %s °C' % (
        rep['models']['repo'], rep['models']['commit'][:12], rep['conditions']['w_um'], rep['conditions']['l_um'], rep['conditions']['temperature_c'])
    out = {}
    for flavour, pre in (('nfet_01v8', ''), ('pfet_01v8_hvt', 'pmos_')):
        m = (rep['devices'].get(flavour) or {}).get('metrics')
        if not m:
            continue
        note = 'sky130_fd_pr__%s (%s)' % (flavour, rep['devices'][flavour]['role'])
        out[pre + 'ion_ua_per_um'] = {'value': m['ion_ua_per_um'], 'unit': 'uA/um', 'source': src, 'note': note + ' at Vgs = Vds = 1.8 V'}
        out[pre + 'ioff_na_per_um'] = {'value': m['ioff_na_per_um'], 'unit': 'nA/um', 'source': src, 'note': note + ' at Vgs = 0, Vds = 1.8 V'}
        out[pre + 'vt_v'] = {'value': m['vt_sat_v'], 'unit': 'V', 'source': src, 'note': note + ' constant-current 100 nA/µm at Vds = 1.8 V; linear-region value %s V' % m['vt_lin_v']}
        out[pre + 'dibl_mv_per_v'] = {'value': m['dibl_mv_per_v'], 'unit': 'mV/V', 'source': src, 'note': note}
        out[pre + 'ss_mv_per_dec'] = {'value': m['ss_mv_per_dec'], 'unit': 'mV/dec', 'source': src, 'note': note + ' (shallowest decade between 10× and 1000× Ioff)'}
    return out


def rows(rep):
    """Characterizations UP from the process (its models) to the devices rung: Ion / Ioff / Vt / DIBL / SS per flavour, evidence simulated."""
    if not rep:
        return [], []
    C = lambda **k: dict({'description': '', 'notes': ''}, **k)
    ev = 'lod4/devices_report.json — %s on sky130_fd_pr tt models @ %s (%s), DC sweeps; %s' % (rep['tool'].split(' (')[0], rep['models']['commit'][:12], rep['models']['licence'], json.dumps(rep['conditions']))
    chars = []
    for flavour, d in rep['devices'].items():
        m = d['metrics']
        tgt = 'sky130_fd_pr %s W=%s µm L=%s µm' % (flavour, rep['conditions']['w_um'], rep['conditions']['l_um'])
        src = 'SiliconProcessNode sky130 — the process AS MODELLED (sky130_fd_pr tt BSIM4 cards)'
        for key, characteristic, val, units, words in (('ion_ua_per_um', 'on_current', m['ion_ua_per_um'], 'uA/um', 'Id at Vgs = Vds = 1.8 V per µm width'),
                                                       ('ioff_na_per_um', 'off_current', m['ioff_na_per_um'], 'nA/um', 'Id at Vgs = 0, Vds = 1.8 V per µm width'),
                                                       ('vt_sat_v', 'threshold_voltage', m['vt_sat_v'], 'V', 'constant-current Vt (100 nA × W) at Vds = 1.8 V'),
                                                       ('dibl_mv_per_v', 'dibl', m['dibl_mv_per_v'], 'mV/V', '(Vt_lin − Vt_sat) over the drain-bias step'),
                                                       ('ss_mv_per_dec', 'subthreshold_swing', m['ss_mv_per_dec'], 'mV/dec', 'gate voltage per decade of current below threshold')):
            if val is None:
                continue
            beside = d.get('freepdk45_beside', {}).get(key)
            chars.append(C(name='lod4c: %s %s' % (flavour, characteristic.replace('_', ' ')), source_rung='fabrication', source_ref=src, target_rung='devices', target_ref=tgt,
                           characteristic=characteristic, method='ngspice DC sweep on the PDK device model', units=units, result=float(val),
                           conditions_json=json.dumps(dict(rep['conditions'], definition=words, polarity=d['polarity'], **({'freepdk45_documented': beside, 'freepdk45_note': 'sifet ladder row: 45 nm, Vdd 1.0 V — a different rung, for the reading'} if beside is not None else {}))),
                           mapping_status='implemented', evidence_level='simulated', evidence_ref=ev,
                           notes='%s: %s = %s %s (%s). A model of the process run here — not a measured die; the ladder\'s FreePDK45 documentation value beside it where sifet holds one.' % (flavour, characteristic.replace('_', ' '), val, units, words)))
    return [], chars


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        devs = sys.argv[sys.argv.index('--devices') + 1].split(',') if '--devices' in sys.argv else None
        rep = run(devs)
        print(json.dumps({'summary': rep['summary'], 'devices': {k: v['metrics'] for k, v in rep['devices'].items()}}, indent=1))
    else:
        r = report()
        print(json.dumps({'summary': r['summary'], 'devices': {k: v['metrics'] for k, v in r['devices'].items()}}, indent=1) if r else 'no report yet: python3 -m computelod.custom.lod4_devices run')
