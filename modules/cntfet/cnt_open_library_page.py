"""
@module cntfet.cnt_open_library_page

The OPEN LIBRARY gate (Dustin 2026-08-29: "focus on the cells we
have proven can be incorporated into open source and are free").

An OpenCellLibrary is a NAMED SUBSET of the cell library — one
complementary device pair + every cell whose proof-of-freedom
(cnt_evidence.freedom_proof, US) is `proven-free` — with a roll-up
status that is the WORST of the pair's two devices and every
admitted cell. A library is `open_source_ready` only when that
roll-up is `proven-free`; an encumbered DEVICE makes the whole
library not-ready even though every cell circuit is free (the
circuits are textbook CMOS; the transistor they are built on is
what carries the claim). The two seeds are the contrast:

  polari-open-si-planar-90   si-nmos-planar-90 / si-pmos-planar-90
                             (si-planar-90-pair) — READY
  polari-open-cnt-s1         cnt-aligned-s1 / cnt-aligned-s1-p —
                             NOT ready: aligned-array process claim
                             (US 9,825,229) on the device

LICENCE STATEMENT (every payload, the Liberty header, LICENSE.txt):
the cell CIRCUITS are public domain (static CMOS, mirror adder,
TG latch — textbook >= 20 y, expired Wanlass CMOS patent); OUR
generated artifacts (Liberty tables, netlists, provenance JSON) are
GPL-3.0 like the rest of the project. Nothing here is legal advice
— cnt_evidence.DISCLAIMER rides every payload.

Admission is a RULE over recorded evidence, never a hand list:
change an EvidenceItem / TechnologyIPRecord row and the admitted
set changes with it.

@consumers
  - cntfet.cnt_api (to wire: GET /api/cntfet/open-library,
    /open-library/{name}, /open-library/{name}/liberty,
    POST {action: characterize | export | refresh})
  - polariServer (OpenCellLibrary registration + SEED_OPEN_LIBRARIES
    + SEED_OPEN_LIBRARY_PAGES)
  - microchip ladder ('standard-cell' rung / 'polari-cell-lib' node)
  - cntfet.open_library_selftest
"""

import json
import os
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet import cnt_evidence_basis as ev
from cntfet import cnt_ip_basis as ip
from cntfet.cnt_cell_library_basis import (
    CELL_LIBRARY, DRIVES, liberty_cell_name, subckt_text,
)
from cntfet.cnt_cell_scoring_seed import (
    _latest_library_row, _liberty_to_cell, parse_liberty,
)

DISCLAIMER = ev.DISCLAIMER
SCOPE_LINE = ev.SCOPE_LINE
ARTIFACT_LICENCE = 'GPL-3.0'
CIRCUIT_LICENCE = 'public domain'
LICENCE_STATEMENT = (
    'CELL CIRCUITS: public domain — static CMOS gates, the 28-T '
    'mirror adder and transmission-gate latches are textbook '
    'knowledge >= 20 years old (see the evidence chain: expired US '
    '3,356,858 Wanlass CMOS, Weste & Eshraghian 1985, Rabaey 2003). '
    'OUR ARTIFACTS (this Liberty, the generated SPICE netlists, the '
    'provenance JSON) are licensed GPL-3.0 like the rest of the '
    'Polari project. ' + SCOPE_LINE + '.')

#: The cell universe the gate judges: every CELL_LIBRARY key (25:
#: combinational incl. multi-output cha/cfa, tri-state ctbuf, the
#: sequential clatch) + the hand DFF `cdff` (cnt_cells) — the same
#: set cnt_evidence.library_proof reports on.
HAND_CELLS = ['cdff']
OPEN_CELL_KEYS = sorted(CELL_LIBRARY) + [c for c in HAND_CELLS
                                         if c not in CELL_LIBRARY]

READY_STATUS = 'proven-free'
PRECEDENCE = ev.PROOF_RULES['precedence']   # worst first


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── the row ────────────────────────────────────────────────────────

