"""
@module cmod.custom.scope

ucd-scope (UNO_CORE_DEMO_PLAN.md §5f, his ruling 2026-10-09, verbatim: "when we have a page we only want to be
concerned about pins and properties we know belong to just the board, chip, and firmware we are using. We do not
want a page with everything possible on it ... dedicated Board pages for going through all possible boards,
dedicated pin pages for looking at all possible pins ... But those should be object specific pages."): THE SCOPED
HARDWARE CHAIN of one HardwareBinding — every list holds ONLY what that binding actually claims, activates or sets.
The exhaustive views (every board, every pin, every register the chip COULD have) stay the CLASS pages
(/class-main-page/<Class>, /object/<Class>/<name>) and /display/boards; this module never duplicates them, only
narrows to one binding's own rows.

Pure derivation over rows `cmod.custom.claims` (PinClaim / PeripheralClaim / RegisterSetting / RegisterFieldSetting /
SignalRoute) and `cmod.custom.binding` already compute, plus the board chain tables (`board.custom.hardware_chain` /
`board.custom.board_object` — BoardPin / SocPin / PinFunction / PeripheralSignal / Peripheral / Register /
RegisterField). Never a second derivation of anything those modules already produce — this module only SELECTS and
tags rows.

`scope_for(binding, graph, manager=None)` -> {binding, board, soc, rows: {pins, soc_pins, pin_functions, signals,
peripherals, registers, fields, settings, field_settings, routes}}. `binding` accepts the same shapes
`cmod.custom.claims`/`cmod.custom.binding` already do ('<solution>' | '<solution>@<board>' string, or an already-
resolved HardwareBinding dict/row). GET /api/firmware/solutions/{name}/hardware
(`cmod.cmod_firmware_api.FirmwareAPI.on_get_hardware`) is the one caller; `?list=<key>` narrows the answer to
`{ok, rows: [...]}` for one list (class-rows-table's `dataPath` contract, same as every other computed-table door
in this arc).
"""
import json


#: the `list` query-param keys GET /api/firmware/solutions/{name}/hardware?list=<key> accepts, in page order
LIST_KEYS = ('pins', 'soc_pins', 'pin_functions', 'signals', 'peripherals', 'registers', 'fields', 'settings',
             'field_settings', 'routes')


def _tag(cls, row):
    """A SHALLOW COPY of `row` with its own `ref` ('Class:name') — never mutates the shared chain-table row (the
    same dict instance may be read by other callers in the same request, e.g. the D3 walk)."""
    out = dict(row)
    out['ref'] = '%s:%s' % (cls, row['name'])
    return out


def _index(tables, cls):
    return {r['name']: r for r in tables.get(cls, [])}


