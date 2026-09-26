"""
@module computelod.custom.repro

THE REPRODUCTION RECORD (his rule, 2026-09-26: "the main thing we should focus on keeping is the initial conditions and
seeds used so it is reproducible, in addition to the results"). Every flow that commits a report under initialData/ attaches
a `reproduction` block built here, one shape for all of them:

    inputs           every file the flow read, by sha256 (a cached PDK/Liberty file is cited by url + sha256, never committed)
    tools            {engine: version line} through the engines ladder (the version of the binary that RAN, wherever it ran)
                     + {image: id/digest} for the pinned images on this device
    knobs            the values a person chose (utilization, budgets, corner, W/L …) — each one a stated decision
    conditions       the physical/analysis conditions the numbers depend on
    generated_files  the decks, configs, Tcl and netlists the flow WROTE, copied beside the report and hashed — the exact
                     text the tool consumed, not a description of it
    seeds            {name: value} for every random element, or {'deterministic': True, 'why': …} — never implicit
    recorded_at / host / how_to_rerun

`attached_after_the_fact` marks a block computed from committed artefacts for a flow that was NOT re-run (the tool versions
are then those on this device at recording time, said so). The explainer's "how to reproduce" points at the block.

    python3 -m computelod.custom.repro attach      # attach blocks to the two reports whose flows are not re-run here (lod-2b's characterization, the fpga kernel)
    python3 -m computelod.custom.repro check       # every committed report has a complete block
"""
import datetime
import glob
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
MODULES = os.path.dirname(MOD)
REQUIRED = ('inputs', 'tools', 'knobs', 'conditions', 'generated_files', 'seeds', 'recorded_at', 'how_to_rerun')
#: the version argv per engine (the engines ladder runs it wherever the engine lives)
VERSION_ARGS = {'riscv-gcc': ['--version'], 'yosys': ['-V'], 'iverilog': ['-V'], 'vvp': ['-V'], 'verilator': ['--version'], 'nextpnr-ice40': ['--version'], 'icetime': ['-h'],
                'sta': ['-version'], 'magic': ['--version'], 'netgen': ['-batch', 'quit'], 'openroad': ['-version']}
_VERSION_CACHE = {}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _rel(path):
    try:
        return os.path.relpath(path, MODULES)
    except ValueError:
        return path


def file_entry(path, label=''):
    e = {'file': _rel(path), 'sha256': sha(path), 'bytes': os.path.getsize(path)}
    if label:
        e['label'] = label
    return e


def tool_version(engine):
    """The first line the engine prints for its version argv, through the engines ladder; '' when it cannot be asked."""
    if engine in _VERSION_CACHE:
        return _VERSION_CACHE[engine]
    out = ''
    try:
        if engine == 'ngspice':
            from cntfet.custom.cnt_osdi import find_ngspice
            path, _ = find_ngspice()
            if path and path != 'remote':
                p = subprocess.run([path, '-v'], capture_output=True, text=True, timeout=30)
                out = ' '.join(l.strip(' *') for l in (p.stdout or '').splitlines() if 'ngspice' in l.lower())[:120] or (p.stdout or '').strip()[:120]
            elif path == 'remote':
                out = 'remote worker (cntfet.engines)'
        elif engine in VERSION_ARGS:
            from computelod.custom.eda_engines import resolve, run as _run
            r = resolve(engine)
            if r['how'] != 'refused':
                work = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'polari-repro'); os.makedirs(work, exist_ok=True)
                res = _run(engine, work, VERSION_ARGS[engine], timeout=120)
                text = (res['stdout'] or '') + (res['stderr'] or '')
                lines = [l.strip() for l in text.splitlines() if l.strip() and not l.lower().startswith('warning')]
                out = (lines[0] if lines else '')[:160] + ' [%s: %s]' % (r['how'], r['where'])
    except Exception as exc:   # a version that cannot be asked is recorded as such, never invented
        out = 'not askable here (%s)' % exc
    _VERSION_CACHE[engine] = out
    return out


