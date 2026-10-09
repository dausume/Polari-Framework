"""
@module board.custom.datasheets

ucd-doc (his ask, 2026-10-09, verbatim): "We should also be tracking data sheets as both documents and believe we
already do as data, but I believe there are 3 different kinds of data sheets usually for a board. Then some happen
to have all 3 in 1 so we have 4 types of data sheets to track." THE KNOWN DOCUMENTS this board arc already cites,
named and kinded, built from the actual sources (never hand-typed a second time where a module already holds the
string): board.custom.uno_facts (boards.txt, the UNO docs page, the Arduino language reference, Optiboot, the
ATmega328P datasheet, the TMP36 datasheet), board.custom.board_uno (the UNO's Full Pinout PDF), board.custom.
soc_atmega328p (the same ATmega328P datasheet), board.custom.board_c3 (the ESP32-C3 datasheet + the ingested Zephyr
board directory), board.custom.pin_roles (the ESP32-C3-DevKitM-1 user guide + Wikipedia, as label+url sources, no
DatasheetFact of their own), board.custom.kit_parts (the Arduino Starter Kit book, cited on every KitPart.source —
also no DatasheetFact of its own).

THE FOUR-PLUS-ONE KINDS (soc | board | programming | combined | other), his wording: the chip's own datasheet (soc),
the board's own reference — pinout/schematic/connectors/parts (board), the bootloader/flash-protocol/toolchain
settings (programming), one document carrying all three (combined — none cited here yet), and everything else named
honestly (other: a kit book, a language reference, a sensor datasheet for a KIT PART rather than the board/chip
itself, a Wikipedia page, an ingested repo file). `rows(fact_rows, field_rows)` is the one function that MATTERS:
given the live DatasheetFact/RegisterField rows a seed just built, it resolves each one's `datasheet` field (set in
place) against the table below, synthesizes an `undetermined` row for anything this table does not recognize
(never dropped, never guessed — brd's derive-or-cite posture), and returns the Datasheet rows with their reverse
links filled. `board_coverage(...)` derives BoardDefinition.datasheets_json from the result.
"""
import json
import re

from board.custom import board_c3 as C
from board.custom import board_uno as U
from board.custom import kit_parts as KP
from board.custom import pin_roles as PR
from board.custom import target_compat as TC
from board.custom.uno_facts import (BOARDS_TXT, BOARDS_TXT_REV, UNO_DOC, DOUBLE_DOC, OPTIBOOT, M328_DOC, M328_REV,
                                    M328_URL, TMP36_DOC, TMP36_REV, TMP36_URL)

KIND_CHOICES = ('soc', 'board', 'programming', 'combined', 'other', 'undetermined')
_SHA_RE = re.compile(r'sha256 ([0-9a-f]{64})')
_DATE_RE = re.compile(r'(20\d\d-\d\d-\d\d)')


def _sha(revision):
    m = _SHA_RE.search(revision or '')
    return m.group(1) if m else ''


def _fetched(revision):
    m = _DATE_RE.search(revision or '')
    return m.group(1) if m else ''


def _zephyr_doc_rev():
    """The (document, revision) board_c3.facts() actually uses for the ingested Zephyr files — read FROM the
    module's own facts rather than retyped here, so a changed TAG/commit never drifts out of sync."""
    for f in C.facts():
        if f['document'].startswith('Zephyr'):
            return f['document'], f['revision']
    return 'Zephyr RTOS (Apache-2.0)', ''  # pragma: no cover — board_c3 always cites it; named, never silently empty


_ZDOC, _ZREV = _zephyr_doc_rev()
_ESPRESSIF_USER_GUIDE_URL = 'https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html'