class OpenCellLibrary(treeObject):
    """One open-source cell library: a device pair + the admitted
    (proven-free) cells + the proof roll-up + artifact refs."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        n_device: str = '',
        p_device: str = '',
        pair_name: str = '',
        cells_json: str = '[]',          # admitted cell keys
        excluded_json: str = '[]',       # [{cell, reason}]
        device_proof_status: str = 'unevaluated',
        library_proof_status: str = 'unevaluated',
        open_source_ready: bool = False,
        licence: str = ARTIFACT_LICENCE,
        run_ref: str = '',               # latest CellCharacterizationRun
        liberty_bytes: int = 0,
        evidence_summary_json: str = '{}',
        generated_at: str = '',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.n_device = n_device
        self.p_device = p_device
        self.pair_name = pair_name
        self.cells_json = cells_json
        self.excluded_json = excluded_json
        self.device_proof_status = device_proof_status
        self.library_proof_status = library_proof_status
        self.open_source_ready = open_source_ready
        self.licence = licence
        self.run_ref = run_ref
        self.liberty_bytes = liberty_bytes
        self.evidence_summary_json = evidence_summary_json
        self.generated_at = generated_at
        self.notes = notes
        self.is_prior = is_prior


_ROW_FIELDS = ('name', 'display_name', 'description', 'n_device',
               'p_device', 'pair_name', 'cells_json', 'excluded_json',
               'device_proof_status', 'library_proof_status',
               'open_source_ready', 'licence', 'run_ref',
               'liberty_bytes', 'evidence_summary_json', 'generated_at',
               'notes', 'is_prior')


def _seed(name, display, desc, n, p, pair, notes):
    return {
        'name': name, 'display_name': display, 'description': desc,
        'n_device': n, 'p_device': p, 'pair_name': pair,
        'cells_json': '[]', 'excluded_json': '[]',
        'device_proof_status': 'unevaluated',
        'library_proof_status': 'unevaluated',
        'open_source_ready': False, 'licence': ARTIFACT_LICENCE,
        'run_ref': '', 'liberty_bytes': 0,
        'evidence_summary_json': '{}', 'generated_at': '',
        'notes': notes + ' Admission is computed live from the '
                 'evidence rows (refresh_open_library stamps it); the '
                 'seed declares the pair only.',
        'is_prior': True,
    }


#: The two seeds — the CONTRAST is the point.
SEED_OPEN_LIBRARIES = [
    _seed('polari-open-si-planar-90', 'Polari open library — Si planar '
          '90 nm-class CMOS',
          'Every proven-free cell on the si-nmos-planar-90 / '
          'si-pmos-planar-90 pair: planar bulk MOSFET + CMOS + planar '
          'process all expired (verified) — the library we can ship '
          'as open source today.',
          'si-nmos-planar-90', 'si-pmos-planar-90', 'si-planar-90-pair',
          'Expected: open_source_ready (device pair proven-free, every '
          'cell proven-free).'),
    _seed('polari-open-cnt-s1', 'Polari CNT S1 library (NOT open-'
          'source-ready)',
          'The same cell circuits on the cnt-aligned-s1 / '
          'cnt-aligned-s1-p pair. The cells are individually proven '
          'free; the DEVICE carries the aligned-array process '
          'encumbrance (US 9,825,229 active), so the library is NOT '
          'open-source-ready — research use with force=True only.',
          'cnt-aligned-s1', 'cnt-aligned-s1-p', 'cnt-s1-mirror-pair',
          'Expected: NOT open_source_ready — reason = the aligned-array '
          'encumbrance on the device, not the cells.'),
]
SEED_BY_NAME = {s['name']: s for s in SEED_OPEN_LIBRARIES}


# ── rows ───────────────────────────────────────────────────────────

def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', {}) or {}).get(
        class_name) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def _library_rows(manager):
    """name -> row-or-seed dict (manager rows win); the live row
    object (if any) under '_row'."""
    out = {}
    for row in _rows(manager, 'OpenCellLibrary'):
        name = getattr(row, 'name', '')
        if name:
            d = {k: getattr(row, k, None) for k in _ROW_FIELDS}
            d['_row'] = row
            out[name] = d
    for name, seed in SEED_BY_NAME.items():
        out.setdefault(name, {**seed, '_row': None})
    return out


def _library(manager, name):
    lib = _library_rows(manager).get(name)
    if lib is None:
        return None, {'ok': False, 'name': name,
                      'error': f'no OpenCellLibrary "{name}" — seeds: '
                               f'{sorted(SEED_BY_NAME)}',
                      'disclaimer': DISCLAIMER}
    return lib, None


def _save(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass


def _worst(statuses):
    for s in PRECEDENCE:
        if s in statuses:
            return s
    return 'unknown'


def _compact_proof(proof):
    """The proof chain, compact: record → recordStatus + the
    satisfying evidence refs."""
    return {
        'subject': proof.get('subject'),
        'subject_kind': proof.get('subject_kind'),
        'status': proof.get('status'),
        'ipVerdict': proof.get('ipVerdict'),
        'chain': [{'record': c['record'], 'verdict': c['verdict'],
                   'recordStatus': c['recordStatus'],
                   'evidence': [e['name'] for e in c['evidence']],
                   'satisfying': [e['name'] for e in c['evidence']
                                  if e['satisfies']]}
                  for c in proof.get('chain', [])],
        'gaps': proof.get('gaps', []),
        'detailPath': proof.get('detailPath'),
    }


# ── admission ──────────────────────────────────────────────────────

def admit_cells(manager, n_device, p_device, today=None):
    """Judge BOTH devices and every cell in OPEN_CELL_KEYS by
    cnt_evidence.freedom_proof. Admitted = cells whose own status is
    proven-free. open_source_ready = devices AND every admitted cell
    proven-free. Always says WHY."""
    proofs = {}
    dev_status = {}
    for role, dn in (('n', n_device), ('p', p_device)):
        pf = ev.freedom_proof(manager, 'device', dn, today)
        proofs[f'device:{dn}'] = pf
        dev_status[role] = pf['status']
    admitted, excluded, cell_status = [], [], {}
    for key in OPEN_CELL_KEYS:
        pf = ev.freedom_proof(manager, 'cell', key, today)
        proofs[f'cell:{key}'] = pf
        cell_status[key] = pf['status']
        if pf['status'] == READY_STATUS:
            admitted.append(key)
        else:
            excluded.append({'cell': key, 'status': pf['status'],
                             'gaps': pf.get('gaps', []),
                             'reason': f'cell {key} is '
                                       f'{pf["status"]}, not '
                                       f'{READY_STATUS}'})
    device_roll = _worst(list(dev_status.values()))
    library_status = _worst([device_roll]
                            + [cell_status[c] for c in admitted])
    ready = (library_status == READY_STATUS and bool(admitted)
             and all(s == READY_STATUS for s in dev_status.values()))
    # why — exact about WHERE the block sits
    dev_gaps = {role: proofs[f'device:{dn}'].get('gaps', [])
                for role, dn in (('n', n_device), ('p', p_device))}
    if ready:
        why = (f'open_source_ready: devices {n_device} ({dev_status["n"]}) '
               f'and {p_device} ({dev_status["p"]}) are proven-free and '
               f'all {len(admitted)} admitted cells are proven-free '
               f'({len(excluded)} excluded). ' + LICENCE_STATEMENT)
    elif device_roll != READY_STATUS:
        blocking = [f'{dn} is {dev_status[role]}: '
                    + ('; '.join(dev_gaps[role]) or 'no gap text')
                    for role, dn in (('n', n_device), ('p', p_device))
                    if dev_status[role] != READY_STATUS]
        why = (f'NOT open_source_ready: the DEVICE pair is {device_roll} '
               f'even though the cell circuits are free ({len(admitted)} '
               f'of {len(OPEN_CELL_KEYS)} cells individually proven-free) '
               f'— a cell library is built on its transistor, so the '
               f'device encumbrance encumbers every cell of it. '
               + ' | '.join(blocking))
    elif not admitted:
        why = 'NOT open_source_ready: no cell is proven-free'
    else:
        why = (f'NOT open_source_ready: library roll-up {library_status}'
               f' (excluded: {[e["cell"] for e in excluded]})')
    return {
        'ok': True, 'n_device': n_device, 'p_device': p_device,
        'admitted': admitted, 'excluded': excluded,
        'deviceStatus': dev_status,
        'deviceGaps': dev_gaps,
        'cellStatus': cell_status,
        'libraryStatus': library_status,
        'open_source_ready': ready,
        'why': why,
        'rule': f'admitted = cells with status {READY_STATUS}; '
                f'library status = worst of (n device, p device, every '
                f'admitted cell) by precedence {PRECEDENCE}; '
                f'open_source_ready = library status {READY_STATUS}',
        'proofs': {k: _compact_proof(v) for k, v in proofs.items()},
        'counts': {'cells': len(OPEN_CELL_KEYS),
                   'admitted': len(admitted),
                   'excluded': len(excluded)},
        'jurisdiction': ev.JURISDICTION, 'scope': SCOPE_LINE,
        'licence': {'artifacts': ARTIFACT_LICENCE,
                    'circuits': CIRCUIT_LICENCE,
                    'statement': LICENCE_STATEMENT},
        'disclaimer': DISCLAIMER,
    }


def _evidence_refs(admission):
    """Every evidence item name the admission's chains rest on."""
    names = []
    for pf in admission['proofs'].values():
        for c in pf['chain']:
            for e in c['satisfying'] or c['evidence']:
                if e not in names:
                    names.append(e)
    return names


