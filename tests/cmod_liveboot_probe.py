"""In-process live-boot PROBE of cmod-0 (C_MODULARIZATION_PLAN.md §10): boot the REAL polariServer with cmod (+ board and what
board needs) enabled and hit its routes — the guarded imports, defClassList, the seeds (the UNO's committed polari-firmware.json
projected into rows), the page seed and the routes outside the selftest. With --engines (the board engines seam must resolve):
the BYTE-IDENTICAL proof — every shipped UNO variant built from the annotated template AND from a copy with every POLARI_NODE
annotation stripped, through board's own gen + build; the .hex shas must match.
Run from a THROWAWAY working directory (the boot writes its sqlite DB into ./data/ of the cwd):
  cd /tmp/somewhere && PYTHONPATH=<framework>:<framework>/modules python3 <framework>/tests/cmod_liveboot_probe.py [--engines]
"""
import json
import os
import shutil
import sys
import tempfile
os.environ['POLARI_MODULES'] = 'techtree,hwmap,hardwareapps,islemesh,grpcbridge,board,cmod'
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
results = []


def check(label, cond, extra=''):
    results.append(bool(cond)); print(('PASS' if cond else 'FAIL') + f': {label}' + (f'  [{extra}]' if extra and not cond else ''))


def byte_identical():
    """Annotated template vs the same template with every annotation line removed → the same .hex for every variant."""
    from board.custom import gen, build
    from board.custom import board_engines as be
    from board.custom.variants import SEED_FIRMWARE_VARIANTS
    from cmod.custom.annotation import find
    if be.resolve('avr-gcc')['how'] == 'refused':
        print('SKIP: no avr-gcc through the board engines seam — the byte-identical proof needs the engine')
        return
    tpl = gen.TEMPLATES['arduino-uno-r3']
    stripped = tempfile.mkdtemp(prefix='cmod-stripped-')
    shutil.copytree(tpl, stripped, dirs_exist_ok=True)
    removed = 0
    for d, _dirs, files in os.walk(stripped):
        for f in files:
            if f.endswith('.c'):
                p = os.path.join(d, f)
                lines = open(p).read().split('\n')
                drop = set()
                for a in find(open(p).read(), f):   # the annotation's own line span (strings may hold parentheses)
                    drop |= set(range(a['line'] - 1, a['end_line']))
                    removed += 1
                open(p, 'w').write('\n'.join(x for i, x in enumerate(lines) if i not in drop))
    check('the stripped copy lost all 12 annotations (and nothing else matched)', removed == 12, removed)
    shas = {}
    for which, root in (('annotated', tpl), ('stripped', stripped)):
        gen.TEMPLATES['arduino-uno-r3'] = root
        try:
            for v in SEED_FIRMWARE_VARIANTS:
                if v['name'] == 'uno-pair':
                    continue
                w = tempfile.mkdtemp(prefix='cmod-bi-')
                gen.gen('uno', work=w, variant=v['name'])
                r = build.build('uno', work=w)
                shas.setdefault(v['name'], {})[which] = r['artifact_sha256']
                shutil.rmtree(w, ignore_errors=True)
        finally:
            gen.TEMPLATES['arduino-uno-r3'] = tpl
    for name, s in shas.items():
        check('byte-identical .hex with and without the annotations: %s (%s)' % (name, s.get('annotated', '')[:16]),
              s.get('annotated') and s.get('annotated') == s.get('stripped'), s)
    shutil.rmtree(stripped, ignore_errors=True)


from falcon import testing  # noqa: E402
sys.path.insert(0, os.path.join(FRAMEWORK, 'tests'))
from board_probe_boot import boot  # noqa: E402
manager = boot(FRAMEWORK)
client = testing.TestClient(manager.polServer.falconServer)
tables = manager.objectTables
typed = {(k if isinstance(k, str) else getattr(k, '__name__', str(k))) for k in manager.objectTypingDict.keys()} \
        | {getattr(v, 'className', '') for v in manager.objectTypingDict.values()}
for cls in ('CProject', 'CModule', 'CFunctionAtom', 'CPort', 'CGraph'):
    check('class %s is typed after boot' % cls, cls in typed)
n = lambda c: len(tables.get(c, {}) or {})  # noqa: E731
m = json.load(open(os.path.join(FRAMEWORK, 'modules', 'board', 'custom', 'firmware', 'uno', 'polari-firmware.json')))
check('seeded from the committed manifest: 1 project, 7 modules, 34 atoms, %d ports, no graph' % m['counts']['ports'],
      (n('CProject'), n('CModule'), n('CFunctionAtom'), n('CPort'), n('CGraph')) == (1, 7, 34, m['counts']['ports'], 0),
      (n('CProject'), n('CModule'), n('CFunctionAtom'), n('CPort'), n('CGraph')))
r = client.simulate_get('/api/cmod')
check('GET /api/cmod → the uno project, 34 atoms, pycparser in this process', r.status_code == 200 and r.json['projects'][0]['name'] == 'uno'
      and r.json['atoms'] == 34 and r.json['parser']['engine'] == 'pycparser', r.text[:200])
r = client.simulate_get('/api/cmod/atoms/hal_millis')
check('GET /api/cmod/atoms/hal_millis → isr_safe yes, out(return) [ms], text 24 B shipped', r.status_code == 200 and r.json['atom']['isr_safe'] == 'yes'
      and r.json['ports'][0]['unit'] == 'ms' and r.json['atom']['text_bytes'] == 24, r.text[:300])
r = client.simulate_get('/api/cmod/atoms', params={'project': 'uno', 'kind': 'isr'})
check('GET /api/cmod/atoms?project=uno&kind=isr → USART_RX_vect, TIMER2_COMPA_vect, INT0_vect', r.status_code == 200
      and sorted(a['isr_vector'] for a in r.json['atoms']) == ['INT0_vect', 'TIMER2_COMPA_vect', 'USART_RX_vect'], r.text[:200])
r = client.simulate_get('/api/cmod/ports', params={'atom': 'uno:hal.hal_adc_read'})
check('GET /api/cmod/ports?atom=uno:hal.hal_adc_read → channel (in) + return (out, count)', r.status_code == 200
      and [(p['port'], p['direction'], p['unit']) for p in r.json['ports']] == [('channel', 'in', ''), ('return', 'out', 'count')], r.text[:200])
r = client.simulate_get('/api/cmod/engines')
check('GET /api/cmod/engines → avr-gcc / avr-nm / make placement (nothing run)', r.status_code == 200 and set(r.json['engines']) == {'avr-gcc', 'avr-nm', 'make'})
r = client.simulate_get('/api/cmod/projects/uno/drift')
check('GET /api/cmod/projects/uno/drift → the committed manifest matches the sources', r.status_code == 200 and r.json['stale'] is False, r.text[:200])
r = client.simulate_get('/api/cmod/projects/nope/drift')
check('drift of an unknown project → 404 in plain words', r.status_code == 404 and 'no template project' in r.json['error'])
pages = [d for d in (tables.get('DisplayDefinition', {}) or {}).values() if getattr(d, 'pageRoute', '') == 'c-atoms']
check('/display/c-atoms is seeded with five configured tables', len(pages) == 1
      and sum(len(row['items']) for row in json.loads(pages[0].definition)['rows']) == 5, len(pages))
check('board still boots beside it: the five seeded FirmwareVariants', n('FirmwareVariant') >= 5, n('FirmwareVariant'))
if '--engines' in sys.argv:
    byte_identical()
print('\n%d/%d checks passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
