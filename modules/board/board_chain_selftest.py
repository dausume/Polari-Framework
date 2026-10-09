"""board_chain_selftest — ucd-0a (UNO_CORE_DEMO_PLAN.md §5f/§5g): THE HARDWARE CHAIN as rows, derived + cited, with stable
names, provenance, and reverse links; navigable both ways; every reference resolves; the D3 walk a novice takes
(Board → Pin → SoC Pin → PinFunction → PeripheralSignal → Peripheral → Register → RegisterField) and its reverse; register
fields expose meanings and typed access; the existing board object is unchanged. Run by board_selftest.run().
"""
import json
import re


def _resolve(rows, cls, name):
    return any(r['name'] == name for r in rows.get(cls, []))


def run_chain(check):
    from board.board_basis import (BOARD_CLASSES, Peripheral, PeripheralSignal, PinFunction, Register, RegisterField, SignalRoute,
                                   RegisterSetting, RegisterFieldSetting, BoardPinNet)
    from board.custom import board_object as BO
    from board.custom import hardware_chain as HC
    from board.custom import register_fields_atmega328p as RF
    from board.board_seed import BOARD_SEED_PAIRS
    tables = BO.seed_tables()

    # 1. the model: nine classes, five of them materialized, four defined for the next slices
    nine = (Peripheral, PeripheralSignal, PinFunction, SignalRoute, Register, RegisterField, RegisterSetting, RegisterFieldSetting, BoardPinNet)
    check('chain: the nine chain classes are BOARD_CLASSES members', all(c in BOARD_CLASSES for c in nine))
    seeded = {c: rows for c, _cls, rows in BOARD_SEED_PAIRS}
    check('chain: Peripheral / PeripheralSignal / PinFunction / Register / RegisterField are seeded (code-owned, converge)',
          all(seeded.get(c) and all('_converge' in r for r in seeded[c]) for c in HC.CHAIN_CLASSES if c in ('Peripheral', 'PeripheralSignal', 'PinFunction', 'Register', 'RegisterField')))
    check('chain: SignalRoute / RegisterSetting / RegisterFieldSetting / BoardPinNet are defined, observed, empty until ucd-0b/0c',
          all(seeded.get(c) == [] for c in ('SignalRoute', 'RegisterSetting', 'RegisterFieldSetting', 'BoardPinNet')))
    try:
        built = [cls(**{k: v for k, v in r.items() if k != '_converge'}) for c, cls, rows in BOARD_SEED_PAIRS if c in HC.CHAIN_CLASSES for r in rows]
        check('chain: every seed row constructs its class (no stray field)', len(built) == sum(len(tables[c]) for c in ('Peripheral', 'PeripheralSignal', 'PinFunction', 'Register', 'RegisterField')))
    except TypeError as e:
        check('chain: every seed row constructs its class (no stray field)', False, str(e))

    # 2. derived or cited, stable identities, provenance
    P, S, F, G, X = (tables[c] for c in ('Peripheral', 'PeripheralSignal', 'PinFunction', 'Register', 'RegisterField'))
    check('chain: counts — %d peripherals, %d signals, %d pin functions, %d registers, %d fields' % (len(P), len(S), len(F), len(G), len(X)),
          len(P) >= 15 and len(S) >= 80 and len(F) == 23 + sum(len(json.loads(s['functions_json'])) for s in tables['SocPin'] if s['soc'] == 'atmega328p')
          and len(G) == len(__import__('board.custom.registers', fromlist=['load']).load('atmega328p')['registers']) and len(X) == len(RF.FIELDS))
    check('chain: every row has a name, an origin and a soc; names are unique per class',
          all(r['name'] and r['origin'] and r['soc'] for c in ('Peripheral', 'PeripheralSignal', 'PinFunction', 'Register', 'RegisterField') for r in tables[c])
          and all(len({r['name'] for r in tables[c]}) == len(tables[c]) for c in ('Peripheral', 'PeripheralSignal', 'PinFunction', 'Register', 'RegisterField')))
    check('chain: no row NAME looks like a Class:name reference (the object page would misread it)',
          not [r['name'] for c in ('Peripheral', 'PeripheralSignal', 'PinFunction', 'Register', 'RegisterField') for r in tables[c] if re.match(r'^[A-Z][A-Za-z0-9]*:', r['name'])])
    check('chain: every RegisterField cites the datasheet (document, section/page, url) and has a typed access + values',
          all(x['document'] and x['page_table'] and x['url'] and x['access'] in RF.ACCESS_KINDS and json.loads(x['values_json']) for x in X))
    check('chain: every Register carries the snapshot sha in origin; cited ones carry title + page + reset; the rest say fields are not captured',
          all('sha256' in g['origin'] for g in G) and all((g['description'] and g['page_table'] and g['reset_value']) if json.loads(g['fields_refs_json']) else g['undetermined'] for g in G))
    check('chain: an io-space register carries its data-space address (io + 0x20 — EIMSK 0x1D → 0x3D as the datasheet prints)',
          next(g for g in G if g['register'] == 'EIMSK')['addr_mem'] == '0x3D' and next(g for g in G if g['register'] == 'EICRA')['addr_mem'] == '')
    check('chain: w1c flags are typed (EIFR.INTF1, TIFR2.TOV2), strobes too (TCCR2B.FOC2A), PINx toggles (PIND.PIND3)',
          {x['name']: x['access'] for x in X}.items() >= {'atmega328p:EIFR.INTF1': 'w1c', 'atmega328p:TIFR2.TOV2': 'w1c',
                                                          'atmega328p:TCCR2B.FOC2A': 'w-strobe', 'atmega328p:PIND.PIND3': 'rw-toggle'}.items())

    # 3. every reference resolves — forward columns and reverse lists, both directions
    refcols = {'PeripheralSignal': [('peripheral', 'Peripheral')], 'PinFunction': [('soc_pin', 'SocPin'), ('signal', 'PeripheralSignal'), ('peripheral', 'Peripheral')],
               'Register': [('peripheral', 'Peripheral')], 'RegisterField': [('register', 'Register'), ('affects_signal', 'PeripheralSignal'), ('affects_pin', 'SocPin')]}
    dangling = [(c, r['name'], col) for c, cols in refcols.items() for r in tables[c] for col, target in cols if r.get(col) and not _resolve(tables, target, r[col])]
    check('chain: every forward reference resolves to a row of the named class', not dangling, str(dangling[:5]))
    bad = []
    for c in ('Peripheral', 'PeripheralSignal', 'PinFunction', 'SocPin', 'BoardPin'):
        for r in tables[c]:
            for col in [k for k in r if k.endswith('_refs_json')]:
                for ref in json.loads(r[col] or '[]'):
                    cls, _, name = ref.partition(':')
                    if not _resolve(tables, cls, name):
                        bad.append((c, r['name'], ref))
    check('chain: every reverse link (Class:name) resolves', not bad, str(bad[:5]))
    uno_pins = [b for b in tables['BoardPin'] if b['board'] == 'arduino-uno-r3']
    check('chain: every UNO BoardPin links to its SocPin and PinFunctions; every atmega328p SocPin links back to board pins + functions',
          all(json.loads(b['links_refs_json'])[:1] == ['SocPin:atmega328p:%s' % b['soc_pin']] for b in uno_pins)
          and all(any(x.startswith('PinFunction:') for x in json.loads(s['links_refs_json'])) for s in tables['SocPin'] if s['soc'] == 'atmega328p'))
    check('chain: the ESP32-C3 SocPins are untouched (links empty — the GPIO matrix is Phase 2, not guessed)',
          all(json.loads(s.get('links_refs_json') or '[]') == [] for s in tables['SocPin'] if s['soc'] != 'atmega328p'))

    # 4. the D3 walk, forward
    hops = HC.chain_for('arduino-uno-r3', 'D3', tables)
    kinds = [h['kind'] for h in hops]
    names = {h['name'] for h in hops}
    check('chain: D3 forward — BoardPin → SocPin PD3 → 4 PinFunctions → signals → peripherals → registers → fields, in that order (%d hops)' % len(hops),
          kinds[:2] == ['BoardPin', 'SocPin'] and hops[1]['name'] == 'atmega328p:PD3'
          and kinds.count('PinFunction') == 4 and kinds == sorted(kinds, key=['BoardPin', 'SocPin', 'PinFunction', 'PeripheralSignal', 'Peripheral', 'Register', 'RegisterField'].index))
    check('chain: D3 discovers its functions GPIO, INT1, OC2B, PCINT19',
          {'atmega328p:PD3:GPIO', 'atmega328p:PD3:INT1', 'atmega328p:PD3:OC2B', 'atmega328p:PD3:PCINT19'} <= names)
    check('chain: D3 reaches its peripherals EXINT, TIMER2, PCINT, GPIO PORTD',
          {'atmega328p:EXINT', 'atmega328p:TIMER2', 'atmega328p:PCINT', 'atmega328p:GPIO PORTD'} <= names)
    check('chain: D3 reaches the registers EICRA, EIMSK, EIFR, PCICR, PCMSK2, DDRD, PORTD, PIND, TCCR2A, TCCR2B, TIMSK2, TIFR2',
          {'atmega328p:%s' % r for r in ('EICRA', 'EIMSK', 'EIFR', 'PCICR', 'PCMSK2', 'DDRD', 'PORTD', 'PIND', 'TCCR2A', 'TCCR2B', 'TIMSK2', 'TIFR2')} <= names)
    own = [h for h in hops if h['kind'] == 'RegisterField']
    check('chain: D3\'s own fields — EICRA.ISC1, EIMSK.INT1, EIFR.INTF1, PCMSK2.PCINT19, DDRD.DDD3, PORTD.PORTD3, PIND.PIND3, TCCR2A.COM2B, TIMSK2.OCIE2B, TIFR2.OCF2B, TCCR2B.FOC2B — and nothing of another pin',
          {'atmega328p:EICRA.ISC1', 'atmega328p:EIMSK.INT1', 'atmega328p:EIFR.INTF1', 'atmega328p:PCMSK2.PCINT19', 'atmega328p:DDRD.DDD3',
           'atmega328p:PORTD.PORTD3', 'atmega328p:PIND.PIND3', 'atmega328p:TCCR2A.COM2B', 'atmega328p:TIMSK2.OCIE2B', 'atmega328p:TIFR2.OCF2B',
           'atmega328p:TCCR2B.FOC2B'} == {h['name'] for h in own})
    isc1 = next(x for x in X if x['name'] == 'atmega328p:EICRA.ISC1')
    vals = json.loads(isc1['values_json'])
    check('chain: EICRA.ISC1 = bits 3:2, rw, four values with the datasheet\'s own words (01 = any logical change), Table 13-1 p.80',
          (isc1['bit_hi'], isc1['bit_lo'], isc1['access']) == (3, 2, 'rw') and set(vals) == {'00', '01', '10', '11'}
          and vals['01'].startswith('Any logical change on INT1') and 'Table 13-1' in isc1['page_table'] and 'p.80' in isc1['page_table'])
    check('chain: every hop carries a Class:name ref a page can open', all(h['ref'] == '%s:%s' % (h['kind'], h['name']) for h in hops))
    check('chain: the walk REFUSES an unknown pin by name', _refuses(HC, tables))

    # 5. the reverse walk: from the field back up to the board pin, every hop by the rows' own links
    fld = isc1
    reg = next(g for g in G if g['name'] == fld['register'])
    per = next(p for p in P if p['name'] == reg['peripheral'])
    sig = next(s for s in S if s['name'] == fld['affects_signal'])
    pf = [f for f in F if f['signal'] == sig['name']]
    sp = next(s for s in tables['SocPin'] if s['name'] == pf[0]['soc_pin'])
    bp = [b for b in uno_pins if 'SocPin:%s' % sp['name'] in json.loads(b['links_refs_json'])]
    check('chain: reverse — EICRA.ISC1 → EICRA → EXINT → signal INT1 → PinFunction PD3:INT1 → SocPin PD3 → BoardPin D3',
          per['peripheral'] == 'EXINT' and sig['signal'] == 'INT1' and [f['name'] for f in pf] == ['atmega328p:PD3:INT1'] and sp['pin'] == 'PD3'
          and [b['canonical'] for b in bp] == ['D3'])
    check('chain: the reverse lists carry the same hops (Peripheral.registers_refs_json names EICRA; PeripheralSignal INT1\'s pin_functions name PD3:INT1; SocPin PD3 links name D3)',
          'Register:atmega328p:EICRA' in json.loads(per['registers_refs_json']) and json.loads(sig['pin_functions_refs_json']) == ['PinFunction:atmega328p:PD3:INT1']
          and 'BoardPin:arduino-uno-r3:D3' in json.loads(sp['links_refs_json']))

    # 6. the existing board object is unchanged by the chain
    r = BO.rows_for('arduino-uno-r3', tables)
    check('chain: the UNO board object still validates and its pin assignment is unchanged (D3 ↔ PD3, D6 ↔ PD6/OC0A, A0 ↔ PC0/ADC0)',
          (BO.validate(r) or ['ok']) == ['ok'] and {p['canonical']: p['soc_pin'] for p in r['pins']}.items() >= {'D3': 'PD3', 'D6': 'PD6', 'A0': 'PC0'}.items())

    # 7. ucd-0b2a: address space as rows (UNO_CORE_DEMO_PLAN.md §5h B3/D-ucd-9)
    run_address_space(check, HC, tables)