# ── characterization lookup ────────────────────────────────────────

def _run_cells(row):
    """Liberty cell names + cell keys the run row covers."""
    names = [n for n in str(getattr(row, 'cell', ''))[len('library:'):]
             .split(',') if n]
    keys = []
    for n in names:
        k, _d = _liberty_to_cell(n)
        if k and k not in keys:
            keys.append(k)
    return names, keys


def latest_characterization(manager, n_device, admitted):
    """The latest library run for the n device + whether it covered
    the admitted cells (cell-4 honesty: name what is missing)."""
    row = _latest_library_row(manager, n_device)
    if row is None:
        return {'ok': False, 'run': None, 'cellCount': 0,
                'coversAdmitted': False, 'missing': list(admitted),
                'refusal': f'no cell-library characterization run for '
                           f'"{n_device}" — characterize_open_library '
                           f'(ngspice + OSDI) first'}
    names, keys = _run_cells(row)
    missing = [c for c in admitted if c not in keys]
    return {'ok': True, 'run': row.name, 'ran_at': getattr(row, 'ran_at', ''),
            'verdict': getattr(row, 'verdict', ''),
            'libertyNames': names, 'cells': keys,
            'cellCount': len(names),
            'coversAdmitted': not missing, 'missing': missing,
            'libertyBytes': len(getattr(row, 'liberty_text', '') or ''),
            'vdd_v': getattr(row, 'vdd_v', None)}


def _device_row(manager, name):
    return ip._find_device(manager, name)


def _vdd(device):
    return float(getattr(device, 'vdd_v', 0.0) or 0.6)


# ── evaluate / refresh (the row as a stamped result) ───────────────

def evaluate_open_library(manager, name, today=None):
    """Admission + characterization for one library; the fields a
    refresh stamps on the row."""
    lib, err = _library(manager, name)
    if err:
        return err
    adm = admit_cells(manager, lib['n_device'], lib['p_device'], today)
    char = latest_characterization(manager, lib['n_device'],
                                   adm['admitted'])
    fields = {
        'cells_json': json.dumps(adm['admitted']),
        'excluded_json': json.dumps([{'cell': e['cell'],
                                      'reason': e['reason']}
                                     for e in adm['excluded']]),
        'device_proof_status': _worst(list(adm['deviceStatus'].values())),
        'library_proof_status': adm['libraryStatus'],
        'open_source_ready': adm['open_source_ready'],
        'licence': ARTIFACT_LICENCE,
        'run_ref': char.get('run') or '',
        'liberty_bytes': char.get('libertyBytes', 0) if char['ok'] else 0,
        'evidence_summary_json': json.dumps({
            'deviceStatus': adm['deviceStatus'],
            'counts': adm['counts'],
            'evidence': _evidence_refs(adm),
            'reviewed_at': ev.REVIEWED_AT}),
        'generated_at': _now(),
    }
    return {'ok': True, 'name': name, 'library': lib, 'admission': adm,
            'characterization': char, 'fields': fields}


