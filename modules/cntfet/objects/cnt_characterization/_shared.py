"""@module cntfet.objects.cnt_characterization._shared — what the cnt_characterization row classes share (constants, seeds, helpers); split from cnt_characterization_basis.py (sap-2c)."""
from cntfet.custom.cnt_cells import (
    PARASITIC_STANDIN_F, _cards, _pwl, _read_full, _run_ngspice,
    _SUBCKTS, _tau_estimate,
)
import os
import shutil
import subprocess

DEFINITIONS = {
    'delay': 'input 50% -> output 50%',
    'transition': 'output 20% -> 80% of VDD',
    'input_slew': '20-80 time of the driving ramp',
    'liberty_units': 'time ps, capacitance fF, voltage V',
}
def _crossing(times, volts, level, rising, t_from=0.0):
    for i in range(1, len(times)):
        if times[i] <= t_from:
            continue
        lo, hi = volts[i-1], volts[i]
        if rising and lo < level <= hi:
            frac = (level - lo) / (hi - lo)
            return times[i-1] + frac * (times[i] - times[i-1])
        if not rising and lo > level >= hi:
            frac = (lo - level) / (lo - hi)
            return times[i-1] + frac * (times[i] - times[i-1])
    return None
def _measure_point(ngspice_path, workdir, osdi_path, cards, vdd,
                   slew_2080_s, load_f, tau):
    """One (slew, load) grid point: a full up/down pulse through
    the inverter; returns rise/fall delay + output transitions."""
    ramp = slew_2080_s / 0.6  # full 0->VDD ramp for a 20-80 slew
    plateau = max(400.0 * tau, 20.0 * slew_2080_s)
    t1, t2 = plateau, 2.0 * plateau
    tstop = 3.0 * plateau
    pairs = [(0.0, 0.0), (t1, 0.0), (t1 + ramp, vdd),
             (t2, vdd), (t2 + ramp, 0.0), (tstop, 0.0)]
    card_n, card_p = cards
    netlist = '\n'.join([
        '* inverter characterization point', card_n, card_p,
        _SUBCKTS,
        f'vdd vddnode 0 {vdd:.6g}',
        f'vin in 0 {_pwl(pairs)}',
        'Xdut in out vddnode cinv',
        f'Cload out 0 {load_f:.6e}',
        '.options reltol=1e-4 abstol=1e-12 method=gear',
        '.control', f'pre_osdi {osdi_path}',
        f'tran {min(tau / 4.0, ramp / 8.0):.3e} {tstop:.3e}',
        'wrdata charpoint.dat v(in) v(out)',
        'quit', '.endc', '.end', ''])
    run = _run_ngspice(ngspice_path, workdir, 'charpoint.sp',
                       netlist)
    times, v_in, v_out = [], [], []
    with open(os.path.join(workdir, 'charpoint.dat')) as fh:
        for line in fh:
            parts = line.split()
            # wrdata with two vectors: t v(in) t v(out)
            if len(parts) >= 4:
                times.append(float(parts[0]))
                v_in.append(float(parts[1]))
                v_out.append(float(parts[3]))
    if not times or times[-1] < 0.95 * tstop:
        raise RuntimeError(
            f'characterization transient TRUNCATED — '
            f'{(run.stdout + run.stderr)[-300:]}')
    half, lo20, hi80 = vdd / 2, 0.2 * vdd, 0.8 * vdd
    # input rising edge at ~t1 -> output FALLS
    t_in_rise = _crossing(times, v_in, half, True, t1 * 0.5)
    t_out_fall = _crossing(times, v_out, half, False, t1 * 0.5)
    tf_80 = _crossing(times, v_out, hi80, False, t1 * 0.5)
    tf_20 = _crossing(times, v_out, lo20, False, t1 * 0.5)
    # input falling edge at ~t2 -> output RISES
    t_in_fall = _crossing(times, v_in, half, False, t2 * 0.98)
    t_out_rise = _crossing(times, v_out, half, True, t2 * 0.98)
    tr_20 = _crossing(times, v_out, lo20, True, t2 * 0.98)
    tr_80 = _crossing(times, v_out, hi80, True, t2 * 0.98)
    if None in (t_in_rise, t_out_fall, tf_80, tf_20, t_in_fall,
                t_out_rise, tr_20, tr_80):
        raise RuntimeError('a crossing was never reached — grid '
                           'point outside the cell\'s working '
                           'range')
    return {
        'cell_fall_s': t_out_fall - t_in_rise,
        'cell_rise_s': t_out_rise - t_in_fall,
        'fall_transition_s': tf_20 - tf_80,
        'rise_transition_s': tr_80 - tr_20,
    }
