"""
@module hwnocode.custom.suggest

THE RUNTIME SUGGESTION — SUGGEST ONLY (D-hn-3 ruled): bare C, FreeRTOS, ESP-IDF or Zephyr, with the EVIDENCE rows, derived from the
graph and the board (HARDWARE_NOCODE_PLAN.md §3). It never writes the knob: `firmware_runtime` stays the person's, and the output
says so. hn-0 carries the features derivable from rows today and the plan's ordered rule table (the first decisive row wins);
hn-1 adds the RuntimeSuggestion rows, the cmod `blocking` verdict and one fixture per rule row.

Features (each with where it came from):
  memory class   the register's device class (MCU-S …) / ram_kb on the BoardDefinition row
  activities     the CGraph's scopes: tick nodes (independent periods), the on-rx drain, the on-command handler — all in one
                 main loop when there is one tick; ISRs pulled in by shared globals
  blocking       atoms whose POLARI_NODE role says "blocking" (the cmod `blocking` verdict is hn-1 — said, not faked)
  shared across priorities / two locks   RTOS-only primitives: a bare-C graph has none (no task, no mutex node exists yet)
  radios         the BoardDefinition `radios` column + radio atoms in the graph
  cost floor     the CGlueBuild's measured flash/RAM against the board's limits
"""
import json

from hwnocode.custom import knobs as K


def _tables(manager):
    return (getattr(manager, 'objectTables', None) or {}) if manager is not None else {}


def _glue_build(cgraph):
    from cmod.custom import glue as GL
    rec = GL.load_record(cgraph) or {}
    return rec


def _atoms(project):
    from cmod.custom import projects as P
    try:
        m = json.load(open(P.manifest_path(P.resolve(project))))
    except Exception:
        return {}
    return {a['name']: a for a in m['atoms']}


def features(parts):
    g, nodes, edges = parts['cgraph']['graph'], parts['cgraph']['nodes'], parts['cgraph']['edges']
    board = parts['board'] or {}
    atoms = _atoms(g.get('project', ''))
    ticks = [n for n in nodes if n.get('kind') == 'tick']
    periods = sorted({dict(kv.split('=', 1) for kv in [p.strip() for p in str(n.get('params', '')).split(';')] if '=' in kv).get('period_ms', '?')
                      for n in ticks})
    rx = [e for e in edges if e.get('kind') == 'on-rx']
    cmd = [e for e in edges if e.get('kind') == 'on-command']
    used = {(n.get('atom') or '').partition(':')[2]: n for n in nodes if n.get('kind') == 'c-atom'}
    # a node's scope: its tick edge's, else the scope of what feeds it by data (cmod's own scoping, simplified to a fixpoint)
    tick_of = {e['to_node']: e['from_node'] for e in edges if e.get('kind') == 'tick'}
    changed = True
    while changed:
        changed = False
        for e in edges:
            if e.get('kind') == 'data' and e['from_node'] in tick_of and e['to_node'] not in tick_of:
                tick_of[e['to_node']] = tick_of[e['from_node']]
                changed = True
    blocking = []
    for k, n in sorted(used.items()):
        role = ((atoms.get(k) or {}).get('annotation') or {}).get('role', '')
        if 'blocking' in role.lower():
            t = tick_of.get(n.get('instance'))
            scope = 'tick %s (period %s)' % (t, ', '.join(periods)) if t else 'loop'
            blocking.append({'atom': k, 'node': n.get('instance'), 'role': role, 'scope': scope})
    isr_shared = sorted({r['name'] for k in used for r in (atoms.get(k) or {}).get('resources', [])
                         if r.get('kind') == 'global' and 'shared with ISR' in (r.get('detail') or '')})
    not_isr_safe = sorted(k for k in used if (atoms.get(k) or {}).get('isr_safe') == 'no')
    radios = str(board.get('radios') or '').strip()
    radio_atoms = sorted(k for k in used if any(w in k.lower() for w in ('wifi', 'ble', 'lora', 'radio', '802154')))
    rec = _glue_build(g.get('name', ''))
    b = rec.get('build') or {}
    flash_kb, ram_kb = int(board.get('flash_kb') or 0), int(board.get('ram_kb') or 0)
    flash = int(b.get('flash_bytes') or 0)
    ram = int(b.get('size_data') or 0) + int(b.get('size_bss') or 0)
    return {
        'memory_class': K.memory_class(board), 'board': board.get('name', ''), 'device_class': board.get('device_class', ''),
        'ram_kb': ram_kb, 'flash_kb': flash_kb,
        'activities': {'main_loops': 1, 'ticks': len(ticks), 'tick_periods': periods, 'rx_drain': len(rx), 'command_handlers': len(cmd),
                       'independent_periods': len(ticks), 'concurrent_activities': max(1, len(ticks))},
        'blocking': blocking, 'isr_shared_globals': isr_shared, 'not_isr_safe_atoms': not_isr_safe,
        'shared_across_priorities': [], 'two_locks': [], 'request_ack_waits': [],
        'radios': radios if radios and radios.lower() != 'none' else '', 'radio_atoms': radio_atoms,
        'cost': {'flash_bytes': flash, 'ram_bytes': ram, 'glue_build': '%s@%s' % (g.get('name', ''), (rec.get('files_sha256') or '')[:12]),
                 'flash_pct': round(100.0 * flash / (flash_kb * 1024), 1) if flash_kb and flash else None,
                 'ram_pct': round(100.0 * ram / (ram_kb * 1024), 1) if ram_kb and ram else None},
    }