def refresh_open_library(manager, name, apply=True):
    """Stamp the computed admission on the OpenCellLibrary row
    (creates the row from the seed when the manager has none)."""
    res = evaluate_open_library(manager, name)
    if not res.get('ok'):
        return res
    row = res['library']['_row']
    if apply:
        if row is None:
            seed = {k: v for k, v in res['library'].items()
                    if k in _ROW_FIELDS}
            try:
                row = OpenCellLibrary(**seed, manager=manager)
            except Exception:
                import types
                row = types.SimpleNamespace(**seed)
            table = (getattr(manager, 'objectTables', None) or {})
            if isinstance(table, dict):
                table.setdefault('OpenCellLibrary', {})
                if isinstance(table['OpenCellLibrary'], dict):
                    table['OpenCellLibrary'][id(row)] = row
        for k, v in res['fields'].items():
            setattr(row, k, v)
        _save(manager, row)
    return {'ok': True, 'name': name, 'applied': bool(apply),
            'fields': res['fields'],
            'open_source_ready': res['admission']['open_source_ready'],
            'why': res['admission']['why'], 'disclaimer': DISCLAIMER}


# ── netlists ───────────────────────────────────────────────────────

def _hand_subckt(cell):
    """The hand cell's subckt (+ the hand sub-blocks it instantiates)
    from cnt_cells._SUBCKTS — cdff needs ctg + cinv (hand names,
    distinct from the library's <cell>_xN names)."""
    from cntfet.custom.cnt_cells import _SUBCKTS
    blocks = {}
    cur, buf = None, []
    for line in _SUBCKTS.splitlines():
        if line.startswith('.subckt '):
            cur, buf = line.split()[1], [line]
        elif cur:
            buf.append(line)
            if line.startswith('.ends'):
                blocks[cur] = '\n'.join(buf)
                cur = None
    if cell not in blocks:
        return f'* {cell}: no hand subckt in cnt_cells'
    need, out = [cell], []

    def deps(name):
        return [ln.split()[-1] for ln in blocks[name].splitlines()
                if ln.startswith('X')]
    for n in need:
        for d in deps(n):
            if d in blocks and d not in need:
                need.append(d)
    for n in reversed(need):
        out.append(blocks[n])
    return '\n'.join(out)


def open_netlists(admitted, drives=(1,)):
    """{cell: subckt text} for every admitted cell (library cells
    via subckt_text per drive; hand cells via cnt_cells)."""
    out = {}
    for key in admitted:
        if key in CELL_LIBRARY:
            out[key] = '\n'.join(subckt_text(key, d) for d in drives)
        else:
            out[key] = _hand_subckt(key)
    return out


def _all_subckt_text(name, admitted, drives=(1,)):
    parts = [f'* {name} — generated cell netlists ({ARTIFACT_LICENCE}); '
             f'cell circuits {CIRCUIT_LICENCE}',
             f'* {SCOPE_LINE}', f'* {DISCLAIMER}']
    # compose targets first, exactly once (library_subckts does this
    # for library cells; keep the same order here)
    needed = []
    for key in admitted:
        for sub, _i, _o in CELL_LIBRARY.get(key, {}).get('compose', []):
            if sub not in needed and sub not in admitted:
                needed.append(sub)
    nets = open_netlists(needed + list(admitted), drives)
    for key in needed + list(admitted):
        parts.append(nets[key])
    return '\n'.join(parts) + '\n'


# ── report ─────────────────────────────────────────────────────────