def images():
    """{image: id or repo digest} for the pinned images present on this device."""
    try:
        from computelod.custom.eda_engines import IMAGE, STA_IMAGE, ORFS_IMAGE
        names = [IMAGE, STA_IMAGE, ORFS_IMAGE]
    except Exception:   # pragma: no cover
        names = []
    out = {}
    for img in names:
        try:
            p = subprocess.run(['docker', 'image', 'inspect', img, '--format', '{{.Id}}|{{join .RepoDigests ","}}'], capture_output=True, text=True, timeout=20)
            if p.returncode == 0:
                iid, digs = (p.stdout.strip().split('|') + [''])[:2]
                out[img] = {'id': iid, 'repo_digest': digs.split(',')[0] if digs else '(local build, no registry digest)'}
        except Exception:
            pass
    return out


def keep_generated(work, out_dir, patterns=('*.sp', '*.tcl', '*.mk', '*.sdc', '*.v', '*.json', '*.txt', '*.log'), exclude=('remote.sp',), max_bytes=400_000):
    """Copy the flow's generated text files from its work dir beside the report (small ones; never PDK-derived netlists — the
    caller passes a work dir that holds only what the flow wrote) and return their entries."""
    os.makedirs(out_dir, exist_ok=True)
    entries = []
    for pat in patterns:
        for src in sorted(glob.glob(os.path.join(work, pat))):
            base = os.path.basename(src)
            if any(base.endswith(x) for x in exclude) or os.path.getsize(src) > max_bytes:
                continue
            dst = os.path.join(out_dir, base); shutil.copy(src, dst); entries.append(file_entry(dst))
    return entries


def record(flow, inputs=(), engines=(), tools=None, knobs=None, conditions=None, generated=(), seeds=None, deterministic='', notes='', after_the_fact=''):
    """One reproduction block. `inputs`: paths, (label, path) pairs, or dicts already carrying url/sha256. `seeds`: a dict of
    every random element, or None with `deterministic` = why there is none."""
    ins = []
    for x in inputs:
        if isinstance(x, dict):
            ins.append(x)
        elif isinstance(x, (tuple, list)):
            ins.append(file_entry(x[1], x[0]))
        else:
            ins.append(file_entry(x))
    t = dict(tools or {})
    for e in engines:
        t[e] = tool_version(e)
    t['images'] = images()
    gen = []
    for g in generated:
        gen.append(g if isinstance(g, dict) else file_entry(g))
    if seeds is None:
        seeds_out = {'deterministic': True, 'why': deterministic or 'no random element: fixed inputs, deterministic tools'}
    else:
        seeds_out = dict(seeds)
    blk = {'inputs': ins, 'tools': t, 'knobs': knobs or {}, 'conditions': conditions or {}, 'generated_files': gen, 'seeds': seeds_out,
           'recorded_at': datetime.datetime.now().isoformat(timespec='seconds'), 'host': {'node': platform.node(), 'machine': platform.machine(), 'python': platform.python_version()},
           'how_to_rerun': 'PYTHONPATH=.:modules python3 -m %s run' % flow, 'rule': 'every result carries the initial conditions and seeds that produced it (2026-09-26)'}
    if notes:
        blk['notes'] = notes
    if after_the_fact:
        blk['attached_after_the_fact'] = after_the_fact
    return blk


def complete(block):
    """(ok, missing) — the block has every required key, every input a hash or url, and a seed posture."""
    if not isinstance(block, dict):
        return False, ['no block']
    missing = [k for k in REQUIRED if k not in block]
    if any(not (i.get('sha256') or i.get('url')) for i in block.get('inputs', []) if isinstance(i, dict)):
        missing.append('inputs without sha256/url')
    s = block.get('seeds')
    if not (isinstance(s, dict) and (s.get('deterministic') is True or any(k != 'deterministic' for k in s))):
        missing.append('seeds')
    return not missing, missing


# ---------------------------------------------------------------- reports whose flows are not re-run here: attach from the committed artefacts
def _p(*parts):
    return os.path.join(MOD, 'initialData', *parts)


def _attach(path, block):
    rep = json.load(open(path)); rep['reproduction'] = block
    json.dump(rep, open(path, 'w'), indent=1)
    return path