def _static_rows():
    """The known-documents table: one dict per distinct document this codebase cites today, each carrying its own
    `_match` spec — (document, revision) pairs and/or bare urls that resolve a DatasheetFact/RegisterField/role
    citation to this row. `pages`/`sha256`/`fetched_at` are extracted from the citing module's own `revision` string
    (derive-or-cite: never a second, hand-typed copy of a fact already on record)."""
    return [
        # ------------------------------------------------------------------ soc
        {'name': 'atmega328p-ds40002061b', 'title': 'Microchip ATmega48A/PA/88A/PA/168A/PA/328/P datasheet (DS40002061B)',
         'kind': 'soc', 'for_soc': 'atmega328p', 'for_board': '', 'publisher': 'Microchip (Atmel)', 'revision': M328_REV,
         'url': M328_URL, 'sha256': _sha(M328_REV), 'fetched_at': _fetched(M328_REV), 'pages': 0, 'format': 'pdf',
         'licence_note': '', 'covers': [],
         'origin': 'derived:board.custom.uno_facts.M328_DOC/M328_REV/M328_URL — the same file soc_atmega328p.py and '
                   'register_fields_atmega328p.py (via hardware_chain._cite) cite for every ATmega328P fact/field',
         'notes': 'the chip\'s own datasheet: registers (register_fields_atmega328p), pins (soc_atmega328p), electrical limits',
         '_match': [(M328_DOC, M328_REV)], '_url': [M328_URL]},
        # ------------------------------------------------------------------ board (the UNO: two distinct documents)
        {'name': 'arduino-uno-r3-docs', 'title': 'Arduino UNO R3 docs page (docs.arduino.cc/hardware/uno-rev3/)',
         'kind': 'board', 'for_soc': '', 'for_board': 'arduino-uno-r3', 'publisher': 'Arduino',
         'revision': 'as cited by plan §3 (not re-fetched 2026-10-01)', 'url': UNO_DOC, 'sha256': '', 'fetched_at': '',
         'pages': 0, 'format': 'web', 'licence_note': '', 'covers': [],
         'origin': 'derived:board.custom.uno_facts.UNO_DOC — the tech-specs facts (flash/sram/eeprom/usb_serial_chip) '
                   'cite this page; pin_roles.ROLES also cites it per-role (ARDUINO_UNO_DOCS, matched here by url)',
         'notes': 'the board\'s own product page: pinout/connectors/parts in summary form',
         '_match': [('Arduino UNO R3 product page', 'as cited by plan §3 (not re-fetched 2026-10-01)')], '_url': [UNO_DOC]},
        {'name': 'arduino-uno-r3-pinout', 'title': U.DOC, 'kind': 'board', 'for_soc': '', 'for_board': 'arduino-uno-r3',
         'publisher': 'Arduino', 'revision': U.REV, 'url': U.URL, 'sha256': _sha(U.REV), 'fetched_at': _fetched(U.REV),
         'pages': 5, 'format': 'pdf', 'licence_note': 'CC BY-SA 4.0 (we cite its facts, we do not copy the drawing)',
         'covers': [],
         'origin': 'derived:board.custom.board_uno.DOC/REV/URL — every board_uno.facts() row (every BoardPin\'s own '
                   'pinout.* fact) cites this file',
         'notes': 'a SECOND board-kind document for the UNO, distinct from arduino-uno-r3-docs (different file, '
                 'different revision/url) — this one IS fetched and hashed, so BoardDefinition.datasheets_json '
                 'prefers it as the UNO\'s "board" coverage slug (board.custom.datasheets.board_coverage: a '
                 'sha256-bearing row is preferred over a not-re-fetched one when more than one of a kind matches)',
         '_match': [(U.DOC, U.REV)], '_url': [U.URL]},
        # ------------------------------------------------------------------ programming (the UNO: two documents)
        {'name': 'arduino-boards-txt', 'title': 'ArduinoCore-avr boards.txt (uno entry)', 'kind': 'programming',
         'for_soc': '', 'for_board': 'arduino-uno-r3', 'publisher': 'Arduino (ArduinoCore-avr)', 'revision': BOARDS_TXT_REV,
         'url': BOARDS_TXT, 'sha256': _sha(BOARDS_TXT_REV), 'fetched_at': _fetched(BOARDS_TXT_REV), 'pages': 0,
         'format': 'repo-file', 'licence_note': '', 'covers': [],
         'origin': 'derived:board.custom.uno_facts.BOARDS_TXT_REV — every upload.*/bootloader.*/build.*/usb_id.* fact cites it',
         'notes': 'the toolchain settings: upload size/speed/protocol, the bootloader file, build.mcu/f_cpu',
         '_match': [('ArduinoCore-avr boards.txt (uno entry)', BOARDS_TXT_REV)], '_url': [BOARDS_TXT]},
        {'name': 'arduino-optiboot-readme', 'title': 'Optiboot README', 'kind': 'programming', 'for_soc': '',
         'for_board': 'arduino-uno-r3', 'publisher': 'Optiboot (GitHub)',
         'revision': 'as cited by plan §3 (not re-fetched 2026-10-01)', 'url': OPTIBOOT, 'sha256': '', 'fetched_at': '',
         'pages': 0, 'format': 'repo-file', 'licence_note': '', 'covers': [],
         'origin': 'derived:board.custom.uno_facts.OPTIBOOT — the optiboot_size fact cites it',
         'notes': 'the bootloader itself (the 512-byte Optiboot that boards.txt\'s upload.maximum_size already subtracts)',
         '_match': [('Optiboot README', 'as cited by plan §3 (not re-fetched 2026-10-01)')], '_url': [OPTIBOOT]},
        # ------------------------------------------------------------------ other (not the board/chip/programming itself)
        {'name': 'arduino-language-reference-double', 'title': 'Arduino language reference: double', 'kind': 'other',
         'for_soc': '', 'for_board': '', 'publisher': 'Arduino', 'revision': 'as cited by plan §1 (not re-fetched 2026-10-01)',
         'url': DOUBLE_DOC, 'sha256': '', 'fetched_at': '', 'pages': 0, 'format': 'web', 'licence_note': '', 'covers': [],
         'origin': 'derived:board.custom.uno_facts.DOUBLE_DOC — the sizeof_double fact cites it',
         'notes': "a SOFTWARE/language reference, not a chip/board/programming document — kept 'other' on purpose "
                  "(it only tells c_twin's AVR mode that sizeof(double)==4)",
         '_match': [('Arduino language reference: double', 'as cited by plan §1 (not re-fetched 2026-10-01)')], '_url': [DOUBLE_DOC]},
        {'name': 'analog-devices-tmp36', 'title': TMP36_DOC, 'kind': 'other', 'for_soc': '', 'for_board': '',
         'publisher': 'Analog Devices', 'revision': TMP36_REV, 'url': TMP36_URL, 'sha256': _sha(TMP36_REV),
         'fetched_at': _fetched(TMP36_REV), 'pages': 0, 'format': 'pdf', 'licence_note': '', 'covers': [],
         'origin': 'derived:board.custom.uno_facts.TMP36_DOC/TMP36_REV/TMP36_URL — the tmp36.scale/tmp36.offset facts '
                   'cite it; board.custom.kit_parts.TMP36 row cites the same datasheet by name in its own `source`',
         'notes': "a KIT-PART sensor's own vendor datasheet, not the UNO board/chip/programming documents — kept "
                  "'other'; NOT fetched this session (TMP36_REV: analog.com timed out from pol-core 2026-10-01), no sha256",
         '_match': [(TMP36_DOC, TMP36_REV)], '_url': [TMP36_URL]},
        {'name': 'arduino-starter-kit-book', 'title': KP.BOOK, 'kind': 'other', 'for_soc': '',
         'for_board': '', 'publisher': 'Arduino', 'revision': '', 'url': '', 'sha256': '', 'fetched_at': '', 'pages': 0,
         'format': 'text', 'licence_note': '', 'covers': [],
         'origin': "derived:board.custom.kit_parts.BOOK — every KitPart row's own `source` cites one of its pages "
                   "(\"Parts in your kit\" pp.6-9, \"The Arduino Board\" p.11, \"Circuit symbols\" p.10); it cites no "
                   "DatasheetFact/RegisterField of its own (KitPart rows are a different class), so this row carries "
                   "no facts_refs/fields_refs — named as his example row regardless",
         'notes': 'a physical book, not re-fetched this session — no url/sha256 to cite',
         '_match': [], '_url': []},
        # ------------------------------------------------------------------ the ESP32-C3
        {'name': 'espressif-esp32-c3-datasheet', 'title': C.DS_DOC, 'kind': 'soc', 'for_soc': 'esp32c3', 'for_board': '',
         'publisher': 'Espressif', 'revision': C.DS_REV, 'url': C.DS_URL, 'sha256': _sha(C.DS_REV),
         'fetched_at': _fetched(C.DS_REV), 'pages': 0, 'format': 'pdf', 'licence_note': '', 'covers': [],
         'origin': 'derived:board.custom.board_c3.DS_DOC/DS_REV/DS_URL — every SocPin IO-MUX fact (Table 2-4/2-6) cites it',
         'notes': "the chip's own datasheet (IO MUX pin functions, analog functions, the USB Serial/JTAG pins)",
         '_match': [(C.DS_DOC, C.DS_REV)], '_url': [C.DS_URL]},
        {'name': 'espressif-esp32-c3-devkitm-user-guide', 'title': 'Espressif ESP32-C3-DevKitM-1 user guide',
         'kind': 'board', 'for_soc': '', 'for_board': 'esp32-c3', 'publisher': 'Espressif', 'revision': '',
         'url': _ESPRESSIF_USER_GUIDE_URL, 'sha256': '', 'fetched_at': '', 'pages': 0, 'format': 'web',
         'licence_note': '', 'covers': [],
         'origin': 'derived:board.custom.pin_roles.ROLES[\'button\'][\'sources\'] — cited only for the BOOT/user button role',
         'notes': "kept kind='board' rather than 'combined': nothing board_c3.py cites from this guide names "
                  "flashing/bootloader content (the C3's own programming reference is not cited anywhere yet — see "
                  "a board's datasheets_json, which names it missing); decide again if a flashing fact ever cites this url",
         '_match': [], '_url': [_ESPRESSIF_USER_GUIDE_URL]},
        {'name': 'zephyr-esp32c3-devkitm-ingest', 'title': 'Zephyr RTOS — esp32c3_devkitm board directory (ingested)',
         'kind': 'other', 'for_soc': 'esp32c3', 'for_board': 'esp32-c3', 'publisher': 'Zephyr Project (Apache-2.0)',
         'revision': _ZREV, 'url': 'https://github.com/zephyrproject-rtos/zephyr/tree/%s/' % C.TAG, 'sha256': '',
         'fetched_at': '', 'pages': 0, 'format': 'repo-file', 'licence_note': 'Apache-2.0', 'covers': [],
         'origin': 'derived:board.custom.board_c3.facts() — the cpu_clock_hz/memory.*/gpio.ngpios/zephyr.<file> facts '
                   'all cite this ingested board directory (each fact\'s own url points at one specific file/symbol '
                   'within it; grouped here as ONE document since document+revision are the same string for all of them)',
         'notes': "his framing: \"Zephyr's dtsi = other/repo-file\" — kept ONE row (not one per ingested file); "
                 'every per-file sha256 is already on the facts themselves (zephyr.<file> rows, value=sha256)',
         '_match': [(_ZDOC, _ZREV)], '_url': []},
        # ------------------------------------------------------------------ Wikipedia (consolidated — his call, said why)
        {'name': 'wikipedia', 'title': 'Wikipedia (general reference pages)', 'kind': 'other', 'for_soc': '',
         'for_board': '', 'publisher': 'Wikimedia Foundation', 'revision': '', 'url': 'https://en.wikipedia.org/',
         'sha256': '', 'fetched_at': '', 'pages': 0, 'format': 'web', 'licence_note': 'CC BY-SA', 'covers': [],
         'origin': 'derived:board.custom.pin_roles.ROLES[*][\'sources\'] + board.custom.target_compat._KIND_META extras',
         'notes': '',  # filled in by _wikipedia_pages() below (the actual page list, so it never drifts by hand)
         '_match': [], '_url': []},
    ]