def open_library_report(manager, name, today=None):
    res = evaluate_open_library(manager, name, today)
    if not res.get('ok'):
        return res
    lib, adm, char = res['library'], res['admission'], \
        res['characterization']
    n_dev = lib['n_device']
    scores = power = None
    if char['ok']:
        try:
            from cntfet.cnt_cell_scoring_seed import score_cells
            scores = score_cells(manager, n_dev)
        except Exception as exc:
            scores = {'ok': False, 'error': f'cell scores: {exc}'}
        try:
            from cntfet.cnt_power_basis import library_power
            power = library_power(manager, n_dev)
        except Exception as exc:
            power = {'ok': False, 'error': f'library power: {exc}'}
    row_fields = {k: lib.get(k) for k in _ROW_FIELDS}
    row_fields.update(res['fields'])
    nets = open_netlists(adm['admitted'])
    return {
        'ok': True, 'name': name, 'row': row_fields,
        'pair': {'n': n_dev, 'p': lib['p_device'],
                 'name': lib['pair_name']},
        'admission': {k: adm[k] for k in (
            'admitted', 'excluded', 'deviceStatus', 'deviceGaps',
            'libraryStatus', 'open_source_ready', 'why', 'rule',
            'counts')},
        'characterization': char,
        'cellScores': scores,
        'power': power,
        'proof': adm['proofs'],
        'evidenceRefs': _evidence_refs(adm),
        'artifacts': {
            'liberty': {'available': bool(char['ok']),
                        'bytes': char.get('libertyBytes', 0),
                        'run': char.get('run'),
                        'coversAdmitted': char.get('coversAdmitted'),
                        'missing': char.get('missing', []),
                        'path': f'/api/cntfet/open-library/{name}/liberty'},
            'netlists': {'available': True,
                         'cells': sorted(nets),
                         'bytes': sum(len(v) for v in nets.values()),
                         'note': 'subckt_text per admitted cell — '
                                 'always available (generated from '
                                 'CELL_LIBRARY; cdff from cnt_cells)'},
            'export': {'action': 'export',
                       'files': [f'{name}.lib', f'{name}.sp',
                                 f'{name}-PROVENANCE.json',
                                 f'{name}-LICENSE.txt']},
        },
        'licence': {'artifacts': ARTIFACT_LICENCE,
                    'circuits': CIRCUIT_LICENCE,
                    'statement': LICENCE_STATEMENT},
        'jurisdiction': ev.JURISDICTION, 'scope': SCOPE_LINE,
        'reviewed_at': ev.REVIEWED_AT,
        'disclaimer': DISCLAIMER,
    }


def open_library_index(manager, today=None):
    libs = []
    for name in sorted(_library_rows(manager)):
        res = evaluate_open_library(manager, name, today)
        adm, char = res['admission'], res['characterization']
        libs.append({
            'name': name, 'display_name': res['library']['display_name'],
            'n_device': res['library']['n_device'],
            'p_device': res['library']['p_device'],
            'pair_name': res['library']['pair_name'],
            'open_source_ready': adm['open_source_ready'],
            'libraryStatus': adm['libraryStatus'],
            'deviceStatus': adm['deviceStatus'],
            'counts': adm['counts'],
            'run': char.get('run'), 'characterized': char['ok'],
            'why': adm['why'],
            'detailPath': f'/api/cntfet/open-library/{name}',
        })
    return {'ok': True, 'libraries': libs,
            'ready': [l['name'] for l in libs if l['open_source_ready']],
            'cellUniverse': OPEN_CELL_KEYS,
            'licence': {'artifacts': ARTIFACT_LICENCE,
                        'circuits': CIRCUIT_LICENCE,
                        'statement': LICENCE_STATEMENT},
            'jurisdiction': ev.JURISDICTION, 'scope': SCOPE_LINE,
            'disclaimer': DISCLAIMER}


# ── characterize ───────────────────────────────────────────────────

def characterize_open_library(manager, name, drives=(1,), slews_s=None,
                              loads_f=None, cells=None, force=False,
                              workdir=None, result_factory=None):
    """characterize_cells on the n device over the ADMITTED cells
    only (the pair-aware p card comes from complementary_of inside
    _pair_params). Refuses by name unless open_source_ready; the
    `force` knob characterizes anyway for RESEARCH and labels the
    result so."""
    res = evaluate_open_library(manager, name)
    if not res.get('ok'):
        return res
    lib, adm = res['library'], res['admission']
    if not adm['open_source_ready'] and not force:
        return {'ok': False, 'name': name, 'refusal':
                f'"{name}" is NOT open_source_ready — {adm["why"]} '
                f'Pass force=True to characterize for research (the '
                f'result is labelled research-only, never an open '
                f'artifact).', 'open_source_ready': False,
                'libraryStatus': adm['libraryStatus'],
                'disclaimer': DISCLAIMER}
    from cntfet.cnt_cell_library_basis import characterize_cells
    device = _device_row(manager, lib['n_device'])
    if device is None:
        return {'ok': False, 'name': name,
                'error': f'no device row "{lib["n_device"]}"',
                'disclaimer': DISCLAIMER}
    wanted = list(cells) if cells else list(adm['admitted'])
    not_admitted = [c for c in wanted if c not in adm['admitted']]
    if not_admitted:
        return {'ok': False, 'name': name,
                'error': f'cells {not_admitted} are not admitted to '
                         f'"{name}" (excluded: '
                         f'{[e["cell"] for e in adm["excluded"]]})',
                'disclaimer': DISCLAIMER}
    # characterize_cells covers combinational cells; sequential /
    # hand cells go through cnt_sequential — named, not silently
    # dropped
    comb = [c for c in wanted if c in CELL_LIBRARY
            and not CELL_LIBRARY[c].get('sequential')]
    deferred = [c for c in wanted if c not in comb]
    if not comb:
        return {'ok': False, 'name': name,
                'error': 'no combinational cell requested',
                'deferred': deferred, 'disclaimer': DISCLAIMER}
    kwargs = dict(cells=comb, drives=tuple(drives), vdd=_vdd(device),
                  slews_s=slews_s, loads_f=loads_f, workdir=workdir)
    if result_factory is not None:
        kwargs['result_factory'] = result_factory
    rep = characterize_cells(manager, device, **kwargs)
    rep = dict(rep)
    rep.update({
        'library': name,
        'open_source_ready': adm['open_source_ready'],
        'forced': bool(force and not adm['open_source_ready']),
        'label': ('OPEN — GPL-3.0 artifact over public-domain circuits'
                  if adm['open_source_ready'] else
                  'RESEARCH-ONLY (force=True): library not '
                  'open_source_ready — ' + adm['why']),
        'deferred': [{'cell': c, 'affordance':
                      'sequential / hand cell — cnt_sequential '
                      '(characterize-latch / characterize-sequential)'}
                     for c in deferred],
        'licence': {'artifacts': ARTIFACT_LICENCE,
                    'circuits': CIRCUIT_LICENCE},
        'disclaimer': DISCLAIMER,
    })
    if rep.get('ok') and lib['_row'] is not None:
        lib['_row'].run_ref = rep.get('resultRow', '')
        lib['_row'].liberty_bytes = rep.get('libertyBytes', 0)
        lib['_row'].generated_at = _now()
        _save(manager, lib['_row'])
    return rep


