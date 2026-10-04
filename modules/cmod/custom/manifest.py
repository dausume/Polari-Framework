"""
@module cmod.custom.manifest

`polari-firmware.json` — THE CONFORMED MANIFEST of a C project (C_MODULARIZATION_PLAN.md §2), the C counterpart of
`polari-app.json` (moduleService.manifests): DERIVED from the sources by the atom parser + the measured cost, never
hand-maintained. It lives in the project's root beside its Makefile (a person's own project carries it like any other
file; `make` never reads it).

  generate(project)   parse every configuration + measure → the manifest dict (nothing written)
  conform(project)    generate, keep the HAND-SET fields of the file on disk (title / description / notes at the top, per
                      atom `title` / `notes` — like manifests._preserve_hand_set), and write ONLY when something derived
                      changed — so a second conform changes nothing (the idempotence proof)

    python3 -m cmod.custom.manifest conform uno | <dir> [--no-measure]
"""
import datetime
import hashlib
import json
import os

from cmod.custom import analyse as AN
from cmod.custom import measure as M
from cmod.custom import preprocess as PP
from cmod.custom import projects as P
from cmod.custom import registers as R

SCHEMA = 'polari-firmware/1'
HAND_TOP = ('title', 'description', 'notes')
HAND_ATOM = ('title', 'notes')
VOLATILE = ('conformed_at',)


def _sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def _parser_block(mcu):
    import pycparser
    reg = R.load(mcu)
    return {'engine': 'pycparser', 'version': pycparser.__version__, 'licence': 'BSD-3-Clause',
            'runs': 'in the framework process (pure Python; cffi already pins it — requirements.txt pycparser==2.21)',
            'preprocessor': 'pycparser.ply.cpp (pure Python) + cmod fake avr-libc headers', 'fake_headers_sha256': PP.fake_headers_sha(),
            'registers': {'mcu': mcu, 'avr_libc': reg.get('avr_libc', ''), 'dm_sha256': reg.get('dm_sha256', ''),
                          'count': len(reg.get('registers', {})), 'vectors': len(reg.get('vectors', {}))}}


def _cost(atom, sym, meas_by_cfg, cfg_order, called=()):
    cfgs = [c for c in cfg_order if c in atom['configs'] and c in meas_by_cfg]
    if not cfgs:
        return {'text_bytes': None, 'stack_bytes': None, 'measured_in': '', 'why': 'not measured (no engine)'}
    ref = meas_by_cfg[cfgs[0]]['modes']
    sh, ni = ref['shipped'], ref['noinline']
    t_sh, t_ni = sh['text'].get(sym), ni['text'].get(sym)
    s_sh, s_ni = sh['stack'].get(sym), ni['stack'].get(sym)
    texts = sorted({meas_by_cfg[c]['modes']['shipped']['text'].get(sym, 0) for c in cfgs})
    c = {'measured_in': cfgs[0], 'symbol': sym,
         'text_bytes': t_sh if t_sh is not None else 0, 'in_shipped_build': t_sh is not None,
         'inlined': t_sh is None and t_ni is not None and atom['function'] in called,
         'text_bytes_noinline': t_ni if t_ni is not None else 0,
         'stack_bytes': (s_sh or s_ni or {}).get('bytes'), 'stack_kind': (s_sh or s_ni or {}).get('kind', ''),
         'stack_from': 'shipped' if s_sh else 'noinline' if s_ni else '',
         'stack_bytes_noinline': (s_ni or {}).get('bytes'), 'text_bytes_range': [texts[0], texts[-1]]}
    why = []
    if t_sh is None and t_ni is None:
        why.append('no symbol in either build')
    elif t_sh is None:
        why.append(('inlined into its caller in the shipped build (no symbol)' if atom['function'] in called else
                    'removed from the shipped build by --gc-sections (no C caller in %s)' % cfgs[0]) + '; text_bytes_noinline is its cost as a node')
    if c['stack_bytes'] is None:
        why.append('no .su frame: GCC cannot compute the stack of a naked function (it has no prologue)')
    if why:
        c['why'] = '; '.join(why)
    return c


def _symbol(atom, mcu):
    if atom['isr']:
        n = R.load(mcu)['vectors'].get(atom['isr'])
        return '__vector_%s' % n if n is not None else atom['isr']
    return atom['function']


