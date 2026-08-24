"""
Selftest for the offline install page (dl-5).

Run from polari-framework/:
  PYTHONPATH=.:modules python3 -m appstore.selftest_offline

Function-level (no server): the honest not-built-yet state, a
staged chunks.json rendering per-disk lists + sizes + media
instructions, the named refusal for a malformed manifest, and the
manifest-is-the-truth file serving (staged-but-unlisted files and
traversal both refuse).
"""

import json
import os
import sys
import tempfile

from appstore import offline_page as off

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    with tempfile.TemporaryDirectory() as staged:
        os.environ['POLARI_OFFLINE_DIR'] = staged

        page = off.render_page('Polari Demo')
        check('nothing staged = the HONEST not-built-yet page: '
              'says so plainly, describes what it will be, links '
              'back, and still carries the explainers (incl. the '
              'open verification decision) — zero JS',
              'Not built yet' in page
              and 'What it will be' in page
              and 'href="/downloads"' in page
              and 'still being' in page
              and '<details class="explain">' in page
              and '<script' not in page)

        # a malformed manifest refuses BY NAME, never a stack trace
        with open(os.path.join(staged, 'chunks.json'), 'w') as fh:
            fh.write('{not json')
        _, refusal = off.load_manifest()
        page = off.render_page()
        check('malformed chunks.json = named refusal on the page, '
              'never a stack trace or a silent empty state',
              refusal is not None and 'unreadable' in refusal
              and 'unreadable' in page)

        with open(os.path.join(staged, 'chunks.json'), 'w') as fh:
            json.dump({'target': 'Ubuntu 24.04 amd64',
                       'builtAt': '2026-08-24',
                       'media': '4.7 GB DVD',
                       'chunks': []}, fh)
        _, refusal = off.load_manifest()
        check('a chunk-less manifest refuses as an unfinished '
              'build, by name',
              refusal is not None and 'no chunks' in refusal)

        manifest = {
            'target': 'Ubuntu 24.04 amd64',
            'builtAt': '2026-08-24',
            'media': '4.7 GB DVD',
            'chunks': [
                {'label': 'Disk 1 — core debs',
                 'files': [{'name': 'chunk1.tar', 'bytes': 9}]},
                {'label': 'Disk 2 — docker images',
                 'files': [{'name': 'chunk2.tar',
                            'bytes': 4096}]},
            ]}
        with open(os.path.join(staged, 'chunks.json'), 'w') as fh:
            json.dump(manifest, fh)
        with open(os.path.join(staged, 'chunk1.tar'), 'wb') as fh:
            fh.write(b'tar-bytes')
        with open(os.path.join(staged, 'stray.tar'), 'wb') as fh:
            fh.write(b'never served')

        page = off.render_page('Polari Demo')
        check('staged manifest renders the product page: target/'
              'built/media facts, one numbered section per disk '
              'with label + total size, write-the-media '
              'instructions',
              'Ubuntu 24.04 amd64' in page
              and 'built 2026-08-24' in page
              and 'Disk 1' in page and 'Disk 2' in page
              and '4.0 KB' in page
              and 'Writing the media' in page)
        check('per-file honesty: a staged file gets a download '
              'link, a manifest-listed-but-missing file says '
              '"not staged yet" instead of a dead link',
              'href="/downloads/offline/chunk1.tar"' in page
              and 'not staged yet' in page
              and 'href="/downloads/offline/chunk2.tar"'
              not in page)

        check('the manifest is the truth for serving: listed+'
              'staged resolves; stray files, missing files, and '
              'traversal all refuse',
              off.resolve_offline_file('chunk1.tar') is not None
              and off.resolve_offline_file('stray.tar') is None
              and off.resolve_offline_file('chunk2.tar') is None
              and off.resolve_offline_file('../etc/passwd') is None
              and off.resolve_offline_file('') is None)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
