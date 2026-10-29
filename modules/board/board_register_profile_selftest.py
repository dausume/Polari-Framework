"""board_register_profile_selftest - rp-0 (MISSION_PROFILE_SOLVER_PLAN.md §2.4): the register profile (every field, then every register, classified from the
cited rows), the memory map (register file, I/O, extended I/O, SRAM, flash application + boot loader, EEPROM), the firmware-use view, the two doors on a REAL falcon.App,
the two configured pages, the nav entries and the CLI. Run by board_selftest.run(). Every verdict is compared with the rows/rules that OWN it, never with a copy.
"""
import contextlib
import copy
import io
import json
import types

SOC = 'atmega328p'
UNO = 'arduino-uno-r3'


def _by(prof):
    return {r['register']: r for r in prof['registers']}


def _fields(r):
    return {f['field']: f['class'] for f in r['fields']}


def run_register_profile(check):
    from board.custom import board_object as BO
    from board.custom import memory_map_atmega328p as MM
    from board.custom import memory_map_view as MV
    from board.custom import register_profile as RP
    with contextlib.redirect_stdout(io.StringIO()):
        t = BO.seed_tables()
    # rm-2b: the seed now holds the C3's drawing-set registers too; this profile is the ATmega328P's, so its counts read the 328P rows
    t = dict(t, Register=[r for r in t['Register'] if r['soc'] == SOC], RegisterField=[f for f in t['RegisterField'] if f['soc'] == SOC])
    prof = RP.profile(t, SOC)
    R = _by(prof)
    PIN, PER, MEM, CPU = RP.PIN, RP.PER, RP.MEM, RP.CPU
    tot = prof['totals']

    # ---- the field/register classification
    check('rp-0: EVERY ATmega328P Register row (%d) gets a class or `mixed`; the four pure counts + mixed add up to all of them' % len(t['Register']),
          len(R) == len(t['Register']) == 96 and all(r['class'] in RP.CLASSES + (RP.MIXED,) for r in R.values())
          and sum(tot['pure'].values()) + tot['mixed'] == 96, str(tot['pure']))
    check('rp-0: all 148 RegisterField rows are classified (source RegisterField) and every one of them is a field of a profiled register',
          tot['fields_from_rows'] == len(t['RegisterField']) == 148 and {f['register'] for f in prof['fields'] if f['source'] == 'RegisterField'} <= set(R))
    check('rp-0: DDRB / PORTB / PINB (and the D and C ports) are pin-configuration, pure',
          all(R[x]['class'] == PIN for x in ('DDRB', 'PORTB', 'PINB', 'DDRD', 'PORTD', 'PIND', 'DDRC', 'PORTC', 'PINC')))
    check('rp-0: the external / pin-change interrupt sense and mask registers (EICRA, EIMSK, PCICR, PCMSK0-2) and DIDR0/DIDR1 are pin-configuration; their flag registers (EIFR, PCIFR) are peripheral-operation',
          all(R[x]['class'] == PIN for x in ('EICRA', 'EIMSK', 'PCICR', 'PCMSK0', 'PCMSK1', 'PCMSK2', 'DIDR0', 'DIDR1')) and R['EIFR']['class'] == PER and R['PCIFR']['class'] == PER)
    u = R['UCSR0B']
    uf = _fields(u)
    check('rp-0: UCSR0B is MIXED - RXEN0 and TXEN0 pin-configuration, the other six fields (RXCIE0, TXCIE0, UDRIE0, UCSZ02, RXB80, TXB80) peripheral-operation; rm-2a: all eight are RegisterField rows now',
          u['class'] == RP.MIXED and uf['RXEN0'] == uf['TXEN0'] == PIN
          and {k for k, v in uf.items() if v == PER} == {'RXCIE0', 'TXCIE0', 'UDRIE0', 'UCSZ02', 'RXB80', 'TXB80'} and 'not modelled' not in u['fields_note'], str(uf))
    m = R['MCUCR']
    mf = _fields(m)
    check('rp-0: MCUCR is MIXED - PUD (a RegisterField row) pin-configuration, IVSEL / IVCE / BODS / BODSE cpu-system, and the register says its fields are only partly modelled',
          m['class'] == RP.MIXED and mf['PUD'] == PIN and {k for k, v in mf.items() if v == CPU} == {'IVSEL', 'IVCE', 'BODS', 'BODSE'} and 'partly modelled' in m['fields_note'], str(mf))
    others = {k: _fields(R[k]) for k in ('SPCR', 'TWCR', 'TCCR0A', 'TCCR0B', 'TCCR1A', 'TCCR2A', 'TCCR2B')}
    check('rp-0: the other alternate-function enables - SPE (SPCR), TWEN (TWCR), COM0A/COM0B (TCCR0A), COM1A/COM1B (TCCR1A), the COM2x/FOC2x rows (TCCR2A/B), FOC0x - are pin-configuration inside MIXED registers; WGM and CS bits stay peripheral-operation',
          others['SPCR']['SPE'] == PIN and others['TWCR']['TWEN'] == PIN and others['TCCR0A']['COM0A'] == others['TCCR0A']['COM0B'] == PIN and others['TCCR1A']['COM1A'] == others['TCCR1A']['COM1B'] == PIN
          and others['TCCR2A']['COM2A'] == others['TCCR2A']['COM2B'] == PIN and others['TCCR2B']['FOC2A'] == PIN and others['TCCR0B']['FOC0A'] == PIN
          and others['TCCR2A']['WGM2_10'] == others['TCCR2B']['CS2'] == others['TCCR0B']['CS02'] == others['TCCR1A']['WGM10'] == PER
          and all(R[k]['class'] == RP.MIXED for k in others), str(others))
    check('rp-0: EEAR / EEARL / EEARH / EEDR / EECR are memory-nvm; SPMCSR is memory-nvm; SP / SPL / SPH are memory-nvm',
          all(R[x]['class'] == MEM for x in ('EEAR', 'EEARL', 'EEARH', 'EEDR', 'EECR', 'SPMCSR', 'SP', 'SPL', 'SPH')))
    check('rp-0: SREG, SMCR, PRR, CLKPR, OSCCAL, WDTCSR, MCUSR and GPIOR0-2 are cpu-system',
          all(R[x]['class'] == CPU for x in ('SREG', 'SMCR', 'PRR', 'CLKPR', 'OSCCAL', 'WDTCSR', 'MCUSR', 'GPIOR0', 'GPIOR1', 'GPIOR2')))
    check('rp-0: the timers\' counts, compare values and mask/flag registers (TCNTn, OCRnx, TIMSKn, TIFRn), the ADC, USART data/baud and TWI registers are peripheral-operation (TIMSK2\'s OCIE2x stay peripheral: they enable the compare interrupt, not the pin)',
          all(R[x]['class'] == PER for x in ('TCNT0', 'TCNT1', 'TCNT2', 'OCR0A', 'OCR1A', 'OCR2A', 'TIMSK0', 'TIMSK1', 'TIMSK2', 'TIFR0', 'TIFR1', 'TIFR2', 'ADMUX', 'ADCSRA', 'UBRR0', 'UDR0', 'UCSR0A', 'TWBR', 'TWDR', 'SPDR')))
    check('rp-0: ONLY the registers whose fields fall in two classes are mixed - exactly %s' % ', '.join(sorted(tot['mixed_registers'])),
          set(tot['mixed_registers']) == {'MCUCR', 'UCSR0B', 'SPCR', 'TWCR', 'TCCR0A', 'TCCR0B', 'TCCR1A', 'TCCR2A', 'TCCR2B'} and all(len(r['classes']) > 1 for r in R.values() if r['mixed'])
          and all(len(r['classes']) == 1 for r in R.values() if not r['mixed']))
    no_rows = [r for r in R.values() if r['fields_note'].startswith('fields not modelled')]
    check('rp-0: a register with no field rows says `fields not modelled` (%d of them) and is still classified' % len(no_rows),
          len(no_rows) == tot['registers_without_field_rows'] == 66 and all(r['class'] in RP.CLASSES + (RP.MIXED,) for r in no_rows))
    bad = [(r['register'], 'reason' if not r['reason'] else 'cite') for r in R.values() if not r['reason'] or not r['cite']]
    badf = [(f['register'], f['field']) for f in prof['fields'] if not f['reason'] or 'p.' not in f['cite'] or not f['cite'].strip()]
    check('rp-0: EVERY verdict carries a reason and a citation naming a page - %d registers, %d fields' % (len(R), len(prof['fields'])), not bad and not badf, str((bad[:3], badf[:3])))
    check('rp-0: a mixed register\'s reason names each class with its fields (MCUCR: pin-configuration PUD, cpu-system BODS ...)',
          'pin-configuration: PUD' in m['reason'] and 'cpu-system: ' in m['reason'] and 'IVSEL' in m['reason'] and 'p.100' in m['cite'])

    # ---- DERIVED, not typed: change a row's tags and the verdict follows
    t2 = copy.deepcopy(t)
    for f in t2['RegisterField']:
        if f['name'] == '%s:EICRA.ISC1' % SOC:
            f['affects_signal'] = ''
        if f['name'] == '%s:TIMSK2.TOIE2' % SOC:
            f['affects_pin'] = '%s:PB3' % SOC
    p2 = _by(RP.profile(t2, SOC))
    check('rp-0: DERIVED from the rows - clearing EICRA.ISC1\'s affects_signal makes that field peripheral-operation (EICRA becomes mixed); tagging TIMSK2.TOIE2 with affects_pin makes it pin-configuration (TIMSK2 becomes mixed)',
          _fields(p2['EICRA'])['ISC1'] == PER and p2['EICRA']['class'] == RP.MIXED and _fields(p2['TIMSK2'])['TOIE2'] == PIN and p2['TIMSK2']['class'] == RP.MIXED
          and R['EICRA']['class'] == PIN and R['TIMSK2']['class'] == PER)
    tagged = [f for f in t['RegisterField'] if (f['affects_pin'] or f['affects_signal']) and f['access'] != 'w1c' and (f['register'].partition(':')[2], f['field']) not in RP.FIELD_RULES]
    cls = {(f['register'], f['field']): f['class'] for f in prof['fields'] if f['source'] == 'RegisterField'}
    check('rp-0: every one of the %d tag-bearing RegisterField rows (affects_pin / affects_signal, not a w1c flag) is pin-configuration, every w1c / w0c flag peripheral-operation - except in a register with its own cited verdict (MCUSR, WDTCSR: cpu-system)' % len(tagged),
          all(cls[(f['register'].partition(':')[2], f['field'])] == PIN for f in tagged)
          and all(cls[(f['register'].partition(':')[2], f['field'])] == PER for f in t['RegisterField'] if f['access'] in ('w1c', 'w0c')
                  and f['register'].partition(':')[2] not in RP.REGISTER_RULES)
          # rm-2a: a flag of a register with its own cited verdict takes that class (MCUSR's w0c reset flags, WDTCSR.WDIF = cpu-system)
          and all(cls[(f['register'].partition(':')[2], f['field'])] == CPU for f in t['RegisterField'] if f['register'].partition(':')[2] in ('MCUSR', 'WDTCSR')))
    check('rp-0: the profile is deterministic (twice = identical JSON)', json.dumps(RP.profile(t, SOC), sort_keys=True) == json.dumps(RP.profile(copy.deepcopy(t), SOC), sort_keys=True))

    # ---- the rule tables agree with the datasheet's Register Summary snapshot
    snap = RP.summary()
    bad_rules = []
    for (reg, label, hi, lo, names, why, cite) in RP.PIN_ENABLE_RULES:
        got = [RP.bit_names(snap['registers'][reg])[7 - b] for b in range(hi, lo - 1, -1)]
        if got != names or not why or 'p.' not in cite:
            bad_rules.append((reg, label, got))
    check('rp-0: every alternate-function enable rule (%d) names exactly the bits the datasheet Register Summary prints at those positions, with a reason and a page' % len(RP.PIN_ENABLE_RULES), not bad_rules, str(bad_rules))
    mism = []
    for f in t['RegisterField']:
        reg = f['register'].partition(':')[2]
        if f['width'] == 1 and reg in snap['registers'] and RP.bit_names(snap['registers'][reg]):
            if RP.bit_names(snap['registers'][reg])[7 - f['bit_lo']] != f['field'] and not (f['field'].startswith(reg) or f['field'] in ('DDB0',)):
                mism.append((reg, f['field'], RP.bit_names(snap['registers'][reg])[7 - f['bit_lo']]))
    check('rp-0: the cited RegisterField rows agree with the Register Summary (every one-bit row sits on the bit the summary names it)', not mism, str(mism[:5]))
    check('rp-0: every FIELD_RULES / REGISTER_RULES entry cites a datasheet page; every CPU / WDT / EEPROM-peripheral register has a REGISTER_RULES verdict (no silent default for them)',
          all('p.' in v[2] and v[1] for v in list(RP.FIELD_RULES.values()) + list(RP.REGISTER_RULES.values()))
          and all(g['register'] in RP.REGISTER_RULES for g in t['Register'] if g['peripheral'].partition(':')[2] in ('CPU', 'WDT', 'EEPROM')))
    check('rp-0: the Register Summary snapshot cites the datasheet file by sha256 and has a row for every register that is not a 16-bit view',
          'b9b9d83cda56a95d999ea8d54fe5a540748ae9020e5e7ae19b913d384ba9320e' in snap['derived_from']
          and all(RP._entry(g['register'])[1] for g in t['Register']))

    # ---- the memory map
    MR = {r['name']: r for r in t['MemoryRegion']}
    DF = {f['name'] for f in t['DatasheetFact']}
    check('rp-0: MemoryRegion has the original three (flash, sram, eeprom) plus register-file, io-registers, ext-io-registers and flash.application / flash.boot (8 rows), each citing a DatasheetFact that exists',
          set(MR) == {'%s:%s' % (SOC, n) for n in ('flash', 'sram', 'eeprom', 'register-file', 'io-registers', 'ext-io-registers', 'flash.application', 'flash.boot')}
          and all(r['fact'] in DF for r in MR.values()))
    check('rp-0: R0-R31 is 32 bytes at 0x0000, the I/O registers 64 at 0x0020, the extended I/O 160 at 0x0060, SRAM 2048 at 0x0100 - all in the data AddressSpace',
          [(MR['%s:%s' % (SOC, n)]['start'], MR['%s:%s' % (SOC, n)]['size']) for n in ('register-file', 'io-registers', 'ext-io-registers', 'sram')] == [('0x0000', 32), ('0x0020', 64), ('0x0060', 160), ('0x0100', 2048)]
          and all(MR['%s:%s' % (SOC, n)]['address_space'] == '%s:data' % SOC for n in ('register-file', 'io-registers', 'ext-io-registers', 'sram')))
    check('rp-0: every new region cites a datasheet SECTION and PAGE (origin) - the register file p.21 / p.28, I/O p.28 / p.30, flash sections p.27 / p.286',
          all('p.' in MR['%s:%s' % (SOC, n)]['origin'] for n in ('register-file', 'io-registers', 'ext-io-registers', 'flash.application', 'flash.boot'))
          and 'p.21' in MR['%s:register-file' % SOC]['origin'] and 'p.28' in MR['%s:io-registers' % SOC]['origin'] and 'p.286' in MR['%s:flash.boot' % SOC]['origin'])
    mm = MV.memory_map(t, SOC)
    check('rp-0: the regions do not overlap within one address space (a flash section and its parent are one thing)', mm['overlaps'] == [], str(mm['overlaps']))
    ds = mm['data_space']
    check('rp-0: the data space is covered 0x0000-0x08FF with no gap: 32 + 64 + 160 + 2048 = 2304 bytes', (ds['start'], ds['end'], ds['bytes'], ds['contiguous']) == ('0x0000', '0x08FF', 2304, True) and 32 + 64 + 160 + 2048 == 2304, str(ds))
    bad_overlap = MV.overlaps([dict(r, start='0x0010') if r['region'] == 'io-registers' else r for r in mm['regions']])
    check('rp-0: the overlap check is real - moving the I/O registers to 0x0010 overlaps the register file', ('atmega328p:register-file', 'atmega328p:io-registers') in bad_overlap or ('atmega328p:io-registers', 'atmega328p:register-file') in bad_overlap, str(bad_overlap))
    boot, app = MR['%s:flash.boot' % SOC], MR['%s:flash.application' % SOC]
    check('rp-0: the boot loader section is present and cited: the chip\'s shipped default (BOOTSZ=00, 2048 words = 4096 B at 0x7000), the application the rest; the four BOOTSZ options are listed',
          boot['size'] == 4096 and boot['start'] == '0x7000' and app['size'] == 28672 and app['size'] + boot['size'] == MR['%s:flash' % SOC]['size']
          and 'BOOTSZ=11 256 words (512 B)' in next(f for f in t['DatasheetFact'] if f['name'] == '%s:memory.boot_sizes' % SOC)['value'] and 'p.292' in boot['origin'])
    check('rp-0: Table 27-13 is carried exactly: boot word addresses x2 = byte start (0x3F00 -> 0x7E00 ... 0x3800 -> 0x7000), pages = words/64, application ends the word before the boot section',
          all(int(o[4][0], 16) * 2 == MM.boot_start_bytes(o) and o[2] == o[1] // 64 and int(o[3][1], 16) + 1 == int(o[4][0], 16) and o[4][1] == '0x3FFF' for o in MM.BOOT_OPTIONS))
    placed = sum(len(v) for v in mm['placed'].values())
    in_region = lambda reg: next(r for r, v in mm['placed'].items() if any(p['register'] == reg for p in v))   # noqa: E731
    check('rp-0: all 96 registers live in a region (from the RegisterAddressMapping rows): PORTB 0x25 / EIMSK 0x3D in io-registers, UCSR0B 0xC1 / TCCR2A 0xB0 / WDTCSR 0x60 in ext-io-registers',
          placed == 96 and in_region('PORTB') == in_region('EIMSK') == '%s:io-registers' % SOC and in_region('UCSR0B') == in_region('TCCR2A') == in_region('WDTCSR') == '%s:ext-io-registers' % SOC
          and len(mm['placed']['%s:io-registers' % SOC]) + len(mm['placed']['%s:ext-io-registers' % SOC]) == 96 and not mm['placed']['%s:register-file' % SOC])
    ctl = {k: [c['register'] for c in v] for k, v in mm['controls'].items()}
    check('rp-0: the memory-nvm registers control their memories: EEAR/EEARH/EEARL/EEDR/EECR -> eeprom, SPMCSR -> flash, SP/SPH/SPL -> sram (all derived memory-nvm)',
          ctl == {'eeprom': ['EEAR', 'EEARH', 'EEARL', 'EEDR', 'EECR'], 'flash': ['SPMCSR'], 'sram': ['SP', 'SPH', 'SPL']}, str(ctl))
    uno = MV.memory_map(t, SOC, board='uno')
    ub = {r['region']: r for r in uno['regions']}
    check('rp-0: with the UNO the boot section is its 512-byte Optiboot (BOOTSZ=11 option, 0x7E00), the application 32256 = boards.txt upload.maximum_size; the BOOTSZ fuse value is said to be undetermined',
          ub['flash-boot']['size'] == 512 and ub['flash-boot']['start'] == '0x7E00' and ub['flash-application']['size'] == 32256 and uno['boot']['consistent'] and uno['boot']['bootsz'] == '11'
          and 'not read' in ub['flash-boot']['undetermined'] and uno['overlaps'] == [] and 'boards.txt' in ' '.join(uno['boot']['cites']))
    refused = ''
    try:
        MV.memory_map(t, SOC, board='esp32-c3')
    except KeyError as e:
        refused = e.args[0]
    check('rp-0: a board built around another chip is refused for this SoC by name', 'esp32-c3' in refused and 'atmega328p' in refused, refused)

    # ---- firmware use: measured or unmeasured, never a guess
    nb = MV.memory_map(t, SOC, board='uno')
    check('rp-0: with no build every region says `unmeasured` (or `reserved` for the boot section) and carries no used/free number', all(r['use'] in ('unmeasured', 'reserved') and r['used'] == '' for r in nb['regions']) and not nb['firmware_use']['measured'])
    z = MV.memory_map(t, SOC, board='uno', build={'name': 'empty', 'size_text': 0, 'size_data': 0, 'size_bss': 0})
    check('rp-0: a build record with no sizes is `unmeasured`, not zero', not z['firmware_use']['measured'] and all(r['used'] == '' for r in z['regions']))
    fb = MV.memory_map(t, SOC, board='uno', build={'name': 'light', 'size_text': 4416, 'size_data': 26, 'size_bss': 737})
    fr = {r['region']: r for r in fb['regions']}
    check('rp-0: a build of .text 4416 + .data 26 + .bss 737 uses 4442 B of flash (text + data) and 763 B of static RAM (data + bss); the application has 32256 - 4442 = 27814 free with the 512-byte bootloader subtracted; SRAM 2048 - 763 = 1285 free',
          fr['flash-application']['used'] == 4442 and fr['flash-application']['free'] == 27814 and fr['sram']['used'] == 763 and fr['sram']['free'] == 1285
          and fb['firmware_use']['bootloader_subtracted'] == 512 and fr['flash-boot']['use'] == 'reserved' and fr['eeprom']['use'] == 'unmeasured' and 'stack' in fr['sram']['use_note'])
    ov = MV.memory_map(t, SOC, board='uno', build={'name': 'big', 'size_text': 32300, 'size_data': 26, 'size_bss': 100})
    check('rp-0: a build past the application section (32326 > 32256) reads `over` - the bootloader is not available to it', {r['region']: r for r in ov['regions']}['flash-application']['use'] == 'over')

    # ---- the doors, on a REAL falcon.App next to every existing board route
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    tabs = {c: {r['name']: types.SimpleNamespace(**r) for r in rows} for c, rows in t.items() if rows and all('name' in r for r in rows)}   # a server holding every seed row
    tabs['FirmwareBuild'] = {'light': types.SimpleNamespace(name='light-build', size_text=4416, size_data=26, size_bss=737, state='built')}
    _S = types.SimpleNamespace(falconServer=falcon.App(), manager=types.SimpleNamespace(objectTables=tabs, idList=[]))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            construct_board_endpoints(_S)
        cl = ft.TestClient(_S.falconServer)
        a = cl.simulate_get('/api/board/socs/%s/register-profile' % SOC)
        a = a.json
        pin_only = cl.simulate_get('/api/board/socs/%s/register-profile?class=pin' % SOC).json
        fld = cl.simulate_get('/api/board/socs/%s/register-profile?list=fields' % SOC).json
        cls_rows = cl.simulate_get('/api/board/socs/%s/register-profile?list=classes' % SOC).json
        bad_cls = cl.simulate_get('/api/board/socs/%s/register-profile?class=zzz' % SOC)
        nope = cl.simulate_get('/api/board/socs/z80/register-profile')
        mmj = cl.simulate_get('/api/board/socs/%s/memory-map' % SOC).json
        mmu = cl.simulate_get('/api/board/socs/%s/memory-map?board=%s' % (SOC, UNO)).json
        mmb = cl.simulate_get('/api/board/socs/%s/memory-map?board=%s&build=light-build' % (SOC, UNO)).json
        mmt = cl.simulate_get('/api/board/socs/%s/memory-map?board=%s&text=4416&data=26&bss=737&list=registers' % (SOC, UNO)).json
        nob = cl.simulate_get('/api/board/socs/%s/memory-map?build=nothing' % SOC)
        badb = cl.simulate_get('/api/board/socs/%s/memory-map?board=esp32-c3' % SOC)
        old = cl.simulate_get('/api/board/%s/pins' % UNO)
        old2 = cl.simulate_get('/api/board/%s/pin-roles' % UNO)
        ok = (a['ok'] and a['count'] == 96 and a['totals']['mixed'] == 9 and pin_only['count'] == 18 + 9 and fld['count'] == len(prof['fields']) and fld['list'] == 'fields'
              and [r['class'] for r in cls_rows['rows']] == [PIN, PER, MEM, CPU, RP.MIXED] and bad_cls.status_code == 400 and nope.status_code == 404
              and mmj['ok'] and mmj['count'] == 8 and mmu['firmware_use']['measured'] is False and {r['region']: r for r in mmu['rows']}['flash-boot']['size'] == 512
              and mmb['firmware_use']['flash_bytes'] == 4442 and mmb['firmware_use']['build'] == 'light-build' and mmt['count'] == 96 and mmt['list'] == 'registers'
              and nob.status_code == 404 and badb.status_code == 404 and old.status_code == 200 and old2.status_code == 200)
        why = str((a.get('count'), pin_only.get('count'), fld.get('count'), mmj.get('count'), mmb.get('firmware_use')))
    except Exception as ex:   # a route clash raises UnacceptableRouteError at add time
        ok, why = False, repr(ex)
    check('rp-0 DOORS: GET /api/board/socs/{soc}/register-profile[?class=&list=fields|classes] and /memory-map[?board=&build=|text=data=bss=&list=registers] ADD on a real falcon.App beside every existing board route (no UnacceptableRouteError) and answer; unknown SoC / class / build / foreign board are refused', ok, why)

    # ---- the pages and the nav
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as P
    pages = {p['pageRoute']: p for p in P}
    rp, mp = pages.get('register-profile'), pages.get('memory-map')
    items = [it for pg in (rp, mp) if pg for row in json.loads(pg['definition'])['rows'] for it in row['items']]
    names = {it['componentProps']['componentName'] for it in items}
    check('rp-0 PAGES: /display/register-profile (4 tables) and /display/memory-map (3 tables) exist as CONFIGURED class-rows-tables only - no raw-JSON panel, no new component - each with a description and a dataPath on the new doors',
          rp and mp and len(items) == 7 and names == {'class-rows-table'} and all(it.get('description') and it['componentProps']['inputs']['dataPath'].startswith('/api/board/socs/%s/' % SOC) for it in items)
          and all('json' not in it['componentProps']['componentName'] for it in items), str(names))
    check('rp-0 PAGES: the mixed-registers table filters class=mixed and no table lists raw *_json columns',
          next(it for it in items if it['id'] == 'rp-mixed')['componentProps']['inputs']['filterValue'] == 'mixed' and all('_json' not in it['componentProps']['inputs']['columns'] for it in items))
    from polariapps.apps_seed import SEED_POLARI_APPS
    hw = next(a for a in SEED_POLARI_APPS if a['name'] == 'app-hardware') if isinstance(SEED_POLARI_APPS[0], dict) else None
    navtxt = json.dumps(hw, default=str) if hw else str(SEED_POLARI_APPS)
    check('rp-0 NAV: the Hardware home links both pages in its own group ("The chip\'s registers and memory")', '/display/register-profile' in navtxt and '/display/memory-map' in navtxt and "registers and memory" in navtxt)

    # ---- the CLI
    outs = []
    for argv in (['registers', SOC], ['registers', SOC, '--class', 'pin'], ['registers', 'uno', '--json'], ['memory', SOC], ['memory', SOC, '--board', 'uno', '--sizes', '4416,26,737'], ['memory', SOC, '--json'],
                 ['registers', SOC, '--class', 'zzz'], ['registers', 'z80']):
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = RP.main(argv)
        outs.append((rc, o.getvalue()))
    j1, j2 = json.loads(outs[2][1]), json.loads(outs[5][1])
    check('rp-0 CLI: `registers <soc> [--class pin|peripheral|memory|cpu] [--json]` and `memory <soc> [--board B] [--sizes T,D,B] [--json]` run; the text names the totals, the mixed registers and the firmware use; --json is valid; a bad class / SoC is refused (rc 2)',
          outs[0][0] == 0 and '96 registers' in outs[0][1] and 'MCUCR' in outs[0][1] and outs[1][0] == 0 and 'DDRB' in outs[1][1] and 'EEAR ' not in outs[1][1]
          and outs[2][0] == 0 and j1['totals']['registers'] == 96 and outs[3][0] == 0 and 'unmeasured' in outs[3][1] and '0x0000-0x08FF' in outs[3][1]
          and outs[4][0] == 0 and 'application free 27814' in outs[4][1] and j2['ok'] and len(j2['regions']) == 8 and outs[6][0] == 2 and outs[7][0] == 2, str([o[0] for o in outs]))
