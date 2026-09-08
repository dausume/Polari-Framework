"""
@module cntfet.custom.cnt_snapshot

Dustin 2026-08-30: "make sure we have our modules stashing all data we
are currently using for these FETs and rows so that future modules have
this data and can get it from the github … lightweight … json format …
if it is things that can be installed later and based on dependencies,
we should not be pushing that up."

This is the EXPORT side of the module data convention
(moduleService.json_seeds): pull the live FET tables that code cannot
regenerate and write them as `modules/<pkg>/initialData/<Class>.json`.
Loading (boot / POST /modules/seed / GET /modules/{m}/initial-data) is
the generic layer — nothing cntfet-specific there.

RULE — what goes in initialData (plain JSON, committed, small):
  KEEP  what cannot be regenerated from code alone:
        - the characterized cell libraries (CellCharacterizationRun:
          Liberty text + grids; need the ngspice/OpenVAF/OpenSTA engines
          worker, ~40 min per library) — LATEST run per (device, cell)
        - the derived device rows (AlignedCNTFETDevice → cntfet,
          SiliconMOSFET → sifet: VS parameters, derived_at, provenance)
        - OpenCellLibrary + FunctionalBlock rows (admission / proof results)
  DROP  what code or a cheap POST regenerates: basis rows, anchors,
        evidence, IP, targets, ladder nodes, cell definitions (seeds in
        code); CNTFETSimResult (derive), FETFieldSample (3 MB, sample).
  Never binaries, venvs, vendored worker inputs (cnt-engines/vendor).
  Refresh only when a library / derivation actually changed — every
  refresh is ~0.8 MB of git history on a free public repo.

@consumers snapshot-cntfet-data.sh, selftest_snapshot
"""

import json
import os

from moduleService.json_seeds import (
    constructor_fields, data_dir, read_file, seed_pairs, to_seed, write_file,
)

#: class → (package that owns its initialData file, defining module)
SNAPSHOT_CLASSES = [
    ('AlignedCNTFETDevice', 'cntfet', 'cntfet.cnt_basis'),
    ('SiliconMOSFET', 'sifet', 'sifet.si_basis'),
    ('CellCharacterizationRun', 'cntfet', 'cntfet.cnt_characterization_basis'),
    ('OpenCellLibrary', 'cntfet', 'cntfet.cnt_open_library_page'),
    ('FunctionalBlock', 'cntfet', 'cntfet.cnt_blocks_page'),
]

#: stated, not silent — why each excluded table is NOT in the repo
EXCLUDED = {
    'CNTMaterialState / AlignedCNTFETGeometry / GateStack / CNTContact / '
    'CNTTransportModel / CNTParasitics': 'seeds in cntfet.cnt_basis',
    'SiliconDopingProfile / SiliconFETShape / SolGelDielectric / SolGelProcess':
        'seeds in sifet.si_basis',
    'SiliconProcessNode / CNTCalibrationAnchor': 'seeds in sifet.si_ladder_basis + cnt_basis',
    'EvidenceItem / TechnologyIPRecord': 'seeds in cnt_evidence / cnt_ip / si_ladder',
    'DesignTarget / FETTargetMapping': 'seeds in cnt_targets',
    'CNTCellDefinition': 'generated from cnt_cell_library seeds',
    'CNTFETSimResult': 'POST derive regenerates in seconds (no engines)',
    'FETFieldSample': '3 MB; POST sample-fields regenerates in seconds',
    'cnt-engines/vendor': 'binaries / worker inputs — fetch-vendor.sh',
}


def resolve_class(class_name):
    import importlib
    mod = {n: m for n, _p, m in SNAPSHOT_CLASSES}.get(class_name)
    if mod is None:
        return None
    try:
        return getattr(importlib.import_module(mod), class_name)
    except (ImportError, AttributeError):
        return None


def latest_per_key(rows, key_fn, stamp='ran_at'):
    """Keep the newest row per key (repeat runs of the same library
    are redundant bytes in a public repo)."""
    best = {}
    for r in rows:
        k = key_fn(r)
        if k not in best or str(r.get(stamp, '')) > str(best[k].get(stamp, '')):
            best[k] = r
    return list(best.values())


def _run_key(r):
    cell = str(r.get('cell', ''))
    return (r.get('device'), 'library' if cell.startswith('library') else cell)


DEDUPE = {'CellCharacterizationRun': _run_key}


def _fetch_rows(api_base, class_name):
    import ssl
    import urllib.request
    ctx = ssl._create_unverified_context()
    url = f'{api_base.rstrip("/")}/{class_name}'
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=120) as r:
            body = json.loads(r.read().decode())
        return body[0][class_name][0]['data'], None
    except Exception as e:  # noqa: BLE001 — reported per class
        return None, f'{url}: {e}'


def export_snapshot(api_base, classes=None):
    """Live tables → initialData files (deduped, meta stripped,
    constructor-filtered). Never raises for one class."""
    report = []
    for class_name, package, _mod in SNAPSHOT_CLASSES:
        if classes and class_name not in classes:
            continue
        rows, err = _fetch_rows(api_base, class_name)
        if err:
            report.append({'class': class_name, 'ok': False, 'error': err})
            continue
        if class_name in DEDUPE:
            rows = latest_per_key(rows, DEDUPE[class_name])
        cls = resolve_class(class_name)
        fields = constructor_fields(cls) if cls else None
        seeds = [to_seed(r, fields) for r in rows]
        path = write_file(package, class_name, seeds, source=api_base)
        report.append({'class': class_name, 'ok': True, 'package': package,
                       'count': len(seeds), 'bytes': os.path.getsize(path),
                       'path': path})
    return report


def snapshot_path(class_name):
    pkg = {n: p for n, p, _m in SNAPSHOT_CLASSES}[class_name]
    return os.path.join(data_dir(pkg), f'{class_name}.json')


def load_snapshot(class_name):
    path = snapshot_path(class_name)
    return read_file(path) if os.path.exists(path) else None


def snapshot_rows():
    """{class_name: rows} through the generic loader (constructor-
    filtered), plus skipped [(class, why)]."""
    out, skipped = {}, []
    for pkg in sorted({p for _n, p, _m in SNAPSHOT_CLASSES}):
        pairs, sk = seed_pairs(pkg, manager=None)
        for n, _c, rows in pairs:
            out[n] = rows
        skipped += sk
    return out, skipped


def snapshot_inventory():
    present = []
    for class_name, package, _mod in SNAPSHOT_CLASSES:
        path = snapshot_path(class_name)
        if os.path.exists(path):
            payload = read_file(path)
            present.append({'class': class_name, 'package': package,
                            'present': True, 'count': payload.get('count'),
                            'bytes': os.path.getsize(path),
                            'source': payload.get('source', '')})
        else:
            present.append({'class': class_name, 'package': package,
                            'present': False})
    return {'classes': present, 'excluded': EXCLUDED,
            'totalBytes': sum(c.get('bytes', 0) for c in present)}


if __name__ == '__main__':
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        'POLARI_API', 'https://api.prf.192.168.0.210.nip.io')
    for r in export_snapshot(base):
        if r['ok']:
            print(f"  {r['package']}/initialData/{r['class']}.json  "
                  f"{r['count']:>3} rows  {r['bytes']:>8} B")
        else:
            print(f"  {r['class']:<26} FAILED {r['error']}")