# ── Liberty with provenance header ─────────────────────────────────

def _header_lines(name, lib, adm, char):
    refs = _evidence_refs(adm)
    lines = [
        f'{name} — Polari open cell library',
        f'devices: n = {lib["n_device"]}, p = {lib["p_device"]} '
        f'(pair {lib["pair_name"]})',
        f'licence (this artifact): {ARTIFACT_LICENCE}',
        f'cell circuits: {CIRCUIT_LICENCE} (see evidence: '
        + ', '.join(refs[:6]) + (' …' if len(refs) > 6 else '') + ')',
        f'proof status: library {adm["libraryStatus"]}; devices '
        f'n {adm["deviceStatus"]["n"]}, p {adm["deviceStatus"]["p"]}; '
        f'open_source_ready = {adm["open_source_ready"]}',
        f'admitted cells ({len(adm["admitted"])}): '
        + ', '.join(adm['admitted']),
        f'characterization run: {char.get("run")} '
        f'({char.get("cellCount", 0)} cells'
        + (f'; NOT covering: {char["missing"]}' if char.get('missing')
           else '') + ')',
        'evidence refs: ' + ', '.join(refs),
        f'jurisdiction: {ev.JURISDICTION}; {SCOPE_LINE}; reviewed '
        f'{ev.REVIEWED_AT}',
        f'disclaimer: {DISCLAIMER}',
    ]
    if not adm['open_source_ready']:
        lines.insert(3, 'RESEARCH-ONLY: NOT open_source_ready — '
                        + adm['why'])
    return lines


def open_liberty_text(manager, name):
    """The latest run's Liberty with a comment-only provenance header
    prepended (stays valid Liberty)."""
    res = evaluate_open_library(manager, name)
    if not res.get('ok'):
        return res
    lib, adm, char = res['library'], res['admission'], \
        res['characterization']
    if not char['ok']:
        return {'ok': False, 'name': name, 'refusal': char['refusal'],
                'disclaimer': DISCLAIMER}
    row = _latest_library_row(manager, lib['n_device'])
    body = row.liberty_text
    hdr = ['/*'] + ['   ' + ln.replace('*/', '* /')
                    for ln in _header_lines(name, lib, adm, char)] + ['*/']
    text = '\n'.join(hdr) + '\n' + body
    return {'ok': True, 'name': name, 'run': row.name, 'text': text,
            'bytes': len(text), 'headerLines': len(hdr),
            'open_source_ready': adm['open_source_ready'],
            'licence': ARTIFACT_LICENCE, 'disclaimer': DISCLAIMER}


# ── export ─────────────────────────────────────────────────────────

def _license_text(name, lib, adm):
    return '\n'.join([
        f'{name} — LICENSE', '',
        f'Artifacts in this directory ({name}.lib, {name}.sp, '
        f'{name}-PROVENANCE.json): {ARTIFACT_LICENCE}',
        '  https://spdx.org/licenses/GPL-3.0-only.html', '',
        f'Cell circuits described by them: {CIRCUIT_LICENCE}.',
        LICENCE_STATEMENT, '',
        f'Devices: n = {lib["n_device"]} ({adm["deviceStatus"]["n"]}), '
        f'p = {lib["p_device"]} ({adm["deviceStatus"]["p"]}); library '
        f'proof status {adm["libraryStatus"]}; open_source_ready = '
        f'{adm["open_source_ready"]}.',
        '' if adm['open_source_ready'] else
        'RESEARCH-ONLY: ' + adm['why'], '',
        f'Jurisdiction {ev.JURISDICTION}; {SCOPE_LINE}.', '',
        DISCLAIMER, '']) + '\n'


