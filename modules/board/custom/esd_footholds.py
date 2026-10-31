"""
@module board.custom.esd_footholds

esd-5 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): AN ESD EVENT ON A FOOTHOLD OF A BOARD WITH NO SIMULATED CIRCUIT (a dev board, a breadboard, a part) - a
small deck per foothold: the pin alone (its capacitance, held at its level through a resistance), the area's protection parts, and the standard's
source (pcb.custom.esd_events: the same networks, the same baseline, the same results and chart).

  pin_deck(foothold, area, model, level_v, parts) -> (deck, t_event)
  run_pin_event(manager, kind, definition, area_name, model=None, level_v=None, runner=None) -> result   (as pcb.custom.esd_events.run_event)
  run_any(manager, area_name, model=None, level_v=None, runner=None) -> result   a PCB area runs on its circuit, any other on its foothold

The pin alone is the worst case for the pin: no chip-internal clamp diodes, nothing else on the net. Its numbers are the area's knobs, said as such:
pin_cap_pf (the chip pin's capacitance - replace it with the datasheet's C_IN) and hold_ohm (what holds the pin at its level - an output's drive, an
input's leakage path). The level it is held at is the foothold's own (rail, else logic volts, else 0 V). The absolute maximum is the area's, else the
foothold's cited max_volts.
"""
T_EVENT = 1e-6


def _foothold(manager, kind, definition, target):
    from board.custom import footholds as FH
    rows, _ = FH.for_definition(kind, definition, manager=manager)
    return next((f for f in rows if f.get('foothold') == target), None)


def board_key(kind, definition):
    """The SpiceRun board a foothold event is kept under (a PCB keeps its own name)."""
    return definition if kind == 'layers' else '%s:%s' % (kind, definition)


def _level(f):
    for k in ('rail_volts', 'logic_volts'):
        v = float(f.get(k, -1.0) if f.get(k) is not None else -1.0)
        if v >= 0:
            return v, k
    return 0.0, 'none known (0 V)'


def pin_deck(f, a, model, level_v, parts):
    from pcb.custom import esd_events as E
    hold_v, basis = _level(f)
    tstop = T_EVENT + max(3.0 * float(a['recover_us']), 20.0) * 1e-6
    lines = ['* esd-5: %s at %g V on foothold %s of %s/%s - the pin alone (board.custom.esd_footholds)'
             % (model, level_v, f['foothold'], a['definition_kind'], a['definition']),
             '* the pin held at %g V (%s) through hold_ohm %g; pin_cap_pf %g (knobs on the area)' % (hold_v, basis, float(a['hold_ohm']), float(a['pin_cap_pf'])),
             'Vhold esd_hold 0 DC %g' % hold_v, 'Rhold esd_hold pin %g' % float(a['hold_ohm']), 'Cpin pin 0 %gp' % float(a['pin_cap_pf'])]
    lines += E.event_lines('pin', model, level_v, T_EVENT) + E.protection_lines('pin', parts)
    return '\n'.join(lines + ['.tran 10n %g' % tstop, '.end']) + '\n', T_EVENT


def run_pin_event(manager, kind, definition, area_name, model=None, level_v=None, runner=None):
    import socket
    from electrodevice.custom import ngspice_shared as NS
    from pcb.custom import esd_events as E
    from pcb.custom import spice_runs as SR
    a = E._area(manager, area_name)
    if a is None:
        return {'ok': False, 'status': 404, 'error': 'no ESD area %r' % area_name}
    if a['scope'] != 'foothold':
        return {'ok': False, 'status': 422, 'error': 'a board with no simulated circuit runs an event on one foothold - area %r is a %s area' % (area_name, a['scope'])}
    model = model or a['model']
    if model not in E.MODELS:
        return {'ok': False, 'status': 400, 'error': 'model must be one of %s' % ', '.join(E.MODELS)}
    f = _foothold(manager, kind, definition, a['target'])
    if f is None:
        return {'ok': False, 'status': 404, 'error': 'no foothold %r on %s/%s' % (a['target'], kind, definition)}
    parts, why = E.protection_of(manager, a)
    if why:
        return {'ok': False, 'status': 422, 'error': why}
    level = float(level_v if level_v is not None else a['level_v'])
    abs_max = float(f.get('max_volts', -1.0) if f.get('max_volts') is not None else -1.0)
    key, host, out = board_key(kind, definition), socket.gethostname(), {}
    for which, v in (('baseline', 0.0), ('event', level)):
        deck, te = pin_deck(f, a, model, v, parts)
        res = (runner or NS.run)(deck, {})
        ev = {'area': area_name, 'model': model, 'level_v': v, 'net': a['target'], 'node': 'pin', 't_event': te, 'protected': ['pin'], 'role': which,
              'baseline': out.get('baseline', {}).get('run', ''), 'foothold': a['target'], 'pin_only': True,
              'foothold_max_v': abs_max, 'foothold_max_basis': f.get('drive_basis') or f.get('signal_basis') or ''}
        if parts:
            ev['protection'] = [p[0] for p in parts]
        out[which] = dict(res, run=SR.store(manager, key, deck, res, 'local', host, event=ev))
    if not (out['event'].get('ok') and out['baseline'].get('ok')):
        bad = out['event'] if not out['event'].get('ok') else out['baseline']
        return {'ok': False, 'status': 503 if 'refused' in bad else 422, 'error': bad.get('refused') or '; '.join(bad.get('errors') or []) or 'no vectors',
                'run': out['event']['run'], 'baseline': out['baseline']['run']}
    summary, rows, why = E.results(manager, out['event']['run'])
    return {'ok': not why, 'run': out['event']['run'], 'baseline': out['baseline']['run'], 'summary': summary, 'rows': rows, 'error': why}


def run_any(manager, area_name, model=None, level_v=None, runner=None):
    from pcb.custom import esd_events as E
    a = E._area(manager, area_name)
    if a is None:
        return {'ok': False, 'status': 404, 'error': 'no ESD area %r' % area_name}
    if a['definition_kind'] == 'layers':
        return E.run_event(manager, a['definition'], area_name, model, level_v, runner=runner)
    return run_pin_event(manager, a['definition_kind'], a['definition'], area_name, model, level_v, runner)