def generate(project, measure=True, make_proof=True):
    parsed = AN.parse_project(project)
    spec = parsed['spec']
    mcu = spec['mcu']
    meas, make = {}, {}
    if measure:
        for cfg in parsed['configs']:
            srcs = sorted(f for f in os.listdir(cfg['dir']) if f.endswith('.c'))
            meas[cfg['name']] = M.measure(cfg['dir'], srcs)
            if make_proof and spec['kind'] == 'template':
                make[cfg['name']] = M.make_alone(cfg['dir'])
    order = [c['name'] for c in parsed['configs']]
    called = {c for a in parsed['atoms'].values() for c in a['calls']} | {c for f in parsed['library'].values() for c in f['calls']}
    atoms = []
    for key in sorted(parsed['atoms']):
        a = parsed['atoms'][key]
        ann = a.get('annotation')
        atoms.append({
            'name': key, 'function': a['function'], 'module': a['module'], 'line': a['line'],
            'kind': 'isr' if a['isr'] else 'entry' if a['function'] == 'main' else 'function', 'isr_vector': a['isr'],
            'signature': AN.signature(a), 'static': a['static'], 'signature_varies': bool(a.get('signature_varies')),
            'ports': a['ports'], 'resources': AN.resources(a, mcu), 'calls': a['calls'],
            'pure': a['pure'], 'pure_why': a['pure_why'], 'isr_safe': a['isr_safe'], 'isr_safe_why': a['isr_safe_why'],
            'atomic_block': a['atomic'], 'configs': a['configs'],
            'annotation': {'form': ann['form'], 'line': ann['line'], 'role': ann['role'], 'uses': ann['uses'], 'raw': ann['raw']} if ann else None,
            'cost': _cost(a, _symbol(a, mcu), meas, order, called) if meas else None,
            'title': '', 'notes': ''})
    modules = []
    for name, files, role in spec['modules']:
        present = [f for f in files if os.path.isfile(os.path.join(spec['root'], f))]
        if not present:
            continue
        modules.append({'name': name, 'role': role, 'files': [{'path': f, 'sha256': _sha(os.path.join(spec['root'], f))} for f in present],
                        'atoms': [x['name'] for x in atoms if x['module'] in present]})
    first = next(iter(meas.values()), None)
    configs = []
    for c in parsed['configs']:
        rec = {k: c[k] for k in ('name', 'kind', 'app', 'flags', 'sources', 'generated', 'source_sha')}
        if c['name'] in meas:
            rec['elf_sha256'] = {m: meas[c['name']]['modes'][m]['elf_sha256'] for m in ('shipped', 'noinline')}
        if c['name'] in make:
            rec['make_alone'] = {'ok': make[c['name']]['ok'], 'hex_sha256': make[c['name']]['hex_sha256']}
        configs.append(rec)
    return {
        'schema': SCHEMA, 'project': spec['name'], 'kind': spec['kind'], 'title': spec['title'], 'description': '', 'notes': '',
        'root': spec['root_rel'], 'board': spec['board'], 'mcu': mcu, 'parser': _parser_block(mcu),
        'build': ({'cc': first['cc'], 'cflags': first['cflags'], 'ldflags': first['ldflags'], 'from': 'the project Makefile',
                   'measure': 'shipped = the Makefile flags + -fstack-usage -Wno-error (no code change); noinline = + -fno-inline; text = nm -S --size-sort; stack = the .su frame',
                   'cc_version': _cc_version(first['cc'])} if first else None),
        'configurations': configs, 'modules': modules, 'atoms': atoms,
        'counts': {'atoms': len(atoms), 'annotated': sum(1 for x in atoms if x['annotation']), 'isr': sum(1 for x in atoms if x['kind'] == 'isr'),
                   'pure': sum(1 for x in atoms if x['pure']), 'ports': sum(len(x['ports']) for x in atoms),
                   'not_isr_safe': sum(1 for x in atoms if x['isr_safe'] in ('no', 'undetermined'))},
        'problems': parsed['problems'], 'annotated_not_compiled': parsed['annotated_not_compiled'],
        'derived_by': 'cmod.custom.manifest generate — never edit by hand except title / description / notes (top and per atom)'}


