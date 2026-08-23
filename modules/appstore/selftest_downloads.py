"""
Selftest for the public downloads page (dl-1).

Run from polari-framework/:
  PYTHONPATH=. python3 -m appstore.selftest_downloads

Function-level (no server): staging discovery + install ordering,
version parsing, the rendered page's user-facing promises, the
empty state, and the traversal/absent refusals.
"""

import os
import sys
import tempfile

from appstore import downloads_page as dl

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    with tempfile.TemporaryDirectory() as staged:
        os.environ['POLARI_DOWNLOADS_DIR'] = staged

        check('empty staging renders the HONEST empty page (never '
              'a 404 wall)',
              'No installers are staged'
              in dl.render_page(dl.staged_debs()))

        # stage a bundle out of order + a decoy non-deb
        for name in ('polari-shell-core_0.1.32_amd64.deb',
                     'isle-app-store_0.1.32_all.deb',
                     'isle-mesh-cli_0.1.126_all.deb',
                     'polari-isle_0.1.0_all.deb'):
            with open(os.path.join(staged, name), 'wb') as fh:
                fh.write(b'deb-bytes-' + name.encode())
        with open(os.path.join(staged, 'notes.txt'), 'w') as fh:
            fh.write('not a deb')

        debs = dl.staged_debs()
        check('staging discovery: four debs found, decoy ignored, '
              'INSTALL ORDER enforced (cli -> shell-core -> store '
              '-> meta) regardless of listing order',
              [d['name'] for d in debs] == dl.INSTALL_ORDER)
        check('version parsing from filenames (the only version '
              'source — no invented numbers)',
              debs[0]['version'] == '0.1.126'
              and debs[1]['version'] == '0.1.32'
              and debs[3]['arch'] == 'all')

        page = dl.render_page(debs, 'Polari Demo')
        check('the page makes the normal-user promises: version '
              'headline, ordered click instructions, no-terminal '
              'flow, archive-viewer fallback tip, offline honestly '
              'named as not-yet',
              'Current version' in page and '0.1.32' in page
              and 'order matters' in page
              and 'Software Install' in page
              and 'no terminal' in page.lower()
              and 'not available yet' in page)
        check('every staged deb is a download link on the page',
              all(f'href="/downloads/{d["file"]}"' in page
                  for d in debs))

        check('download resolution serves ONLY staged debs — '
              'traversal, absent files, and non-debs all refuse',
              dl.resolve_download(
                  'isle-mesh-cli_0.1.126_all.deb') is not None
              and dl.resolve_download('../etc/passwd') is None
              and dl.resolve_download('notes.txt') is None
              and dl.resolve_download(
                  'ghost_1.0_all.deb') is None
              and dl.resolve_download('') is None)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