def export_open_library(manager, name, outdir, force=False):
    """<name>.lib, <name>.sp, <name>-PROVENANCE.json,
    <name>-LICENSE.txt → {paths}. Refuses without a run unless the
    netlists-only export is acceptable (liberty then absent, said)."""
    res = evaluate_open_library(manager, name)
    if not res.get('ok'):
        return res
    lib, adm, char = res['library'], res['admission'], \
        res['characterization']
    if not adm['open_source_ready'] and not force:
        return {'ok': False, 'name': name, 'refusal':
                f'"{name}" is NOT open_source_ready — {adm["why"]} '
                f'(force=True exports a research-only bundle)',
                'disclaimer': DISCLAIMER}
    os.makedirs(outdir, exist_ok=True)
    paths, missing = {}, []
    libt = open_liberty_text(manager, name)
    if libt.get('ok'):
        paths['liberty'] = os.path.join(outdir, f'{name}.lib')
        with open(paths['liberty'], 'w') as fh:
            fh.write(libt['text'])
    else:
        missing.append({'file': f'{name}.lib',
                        'refusal': libt.get('refusal')})
    paths['netlists'] = os.path.join(outdir, f'{name}.sp')
    with open(paths['netlists'], 'w') as fh:
        fh.write(_all_subckt_text(name, adm['admitted']))
    prov = {
        'library': name, 'generated_at': _now(),
        'devices': {'n': lib['n_device'], 'p': lib['p_device'],
                    'pair': lib['pair_name']},
        'proof_status': adm['libraryStatus'],
        'device_status': adm['deviceStatus'],
        'open_source_ready': adm['open_source_ready'],
        'admitted': adm['admitted'], 'excluded': adm['excluded'],
        'why': adm['why'], 'rule': adm['rule'],
        'proof_chain': adm['proofs'],
        'evidence': [ev.item_summary(ev.item_payload(it))
                     for n_, it in ev.evidence_items(manager).items()
                     if n_ in _evidence_refs(adm)],
        'evidence_names': _evidence_refs(adm),
        'characterization': char,
        'licence': {'artifacts': ARTIFACT_LICENCE,
                    'circuits': CIRCUIT_LICENCE,
                    'statement': LICENCE_STATEMENT},
        'jurisdiction': ev.JURISDICTION, 'scope': SCOPE_LINE,
        'reviewed_at': ev.REVIEWED_AT, 'disclaimer': DISCLAIMER,
    }
    paths['provenance'] = os.path.join(outdir, f'{name}-PROVENANCE.json')
    with open(paths['provenance'], 'w') as fh:
        json.dump(prov, fh, indent=1)
    paths['license'] = os.path.join(outdir, f'{name}-LICENSE.txt')
    with open(paths['license'], 'w') as fh:
        fh.write(_license_text(name, lib, adm))
    return {'ok': True, 'name': name, 'outdir': outdir, 'paths': paths,
            'missing': missing, 'open_source_ready':
            adm['open_source_ready'], 'forced': bool(force),
            'disclaimer': DISCLAIMER}


# ── ladder tie-in (cell-4 as DATA) ─────────────────────────────────

LADDER_RUNG = 'standard-cell'       # DesignLevelDefinition.name
LADDER_NODE = 'polari-cell-lib'     # MicrochipDesignNode.name


def _find(manager, cls, name):
    for r in _rows(manager, cls):
        if getattr(r, 'name', '') == name:
            return r
    return None


def ladder_cell_rung_update(manager, apply=False):
    """The update the microchip ladder's 'standard-cell' rung
    (DesignLevelDefinition) and 'polari-cell-lib' node
    (MicrochipDesignNode) need: status 'characterized' with artifact
    refs = the library run names, metrics = cell count / proven
    count / open-ready libraries. Writes the rows only with
    apply=True (manager.db try/except like every other module)."""
    idx = open_library_index(manager)
    runs = [r for r in _rows(manager, 'CellCharacterizationRun')
            if str(getattr(r, 'cell', '')).startswith('library:')
            and getattr(r, 'liberty_text', '')]
    runs.sort(key=lambda r: getattr(r, 'ran_at', ''))
    run_names = [r.name for r in runs]
    characterized_cells = set()
    for r in runs:
        characterized_cells.update(_run_cells(r)[1])
    proven = sorted({c for l in idx['libraries'] for c in
                     json.loads(evaluate_open_library(manager, l['name'])
                                ['fields']['cells_json'])})
    status = 'characterized' if run_names else 'unbuilt'
    metrics = {
        'cell_count': len(OPEN_CELL_KEYS),
        'proven_free_cells': len(proven),
        'characterized_cells': sorted(characterized_cells),
        'characterized_cell_count': len(characterized_cells),
        'runs': run_names,
        'open_ready_libraries': idx['ready'],
        'libraries': [{'name': l['name'],
                       'open_source_ready': l['open_source_ready'],
                       'libraryStatus': l['libraryStatus'],
                       'run': l['run']} for l in idx['libraries']],
        'cell4_stamp': _now(),
        'licence': ARTIFACT_LICENCE,
    }
    refs = ([{'module': 'cntfet', 'class': 'CellCharacterizationRun',
              'name': n} for n in run_names]
            + [{'module': 'cntfet', 'class': 'OpenCellLibrary',
                'name': l['name']} for l in idx['libraries']])
    rung_update = {
        'name': LADDER_RUNG, 'class': 'DesignLevelDefinition',
        'status': status,
        'artifact_classes_json': json.dumps([
            {'module': 'cntfet', 'class': 'CNTCellDefinition'},
            {'module': 'cntfet', 'class': 'CellCharacterizationRun'},
            {'module': 'cntfet', 'class': 'OpenCellLibrary'}]),
        'notes': (f'cell-4: {len(characterized_cells)} cells characterized '
                  f'over {len(run_names)} run(s); {len(proven)}/'
                  f'{len(OPEN_CELL_KEYS)} cells proven-free; open-ready '
                  f'libraries: {idx["ready"]}' if run_names else
                  'refuses until a library run exists — no fake cells'),
    }
    node_update = {
        'name': LADDER_NODE, 'class': 'MicrochipDesignNode',
        'status': status,
        'artifact_refs_json': json.dumps(refs),
        'metrics_json': json.dumps(metrics),
        'notes': rung_update['notes'],
    }
    out = {'ok': True, 'status': status, 'rung': rung_update,
           'node': node_update, 'applied': False, 'found': {},
           'disclaimer': DISCLAIMER}
    if not run_names:
        out['refusal'] = ('no library characterization run — the rung '
                          'stays unbuilt (characterize_open_library)')
    if apply:
        for upd in (rung_update, node_update):
            row = _find(manager, upd['class'], upd['name'])
            out['found'][upd['name']] = row is not None
            if row is None:
                continue
            for k, v in upd.items():
                if k in ('name', 'class'):
                    continue
                if k == 'metrics_json':
                    try:
                        merged = json.loads(getattr(row, k, '{}') or '{}')
                    except ValueError:
                        merged = {}
                    merged.update(json.loads(v))
                    v = json.dumps(merged)
                setattr(row, k, v)
            _save(manager, row)
        out['applied'] = True
    return out


