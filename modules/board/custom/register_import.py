"""
@module board.custom.register_import

The HARDWARE CAPABILITY REGISTER (AI-Notes/designs/HARDWARE_CAPABILITY_REGISTER.md) §1 devices + §1a adapters,
read cell by cell into `custom/register_rows.json` — the committed snapshot the seeds are built from (the register
lives in the suite repo; a running framework never sees it). Cells are copied VERBATIM; nothing is interpreted here
(the mapping to rows is `board.custom.register_map`). Re-run after the register changes:

    python3 -m board.custom.register_import <path/to/HARDWARE_CAPABILITY_REGISTER.md>    # from polari-framework/
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, 'register_rows.json')
DEVICE_SECTION = '## 1. Devices register'
ADAPTER_SECTION = '## 1a. Adapters and programmers register'


def _cells(line):
    # a markdown row: split on unescaped pipes, drop the outer empties
    parts = re.split(r'(?<!\\)\|', line.strip())
    return [p.strip().replace('\\|', '|') for p in parts[1:-1]]


def _table(text, heading):
    """The first pipe table after `heading`: (columns, [row dict])."""
    start = text.index(heading)
    lines = text[start:].splitlines()[1:]
    rows, cols = [], None
    for ln in lines:
        if ln.startswith('## '):
            break
        if not ln.startswith('|'):
            if cols is not None and rows:
                break
            continue
        cells = _cells(ln)
        if cols is None:
            cols = cells
        elif set(''.join(cells)) <= set('-: '):
            continue
        else:
            rows.append(dict(zip(cols, cells)))
    return cols, rows


def read(path):
    text = open(path, encoding='utf-8').read()
    dcols, devices = _table(text, DEVICE_SECTION)
    acols, adapters = _table(text, ADAPTER_SECTION)
    return {'source': 'AI-Notes/designs/HARDWARE_CAPABILITY_REGISTER.md', 'source_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'device_columns': dcols, 'devices': devices, 'adapter_columns': acols, 'adapters': adapters}


def load():
    with open(SNAPSHOT, encoding='utf-8') as fh:
        return json.load(fh)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    snap = read(argv[0])
    with open(SNAPSHOT, 'w', encoding='utf-8') as fh:
        json.dump(snap, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    print('%d devices, %d adapters -> %s' % (len(snap['devices']), len(snap['adapters']), SNAPSHOT))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