def scope_for(binding, graph, manager=None):
    """The scoped chain for one binding — never raises on an unmaterialized board (every list is simply empty, the
    same `incomplete` posture `cmod.custom.binding.validity` already has for Phase 2 boards)."""
    from cmod.custom import claims as C

    b, naming = C._as_binding(binding, manager=manager)
    board = b.get('board', '')
    tables = C._chain_tables(manager)
    board_pins = _index(tables, 'BoardPin')
    soc_pins = _index(tables, 'SocPin')
    pin_functions_idx = _index(tables, 'PinFunction')
    signals_idx = _index(tables, 'PeripheralSignal')
    peripherals_idx = _index(tables, 'Peripheral')
    registers_idx = _index(tables, 'Register')
    fields_idx = _index(tables, 'RegisterField')

    claims = C.pin_claims(b, graph, manager=manager)
    periph_claims = C.peripheral_claims(b, graph, manager=manager)
    gen = C.register_settings(b, graph, manager=manager)

    soc = b.get('soc', '') or next((sp.get('soc', '') for sp in soc_pins.values()), '')

    # ---- pins + soc_pins: the BoardPins this binding CLAIMS (one PinClaim each), + the SocPins behind them
    pins_out, soc_pins_out = [], []
    seen_soc = set()
    for c in sorted(claims, key=lambda c: c['board_pin']):
        bp = board_pins.get(c['board_pin'])
        if bp is None:
            continue
        row = _tag('BoardPin', bp)
        row.update({'claim': c['name'], 'claim_mode': c['mode'], 'claim_pull': c['pull'], 'claim_edge': c['edge'],
                    'claim_initial': c['initial'], 'task': c['task']})
        pins_out.append(row)
        sp = soc_pins.get(c['soc_pin'])
        if sp is not None and sp['name'] not in seen_soc:
            seen_soc.add(sp['name'])
            soc_pins_out.append(_tag('SocPin', sp))

    # ---- pin_functions + signals: what each claim ACTIVATES (its own alt function) or plainly carries (the GPIO
    # function of a plain out/in pin) — never every function the pin COULD take (that is PinFunction's class page)
    pf_names = []
    for c in claims:
        if c['mode'] == 'alt' and c['pin_function']:
            pf_names.append(c['pin_function'])
        elif c['mode'] in ('out', 'in'):
            sp = soc_pins.get(c['soc_pin'])
            if sp is not None:
                pf_names.append('%s:%s:GPIO' % (sp.get('soc', soc), sp['pin']))
    pin_functions_out, signals_out = [], []
    seen_pf, seen_sig = set(), set()
    for name in pf_names:
        if name in seen_pf or name not in pin_functions_idx:
            continue
        seen_pf.add(name)
        pf = pin_functions_idx[name]
        pin_functions_out.append(_tag('PinFunction', pf))
        sig_name = pf.get('signal', '')
        if sig_name and sig_name not in seen_sig and sig_name in signals_idx:
            seen_sig.add(sig_name)
            signals_out.append(_tag('PeripheralSignal', signals_idx[sig_name]))

    # ---- peripherals: the ones this binding CLAIMS (PeripheralClaim) — the same set the active functions/signals
    # above belong to (every PinFunction/PeripheralSignal scoped in is one this binding's own claims produced)
    usage_by_peripheral, tasks_by_peripheral = {}, {}
    for p in periph_claims:
        usage_by_peripheral.setdefault(p['peripheral'], []).append(p['usage'])
        tasks_by_peripheral.setdefault(p['peripheral'], set()).update(json.loads(p['tasks_json']))
    peripheral_names = (set(usage_by_peripheral)
                        | {pin_functions_idx[n]['peripheral'] for n in seen_pf if pin_functions_idx[n].get('peripheral')}
                        | {signals_idx[n]['peripheral'] for n in seen_sig if signals_idx[n].get('peripheral')})
    peripherals_out = []
    for name in sorted(n for n in peripheral_names if n and n in peripherals_idx):
        row = _tag('Peripheral', peripherals_idx[name])
        row['usage'] = '; '.join(sorted(set(usage_by_peripheral.get(name, []))))
        row['tasks'] = ', '.join(sorted(tasks_by_peripheral.get(name, set())))
        peripherals_out.append(row)

    # ---- registers: the ones its RegisterSettings WRITE ('set at init') + the ones its claimed Peripherals OWN but
    # never write this slice ('claimed peripheral' — e.g. TIMER2's OCR2A/TCCR2x, USART0's UBRRn/UCSRn/UDR0)
    settings_by_register = {s['register']: s for s in gen['RegisterSetting']}
    peripheral_regs = set()
    for p in periph_claims:
        peripheral_regs.update(('%s:%s' % (soc, r)) if ':' not in r else r for r in json.loads(p['registers_json']))
    registers_out = []
    for name in sorted(set(settings_by_register) | peripheral_regs):
        reg = registers_idx.get(name)
        if reg is None:
            continue
        row = _tag('Register', reg)
        s = settings_by_register.get(name)
        if s is not None:
            row.update({'why': 'set at init', 'value': s['value'], 'mask': s['write_mask']})
        else:
            row.update({'why': 'claimed peripheral', 'value': '', 'mask': ''})
        registers_out.append(row)

    # ---- fields: the ones its RegisterFieldSettings SET — one row each, never every field of the register
    fields_out = []
    for fs in sorted(gen['RegisterFieldSetting'], key=lambda x: x['register_field']):
        fld = fields_idx.get(fs['register_field'])
        if fld is None:
            continue
        row = _tag('RegisterField', fld)
        row.update({'value': fs['value'], 'meaning': fs['meaning'],
                    'claim': fs.get('pin_claim') or fs.get('peripheral_claim') or '',
                    'task': fs['task'], 'rule': fs['rule']})
        fields_out.append(row)

    settings_out = [_tag('RegisterSetting', s) for s in gen['RegisterSetting']]
    field_settings_out = [_tag('RegisterFieldSetting', s) for s in gen['RegisterFieldSetting']]
    routes_out = [_tag('SignalRoute', s) for s in gen['SignalRoute']]

    return {'binding': b.get('name', naming), 'board': board, 'soc': soc,
            'rows': {'pins': pins_out, 'soc_pins': soc_pins_out, 'pin_functions': pin_functions_out,
                    'signals': signals_out, 'peripherals': peripherals_out, 'registers': registers_out,
                    'fields': fields_out, 'settings': settings_out, 'field_settings': field_settings_out,
                    'routes': routes_out}}