def _liberty(cell, vdd, slews_s, loads_f, tables, input_cap_f):
    """Minimal NLDM Liberty: ps / fF (stated), 3x3 templates."""
    def ps(x):
        return x * 1e12

    def ff(x):
        return x * 1e15

    def table(kind):
        rows = []
        for si in range(len(slews_s)):
            vals = ', '.join(f'{ps(tables[si][li][kind]):.5g}'
                             for li in range(len(loads_f)))
            rows.append(f'        values("{vals}");'
                        if si == len(slews_s) - 1 else
                        f'        values("{vals}", \\')
        # Liberty wants one values() with row continuations:
        value_rows = ', \\\n                '.join(
            '"' + ', '.join(f'{ps(tables[si][li][kind]):.5g}'
                            for li in range(len(loads_f))) + '"'
            for si in range(len(slews_s)))
        return value_rows

    idx1 = ', '.join(f'{ps(s):.5g}' for s in slews_s)
    idx2 = ', '.join(f'{ff(c):.5g}' for c in loads_f)
    tpl = (f'    lu_table_template (tpl_{len(slews_s)}x'
           f'{len(loads_f)}) {{\n'
           '      variable_1 : input_net_transition;\n'
           '      variable_2 : total_output_net_capacitance;\n'
           f'      index_1 ("{idx1}");\n'
           f'      index_2 ("{idx2}");\n    }}\n')

    def timing_block(kind):
        return (f'          {kind} (tpl_{len(slews_s)}x'
                f'{len(loads_f)}) {{\n'
                f'            index_1 ("{idx1}");\n'
                f'            index_2 ("{idx2}");\n'
                f'            values ( \\\n                '
                f'{table(_KIND_MAP[kind])} );\n'
                '          }\n')

    return (
        'library (polari_cnt) {\n'
        '  /* generated by cntfet.cnt_characterization_basis — '
        'executor polari-own-loop.\n'
        '     UNITS: time ps, capacitance fF. INTRINSIC-grade '
        'numbers (S1 model,\n'
        '     no junction parasitics beyond the labeled '
        'stand-ins); 50/50 charge\n'
        '     partition (delay-grade). NOT signoff (plan D1). */\n'
        '  delay_model : table_lookup;\n'
        '  time_unit : "1ps";\n'
        '  capacitive_load_unit (1, ff);\n'
        '  voltage_unit : "1V";\n'
        '  current_unit : "1uA";\n'
        '  pulling_resistance_unit : "1kohm";\n'
        '  leakage_power_unit : "1nW";\n'
        f'  nom_voltage : {vdd};\n'
        '  nom_temperature : 300;\n'
        '  nom_process : 1;\n'
        f'{tpl}'
        f'  cell ({cell}) {{\n'
        '    pin (A) {\n'
        '      direction : input;\n'
        f'      capacitance : {ff(input_cap_f):.5g};\n'
        '    }\n'
        '    pin (Y) {\n'
        '      direction : output;\n'
        '      function : "(!A)";\n'
        '      timing () {\n'
        '        related_pin : "A";\n'
        '        timing_sense : negative_unate;\n'
        f'{timing_block("cell_rise")}'
        f'{timing_block("cell_fall")}'
        f'{timing_block("rise_transition")}'
        f'{timing_block("fall_transition")}'
        '      }\n'
        '    }\n'
        '  }\n'
        '}\n')
_KIND_MAP = {'cell_rise': 'cell_rise_s',
             'cell_fall': 'cell_fall_s',
             'rise_transition': 'rise_transition_s',
             'fall_transition': 'fall_transition_s'}
def _find_sta_local():
    sta = shutil.which('sta') or shutil.which('opensta')
    if sta:
        return sta, sta
    return None, ('OpenSTA not installed (no `sta`/`opensta` on PATH; '
                  'install parallaxsw/OpenSTA or the openroad/opensta '
                  'docker wrapper)')
def find_sta():
    """OpenSTA per the dist ladder (cnt_remote.resolve): the
    CNTFET_ENGINES_URL worker wins, else local, else the topology's
    cnt-engines provider. (path | 'remote', detail) or (None, why)."""
    from cntfet.cnt_remote import resolve
    return resolve('opensta', _find_sta_local)
def run_sta(sta_path, workdir, script_text, files=(), timeout=180):
    """Run one OpenSTA tcl script whose file references are
    BASENAMES relative to workdir (the remote worker recreates the
    directory from `files`). Returns an object with
    returncode/stdout/stderr like subprocess.run; remote transport
    failure = returncode -1 with the reason in stderr."""
    import types
    from cntfet.cnt_remote import REMOTE, RemoteError, remote_post
    if sta_path != REMOTE:
        script = os.path.join(workdir, 'run.tcl')
        with open(script, 'w') as fh:
            fh.write(script_text)
        return subprocess.run([sta_path, '-no_splash', '-exit', script],
                              capture_output=True, text=True,
                              timeout=timeout, cwd=workdir)
    payload_files = {}
    for name in files:
        with open(os.path.join(workdir, name)) as fh:
            payload_files[name] = fh.read()
    try:
        rep = remote_post('/sta/run', {'files': payload_files,
                                       'script': script_text,
                                       'timeout': timeout},
                          timeout=timeout + 60)
    except RemoteError as exc:
        return types.SimpleNamespace(returncode=-1, stdout='',
                                     stderr=f'cnt-engines: {exc}')
    if not rep.get('ok'):
        return types.SimpleNamespace(
            returncode=-1, stdout='',
            stderr=f'cnt-engines: {rep.get("error", rep)}')
    return types.SimpleNamespace(returncode=rep.get('returncode', 0),
                                 stdout=rep.get('stdout', ''),
                                 stderr=rep.get('stderr', ''))
def _sta_gate(workdir, liberty_text):
    """OpenSTA acceptance: load the library, report a trivial
    path. Absent binary = recorded refusal (the D11 SPICE-vs-STA
    cross-check stays an OPEN box until then)."""
    sta, why = find_sta()
    if not sta:
        return {'ran': False,
                'refusal': f'{why} — the MANDATORY D11 SPICE-vs-STA '
                           f'cross-check remains OPEN'}
    lib_path = os.path.join(workdir, 'polari_cnt.lib')
    with open(lib_path, 'w') as fh:
        fh.write(liberty_text)
    run = run_sta(sta, workdir,
                  'read_liberty polari_cnt.lib\n'
                  'puts "LIBERTY-ACCEPTED"\nexit\n',
                  files=('polari_cnt.lib',), timeout=120)
    accepted = 'LIBERTY-ACCEPTED' in run.stdout
    return {'ran': True, 'accepted': accepted, 'where': why,
            'output': (run.stdout[-500:] + run.stderr[-300:])
            if not accepted else 'LIBERTY-ACCEPTED'}
