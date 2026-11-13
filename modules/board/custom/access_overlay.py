"""
@module board.custom.access_overlay

hal-4 (econ, HAL_CATOM_CATALOGUE_PLAN.md §4b): the ACCESS half of a chip description. An imported structure (board.custom.svd_import)
knows bits and resets but only a coarse access word; the reference manual's register chapters say each field's access CODE (R/W, RO,
WT, WO, R/W/SC, R/SS/WTC, R/WTC/SS ...) and what it means. This module reads those codes out of the manual's text and merges them, cited,
onto the imported rows.

Input text = `pdftotext -layout` of the manual, pages split on form feeds, and a chapter table per block: (first page, last page, the
manual's field-name prefix, optional spelling aliases). The rules, learnt on the ESP32-C3 TRM v1.4:
- A field description starts at a NAME line (an upper-case name that may carry a lowercase n / x array placeholder: LEDC_TIMER_SEL_CHn)
  and runs until its code "(R/W)"; it is capped at 6 lines on its own page, so a code is never borrowed from a neighbouring field.
- ACCEPTANCE: a code is accepted only when the field's NAME matches an imported field AND the register header printed above it (its
  offset, or for an array "0x0000+20*n" (n: 0-5) any element's offset) is that field's register. pdftotext prints two-register pages
  out of order, so a name-only match goes to REVIEW: the field stays trm_access '' (= missing to the HAL's choose(), which fails closed)
  until a person cites it from the rendered page.
- One field described once for a run of registers (INTERRUPT_CORE0_SOURCE_X_MAP, p.214) applies to every register of the run that
  prints no field of its own.
- Placeholders collapse only where the manual uses one (CHn ~ CH0..5 / LSCH0..5; TIMERx ~ TIMER0..3); a real index (UNIT0 vs UNIT1) never
  collapses. A per-block alias (canon) maps spellings that differ between sources to one form.
merge() never resolves a disagreement silently: a code whose direction contradicts the SVD's word is merged (the manual's code is the
access fact) AND reported.
"""
import re

CODES = ('R/W', 'RO', 'WO', 'WT', 'R/W/SC', 'R/W/SS', 'R/SS/WTC', 'R/WTC/SS', 'R/SC/WTC', 'R/SS/SC/WTC', 'R/W/SS/SC', 'R/WC/SS', 'R/WS/SS/SC',
         'R/WC/SC', 'R/WS/SC', 'R/SS', 'R/SC')
_CODE = r'(' + '|'.join(re.escape(c) for c in sorted(CODES, key=len, reverse=True)) + r')'
CODE_RE = re.compile(r'\(' + _CODE + r'\)')
NAME = r'[A-Z][A-Z0-9_]*(?:[nx][A-Z0-9_]*)*'
REG_RE = re.compile(r'Register\s+(\d+\.\d+)\.\s+(' + NAME + r'_REG)\s*(?:\(([nx]):\s*(\d+)\s*[-~]\s*(\d+)\))?\s*\((0x[0-9A-Fa-f]+)(?:\s*\+\s*(\d+)\s*\*\s*[nx])?\)')
START_RE = re.compile(r'^\s*(' + NAME + r')(?:\s+(\S.*))?$')
SHARED_RE = re.compile(r'_SOURCE_X_')
MAXLINES = 6


def placeholders(s):
    """the manual's array placeholders and an SVD's indices / %s -> '#' (LSCH3 / CHn / CH%s -> CH#; LSTIMER2 / TIMERx -> TIMER#)"""
    s = s.replace('%s', '#')
    s = re.sub(r'(^|_)LS(?=CH|TIMER)', r'\1', s)
    s = re.sub(r'(CH|TIMER)(?:[nx]|\d+|#)(?=_|$)', r'\1#', s)
    return re.sub(r'(?<=_)[nx](?=_|$)', '#', s)


def _header(m, page):
    off = int(m.group(6), 16)
    stride = int(m.group(7)) if m.group(7) else 0
    lo, hi = (int(m.group(4)), int(m.group(5))) if m.group(3) else (0, 0)
    return {'name': m.group(2), 'table': m.group(1), 'page': page, 'offsets': {off + stride * i for i in range(lo, hi + 1)} if stride else {off}}