# ── page seed ──────────────────────────────────────────────────────

def _item(item_id, index, segments, title, component, inputs):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {'componentName': component, 'inputs': inputs},
        'item': None, 'nestedRows': [],
    }


def _open_library_page():
    from cntfet.cnt_page import _device_graph, _row, _sapi, _table
    # Every GET payload reads through api-structured-panel (chips /
    # prose / tables / key-value) — never a JSON wall. hide/pick are
    # tuned to the report shape: `row` is the OpenCellLibrary record
    # (already the table above, and it carries *_json strings),
    # `proof` is a dict-of-dicts (the freedom-proof-panel beside it
    # IS that reading) and `artifacts` is a dict-of-dicts that only
    # renders once picked as its own panel.
    rows = [
        _row(0, [
            _table('open-library-table', 0, 6,
                   'Open cell libraries (rows: admitted cells, proof '
                   'roll-up, open_source_ready, run, licence)',
                   'OpenCellLibrary',
                   'name,n_device,p_device,pair_name,'
                   'library_proof_status,open_source_ready,licence,'
                   'run_ref,liberty_bytes'),
            _sapi('open-library-index', 1, 6,
                  'Open libraries: ready flag + counts + why '
                  '(US; circuits public domain, artifacts GPL-3.0)',
                  '/api/cntfet/open-library', hide='cellUniverse'),
        ], min_height=360),
    ]
    for i, seed in enumerate(SEED_OPEN_LIBRARIES):
        name, n_dev = seed['name'], seed['n_device']
        rows.append(_row(10 * (i + 1), [
            _sapi(f'open-library-{name}', 0, 6,
                  f'{seed["display_name"]}: admission, characterization, '
                  f'scores, power, licence',
                  f'/api/cntfet/open-library/{name}',
                  hide='row,proof,artifacts'),
            _item(f'open-library-{name}-proof', 1, 6,
                  f'{name}: freedom proof of the n device {n_dev} '
                  f'(the chain that gates the library)',
                  'freedom-proof-panel',
                  {'path': f'/api/cntfet/device/{n_dev}/proof'}),
        ], min_height=460))
        rows.append(_row(10 * (i + 1) + 1, [
            _sapi(f'open-library-{name}-artifacts', 0, 4,
                  f'{name}: artifacts (Liberty, netlists, export)',
                  f'/api/cntfet/open-library/{name}', pick='artifacts'),
            _device_graph(f'open-library-{name}-cell-scores', 1, 8,
                          f'{name}: admitted cells scored vs {n_dev}\'s '
                          f'intrinsic limits (refuses until '
                          f'characterized)',
                          n_dev, 'cell-scores'),
        ], min_height=430))
    rows.append(_row(100, [
        _item('open-library-evidence-browser', 0, 12,
              'Evidence (patents, papers, licences) + proof status per '
              'FET / cell / process (US) — the rows admission is a rule '
              'over', 'evidence-browser', {}),
    ], min_height=520))
    return {
        'name': 'open-library',
        'description': 'The open-library gate: which cells on which '
                       'device pair are PROVEN free (US) to ship as '
                       'open source, the roll-up, the characterized '
                       'Liberty + netlists, and the evidence behind '
                       'every admission. ' + DISCLAIMER,
        'source_class': 'OpenCellLibrary',
        'isPage': True, 'pageRoute': 'open-library',
        'linkedSolutions': '[]',
        'definition': json.dumps({'rows': rows}),
    }


SEED_OPEN_LIBRARY_PAGES = [_open_library_page()]

#: Routes the integrator wires (cnt_api) — data, so the selftest and
#: the handoff read the same list.
API_ROUTES = [
    {'method': 'GET', 'path': '/api/cntfet/open-library',
     'fn': 'open_library_index(manager)'},
    {'method': 'GET', 'path': '/api/cntfet/open-library/{name}',
     'fn': 'open_library_report(manager, name)'},
    {'method': 'GET', 'path': '/api/cntfet/open-library/{name}/liberty',
     'fn': 'open_liberty_text(manager, name) → text/plain'},
    {'method': 'POST', 'path': '/api/cntfet/open-library/{name}',
     'fn': '{action: refresh | characterize (drives, force) | export '
           '(outdir, force) | ladder-update (apply)}'},
]