def attach_all():
    done = []
    rtl = os.path.join(HERE, 'rtl', 'picorv32', 'picorv32.v')
    # lod-2b: the CNT Liberty (a characterization run on this instance's derived device) + mapping + OpenSTA
    r2c = json.load(open(_p('lod2', 'cnt', 'report.json')))
    done.append(_attach(_p('lod2', 'cnt', 'report.json'), record('computelod.custom.lod2_cnt', inputs=[('RTL (lod-1)', _p('lod1', 'rv32_add.v')), ('OUR CNT Liberty (characterized here; committed)', _p('lod2', 'cnt', 'polari_cnt_lib.lib'))],
                                                                engines=['yosys', 'sta', 'ngspice'], tools={'characterization': (r2c.get('characterization') or {}).get('executor', ''), 'osdi_model': 'OpenVAF-compiled VS model (cntfet.custom.cnt_osdi)'},
                                                                knobs={'device': r2c.get('device'), 'partner': (r2c.get('partner') or {}).get('name'), 'vdd_v': (r2c.get('characterization') or {}).get('vdd_v'), 'drives': [1], 'cells': [c['cell'] for c in (r2c.get('characterization') or {}).get('cells', [])],
                                                                       'slew_grid_s': (r2c.get('characterization') or {}).get('grid_slews_s'), 'load_grid_f': (r2c.get('characterization') or {}).get('grid_loads_f')},
                                                                conditions=r2c.get('conditions', {}), generated=[_p('lod2', 'cnt', f) for f in ('rv32_add_cnt.v', 'sta.tcl', 'mapped_stat.json', 'sta.log', 'map.log') if os.path.exists(_p('lod2', 'cnt', f))],
                                                                deterministic='the S5 characterization sweep is ngspice transient analysis on fixed decks (no Monte Carlo: CNTFETMonteCarloRun is a different row and was not used); yosys/abc/OpenSTA deterministic',
                                                                after_the_fact='the characterization ran 2026-09-24 (CellCharacterizationRun %s, derived device %s at %s); not re-run here — the Liberty it wrote is committed and hashed above' % (
                                                                    (r2c.get('characterization') or {}).get('result_row'), r2c.get('device'), (r2c.get('derivation') or {}).get('derived_at', '')[:19]))))
    # tensormath fpga: the tt-3 kernel (needs a manager to re-run; attached from the committed sources + tool versions now)
    fp = os.path.join(MODULES, 'tensormath', 'initialData', 'fpga')
    if os.path.exists(os.path.join(fp, 'report.json')):
        rf = json.load(open(os.path.join(fp, 'report.json')))
        done.append(_attach(os.path.join(fp, 'report.json'), record('tensormath.custom.fpga_kernel (run(manager) — see tests/tensor_liveboot_probe.py)', inputs=[(l, os.path.join(fp, f)) for l, f in (('kernel RTL', 'stress_mac.v'), ('top (register bus)', 'stress_mac_top.v'), ('testbench', 'tb_stress_mac.v'))],
                                                                    engines=['yosys', 'nextpnr-ice40', 'iverilog'], knobs={'fixed_point': rf.get('fixed_point'), 'part': 'iCE40 HX8K ct256', 'nextpnr_freq_target_mhz': 50, 'case': rf.get('case')},
                                                                    conditions={'elements': rf.get('elements')}, generated=[os.path.join(fp, f) for f in ('ice_stat.json', 'pnr.json') if os.path.exists(os.path.join(fp, f))],
                                                                    seeds={'nextpnr-ice40 --seed': 'not passed → nextpnr default (1); the placement is seeded, the seed is this default — pass --seed to perturb'},
                                                                    after_the_fact='the flow ran 2026-09-23 (tt-3); it needs a live manager to re-run (the FEM case), so the block is attached from the committed sources with the tool versions askable now')))
    return done


def all_reports():
    out = [p for p in glob.glob(os.path.join(MOD, 'initialData', '**', '*.json'), recursive=True) if not any(x in os.path.basename(p) for x in ('stat', '6_report', 'ice_stat', 'pnr.json'))]
    fp = os.path.join(MODULES, 'tensormath', 'initialData', 'fpga', 'report.json')
    return sorted(out + ([fp] if os.path.exists(fp) else []))


def check_all():
    res = {}
    for p in all_reports():
        try:
            ok, missing = complete(json.load(open(p)).get('reproduction'))
        except Exception as exc:
            ok, missing = False, [str(exc)]
        res[_rel(p)] = {'ok': ok, 'missing': missing}
    return res


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'attach':
        print(json.dumps([_rel(p) for p in attach_all()], indent=1))
    else:
        print(json.dumps(check_all(), indent=1))
