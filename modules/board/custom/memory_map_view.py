"""
@module board.custom.memory_map_view

rp-0 (MISSION_PROFILE_SOLVER_PLAN.md §2.4, "the memory map view"): a SoC's MemoryRegion rows laid out per ADDRESS SPACE (the data
space, program memory, EEPROM), which registers live in which region (from the RegisterAddressMapping rows - never re-computed from
a name), which registers CONTROL which memory (the memory-nvm class of board.custom.register_profile), and - when a board and/or
a firmware build is given - what the firmware uses of each region, MEASURED:

  board     the board's cited bootloader (boards.txt upload.maximum_size, Optiboot size - board.custom.uno_facts) fixes the
            application / boot loader boundary: the boot section is the smallest BOOTSZ option that holds the bootloader
            (Table 27-13), the application is the rest. No board => the chip's shipped default split (BOOTSZ=00, maximum boot).
            Which BOOTSZ fuse value the board actually ships with is `undetermined` unless a fact says so.
  build     a FirmwareBuild's avr-size numbers: flash = .text + .data, static RAM = .data + .bss (the stack and heap are NOT
            measured and the view says so); EEPROM is not part of the build record => `unmeasured`. A build with no sizes, or
            no build at all, reports `unmeasured` - never an estimate.
"""
from board.custom import memory_map_atmega328p as MM
from board.custom import register_profile as RP
from board.custom.soc_atmega328p import SOC

#: the region each memory-nvm register CONTROLS (the class itself comes from register_profile; the target region from the cited section)
CONTROLS = {
    'EEAR': ('eeprom', '§8.4.1 EEPROM Read/Write Access, p.29'), 'EEARH': ('eeprom', '§8.4.1, p.29'), 'EEARL': ('eeprom', '§8.4.1, p.29'),
    'EEDR': ('eeprom', '§8.4.1, p.29'), 'EECR': ('eeprom', '§8.4.1, p.29'),
    'SPMCSR': ('flash', '§26.3.1 SPMCSR, p.270 (Program memory operations)'),
    'SP': ('sram', '§7.5 Stack Pointer, p.22'), 'SPH': ('sram', '§7.5.1, p.22'), 'SPL': ('sram', '§7.5.1, p.22'),
}
_ORDER = {'data': 0, 'program': 1, 'eeprom': 2}


def space_of(region):
    if (region.get('address_space') or '').endswith(':data'):
        return 'data'
    if region['region'].startswith('flash'):
        return 'program'
    return 'eeprom' if region['region'] == 'eeprom' else 'other'


def parent_of(region):
    """A section row is named `<parent>.<section>` ('atmega328p:flash.boot' is part of 'atmega328p:flash')."""
    return region['name'].rpartition('.')[0] if '.' in region['name'] else ''


def _hex(n):
    return '0x%04X' % n


def board_facts(tables, board):
    from board.custom.uno_facts import SEED_UNO_FACTS
    facts = {f['fact_key']: f for f in SEED_UNO_FACTS if f['board'] == board}
    facts.update({f['fact_key']: f for f in tables.get('DatasheetFact', []) if f.get('board') == board})
    return facts


def board_boot(tables, soc, board):
    """The bootloader a BOARD fixes on `soc`'s flash: {size, option, application, cites, undetermined} or None when the board names none."""
    from board.custom import board_object as BO
    board = BO.board_name(board)
    bd = next((b for b in tables.get('BoardDefinition', []) if b.get('name') == board), None)
    if bd is None:
        raise KeyError('no board %s' % board)
    if bd.get('soc_definition') != soc:
        raise KeyError('%s is built around %s, not %s' % (board, bd.get('soc_definition') or 'an unmodelled SoC', soc))
    f = board_facts(tables, board)
    if 'optiboot_size' not in f or 'upload.maximum_size' not in f:
        return None
    boot, app_max = int(f['optiboot_size']['value']), int(f['upload.maximum_size']['value'])
    option = next((o for o in sorted(MM.BOOT_OPTIONS, key=MM.boot_bytes) if MM.boot_bytes(o) >= boot), None)
    return {'board': board, 'bootloader_bytes': boot, 'application_max': app_max, 'consistent': app_max == MM.FLASH_BYTES - boot,
            'option': option, 'bootsz': option[0] if option else '',
            'cites': ['%s %s %s' % (f['optiboot_size']['document'], f['optiboot_size']['page_table'], f['optiboot_size']['url']),
                      '%s %s %s' % (f['upload.maximum_size']['document'], f['upload.maximum_size']['page_table'], f['upload.maximum_size']['url']),
                      'Table 27-13 Boot Size Configuration, p.286 (the smallest option that holds %d bytes)' % boot],
            'undetermined': 'the BOOTSZ fuse value the %s ships with (boards.txt high_fuses) was not read - the %d-byte bootloader is consistent with BOOTSZ=%s, not proven by it'
                            % (board, boot, option[0] if option else '?')}


