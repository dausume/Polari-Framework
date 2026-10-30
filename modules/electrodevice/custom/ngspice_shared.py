"""
@module electrodevice.custom.ngspice_shared

kxc-3 (KICAD_INTERCHANGE_PLAN.md): ngspice as a SHARED LIBRARY beside the executable (electrodevice.custom.spice_run). KiCad installs libngspice without
an ngspice program (econ-core: libngspice.so.0, no binary), so the simulation capability is two separate things, each said:

  capability()            {'executable': path | '', 'shared_library': name | '', 'available': bool, 'suggestion'}
  run(deck, files=None, timeout=60)  → {'ok', 'engine', 'plot', 'vectors', 'errors'} | {'ok': False, 'refused': why}
                          writes the deck (+ the model files it includes) into a temp dir and runs the standalone runner script in its OWN process
                          (bounded by `timeout`; a solver crash stays in that process). The shared library first, else the executable in batch mode
                          (its raw output is not parsed into vectors here - the result says so).
"""
import ctypes.util
import json
import os
import subprocess
import sys
import tempfile

RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ngspice_shared_runner.py')


def capability():
    from electrodevice.custom.spice_run import ngspice_bin
    exe, lib = ngspice_bin() or '', ctypes.util.find_library('ngspice') or ''
    return {'executable': exe, 'shared_library': lib, 'available': bool(exe or lib),
            'suggestion': None if (exe or lib) else {'knob': 'install KiCad (it ships libngspice) or ngspice; NGSPICE_BIN for an executable',
                                                    'where': 'econ-core has libngspice (KiCad 10.0.6)'}}


def run(deck, files=None, timeout=60):
    cap = capability()
    if not cap['shared_library']:
        return {'ok': False, 'refused': 'no ngspice shared library on this host (%s)' % ('an executable exists: %s - batch mode is spice_run\'s' % cap['executable']
                                                                                         if cap['executable'] else 'and no executable'), 'capability': cap}
    with tempfile.TemporaryDirectory(prefix='ngspice-') as d:
        for name, text in (files or {}).items():
            fp = os.path.join(d, os.path.basename(name))
            open(fp, 'w').write(text)
        path = os.path.join(d, 'deck.cir')
        open(path, 'w').write(deck)
        try:
            p = subprocess.run([sys.executable, '-I', RUNNER, path], cwd=d, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {'ok': False, 'refused': 'the solver ran past %d s and was stopped' % timeout}
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'ok': False, 'refused': 'the runner returned no result (exit %s): %s' % (p.returncode, (p.stderr or '')[-400:])}
    res['engine'] = 'libngspice (%s)' % res.get('library', '')
    return res
