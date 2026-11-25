"""
@module hwnocode.custom.feature_derive

cb-2 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §4), DERIVED: one `HardwareFeature` per schematic component of a board HardwareSolution,
every column filled from rows that already exist and are already checked:
  struct field     the Catom assertions' pin <-> field couplings (cmod.custom.catom_assertions.struct_pin_bindings) on the component's pins,
                   on the struct map that carries them (StructObjectMap)
  UI control       the same couplings' bridge side: a field the screen sets (updater US, from the bridge) is a bridge input, the struct the
                   firmware reports (to the bridge) a bridge output
  no-code piece    the firmware variant's HAL variables (cmod.custom.catom_variables) on those pins, with their HAL roles and their verdicts
  protocol         in words, from the HAL role, the firmware's pin claims (edge, pull), the active level the component's wiring gives
                   (a switch to ground with a pull-up is active-low; an LED from the pin to ground is active-high) and the debounce knob
  chip and pins    the SoC and the board pins (the SoC pin each one is)
  device / simulator   the real board, and the twin engine that stands in for it (board.custom.twin_kinds, matched by board exactly; no
                   match = no simulator pair defined, said)
One row per component (the drawing binds one field group per block: ButtonOn -> the button, LightOn -> the light).
`chosen` = pins: the pins are the person's own bench wiring (the variant's knobs, written by a slot choice); every other column is
suggested (derived) and is derived again on every solve.

  features(solution, variant, board, soc, solved)  -> [HardwareFeature dict]   (`solved` = schematic_solve.solve's output)
  simulator_of(board)                              -> (words, '') | ('', why)
"""

def simulator_of(board):
    from board.custom import twin_kinds as TK
    k = next((k for k in TK.KINDS if k['board'] == board), None)
    if k is None:
        return '', 'no twin kind is defined for %s (board.custom.twin_kinds): its simulator pair is not defined' % board
    return '%s twin (kind %s, %s-engines)' % (k['mcu'], k['name'], 'board' if k['family'] == 'avr' else k['family']), ''


def _uniq(xs):
    out = []
    for x in xs:
        if x and x not in out:
            out.append(x)
    return out


def _map_of(struct):
    from cmod.custom import catom_assertions as CA
    m = next((m for m in CA.SEED_STRUCT_OBJECT_MAPS if m.get('struct') == struct), None)
    return m['name'] if m else struct


def _protocol(comp, sig_ports, variables, claims_by_pin, bindings, knobs, meta, soc):
    from cmod.custom import catom_variables as CV
    words = []
    for p in sig_ports:
        m = meta.get(p['name'], {})
        var = next((v for v in variables if v.get('pin') == CV.resolve_pin(soc, p['pin'])), None)
        claim = claims_by_pin.get(m.get('board_pin', ''))
        role = var['role'] if var else 'no HAL variable'
        bits = ['%s %s on %s' % (var['variable'] if var else '-', role, p['pin'])]
        events = _uniq(b['event'] for b in bindings if b['pin'] == (var or {}).get('pin'))
        if claim and claim.get('edge') not in (None, '', 'none', 'undetermined'):
            bits.append('%s edge' % claim['edge'])
        elif events:
            bits.append('/'.join(events))
        if m.get('role') == 'input' and comp['core_part'] == 'pushbutton':
            pull = claim.get('pull') if claim else ''
            bits.append('active-low: the %s holds it high, the switch pulls it to ground' % ('internal pull-up' if pull == 'up' else 'pull'))
            if isinstance(knobs.get('debounce_ms'), (int, float)) and knobs['debounce_ms'] > 0:
                bits.append('debounced in the firmware (%s ms)' % knobs['debounce_ms'])
        elif m.get('role') == 'output' and comp['core_part'] == 'led':
            bits.append('active-high: the LED runs from the pin to ground')
        elif m.get('role') == 'input':
            bits.append('reads the line this board drives')
        words.append(', '.join(bits))
    return '; '.join(words)


def features(solution, variant, board, soc, solved):
    from cmod.custom import catom_assertions as CA
    from cmod.custom import catom_variables as CV
    variables = [v for v in CV.variables(variant) if v.get('type', 'pin') == 'pin']
    bindings = CA.struct_pin_bindings(variant)
    knobs = CV.variant_knobs(variant, soc)
    claims_by_pin = {c.get('board_pin'): c for c in solved.get('_claims', ())}
    meta = solved.get('_port_meta', {})
    sim, sim_why = simulator_of(board)
    out = []
    for comp in solved['SchematicComponent']:
        ports = sorted([p for p in solved['SchematicComponentPort'] if p['component'] == comp['name']], key=lambda p: p['order'])
        sig = [p for p in ports if p['kind'] == 'signal']
        soc_pins = {CV.resolve_pin(soc, p['pin']): p['pin'] for p in sig}
        vs = [v for v in variables if v.get('pin') in soc_pins]
        mine = [b for b in bindings if b['pin'] in soc_pins and b['field'] != '*']
        fields = _uniq(b['field'] for b in mine)
        structs = _uniq(b['struct'] for b in mine)
        ui_in = _uniq(b['atom'] for b in bindings if b['field'] in fields and b['updater'] == 'US')
        ui_out = _uniq(b['atom'] for b in bindings if b['direction'] == 'to-bridge')
        ui = '; '.join(x for x in ('the screen sets it through %s' % ', '.join(ui_in) if ui_in else '',
                                   'the firmware reports it through %s' % ', '.join(ui_out) if ui_out else '') if x)
        direction = ' + '.join(x for x in ('bridge input' if ui_in else '', 'bridge output' if ui_out else '') if x)
        notes = ['derived by hwnocode.custom.feature_derive from %s (FirmwareVariant %s on %s), its circuit %s and the catom assertions; '
                 're-derived on every solve' % (solution or 'no HardwareSolution', variant, board, comp['circuit'])]
        if not sim:
            notes.append(sim_why)
        unverified = [b['assertion'] for b in mine if b.get('status') != 'verified']
        if unverified:
            notes.append('the struct couplings are %d unverified catom assertion(s) (a cycle record shows the traffic, not the field writes)' % len(unverified))
        out.append({
            'name': '%s:%s' % (solution or comp['circuit'], comp['intent']) if sum(1 for c in solved['SchematicComponent'] if c['intent'] == comp['intent']) == 1
                    else comp['name'],
            'title': 'The %s (%s)' % (comp['intent'], comp['title'].split(' ', 1)[-1]),
            'struct_instance': ', '.join(_map_of(s) for s in structs), 'struct_field': ', '.join(fields),
            'ui_control': ui, 'ui_direction': direction,
            'nocode_variable': ', '.join(v['variable'] for v in vs), 'hal_role': ', '.join('%s %s' % (v['variable'], v['role']) for v in vs),
            'protocol': _protocol(comp, sig, vs, claims_by_pin, bindings, knobs, meta, soc),
            'schematic_component': comp['name'], 'chip': soc,
            'pins': ', '.join('%s (%s)' % (p['pin'], CV.resolve_pin(soc, p['pin'])) if CV.resolve_pin(soc, p['pin']) != p['pin'] else p['pin'] for p in sig),
            'hardware_solution': solution, 'firmware_variant': variant, 'device': board, 'simulator': sim,
            'chosen': 'pins', 'notes': '; '.join(notes)})
    return out

