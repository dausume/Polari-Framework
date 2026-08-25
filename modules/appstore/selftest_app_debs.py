"""
Selftest for the on-request app-deb generator + /downloads/apps
page (dl-4).

Run from polari-framework/:
  PYTHONPATH=.:modules python3 -m appstore.selftest_app_debs

Function-level (no server), against a FIXTURE framework root:
the pure-python deb's binary format (ar + control + data.tar.gz,
verified by parsing, plus dpkg-deb when the host has it), payload
placement + manifest honesty, content-hash caching, shared-payload
factoring with dpkg Depends + symlinks, named refusals, the
DebGenerationRecord ledger + honest estimates, TTL purging, and
the rendered page's transparency promises.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

from appstore import app_deb_builder as builder
from appstore import app_debs_page as page_mod

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = 'wb' if isinstance(content, bytes) else 'w'
    with open(path, mode) as fh:
        fh.write(content)


def make_fixture_root(tmp):
    """A fake framework root: three downloaded modules (two sharing
    one big file), one registered-but-absent module, one deb-name
    collision pair."""
    root = os.path.join(tmp, 'framework')
    shared_big = b'S' * 8192          # factors (>= SHARED_MIN_BYTES)
    shared_small = b's' * 100         # stays inline (< floor)
    _write(os.path.join(root, 'modules/alpha/__init__.py'), '')
    _write(os.path.join(root, 'modules/alpha/alpha_api.py'),
           'API = "alpha"\n')
    _write(os.path.join(root, 'modules/alpha/seed_data.json'),
           '{"rows": 1}\n')
    _write(os.path.join(root, 'modules/alpha/big_asset.bin'),
           shared_big)
    _write(os.path.join(root, 'modules/alpha/tiny_common.txt'),
           shared_small)
    _write(os.path.join(root, 'modules/beta/__init__.py'), '')
    _write(os.path.join(root, 'modules/beta/big_asset.bin'),
           shared_big)
    _write(os.path.join(root, 'modules/beta/tiny_common.txt'),
           shared_small)
    _write(os.path.join(root, 'modules/solo/__init__.py'), '')
    _write(os.path.join(root, 'modules/solo/solo_engine.py'),
           'ENGINE = 1\n')
    # decoy that must never enter a payload
    _write(os.path.join(root,
                        'modules/alpha/__pycache__/x.cpython.pyc'),
           b'junk')
    registry = {
        'schema_version': '1', 'note': 'fixture',
        'modules': {
            'alpha': {'kind': 'official', 'path': 'modules/alpha',
                      'description': 'Fixture module alpha.'},
            'beta': {'kind': 'official', 'path': 'modules/beta',
                     'description': 'Fixture module beta.'},
            'solo': {'kind': 'official', 'path': 'modules/solo',
                     'description': 'No shared content.'},
            'ghost': {'kind': 'official', 'path': 'modules/ghost',
                      'description': 'Registered, never '
                                     'downloaded.'},
        }}
    _write(os.path.join(root, 'modules/polari-modules.json'),
           json.dumps(registry))
    return root


def parse_deb(path):
    """{'members': [names], 'control': {field: value},
    'data': {arcname: TarInfo}} via pure parsing — the format
    check must not depend on dpkg."""
    with open(path, 'rb') as fh:
        blob = fh.read()
    assert blob[:8] == b'!<arch>\n', 'bad ar magic'
    offset, members = 8, {}
    while offset < len(blob):
        name = blob[offset:offset + 16].decode().strip()
        size = int(blob[offset + 48:offset + 58].decode().strip())
        data = blob[offset + 60:offset + 60 + size]
        members[name] = data
        offset += 60 + size + (size % 2)
    control_tar = tarfile.open(
        fileobj=io.BytesIO(members['control.tar.gz']), mode='r:gz')
    control_text = control_tar.extractfile('./control').read()
    control = {}
    for line in control_text.decode().splitlines():
        if ': ' in line and not line.startswith(' '):
            key, value = line.split(': ', 1)
            control[key] = value
    data_tar = tarfile.open(
        fileobj=io.BytesIO(members['data.tar.gz']), mode='r:gz')
    data = {info.name: info for info in data_tar.getmembers()}
    return {'members': list(members), 'control': control,
            'data': data}


def main():
    tmp = tempfile.mkdtemp(prefix='app-debs-selftest-')
    os.environ['POLARI_APP_DEBS_DIR'] = os.path.join(tmp, 'work')
    os.environ['POLARI_APP_DEB_TTL'] = '3600'
    root = make_fixture_root(tmp)
    try:
        analysis = builder.analyze(root)
        check('analysis: three downloaded payloads, ghost refused '
              'BY NAME (registered but not downloaded)',
              sorted(analysis['payloads']) == ['alpha', 'beta',
                                               'solo']
              and 'not downloaded' in analysis['refusals'].get(
                  'ghost', ''))
        check('shared factoring: the 8 KB duplicate factors into '
              'ONE shared group owned by alpha+beta; the 100 B '
              'duplicate stays inline (size floor — a symlink '
              'would cost more than it saves)',
              len(analysis['shared']) == 1
              and list(analysis['shared'].values())[0]['modules']
              == ['alpha', 'beta']
              and len(list(
                  analysis['shared'].values())[0]['files']) == 1)

        result = builder.generate('alpha', root=root,
                                  analysis=analysis)
        check('generation succeeds with named steps + timing',
              result.get('ok') and result['seconds'] >= 0
              and not result['cached'])
        deb = parse_deb(result['path'])
        check('the deb IS a deb: ar(debian-binary, control.tar.gz, '
              'data.tar.gz), Package/Version/Architecture correct, '
              'version embeds the content hash',
              deb['members'] == ['debian-binary', 'control.tar.gz',
                                 'data.tar.gz']
              and deb['control']['Package'] == 'polari-app-alpha'
              and deb['control']['Architecture'] == 'all'
              and '+g' in deb['control']['Version'])
        payload_root = './var/lib/polari/apps/alpha'
        payload_files = [n for n, i in deb['data'].items()
                         if i.isfile() or i.issym()]
        check('payload stages ONLY under /var/lib/polari/apps/'
              '<module>/ and pycache junk never rides along',
              payload_files
              and all(n.startswith(payload_root)
                      for n in payload_files)
              and not any('__pycache__' in n
                          for n in deb['data']))
        shared_name = list(analysis['shared'])[0]
        check('the shared file rides as a SYMLINK into _shared/ '
              'and the deb Depends on the shared deb (pinned '
              'version) — content installs once, dpkg-enforced',
              deb['data'][f'{payload_root}/big_asset.bin'].issym()
              and deb['data'][f'{payload_root}/big_asset.bin']
                  .linkname.startswith('/var/lib/polari/apps/'
                                       '_shared/')
              and shared_name in deb['control'].get('Depends', '')
              and '(=' in deb['control'].get('Depends', ''))
        with open(result['path'], 'rb') as fh:
            blob = fh.read()
        mtar = tarfile.open(fileobj=io.BytesIO(
            _ar_member_bytes(blob, 'data.tar.gz')), mode='r:gz')
        manifest = json.loads(mtar.extractfile(
            f'{payload_root}/manifest.json').read())
        check('manifest.json is honest: module, hash-bearing '
              'version, data files listed, shared depends named, '
              'admit gap stated in plain words',
              manifest['module'] == 'alpha'
              and manifest['version'] == result['version']
              and 'seed_data.json' in manifest['dataFiles']
              and manifest['sharedDepends'] == [shared_name]
              and 'manual step' in manifest['admit'])

        again = builder.generate('alpha', root=root)
        check('identical content = cache hit within the TTL '
              'window: same file, cached flag, and NO second '
              'ledger row (a cache hit is not a generation)',
              again['ok'] and again['cached']
              and again['file'] == result['file']
              and len(builder.generation_records('alpha')) == 1)

        shared_path = os.path.join(
            builder.pool_dir(), result['sharedFiles'][0])
        shared_deb = parse_deb(shared_path)
        check('the shared deb owns the REAL bytes under _shared/ '
              'and names its sharing modules in the description',
              any(n.startswith('./var/lib/polari/apps/_shared/')
                  and i.isfile()
                  for n, i in shared_deb['data'].items())
              and 'alpha, beta' in shared_deb['control'
                                              ]['Description'])

        check('named refusal for a module outside the registry',
              'not in the module registry'
              in builder.generate('nope', root=root)['refusal'])
        check('named refusal for registered-but-not-downloaded',
              'not downloaded'
              in builder.generate('ghost', root=root)['refusal'])

        # deb-name collision: foo_bar vs foo-bar
        _write(os.path.join(root, 'modules/foo_bar/__init__.py'),
               '')
        _write(os.path.join(root, 'modules/foo-bar/__init__.py'),
               '')
        registry = json.loads(open(os.path.join(
            root, 'modules/polari-modules.json')).read())
        registry['modules']['foo_bar'] = {
            'kind': 'official', 'path': 'modules/foo_bar'}
        registry['modules']['foo-bar'] = {
            'kind': 'official', 'path': 'modules/foo-bar'}
        _write(os.path.join(root, 'modules/polari-modules.json'),
               json.dumps(registry))
        collision = builder.analyze(root)
        check('deb-name COLLISION refuses BOTH modules by name '
              '(never a silently clobbered package)',
              'both map' in collision['refusals'].get('foo_bar', '')
              and 'both map' in collision['refusals'].get(
                  'foo-bar', '')
              and 'foo_bar' not in collision['payloads']
              and 'foo-bar' not in collision['payloads'])

        est_none = builder.estimate_seconds('solo')
        builder.generate('solo', root=root)
        est_real = builder.estimate_seconds('solo')
        check('estimates are measured history, never invented: '
              'None before any generation, median seconds after',
              est_none is None
              and isinstance(est_real, float))

        # age solo's pool copy out so the page shows BOTH states:
        # alpha READY (download button), solo regenerate-with-
        # history, beta never-generated
        os.remove(os.path.join(builder.pool_dir(),
                               builder.pool_file_for('solo')
                               ['file']))
        page = page_mod.render_page('Polari Demo', root=root)
        check('the page lists the REGISTRY, not files on disk: '
              'ghost renders as named-unavailable; a READY app '
              'offers the direct Download, an aged-out one offers '
              'Generate & download again',
              'ghost' in page
              and 'Not available here' in page
              and 'READY — ' in page
              and '/downloads/apps/file/' in page
              and '/downloads/apps/status/solo?flavor=online'
              in page)
        check('per-item transparency: on-demand provenance, the '
              'named generation steps BEFORE the click, honest '
              '"never generated yet" for unmeasured modules, '
              'measured "usually ~" once history exists, shared '
              'payload linked install-first',
              'Generated fresh when you click' in page
              and 'package module' in page
              and 'never generated yet' in page
              and 'usually ~' in page
              and f'/downloads/apps/shared/{shared_name}' in page)
        check('the admit gap is stated in plain words (dyn merge '
              'honesty) and the page carries explainers, zero JS',
              'dynamic-modules' in page
              and '<details class="explain">' in page
              and '<script' not in page)

        old = os.path.join(builder.pool_dir(), result['file'])
        os.utime(old, (time.time() - 7200, time.time() - 7200))
        removed = builder.purge_expired()
        check('TTL purge removes expired pool debs '
              '(opportunistic, no background thread)',
              result['file'] in removed
              and not os.path.exists(old))

        check('pool serving refuses traversal / absent / non-deb '
              'names identically',
              builder.resolve_pool_file('../../etc/passwd') is None
              and builder.resolve_pool_file('ghost_1.0_all.deb')
              is None
              and builder.resolve_pool_file('') is None)

        dpkg = shutil.which('dpkg-deb')
        if dpkg:
            fresh = builder.generate('alpha', root=root)
            info = subprocess.run(
                [dpkg, '-I', fresh['path']],
                capture_output=True, text=True)
            listing = subprocess.run(
                [dpkg, '-c', fresh['path']],
                capture_output=True, text=True)
            check('REAL dpkg-deb accepts the pure-python deb '
                  '(-I and -c both parse)',
                  info.returncode == 0 and listing.returncode == 0
                  and 'polari-app-alpha' in info.stdout)
        else:
            print('SKIP: dpkg-deb not on this host — format '
                  'covered by the pure parser above')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


def _ar_member_bytes(blob, wanted):
    offset = 8
    while offset < len(blob):
        name = blob[offset:offset + 16].decode().strip()
        size = int(blob[offset + 48:offset + 58].decode().strip())
        if name == wanted:
            return blob[offset + 60:offset + 60 + size]
        offset += 60 + size + (size % 2)
    raise KeyError(wanted)


if __name__ == '__main__':
    sys.exit(main())
