"""
@module appstore.custom.offline_chunker

off-1 machinery: split an offline-bundle pool across CDs/DVDs/USB
sticks (OFFLINE_INSTALL_PLAN.md — decisions 1+2 ratified: Ubuntu
target, multi-disk/multi-USB chunking first-class). This module is
the ONE chunk-planning implementation: the suite's
build-offline-bundle.sh calls it, and it emits exactly the
chunks.json contract that appstore.offline_page renders — producer
and consumer share this repo so the contract cannot drift.

What it does:
- plan_chunks(): deterministic first-fit-decreasing packing of a
  file pool into media-sized chunks. A file bigger than the medium
  is a NAMED refusal (never a silently oversized disk); packing is
  stable across runs (sorted by size desc, then name).
- emit_chunk(): write ONE chunk's files to a destination (the
  staging dir, or the mounted medium itself) — the piece-by-piece
  flow: generate → write → verify → move to the next chunk, so the
  server never needs the whole set on disk at once (the ratified
  answer to the disk blocker).
- write_manifests(): chunks.json (the offline_page contract:
  target/builtAt/media + per-chunk labeled file lists) +
  sha256SUMS covering every pool file.

Verification honesty: sha256SUMS ships now. Signing the bundle
(decision 3, the anchor for media built before any isle exists) is
OPEN — nothing here pretends to sign; the README the bundle
builder writes says how verification stands.

@consumers
  - polari-suite/build-offline-bundle.sh (via the CLI below)
  - appstore.offline_chunker_selftest
  - appstore.offline_page (renders the chunks.json this emits)
"""

import hashlib
import json
import os
import shutil

#: Usable capacity presets, deliberately conservative (filesystem
#: overhead + burn slack). Override with an explicit byte count.
MEDIA_PRESETS = {
    'cd': 650 * 1000 * 1000,
    'dvd': 4_400 * 1000 * 1000,
    'usb4': 3_800 * 1000 * 1000,
    'usb8': 7_700 * 1000 * 1000,
    'usb16': 15_500 * 1000 * 1000,
}


def media_bytes(media):
    """Preset name or explicit byte count → usable bytes; named
    refusal for nonsense."""
    if isinstance(media, int):
        return media
    if media in MEDIA_PRESETS:
        return MEDIA_PRESETS[media]
    try:
        return int(media)
    except (TypeError, ValueError):
        raise ValueError(
            f'unknown media "{media}" — use one of '
            f'{sorted(MEDIA_PRESETS)} or a byte count')


def scan_pool(pool_dir):
    """Sorted [(relpath, bytes)] of every file under the pool."""
    files = []
    for dirpath, dirnames, filenames in os.walk(pool_dir):
        dirnames.sort()
        for fname in sorted(filenames):
            path = os.path.join(dirpath, fname)
            rel = os.path.relpath(path, pool_dir)
            files.append((rel, os.path.getsize(path)))
    return files


def plan_chunks(files, media, labeler=None):
    """First-fit-decreasing pack of [(relpath, bytes)] into chunks
    of media capacity. Deterministic: sort by (-size, name).
    Returns {'mediaBytes': int, 'chunks': [{'label', 'files':
    [{'name', 'bytes'}]}]}. Raises ValueError NAMING any file that
    cannot fit one medium."""
    capacity = media_bytes(media)
    oversized = [(name, size) for name, size in files
                 if size > capacity]
    if oversized:
        worst = ', '.join(f'{name} ({size} B)'
                          for name, size in oversized[:3])
        raise ValueError(
            f'{len(oversized)} file(s) exceed one medium '
            f'({capacity} B): {worst} — use larger media or '
            'split the file upstream')
    chunks = []
    for name, size in sorted(files, key=lambda f: (-f[1], f[0])):
        for chunk in chunks:
            if chunk['bytes'] + size <= capacity:
                chunk['files'].append({'name': name,
                                       'bytes': size})
                chunk['bytes'] += size
                break
        else:
            chunks.append({'files': [{'name': name,
                                      'bytes': size}],
                           'bytes': size})
    labeler = labeler or (lambda i, c: f'Disk {i}')
    return {'mediaBytes': capacity,
            'chunks': [{'label': labeler(i, chunk),
                        'files': sorted(chunk['files'],
                                        key=lambda f: f['name'])}
                       for i, chunk in enumerate(chunks,
                                                 start=1)]}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 16), b''):
            digest.update(block)
    return digest.hexdigest()