def extract(pages, first, last, prefix):
    """the manual's field descriptions on pages first..last -> [{field, code | None, text, page, header | None, run | None}]"""
    rows, cur, header, run = [], None, None, []

    def close():
        if cur:
            e = CODE_RE.search(cur['text'])
            cur['code'] = e.group(1) if e else None
            cur['text'] = re.sub(r'(\w)- (\w)', r'\1\2', ' '.join(CODE_RE.sub('', cur['text']).split())).strip().rstrip('.') + '.'
            rows.append(cur)
    for pno in range(first, last + 1):
        for line in pages[pno - 1].splitlines():
            m = REG_RE.search(line)
            if m:
                header = _header(m, pno)
                run.append(header)
                continue
            s = START_RE.match(line)
            d0 = (s.group(2) or ' ')[0] if s else ''
            if s and s.group(1).startswith(prefix.rstrip('_')) and not s.group(1).endswith('_REG') and len(s.group(1)) >= 4 \
                    and (not s.group(2) or d0.isupper() or d0.isdigit() or d0 in '(•'):
                desc = s.group(2) or ''
                if cur and not CODE_RE.search(cur['text']) and desc[:1].islower():
                    cur['text'] += ' ' + line.strip()
                    continue
                close()
                cur = {'field': s.group(1), 'text': desc, 'page': pno, 'header': header, 'lines': 0, 'run': None}
                if SHARED_RE.search(s.group(1)):
                    cur['run'], run = list(run), []
                else:
                    run = []
            elif cur and not CODE_RE.search(cur['text']) and line.strip():
                cur['lines'] += 1
                if cur['lines'] <= MAXLINES and pno == cur['page']:
                    cur['text'] += ' ' + line.strip()
    close()
    return rows


def _forms(rn, fn, prefix, canon):
    """the ways the manual may name an imported field: FIELD, REG_FIELD, TOKEN_FIELD, FIELD_TOKEN (+ the block prefix stripped from the field)"""
    fns, parts = {canon(fn)}, canon(fn).split('_')
    ptoks = set(prefix.strip('_').split('_'))
    while len(parts) > 1 and parts[0] in ptoks:
        parts = parts[1:]
        fns.add('_'.join(parts))
    toks = [t for t in rn.split('_') if t]
    out = set()
    for f in fns:
        out |= {f, rn + '_' + f} | {t + '_' + f for t in toks} | {f + '_' + t for t in toks}
    return out


def overlay(pages, chapter, fields, registers, canon=None):
    """the codes one chapter's text gives the imported rows of its block.
    chapter = {'first', 'last', 'prefix'}; fields / registers = the svd_import rows of that block.
    -> {'accepted': {(register, field): {...}}, 'review': [...], 'no_code': [...], 'unmatched': [...], 'ambiguous': [...]}"""
    aliased = canon is not None
    canon = canon or (lambda x: x)
    prefix = chapter['prefix']
    off = {r['register']: r['offset'] for r in registers}
    idx = []
    for f in fields:
        rn = f['svd_register']
        idx.append((f, placeholders(rn), placeholders(f['field']), rn, f['field']))
    out = {'accepted': {}, 'review': [], 'no_code': [], 'unmatched': [], 'ambiguous': []}
    for row in extract(pages, chapter['first'], chapter['last'], prefix):
        if row['code'] is None:
            out['no_code'].append(row['field'])
            continue
        if row['run'] is not None:   # one field described for a run of registers: each register of the run, field = its name
            for h in row['run']:
                hit = [f for f in fields if off[f['register']] in h['offsets']]
                if len(hit) == 1:
                    out['accepted'][(hit[0]['register'], hit[0]['field'])] = dict(code=row['code'], page=row['page'], text=row['text'],
                                                                                  table=h['table'], trm_field=row['field'], header=h['name'])
            continue
        # a block with a spelling alias canonicalises the whole name (the alias strips the prefix itself); otherwise drop the prefix
        t = canon(row['field']) if aliased else (row['field'][len(prefix):] if row['field'].startswith(prefix) else row['field'])
        ph = re.search(r'(?:CH|TIMER)[nx](?=_|$)|(?<=_)[nx](?=_|$)', t) is not None
        tt = placeholders(t) if ph else t
        cands = [f for f, prn, pfn, rn, fn in idx if tt in (_forms(prn, pfn, prefix, canon) if ph else _forms(rn, fn, prefix, canon))]
        fams = {(placeholders(f['svd_register']), placeholders(f['field'])) if ph else (f['svd_register'], f['field']) for f in cands}
        if len(fams) > 1 and row['header']:
            here = [f for f in cands if off[f['register']] in row['header']['offsets']]
            if here:
                cands = here
                fams = {(placeholders(f['svd_register']), placeholders(f['field'])) if ph else (f['svd_register'], f['field']) for f in cands}
        if not cands:
            out['unmatched'].append(row['field'])
            continue
        if len(fams) > 1:
            out['ambiguous'].append(row['field'])
            continue
        if not (row['header'] and all(off[f['register']] in row['header']['offsets'] for f in cands)):
            out['review'].extend({'register': f['register'], 'field': f['field'], 'code_seen': row['code'], 'page': row['page'], 'trm_field': row['field']}
                                 for f in cands)
            continue
        for f in cands:
            out['accepted'][(f['register'], f['field'])] = dict(code=row['code'], page=row['page'], text=row['text'], table=row['header']['table'],
                                                                trm_field=row['field'], header=row['header']['name'])
    return out