def suggest(name, manager=None, parts=None):
    from hwnocode.custom import split as SP
    p = parts or SP.solution_rows(name, manager)
    f = features(p)
    hs = p['solution']
    board = f['board']
    ev_board = 'BoardDefinition %s (device_class %s, ram_kb %s, flash_kb %s, radios %s)' % (
        board, f['device_class'] or '?', f['ram_kb'] or '?', f['flash_kb'] or '?', f['radios'] or 'none')
    ev_cost = 'CGlueBuild %s (flash %s B = %s %% of %s KB, RAM %s B = %s %% of %s KB, measured by make alone)' % (
        f['cost']['glue_build'], f['cost']['flash_bytes'], f['cost']['flash_pct'], f['flash_kb'], f['cost']['ram_bytes'],
        f['cost']['ram_pct'], f['ram_kb'])
    act = f['activities']
    rules = [
        {'rule': 1, 'condition': 'the board is S class', 'holds': f['memory_class'] == 'S', 'suggests': 'bare-c',
         'evidence': [ev_board, ev_cost], 'note': 'an RTOS is refused on it if picked (the RAM: a kernel + per-task stacks)'},
        {'rule': 2, 'condition': 'a radio stack is needed', 'holds': bool(f['radios'] or f['radio_atoms']),
         'suggests': 'esp-idf (Espressif) / zephyr (nRF, STM32G4)', 'evidence': [ev_board + ' — radios column', 'radio atoms in the graph: %s'
                                                                                % (', '.join(f['radio_atoms']) or 'none')]},
        {'rule': 3, 'condition': '≥ 2 concurrent activities AND (a blocking atom OR a shared resource across priorities)',
         'holds': act['concurrent_activities'] >= 2 and bool(f['blocking'] or f['shared_across_priorities']),
         'suggests': 'freertos / esp-idf (zephyr on L-class boards)',
         'evidence': ['Scenario priority-inversion-mutex (sc-3: H waited 12 160 µs → 2 098 µs with a mutex, −38 B)',
                      'Scenario two-lock-deadlock (cycle closed at tick 370; ordering −40 B)']},
        {'rule': 4, 'condition': 'only ISRs + one loop; timeouts by state machine', 'holds': act['concurrent_activities'] <= 1,
         'suggests': 'bare-c', 'evidence': ['Scenario lost-ack-hang (S2: fixed in bare C by a timeout FSM, +80 B flash / +4 B RAM)',
                                            'Scenario torn-millis-read (sc-0: the atomic fix in bare C, +6 B, +3 cycles)',
                                            'FormalCheck hal-millis-not-torn@uno-sim-rig']},
        {'rule': 5, 'condition': 'otherwise', 'holds': True, 'suggests': 'bare-c', 'evidence': [ev_cost]},
    ]
    decisive = next(r for r in rules if r['holds'])
    suggested = decisive['suggests'].split(' ')[0].split('/')[0]
    reasons = []
    if f['memory_class']:
        reasons.append('memory class %s (%s, %s KB RAM)' % (f['memory_class'], f['device_class'] or '-', f['ram_kb']))
    reasons.append('activities: %d main loop, %d tick (%s), %d rx drain, %d command handler — one pass, no independent periods'
                   % (act['main_loops'], act['ticks'], ', '.join(act['tick_periods']) or '-', act['rx_drain'], act['command_handlers'])
                   if act['concurrent_activities'] <= 1 else '%d concurrent activities' % act['concurrent_activities'])
    reasons.append('blocking atoms: %s' % ('; '.join('%s in %s ("%s")' % (b['atom'], b['scope'], b['role']) for b in f['blocking'])
                                           if f['blocking'] else 'none') + ' — the cmod `blocking` verdict is hn-1; read from the annotation')
    reasons.append('shared resource across priorities: none (no task or mutex node in a bare-C graph); ISR-shared globals: %s; '
                   'not ISR-safe atoms: %s' % (', '.join(f['isr_shared_globals']) or 'none', ', '.join(f['not_isr_safe_atoms']) or 'none'))
    reasons.append('radio: %s' % (f['radios'] or 'none'))
    ok, why = K.check_runtime(hs.get('firmware_runtime'), p['board'])
    return {'solution': hs['name'], 'suggested': suggested, 'decisive_rule': decisive['rule'], 'rules': rules, 'reasons': reasons,
            'features': f, 'knob': {'firmware_runtime': hs.get('firmware_runtime') or 'bare-c', 'ok': ok, 'why': why},
            'applied': False,
            'policy': 'SUGGEST ONLY (D-hn-3): nothing was changed — firmware_runtime stays the person\'s pick on the HardwareSolution row'}
