"""
Selftest for per-module dependency/engine accounting + the
online/offline deb flavors (Dustin 2026-08-24: file counts are not
honest accounting — libraries and engines take definitive space
that online debs install dynamically and offline debs must carry).

Run from polari-framework/:
  PYTHONPATH=.:modules python3 -m appstore.selftest_module_requirements

Uses a fixture registry + the REAL environment for measurement
(falcon is installed here), and a fake wheel fetcher so no network
is touched.
"""

import io
import json
import os
import sys
import tarfile
import tempfile

from appstore import app_deb_builder as builder
from appstore import module_requirements as modreqs
from appstore.selftest_app_debs import (_ar_member_bytes, _write,
                                        parse_deb)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    tmp = tempfile.mkdtemp(prefix='modreqs-selftest-')
    os.environ['POLARI_APP_DEBS_DIR'] = os.path.join(tmp, 'work')
    os.environ['POLARI_APP_DEB_TTL'] = '3600'
    root = os.path.join(tmp, 'framework')
    _write(os.path.join(root, 'modules/alpha/__init__.py'), '')
    _write(os.path.join(root, 'modules/alpha/alpha_api.py'),
           'import json\nimport falcon\nimport beta\n'
           'import ghostlib\n')
    _write(os.path.join(root, 'modules/beta/__init__.py'), '')
    _write(os.path.join(root, 'modules/polari-modules.json'),
           json.dumps({'schema_version': '1', 'note': '',
                       'modules': {
                           'alpha': {'kind': 'official',
                                     'path': 'modules/alpha'},
                           'beta': {'kind': 'official',
                                    'path': 'modules/beta',
                                    'requires': ['gamma']},
                       }}))

    reqs = modreqs.module_requirements('alpha', root)
    lib_names = [l['name'].lower() for l in reqs['libraries']]
    falcon_row = next(l for l in reqs['libraries']
                      if l['name'].lower() == 'falcon')
    check('scan splits honestly: stdlib excluded, sibling module '
          'beta -> polariRequires (never a pip payload), falcon '
          'stays a library',
          'json' not in lib_names and 'beta' not in lib_names
          and reqs['polariRequires'] == ['beta']
          and 'falcon' in lib_names)
    check('installed libraries carry MEASURED bytes from the live '
          'environment; the unknown import is unmeasured, counted, '
          'never invented',
          falcon_row['installed']
          and isinstance(falcon_row['bytes'], int)
          and falcon_row['bytes'] > 100_000
          and reqs['librariesUnmeasured'] >= 1
          and reqs['librariesBytes'] >= falcon_row['bytes'])
    check('registry `requires` unions into polariRequires',
          modreqs.module_requirements('beta', root)
          ['polariRequires'] == ['gamma'])
    check('engines: curated map probes live (materials_science '
          'python engines report presence; absent = present False '
          'with bytes None, never a made-up size)',
          any(e['present'] and e['bytes']
              for e in modreqs.module_engines('materials_science'))
          and all(e['bytes'] is None
                  for e in modreqs.module_engines(
                      'materials_science') if not e['present']))

    # --- offline flavor with a FAKE fetcher (no network) ---
    real_fetch = builder._fetch_wheels

    def fake_fetch(libraries, dest):
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, 'falcon-0.0-fake.whl'),
                  'wb') as fh:
            fh.write(b'wheel-bytes' * 100)
        return ['falcon-0.0-fake.whl']

    builder._fetch_wheels = fake_fetch
    try:
        online = builder.generate('alpha', root=root)
        offline = builder.generate('alpha', root=root,
                                   flavor='offline')
    finally:
        builder._fetch_wheels = real_fetch

    check('two flavors, two packages: offline gains -offline and '
          'a DIFFERENT content hash (wheels are payload)',
          online['ok'] and offline['ok']
          and offline['file'].startswith('polari-app-alpha-offline_')
          and online['version'] != offline['version'])
    deb = parse_deb(offline['path'])
    check('offline deb CARRIES the wheels under wheels/ and '
          'Provides/Conflicts/Replaces the online name — the two '
          'can never coexist',
          any(n.endswith('wheels/falcon-0.0-fake.whl')
              for n in deb['data'])
          and deb['control'].get('Provides') == 'polari-app-alpha'
          and deb['control'].get('Conflicts') == 'polari-app-alpha')
    with open(offline['path'], 'rb') as fh:
        blob = fh.read()
    mtar = tarfile.open(fileobj=io.BytesIO(
        _ar_member_bytes(blob, 'data.tar.gz')), mode='r:gz')
    manifest = json.loads(mtar.extractfile(
        './var/lib/polari/apps/alpha/manifest.json').read())
    check('offline manifest: flavor, carried-wheels delivery with '
          'the pip --no-index install line, wheel list, full '
          'requirements accounting (libraries + polariRequires)',
          manifest['flavor'] == 'offline'
          and 'carried-wheels' in manifest['requirements'
                                           ]['delivery']
          and '--no-index' in manifest['requirements']['delivery']
          and manifest['requirements']['wheels']
          == ['falcon-0.0-fake.whl']
          and manifest['requirements']['polariRequires']
          == ['beta'])
    with open(online['path'], 'rb') as fh:
        blob = fh.read()
    mtar = tarfile.open(fileobj=io.BytesIO(
        _ar_member_bytes(blob, 'data.tar.gz')), mode='r:gz')
    manifest = json.loads(mtar.extractfile(
        './var/lib/polari/apps/alpha/manifest.json').read())
    check('online manifest says dynamic-after-install and carries '
          'the same accounting so nothing downloads invisibly',
          manifest['flavor'] == 'online'
          and 'dynamic-after-install' in manifest['requirements'
                                                  ]['delivery']
          and manifest['requirements']['wheels'] == []
          and any(l['name'].lower() == 'falcon'
                  for l in manifest['requirements']['libraries']))
    check('estimates are per-flavor (offline history never '
          'answers for online)',
          builder.estimate_seconds('alpha', flavor='online')
          is not None
          and builder.estimate_seconds('alpha', flavor='offline')
          is not None
          and len(builder.generation_records('alpha')) == 2)
    check('unknown flavor refuses by name',
          'unknown flavor' in builder.generate(
              'alpha', root=root, flavor='floppy')['refusal'])

    # --- dl-9: pool awareness + measured download times ---
    check('pool_file_for is flavor-exact: the online pool entry '
          'never answers for offline and vice versa',
          builder.pool_file_for('alpha', 'online')['file']
          == online['file']
          and builder.pool_file_for('alpha', 'offline')['file']
          == offline['file']
          and builder.pool_file_for('beta', 'online') is None)
    check('download estimate: honest None with no history, then '
          'a throughput-based prediction from measured rows',
          builder.download_estimate_seconds(1_000_000) is None
          and (builder.record_download('x.deb', 5_000_000, 2.5)
               or builder.download_estimate_seconds(4_000_000)
               == 2.0)
          and len(builder.generation_records('alpha')) == 2)
    from appstore import app_debs_page as page_mod
    page = page_mod.render_page('X', root=root)
    check('an already-generated app offers DOWNLOAD (direct file '
          'link + READY state), never Generate & download',
          f'/downloads/apps/file/{online["file"]}' in page
          and 'READY — ' in page
          and f'status/alpha?flavor=online">Generate' not in page)
    check('a never-generated app offers Generate & download',
          'status/beta?flavor=online">'
          'Generate &amp; download' in page)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