def run_address_space(check, HC, tables):
    """ucd-0b2a: AddressSpace, RegisterAddressMapping, RegisterBlock, MemoryRegion — derived + cited, one source
    for Register.addr/addr_mem, materializes twice identically, every ref resolves."""
    AS = {r['name']: r for r in tables['AddressSpace']}
    M = tables['RegisterAddressMapping']
    RB = {r['name']: r for r in tables['RegisterBlock']}
    MR = {r['name']: r for r in tables['MemoryRegion']}
    G = {r['name']: r for r in tables['Register']}

    check('address-space: exactly 2 AddressSpace rows (io, data), both cited §8.5 "I/O Memory", p.30',
          set(AS) == {'atmega328p:io', 'atmega328p:data'}
          and all(a['document'] and 'p.30' in a['page_table'] and '§8.5' in a['page_table'] for a in AS.values()))
    check('address-space: io = IN/OUT 0x00-0x3F; data = LD/ST… at +0x20, 0x20-0xFF',
          AS['atmega328p:io']['access_instructions'].startswith('IN/OUT') and (AS['atmega328p:io']['range_lo'], AS['atmega328p:io']['range_hi']) == ('0x00', '0x3F')
          and AS['atmega328p:data']['access_instructions'] == 'LD/ST/LDS/STS/LDD/STD' and AS['atmega328p:data']['offset_from_io'] == '0x20')

    by_reg = {}
    for m in M:
        by_reg.setdefault(m['register'], []).append(m)
    io_regs = {g['name'] for g in G.values() if g['space'] == 'io'}
    mem_regs = {g['name'] for g in G.values() if g['space'] == 'mem'}
    check('address-space: every io-space register has exactly 2 mappings (@io + @data), every mem-space register exactly 1 (@data)',
          all(len(by_reg.get(n, [])) == 2 for n in io_regs) and all(len(by_reg.get(n, [])) == 1 for n in mem_regs))
    eimsk = {m['address_space']: m['address'] for m in by_reg['atmega328p:EIMSK']}
    check('address-space: EIMSK maps to io 0x1d and data 0x3D (io + 0x20, cited §8.5 p.30)',
          eimsk.get('atmega328p:io') == '0x1d' and eimsk.get('atmega328p:data') == '0x3D'
          and any('§8.5' in m['origin'] for m in by_reg['atmega328p:EIMSK'] if m['address_space'] == 'atmega328p:data'))
    check('address-space: no mem-space register address is below 0x60 (no invented io alias — the UNO snapshot has none)',
          all(int(G[n]['addr'], 16) >= 0x60 for n in mem_regs))

    check('address-space: every Register.block resolves to a RegisterBlock, and that block\'s registers_refs_json names it back',
          all(g['block'] in RB for g in G.values())
          and all(('Register:%s' % g['name']) in json.loads(RB[g['block']]['registers_refs_json']) for g in G.values()))
    check('address-space: MCUCR\'s block (CPU) is shared with the three GPIO port peripherals, cited §14.4.1 MCUCR, p.100',
          {'Peripheral:atmega328p:GPIO PORTB', 'Peripheral:atmega328p:GPIO PORTC', 'Peripheral:atmega328p:GPIO PORTD'}
          == set(json.loads(RB[G['atmega328p:MCUCR']['block']]['shared_with_refs_json']))
          and 'p.100' in RB[G['atmega328p:MCUCR']['block']]['notes'])

    check('address-space: 3 MemoryRegion rows (flash, sram, eeprom), each carrying its own cited DatasheetFact',
          set(MR) == {'atmega328p:flash', 'atmega328p:sram', 'atmega328p:eeprom'} and all(r['fact'] for r in MR.values())
          and all(any(f['name'] == r['fact'] for f in tables['DatasheetFact']) for r in MR.values()))
    check('address-space: sram is addressed through the data AddressSpace; flash/eeprom are not (said so in undetermined, never guessed)',
          MR['atmega328p:sram']['address_space'] == 'atmega328p:data'
          and MR['atmega328p:flash']['address_space'] == '' and MR['atmega328p:flash']['undetermined']
          and MR['atmega328p:eeprom']['address_space'] == '' and MR['atmega328p:eeprom']['undetermined'])

    # materialize twice → identical rows (deep-compare, the same posture as the rest of the chain)
    sp2 = [dict(s) for s in tables['SocPin'] if s['soc'] == 'atmega328p']
    bp2 = [dict(b) for b in tables['BoardPin'] if b['board'] == 'arduino-uno-r3']
    again = HC.build(sp2, bp2)
    check('address-space: materializing twice gives byte-identical AddressSpace/RegisterAddressMapping/RegisterBlock/MemoryRegion rows',
          all(sorted(again[c], key=lambda r: r['name']) == sorted([dict(r) for r in tables[c]], key=lambda r: r['name'])
              for c in ('AddressSpace', 'RegisterAddressMapping', 'RegisterBlock', 'MemoryRegion')))

    # every ref resolves — forward + reverse, the new classes included
    dangling = []
    for m in M:
        for col, cls in (('register', 'Register'), ('address_space', 'AddressSpace')):
            if m.get(col) and not _resolve(tables, cls, m[col]):
                dangling.append(('RegisterAddressMapping', m['name'], col))
    for rb in RB.values():
        if rb.get('peripheral') and not _resolve(tables, 'Peripheral', rb['peripheral']):
            dangling.append(('RegisterBlock', rb['name'], 'peripheral'))
        for col in ('registers_refs_json', 'shared_with_refs_json'):
            for ref in json.loads(rb[col] or '[]'):
                cls, _, name = ref.partition(':')
                if not _resolve(tables, cls, name):
                    dangling.append(('RegisterBlock', rb['name'], col))
    for mr in MR.values():
        if mr.get('address_space') and not _resolve(tables, 'AddressSpace', mr['address_space']):
            dangling.append(('MemoryRegion', mr['name'], 'address_space'))
        if mr.get('fact') and not _resolve(tables, 'DatasheetFact', mr['fact']):
            dangling.append(('MemoryRegion', mr['name'], 'fact'))
    for g in G.values():
        for ref in json.loads(g.get('mappings_refs_json') or '[]'):
            cls, _, name = ref.partition(':')
            if not _resolve(tables, cls, name):
                dangling.append(('Register', g['name'], 'mappings_refs_json'))
        if g.get('block') and not _resolve(tables, 'RegisterBlock', g['block']):
            dangling.append(('Register', g['name'], 'block'))
    check('address-space: every reference (forward and reverse) of the four new classes resolves', not dangling, str(dangling[:5]))


def _refuses(HC, tables):
    try:
        HC.chain_for('arduino-uno-r3', 'D99', tables)
    except KeyError as e:
        return 'D99' in str(e)
    return False