def _cc_version(cc):
    try:
        if cc.startswith('avr-'):
            from board.custom import engine_run
            return engine_run.version('avr-gcc')
        import subprocess
        return subprocess.run([cc, '--version'], capture_output=True, text=True, timeout=30).stdout.splitlines()[0]
    except Exception:
        return ''


def load(path):
    return json.load(open(path)) if os.path.isfile(path) else None


def preserve_hand_set(fresh, old):
    if not old:
        return fresh
    for k in HAND_TOP:
        if old.get(k):
            fresh[k] = old[k]
    prev = {a['name']: a for a in old.get('atoms', [])}
    for a in fresh['atoms']:
        for k in HAND_ATOM:
            if prev.get(a['name'], {}).get(k):
                a[k] = prev[a['name']][k]
    return fresh


def _comparable(m):
    return {k: v for k, v in (m or {}).items() if k not in VOLATILE}


def validate(m):
    problems = []
    if m.get('schema') != SCHEMA:
        problems.append('schema must be %r' % SCHEMA)
    for k in ('project', 'kind', 'atoms', 'modules', 'parser', 'configurations'):
        if k not in m:
            problems.append('missing %r' % k)
    names = [a.get('name') for a in m.get('atoms', [])]
    if len(names) != len(set(names)):
        problems.append('duplicate atom names')
    for a in m.get('atoms', []):
        for k in ('ports', 'resources', 'calls', 'cost', 'isr_safe', 'pure'):
            if k not in a:
                problems.append('%s: missing %r' % (a.get('name'), k))
    return problems


def conform(project, measure=True, write=True):
    spec = P.resolve(project)
    path = P.manifest_path(spec)
    old = load(path)
    fresh = generate(project, measure=measure)
    if not measure and old:   # keep the measured blocks of atoms whose module did not change
        osha = {f['path']: f['sha256'] for mm in old.get('modules', []) for f in mm['files']}
        nsha = {f['path']: f['sha256'] for mm in fresh['modules'] for f in mm['files']}
        prev = {a['name']: a for a in old.get('atoms', [])}
        for a in fresh['atoms']:
            if a['name'] in prev and osha.get(a['module']) == nsha.get(a['module']):
                a['cost'] = prev[a['name']].get('cost')
        fresh['build'] = old.get('build')
        fresh['configurations'] = [dict(c, **{k: v for k, v in next((o for o in old.get('configurations', []) if o['name'] == c['name']), {}).items()
                                              if k in ('elf_sha256', 'make_alone')}) for c in fresh['configurations']]
    fresh = preserve_hand_set(fresh, old)
    changed = _comparable(fresh) != _comparable(old)
    before = {a['name'] for a in (old or {}).get('atoms', [])}
    after = {a['name'] for a in fresh['atoms']}
    edited = sorted(a['name'] for a in fresh['atoms'] if a['name'] in before and a != next(x for x in old['atoms'] if x['name'] == a['name']))
    if changed and write:
        fresh['conformed_at'] = datetime.datetime.now().isoformat(timespec='seconds')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(fresh, fh, indent=1, ensure_ascii=False)
            fh.write('\n')
    elif old:
        fresh['conformed_at'] = old.get('conformed_at', '')
    return {'ok': not validate(fresh), 'path': path, 'changed': changed, 'written': bool(changed and write), 'problems': validate(fresh),
            'added': sorted(after - before), 'removed': sorted(before - after), 'edited': edited, 'manifest': fresh}


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='python3 -m cmod.custom.manifest')
    ap.add_argument('verb', choices=('conform', 'generate'))
    ap.add_argument('project')
    ap.add_argument('--no-measure', action='store_true')
    a = ap.parse_args(argv)
    if a.verb == 'generate':
        print(json.dumps(generate(a.project, measure=not a.no_measure), indent=1))
        return 0
    r = conform(a.project, measure=not a.no_measure)
    print('%s %s — %d atoms (%s)' % ('wrote' if r['written'] else 'unchanged', r['path'], r['manifest']['counts']['atoms'],
                                    ', '.join('%s %d' % (k, v) for k, v in r['manifest']['counts'].items() if k != 'atoms')))
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
