"""
Selftest for the offline chunk planner (off-1 machinery).

Run from polari-framework/:
  PYTHONPATH=.:modules python3 -m appstore.selftest_offline_chunker

Function-level: deterministic packing, capacity honesty (no chunk
over media size), the named refusal for an unsplittable file, the
piece-by-piece emit (write→verify→delete-source), sha256SUMS
correctness, and the PRODUCER/CONSUMER contract — the chunks.json
this module emits must render on appstore.offline_page unchanged.
"""

import hashlib
import json
import os
import sys
import tempfile

from appstore import offline_chunker as chunker
from appstore import offline_page as off

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        pool = os.path.join(tmp, 'pool')
        os.makedirs(os.path.join(pool, 'repo'))
        sizes = {'repo/big-a.deb': 600, 'repo/big-b.deb': 500,
                 'repo/mid.deb': 300, 'small-1.deb': 120,
                 'small-2.deb': 80}
        for name, size in sizes.items():
            with open(os.path.join(pool, name), 'wb') as fh:
                fh.write(name.encode() * (size // len(name))
                         + b'x' * (size % len(name)))

        files = chunker.scan_pool(pool)
        check('pool scan finds every file with its size, '
              'subdirs included',
              dict(files) == sizes)

        plan = chunker.plan_chunks(files, 700)
        totals = [sum(f['bytes'] for f in c['files'])
                  for c in plan['chunks']]
        check('packing honors capacity: no chunk exceeds the '
              'medium, FFD keeps the count tight (1600 B over '
              '700 B media = 3 disks)',
              len(plan['chunks']) == 3
              and all(t <= 700 for t in totals))
        check('packing is DETERMINISTIC (same pool + media = '
              'byte-identical plan)',
              plan == chunker.plan_chunks(files, 700))
        check('media presets resolve, nonsense refuses by name',
              chunker.media_bytes('dvd') == 4_400_000_000
              and chunker.media_bytes(1234) == 1234)
        try:
            chunker.media_bytes('betamax')
            named = False
        except ValueError as error:
            named = 'betamax' in str(error)
        check('unknown media preset = named refusal', named)

        try:
            chunker.plan_chunks(files, 500)
            named = False
        except ValueError as error:
            named = 'big-a.deb' in str(error)
        check('a file bigger than one medium REFUSES naming the '
              'file, never a silently oversized disk', named)

        out = os.path.join(tmp, 'out')
        doc = chunker.write_manifests(
            plan, pool, out, target='Ubuntu 24.04 amd64',
            media_label='700 B test media',
            built_at='2026-08-24')
        sums = open(os.path.join(out, 'sha256SUMS')).read()
        digest = hashlib.sha256(open(
            os.path.join(pool, 'repo/big-a.deb'),
            'rb').read()).hexdigest()
        check('sha256SUMS covers every pool file with real '
              'digests',
              len(sums.strip().splitlines()) == len(sizes)
              and f'{digest}  repo/big-a.deb' in sums)

        # PRODUCER/CONSUMER: the page must render this chunks.json
        os.environ['POLARI_OFFLINE_DIR'] = out
        page = off.render_page('Polari')
        check('CONTRACT: offline_page renders the emitted '
              'chunks.json — target/built facts, one section per '
              'disk, per-file sizes',
              'Ubuntu 24.04 amd64' in page
              and 'built 2026-08-24' in page
              and page.count('Disk ') >= 3
              and 'big-a.deb' in page)

        medium = os.path.join(tmp, 'medium-1')
        report = chunker.emit_chunk(plan, 1, pool, medium,
                                    delete_source=True)
        first = plan['chunks'][0]['files']
        check('piece-by-piece emit: chunk 1 lands on the medium '
              'verified, CHUNK_ID marker written, and the pool '
              'copies are GONE (the server never holds pool + '
              'medium at once)',
              report['files'] == len(first)
              and all(os.path.isfile(os.path.join(
                  medium, f['name'])) for f in first)
              and '1/3' in open(os.path.join(
                  medium, 'CHUNK_ID')).read()
              and not any(os.path.exists(os.path.join(
                  pool, f['name'])) for f in first))
        check('files outside chunk 1 still wait in the pool',
              any(os.path.exists(os.path.join(pool, f['name']))
                  for c in plan['chunks'][1:] for f in c['files']))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