def _wikipedia_pages():
    """[(label, url), ...] every Wikipedia page cited by pin_roles.ROLES/target_compat's extra sources — read live,
    never a second hand-typed list."""
    seen, out = set(), []
    for info in PR.ROLES.values():
        for s in info['sources']:
            if 'wikipedia.org' in s['url'] and s['url'] not in seen:
                seen.add(s['url'])
                out.append((s['label'], s['url']))
    for kind in TC.TASK_KINDS:
        for s in TC.sources_for(kind):
            if 'wikipedia.org' in s['url'] and s['url'] not in seen:
                seen.add(s['url'])
                out.append((s['label'], s['url']))
    return sorted(out)


def _slugify(text):
    s = re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')
    return s or 'doc'


def _build_indices(static_rows):
    by_doc_rev, by_url = {}, {}
    for d in static_rows:
        for key in d['_match']:
            by_doc_rev[key] = d['name']
        for u in d['_url']:
            if u:
                by_url[u] = d['name']
    return by_doc_rev, by_url


def rows(fact_rows, field_rows):
    """The Datasheet rows for one seed: `fact_rows` (DatasheetFact dicts) and `field_rows` (RegisterField dicts) are
    MUTATED IN PLACE — each gains its own `datasheet` slug, resolved by (document, revision) first, falling back to
    url (RegisterField carries no `revision` column at all; a handful of DatasheetFact citations share one document
    across several per-file urls, e.g. the ingested Zephyr board directory — document+revision is the document's
    real identity there, not url). A citation this table does not recognize gets a freshly synthesized
    kind='undetermined' row instead of being dropped or guessed at (the brd-bo/derive-or-cite posture) — exercised by
    board_datasheets_selftest.run_datasheets() with a synthetic fact."""
    static = _static_rows()
    wiki = next(d for d in static if d['name'] == 'wikipedia')
    pages = _wikipedia_pages()
    wiki['notes'] = 'pages cited: ' + '; '.join('%s (%s)' % (label, url) for label, url in pages) if pages else 'no Wikipedia page cited yet'
    by_doc_rev, by_url = _build_indices(static)
    facts_refs, fields_refs = {d['name']: [] for d in static}, {d['name']: [] for d in static}
    undetermined = {}

    def resolve(document, revision, url):
        key = (document or '', revision or '')
        if key in by_doc_rev:
            return by_doc_rev[key]
        if url and url in by_url:
            return by_url[url]
        slug = 'undetermined-%s' % _slugify(document)[:48]
        if slug not in undetermined:
            undetermined[slug] = {
                'name': slug, 'title': document or '(no document named)', 'kind': 'undetermined', 'for_soc': '',
                'for_board': '', 'publisher': '', 'revision': revision, 'url': url, 'sha256': _sha(revision),
                'fetched_at': _fetched(revision), 'pages': 0, 'format': 'pdf' if url.lower().endswith('.pdf') else 'text',
                'licence_note': '', 'covers': [],
                'origin': 'polari:synthesized — a DatasheetFact/RegisterField cited this (document, revision, url) '
                          'and board.custom.datasheets._static_rows() does not recognize it',
                'notes': 'undetermined on purpose: never dropped, never guessed a kind for an unrecognized citation '
                         '(document=%r, revision=%r, url=%r)' % (document, revision, url),
                'undetermined': 'kind not known — a person should name it (soc | board | programming | combined | other)',
                '_match': [key], '_url': [url] if url else [],
            }
            facts_refs[slug], fields_refs[slug] = [], []
        return slug

    for f in fact_rows:
        name = resolve(f.get('document', ''), f.get('revision', ''), f.get('url', ''))
        f['datasheet'] = name
        facts_refs.setdefault(name, []).append('DatasheetFact:%s' % f['name'])
    for rf in field_rows:
        name = resolve(rf.get('document', ''), rf.get('revision', ''), rf.get('url', ''))
        rf['datasheet'] = name
        fields_refs.setdefault(name, []).append('RegisterField:%s' % rf['name'])

    out = static + list(undetermined.values())
    for d in out:
        d.pop('_match', None)
        d.pop('_url', None)
        covers = d.pop('covers', [])
        d.setdefault('undetermined', '')
        d['facts_refs_json'] = json.dumps(sorted(facts_refs.get(d['name'], [])))
        d['fields_refs_json'] = json.dumps(sorted(fields_refs.get(d['name'], [])))
        d['covers_json'] = json.dumps(covers)
    return out