def emit_chunk(plan, index, pool_dir, dest_dir, delete_source=False):
    """Write chunk #index (1-based) to dest_dir, verifying each
    file's size on arrival. delete_source=True is the
    piece-by-piece flow: the pool copy goes away as soon as the
    medium holds it. Returns {'label', 'files', 'bytes'}."""
    chunk = plan['chunks'][index - 1]
    os.makedirs(dest_dir, exist_ok=True)
    total = 0
    for entry in chunk['files']:
        src = os.path.join(pool_dir, entry['name'])
        dst = os.path.join(dest_dir, entry['name'])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        got = os.path.getsize(dst)
        if got != entry['bytes']:
            raise IOError(
                f'{entry["name"]}: wrote {got} B, expected '
                f'{entry["bytes"]} B — medium full or faulty?')
        total += got
        if delete_source:
            os.remove(src)
    with open(os.path.join(dest_dir, 'CHUNK_ID'), 'w') as fh:
        fh.write(f'{index}/{len(plan["chunks"])} '
                 f'{chunk["label"]}\n')
    return {'label': chunk['label'],
            'files': len(chunk['files']), 'bytes': total}


def write_manifests(plan, pool_dir, out_dir, target='',
                    media_label='', built_at=''):
    """chunks.json (the offline_page contract) + sha256SUMS into
    out_dir. Hashes are computed from the POOL (before any
    piece-by-piece deletion) — call this first."""
    os.makedirs(out_dir, exist_ok=True)
    chunks_doc = {'target': target, 'builtAt': built_at,
                  'media': media_label,
                  'chunks': plan['chunks']}
    with open(os.path.join(out_dir, 'chunks.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(chunks_doc, fh, indent=2)
        fh.write('\n')
    with open(os.path.join(out_dir, 'sha256SUMS'), 'w',
              encoding='utf-8') as fh:
        for chunk in plan['chunks']:
            for entry in chunk['files']:
                digest = _sha256(os.path.join(pool_dir,
                                              entry['name']))
                fh.write(f'{digest}  {entry["name"]}\n')
    return chunks_doc


def main(argv):
    """CLI for build-offline-bundle.sh:
      python3 -m appstore.custom.offline_chunker plan <pool> <media> \\
          <out_dir> [--target T] [--media-label L] \\
          [--built-at DATE]
      python3 -m appstore.custom.offline_chunker emit <pool> <media> \\
          <chunk#> <dest> [--delete-source]
    """
    def flag(name, default=''):
        if name in argv:
            i = argv.index(name)
            value = argv[i + 1]
            del argv[i:i + 2]
            return value
        return default

    delete_source = '--delete-source' in argv
    if delete_source:
        argv.remove('--delete-source')
    target = flag('--target')
    media_label = flag('--media-label')
    built_at = flag('--built-at')
    if len(argv) < 4:
        print(main.__doc__)
        return 2
    verb, pool, media = argv[0], argv[1], argv[2]
    try:
        if verb == 'plan':
            plan = plan_chunks(scan_pool(pool), media)
            doc = write_manifests(
                plan, pool, argv[3], target=target,
                media_label=media_label, built_at=built_at)
            for chunk in doc['chunks']:
                size = sum(f['bytes'] for f in chunk['files'])
                print(f'{chunk["label"]}: '
                      f'{len(chunk["files"])} files, {size} B')
            print(f'{len(doc["chunks"])} chunk(s) -> '
                  f'{argv[3]}/chunks.json + sha256SUMS')
            return 0
        if verb == 'emit':
            plan = plan_chunks(scan_pool(pool), media)
            report = emit_chunk(plan, int(argv[3]), pool,
                                argv[4],
                                delete_source=delete_source)
            print(f'{report["label"]}: {report["files"]} files, '
                  f'{report["bytes"]} B -> {argv[4]}'
                  + (' (pool copies deleted)' if delete_source
                     else ''))
            return 0
    except (ValueError, IOError) as error:
        print(f'REFUSED: {error}')
        return 1
    print(main.__doc__)
    return 2


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
