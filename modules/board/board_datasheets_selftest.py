"""board_datasheets_selftest — ucd-doc (his ask, 2026-10-09, verbatim): "We should also be tracking data sheets as
both documents ... I believe there are 3 different kinds of data sheets usually for a board ... Let's trace these."
Datasheet rows, one per cited document, kinded (soc | board | programming | combined | other | undetermined); every
DatasheetFact/RegisterField resolves to one; a board's own coverage names what is covered and what is missing; a
citation this table does not recognize is 'undetermined', never dropped. Run by board_selftest.run().
"""
import json


def run_datasheets(check):
    from board.board_basis import BOARD_CLASSES, Datasheet, DatasheetFact, RegisterField
    from board.board_seed import BOARD_SEED_PAIRS, SEED_DATASHEETS
    from board.custom import datasheets as DS
    from board.custom.uno_facts import M328_REV

    check('datasheets: Datasheet is a BOARD_CLASSES member', Datasheet in BOARD_CLASSES)

    seeded = {c: rows for c, _cls, rows in BOARD_SEED_PAIRS}
    facts = seeded['DatasheetFact']
    fields = seeded['RegisterField']
    boards = {b['name']: b for b in seeded['BoardDefinition']}
    sheets = {d['name']: d for d in SEED_DATASHEETS}

    try:
        built = [Datasheet(**{k: v for k, v in d.items() if k != '_converge'}) for d in SEED_DATASHEETS]
        check('datasheets: every seed row constructs its class (no stray field)', len(built) == len(SEED_DATASHEETS))
    except TypeError as e:
        check('datasheets: every seed row constructs its class (no stray field)', False, str(e))

    # 1. every DatasheetFact and every RegisterField resolves to a Datasheet row
    bad_facts = [f['name'] for f in facts if not f.get('datasheet') or f['datasheet'] not in sheets]
    check('datasheets: every DatasheetFact resolves to a Datasheet row (%d facts)' % len(facts), not bad_facts, bad_facts[:5])
    bad_fields = [x['name'] for x in fields if not x.get('datasheet') or x['datasheet'] not in sheets]
    check('datasheets: every RegisterField resolves to a Datasheet row (%d fields)' % len(fields), not bad_fields, bad_fields[:5])

    # 2. every Datasheet's own reverse links resolve back to a real fact/field
    fact_by_name = {f['name']: f for f in facts}
    field_by_name = {x['name']: x for x in fields}
    bad_refs = []
    for d in SEED_DATASHEETS:
        for ref in json.loads(d['facts_refs_json']):
            cls, _, name = ref.partition(':')
            if cls != 'DatasheetFact' or name not in fact_by_name:
                bad_refs.append(('facts_refs_json', d['name'], ref))
        for ref in json.loads(d['fields_refs_json']):
            cls, _, name = ref.partition(':')
            if cls != 'RegisterField' or name not in field_by_name:
                bad_refs.append(('fields_refs_json', d['name'], ref))
    check('datasheets: every Datasheet.facts_refs_json/fields_refs_json entry resolves back to a real row', not bad_refs, bad_refs[:5])
    # and the forward/reverse links agree exactly (no fact/field missing from its own datasheet's reverse list)
    want_facts, want_fields = {}, {}
    for f in facts:
        want_facts.setdefault(f['datasheet'], []).append('DatasheetFact:%s' % f['name'])
    for x in fields:
        want_fields.setdefault(x['datasheet'], []).append('RegisterField:%s' % x['name'])
    mismatched = [d['name'] for d in SEED_DATASHEETS
                  if sorted(json.loads(d['facts_refs_json'])) != sorted(want_facts.get(d['name'], []))
                  or sorted(json.loads(d['fields_refs_json'])) != sorted(want_fields.get(d['name'], []))]
    check('datasheets: forward (fact/field.datasheet) and reverse (Datasheet.*_refs_json) links agree exactly', not mismatched, mismatched[:5])

    # 3. the ATmega328P row: kind soc, the sha from M328_REV, for_soc atmega328p
    m328 = sheets.get('atmega328p-ds40002061b')
    check('datasheets: the ATmega328P row is kind=soc, for_soc=atmega328p, sha256 from M328_REV, fetched_at 2026-10-01',
          bool(m328) and m328['kind'] == 'soc' and m328['for_soc'] == 'atmega328p'
          and m328['sha256'] == 'b9b9d83cda56a95d999ea8d54fe5a540748ae9020e5e7ae19b913d384ba9320e'
          and m328['sha256'] in M328_REV and m328['fetched_at'] == '2026-10-01', m328)
    check('datasheets: the ATmega328P row carries every atmega328p-cited RegisterField (the whole chain cites one document)',
          set(json.loads(m328['fields_refs_json'])) == {'RegisterField:%s' % x['name'] for x in fields if x['soc'] == 'atmega328p'})

    # 4. the UNO's coverage: soc + board + programming covered (named), combined empty
    uno_cov = json.loads(boards['arduino-uno-r3']['datasheets_json'])
    check('datasheets: the UNO is covered soc=atmega328p-ds40002061b, board=arduino-uno-r3-pinout (the fetched+hashed '
          'one, preferred over the not-re-fetched product-page row), programming=arduino-boards-txt (fetched+hashed, '
          'preferred over the Optiboot README), combined empty',
          uno_cov == {'soc': 'atmega328p-ds40002061b', 'board': 'arduino-uno-r3-pinout',
                      'programming': 'arduino-boards-txt', 'combined': ''}, uno_cov)
    check('datasheets: the OTHER UNO board/programming documents still exist as their own rows (not dropped for not being picked)',
          {'arduino-uno-r3-docs', 'arduino-optiboot-readme'} <= set(sheets))

    # 5. the C3's coverage says what is missing by name
    c3_cov = json.loads(boards['esp32-c3']['datasheets_json'])
    check('datasheets: the C3 is covered soc=espressif-esp32-c3-datasheet, board=espressif-esp32-c3-devkitm-user-guide, '
          'programming MISSING (named \'\' — no boards.txt/Optiboot/avrdude equivalent cited for the C3 yet), combined empty',
          c3_cov == {'soc': 'espressif-esp32-c3-datasheet', 'board': 'espressif-esp32-c3-devkitm-user-guide',
                     'programming': '', 'combined': ''}, c3_cov)

    # 6. the kit book + Wikipedia rows exist, named 'other', with why
    check('datasheets: the kit book is its own row, kind=other', sheets.get('arduino-starter-kit-book', {}).get('kind') == 'other')
    wiki = sheets.get('wikipedia', {})
    check('datasheets: Wikipedia is consolidated into ONE row (kind=other), the cited pages named in its own notes',
          wiki.get('kind') == 'other' and 'Wikipedia' in wiki.get('title', '') and wiki.get('notes', '').startswith('pages cited:')
          and 'Analog-to-digital converter' in wiki['notes'], wiki.get('notes'))

    # 7. a cited-but-unknown document is 'undetermined', never dropped (a synthetic fact this table cannot name)
    synthetic = [dict(name='test:synthetic.fact', board='test', fact_key='synthetic.fact', value='1', unit='',
                      document='Some Unknown Vendor Datasheet, Rev Z', revision='Rev Z (never seen before)',
                      page_table='p.1', url='https://example.invalid/unknown.pdf', notes='')]
    extra = DS.rows(synthetic, [])
    und = next((d for d in extra if d['kind'] == 'undetermined'), None)
    check('datasheets: a citation this table does not recognize synthesizes an undetermined row, never dropped',
          bool(und) and 'Some Unknown Vendor Datasheet' in und['title'] and und['undetermined']
          and synthetic[0]['datasheet'] == und['name']
          and 'DatasheetFact:test:synthetic.fact' in json.loads(und['facts_refs_json']))
    check('datasheets: every KNOWN document is unaffected by the synthetic citation (same 13 known rows still present)',
          {d['name'] for d in extra if d['kind'] != 'undetermined'} == {d['name'] for d in DS._static_rows()})

    # 8. materialize twice -> identical
    from board.custom import board_object_seed as S
    from board.custom.register_map import board_rows
    boards1 = board_rows()
    for b in boards1:
        b.update(S.IDENTITY.get(b['name'], {}))
    out1 = S.build(boards1)
    boards2 = board_rows()
    for b in boards2:
        b.update(S.IDENTITY.get(b['name'], {}))
    out2 = S.build(boards2)
    check('datasheets: materializing twice gives byte-identical Datasheet rows',
          sorted(out1['Datasheet'], key=lambda d: d['name']) == sorted(out2['Datasheet'], key=lambda d: d['name']))
    check('datasheets: materializing twice gives the same per-board coverage',
          sorted((b['name'], b['datasheets_json']) for b in boards1) == sorted((b['name'], b['datasheets_json']) for b in boards2))

    # 9. the pages still render (board_selftest.page() re-checks /display/boards + /display/hardware-chain directly;
    # named here so a reader of this file knows it is covered, not missed)