def measured(build):
    """(flash_used, ram_used, text, data, bss) from a build/sizes dict, or None when it carries no sizes."""
    if not build:
        return None
    t, d, b = (int(build.get('size_text') or 0), int(build.get('size_data') or 0), int(build.get('size_bss') or 0))
    return (t + d, d + b, t, d, b) if (t or d or b) else None


def memory_map(tables, soc=SOC, board=None, build=None):
    if soc != SOC:
        raise KeyError('%s has no memory rows - modelled SoCs: %s' % (soc, SOC))
    regions = [dict(r) for r in tables.get('MemoryRegion', []) if r.get('soc') == soc]
    if not regions:
        raise KeyError('%s has no MemoryRegion rows' % soc)
    boot = board_boot(tables, soc, board) if board else None
    basis = 'the chip\'s shipped default split (BOOTSZ=%s, maximum boot section) - give a board for its bootloader' % MM.DEFAULT_BOOTSZ
    if boot and boot['option']:
        size = MM.boot_bytes(boot['option'])
        for r in regions:
            if r['region'] == 'flash-boot':
                r.update(size=size, start=_hex(MM.FLASH_BYTES - size), undetermined=boot['undetermined'],
                         notes='%s; the %s\'s bootloader is %d bytes (BOOTSZ=%s)' % (r['notes'].split(';')[0], boot['board'], boot['bootloader_bytes'], boot['bootsz']))
            elif r['region'] == 'flash-application':
                r.update(size=MM.FLASH_BYTES - size, undetermined='program memory (§8.1); the boundary is the %s\'s bootloader' % boot['board'],
                         notes='the Application Flash Section: byte addresses 0x0000-%s; part of the `flash` row; boards.txt upload.maximum_size = %d' % (_hex(MM.FLASH_BYTES - size - 1), boot['application_max']))
        basis = 'the %s\'s cited bootloader (%d bytes -> BOOTSZ=%s option); %s' % (boot['board'], boot['bootloader_bytes'], boot['bootsz'], boot['undetermined'])
    m = measured(build)
    regs_by = {}
    for g in tables.get('Register', []):
        if g.get('soc') == soc:
            regs_by[g['name']] = g
    placed = {r['name']: [] for r in regions}
    for mp in tables.get('RegisterAddressMapping', []):
        if mp.get('soc') != soc or not (mp.get('address_space') or '').endswith(':data'):
            continue
        g = regs_by.get(mp['register'])
        if g is None:
            continue
        a = int(mp['address'], 16)
        home = next((r for r in regions if space_of(r) == 'data' and int(r['start'], 16) <= a < int(r['start'], 16) + r['size']), None)
        if home is not None:
            placed[home['name']].append({'register': g['register'], 'address': _hex(a), 'io_address': g['addr'] if g['space'] == 'io' else '', 'width_bytes': g['width_bytes']})
    prof = RP.profile(tables, soc)
    cls_of = {r['register']: r['class'] for r in prof['registers']}
    controls = {}
    for reg, (region, cite) in CONTROLS.items():
        if reg in cls_of and cls_of[reg] == RP.MEM:
            controls.setdefault(region, []).append({'register': reg, 'cite': cite})
    out = []
    for r in sorted(regions, key=lambda r: (_ORDER.get(space_of(r), 9), int(r['start'], 16), -r['size'])):
        sp = space_of(r)
        start = int(r['start'], 16)
        row = {'name': r['name'], 'region': r['region'], 'space': sp, 'parent': parent_of(r), 'start': _hex(start), 'end': _hex(start + r['size'] - 1), 'size': r['size'],
               'address_space': r['address_space'], 'holds': r['notes'], 'registers': len(placed[r['name']]), 'controlled_by': ', '.join(c['register'] for c in controls.get(r['region'], [])),
               'cite': r['origin'].replace('cited:', ''), 'fact': r['fact'], 'undetermined': r['undetermined'], 'used': '', 'available': '', 'free': '', 'use': 'unmeasured',
               'use_note': 'no firmware build given - nothing is guessed' if m is None else ''}
        out.append(row)
    by = {r['name']: r for r in out}
    use = {'build': (build or {}).get('name', ''), 'measured': m is not None}
    if m is not None:
        flash_used, ram_used, t, d, b = m
        app = next(r for r in out if r['region'] == 'flash-application')
        for r, used, what in ((app, flash_used, '.text %d + .data %d (flash holds the initial values of .data)' % (t, d)),
                              (by['%s:sram' % soc], ram_used, '.data %d + .bss %d (static RAM only: the stack and the heap are not measured)' % (d, b))):
            r.update(used=used, available=r['size'], free=r['size'] - used, use='measured' if used <= r['size'] else 'over', use_note=what)
        by['%s:flash' % soc].update(used=flash_used, available=MM.FLASH_BYTES, free=MM.FLASH_BYTES - flash_used, use='measured',
                                    use_note='the used application bytes of the whole flash; the boot loader section (%d B) is reserved and subtracted from what the application may use' % by['%s:flash.boot' % soc]['size'])
        ee = by['%s:eeprom' % soc]
        ee.update(use='unmeasured', use_note='the build record carries no .eeprom size')
        for r in out:
            if r['space'] == 'data' and r['region'] in ('register-file', 'io-registers', 'ext-io-registers'):
                r.update(use='n/a', use_note='registers - not allocatable memory')
        use.update(flash_bytes=flash_used, ram_bytes=ram_used, application_free=app['free'], sram_free=by['%s:sram' % soc]['free'],
                   bootloader_subtracted=by['%s:flash.boot' % soc]['size'], basis=basis)
    bl = next(r for r in out if r['region'] == 'flash-boot')
    bl.update(use='reserved', use_note=('the boot loader (%d bytes) - not available to the application' % boot['bootloader_bytes']) if boot else
              'reserved for the boot loader section (size = the BOOTSZ fuses); not available to the application')
    problems = overlaps(out)
    covered = sorted((int(r['start'], 16), r['size']) for r in out if r['space'] == 'data')
    data_bytes = sum(s for _, s in covered)
    return {'soc': soc, 'board': board or '', 'basis': basis, 'regions': out, 'placed': placed, 'controls': controls, 'firmware_use': use, 'overlaps': problems,
            'data_space': {'start': _hex(covered[0][0]), 'end': _hex(covered[-1][0] + covered[-1][1] - 1), 'bytes': data_bytes,
                           'contiguous': all(covered[i][0] + covered[i][1] == covered[i + 1][0] for i in range(len(covered) - 1))},
            'boot': None if not boot else {k: v for k, v in boot.items() if k != 'option'}}