def _preferred(candidates):
    """Of several Datasheet rows naming the SAME (kind, for_soc/for_board) — the UNO today has two 'board' rows and
    two 'programming' rows — prefer the one actually fetched-and-hashed (sha256 present) over one not re-fetched
    this session; otherwise the first by name, so the pick is deterministic. Said here once, used by board_coverage
    below, rather than a silent pick buried in a dict comprehension."""
    if not candidates:
        return ''
    with_sha = sorted((c for c in candidates if c.get('sha256')), key=lambda c: c['name'])
    return with_sha[0]['name'] if with_sha else sorted(candidates, key=lambda c: c['name'])[0]['name']


def board_coverage(board_name, soc_definition_name, datasheet_rows):
    """{kind: slug|''} for soc/board/programming/combined — what BoardDefinition.datasheets_json carries. A board
    with no SoC/board/programming document cited yet names it missing (''), e.g. the C3's programming slug today."""
    by_kind_for_soc = {}
    by_kind_for_board = {}
    for d in datasheet_rows:
        if soc_definition_name and d.get('for_soc') == soc_definition_name:
            by_kind_for_soc.setdefault(d['kind'], []).append(d)
        if board_name and d.get('for_board') == board_name:
            by_kind_for_board.setdefault(d['kind'], []).append(d)
    out = {
        'soc': _preferred(by_kind_for_soc.get('soc', [])),
        'board': _preferred(by_kind_for_board.get('board', [])),
        'programming': _preferred(by_kind_for_board.get('programming', [])),
        'combined': _preferred(by_kind_for_board.get('combined', []) + by_kind_for_soc.get('combined', [])),
    }
    return out


def board_coverage_json(board_name, soc_definition_name, datasheet_rows):
    return json.dumps(board_coverage(board_name, soc_definition_name, datasheet_rows), sort_keys=True)