_READS = lambda c: not c.startswith(('WO', 'WT'))
_WRITES = lambda c: c not in ('RO', 'R/SS', 'R/SC')


def merge(fields, ov, document):
    """the imported fields with the accepted codes merged, cited -> (fields, conflicts). A reviewed or uncited field keeps trm_access ''.
    A conflict = the manual's code says a direction the SVD's word denies (read-only but writable, ...): merged, AND reported."""
    out, conflicts = [], []
    for f in fields:
        a = ov['accepted'].get((f['register'], f['field']))
        if not a:
            out.append(dict(f))
            continue
        c, sv = a['code'], f.get('svd_access', '')
        if (sv == 'read-only' and _WRITES(c)) or (sv == 'write-only' and _READS(c)) or (sv == 'read-write' and not (_READS(c) and _WRITES(c))):
            conflicts.append({'register': f['register'], 'field': f['field'], 'trm': c, 'svd': sv, 'page': a['page']})
        out.append(dict(f, trm_access=c, description=a['text'] or f['description'],
                        page_table='Register %s %s, p.%d (%s)' % (a['table'], a['header'], a['page'], document),
                        notes='TRM access %s (overlay: name + register header agree)' % c))
    return out, conflicts


#: the HAL access table's words (agreed with pol, plan §4b) that an SVD can say by itself: (svd access, modifiedWriteValues) -> word
SVD_WORDS = {('read-write', ''): 'rw', ('read-only', ''): 'r', ('write-only', ''): 'w', ('read-write', 'oneToClear'): 'r-w1c'}


def from_svd(field):
    """For a chip with no reference manual of its own (our own RTL: SystemRDL -> SVD), the SVD IS the spec: its access word and
    svd_semantics -> (the HAL access word, the cite) or (None, why). Only the combinations in SVD_WORDS are mapped; anything else (a
    readAction, oneToSet, writeConstraint ...) has no agreed word yet and stays missing, said - never guessed. A self-clearing
    write (SystemRDL singlepulse) has no CMSIS-SVD form, so from the SVD alone it is a plain 'w', never 'w-strobe'."""
    sem = field.get('svd_semantics') or {}
    if sem.get('readAction'):
        return None, 'readAction %s: no HAL access word agreed for a read side effect yet' % sem['readAction']
    if sem.get('writeConstraint'):
        return None, 'writeConstraint %s: not mapped yet' % sem['writeConstraint']
    key = (field.get('svd_access', ''), sem.get('modifiedWriteValues', ''))
    word = SVD_WORDS.get(key)
    if word is None:
        return None, 'SVD access %s / modifiedWriteValues %s: no HAL access word agreed' % (key[0] or '-', key[1] or '-')
    return word, 'SVD %s: access %s%s' % (field.get('page_table', '').replace('SVD ', ''), key[0], ', modifiedWriteValues ' + key[1] if key[1] else '')


def apply_svd(fields):
    """from_svd over imported rows -> (fields with access_word / access_source 'svd' / access_cite, the fields left without a word + why).
    trm_access stays '' (there is no manual): the HAL's access table reads access_word when access_source is 'svd'."""
    out, left = [], []
    for f in fields:
        word, why = from_svd(f)
        if word:
            out.append(dict(f, access_word=word, access_source='svd', access_cite=why))
        else:
            out.append(dict(f, access_word='', access_source='', access_cite=''))
            left.append({'register': f['register'], 'field': f['field'], 'why': why})
    return out, left