def overlaps(regions):
    """[(a, b)] of regions that overlap in one address space (a section and its parent are one thing, not an overlap)."""
    bad = []
    for sp in {r['space'] for r in regions}:
        rs = [r for r in regions if r['space'] == sp]
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if a['name'] == b['parent'] or b['name'] == a['parent']:
                    continue
                a0, b0 = int(a['start'], 16), int(b['start'], 16)
                if a0 < b0 + b['size'] and b0 < a0 + a['size']:
                    bad.append((a['name'], b['name']))
    return bad


def register_rows(mm):
    """One row per register with its region (for a configured table)."""
    out = []
    for r in mm['regions']:
        for p in sorted(mm['placed'][r['name']], key=lambda x: (int(x['address'], 16), x['register'])):
            out.append(dict(p, region=r['region'], space=r['space']))
    return out


def render(mm):
    lines = ['%s memory map%s - %s' % (mm['soc'], (' for ' + mm['board']) if mm['board'] else '', mm['basis'])]
    for r in mm['regions']:
        ind = '    ' if r['parent'] else '  '
        lines.append('%s%-8s %-18s %s-%s %6d B  %-9s %s' % (ind, r['space'], r['region'], r['start'], r['end'], r['size'], r['use'] + (' %s/%s' % (r['used'], r['available']) if r['used'] != '' else ''),
                                                          ('(%d registers) ' % r['registers'] if r['registers'] else '') + (('controlled by ' + r['controlled_by']) if r['controlled_by'] else '')))
    ds = mm['data_space']
    lines.append('  data space %s-%s = %d bytes, %s' % (ds['start'], ds['end'], ds['bytes'], 'contiguous' if ds['contiguous'] else 'GAPS'))
    if mm['overlaps']:
        lines.append('  OVERLAPS: %s' % mm['overlaps'])
    u = mm['firmware_use']
    lines.append('  firmware use: ' + ('%s - flash %d B, static RAM %d B; application free %d B, SRAM free %d B (bootloader %d B subtracted)' % (u['build'] or 'sizes given', u['flash_bytes'], u['ram_bytes'], u['application_free'], u['sram_free'], u['bootloader_subtracted'])
                                      if u['measured'] else 'unmeasured (give --sizes TEXT,DATA,BSS or a FirmwareBuild)'))
    return '\n'.join(lines)
