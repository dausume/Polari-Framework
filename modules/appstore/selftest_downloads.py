"""
Selftest for the public downloads page (dl-1 + dl-3).

Run from polari-framework/:
  PYTHONPATH=.:modules python3 -m appstore.selftest_downloads

Function-level (no server): staging discovery + install ordering,
version parsing, the rendered page's user-facing promises, the
empty state, the traversal/absent refusals, and the dl-3 split —
no combined deb staged = the dl-1b single-list page; combined deb
staged = Option A hero + Option B demotion; transparency
explainers + per-item provenance on every variant.
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
        check('NO combined deb staged = the dl-1b single-list '
              'layout (numbered steps, no Option A/B) — the '
              'fallback never advertises a file that is not there',
              '<span class="step-no">1</span>' in page
              and 'Option A' not in page
              and 'polari-complete' not in page)
        check('transparency explainers render on the piecewise '
              'page: what a deb is, install order, pre-prepped vs '
              'on-demand, internet fetches, disk locations '
              '— native <details>, zero JS',
              'What is a .deb file?' in page
              and 'install order matter' in page
              and 'generated on demand' in page.lower()
              and 'official repositories' in page
              and '/var/lib/polari' in page
              and '<details class="explain">' in page
              and '<script' not in page)
        check('per-item provenance: every pre-prepped deb says '
              'when it was built and that it downloads instantly',
              page.count('class="prov prov-prepped"') == len(debs)
              and debs[0]['built'] in page
              and 'Downloads instantly' in page)

        # --- dl-3: stage the TRUE MERGED deb -> Option A/B ---
        with open(os.path.join(
                staged, 'polari-complete_0.1.32_amd64.deb'),
                'wb') as fh:
            fh.write(b'deb-bytes-combined' * 4096)

        debs = dl.staged_debs()
        combined_page = dl.render_page(debs, 'Polari Demo')
        check('combined deb staged: Option A hero card renders '
              'first — one file installs everything, marked '
              'pre-prepped, with its own download link',
              'Option A' in combined_page
              and 'One file installs everything' in combined_page
              and 'hero-card' in combined_page
              and ('href="/downloads/polari-complete_0.1.32_'
                   'amd64.deb"') in combined_page
              and combined_page.index('Option A')
                  < combined_page.index('Option B'))
        check('the piecewise list DEMOTES to Option B and keeps '
              'all four member debs + the order instructions',
              'Piece by piece' in combined_page
              and all(f'href="/downloads/{d["file"]}"'
                      in combined_page
                      for d in debs if d['name'] != 'polari-complete')
              and 'order matters' in combined_page)
        check('the page says A and B cannot be combined (the '
              'Conflicts relationship, in user words)',
              'can\'t be installed' in combined_page)
        check('combined deb never double-lists inside Option B',
              combined_page.count(
                  'polari-complete_0.1.32_amd64.deb') == 2)
        check('headline version still reads from the store deb',
              '<strong>0.1.32</strong>' in combined_page)
        check('provenance renders for the combined deb too '
              '(5 pre-prepped items total)',
              combined_page.count(
                  'class="prov prov-prepped"') == 5)
        check('transparency explainers also on the two-option page',
              'What is a .deb file?' in combined_page
              and '<details class="explain">' in combined_page)

        check('download resolution serves ONLY staged debs — '
              'traversal, absent files, and non-debs all refuse',
              dl.resolve_download(
                  'isle-mesh-cli_0.1.126_all.deb') is not None
              and dl.resolve_download(
                  'polari-complete_0.1.32_amd64.deb') is not None
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
