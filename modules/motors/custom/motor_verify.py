"""
@module motors.custom.motor_verify

mag-7 remainder (2026-07-30): THE VERIFICATION-RUN RECORDING SEAM.
MotorVerificationRun rows are NEVER seeded — they are observed state,
and this module is the one honest way they come into existence:

- record_verification_run holds the derivations a flat CRUDE POST
  can't (the odoo_orders argument): clock_error_s DERIVES from the
  design's own drive rate (missed steps / rate_hz — M0's metric is
  time progression itself), duration defaults to commanded/rate and
  says so, names are allocated per design, and impossible claims
  (more steps than commanded, unknown kind) REFUSE instead of
  persisting nonsense.
- verification_summary is what made-and-measured reads: only rows
  with kind='measured' count toward it (a sim replay recorded here
  is provenance, not proof — the payload says so on every record).

@consumers motors.motor_api, motors.motors_selftest
"""

import json

from magnetics.custom.magnet_analysis import _named, _rows

RUN_KINDS = ('sim-quasi-static', 'measured')


def _class_for(manager, class_name):
    typing = getattr(manager, 'objectTypingDict', {}).get(class_name)
    if typing is None:
        return None
    try:
        return typing.getCreateMethod()
    except Exception:  # noqa: BLE001 — treat as not-instantiable
        return None


def _design_rate_hz(design):
    try:
        drive = json.loads(getattr(design, 'drive_json', '{}') or '{}')
    except (TypeError, ValueError):
        drive = {}
    try:
        return float(drive.get('rate_hz', 1.0)) or 1.0
    except (TypeError, ValueError):
        return 1.0


def record_verification_run(manager, design_name, kind,
                            steps_commanded, steps_taken,
                            duration_s=None, notes=''):
    """Create ONE MotorVerificationRun row with honest derivations.
    Returns the recorded payload, or a refusal explaining exactly
    which claim didn't hold."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no MotorDesignDefinition named '
                           f'"{design_name}"'}
    if kind not in RUN_KINDS:
        return {'ok': False,
                'refusal': f'kind must be one of {RUN_KINDS} — got '
                           f'"{kind}" (only "measured" rows earn '
                           f'made-and-measured)'}
    try:
        commanded = int(steps_commanded)
        taken = int(steps_taken)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'steps_commanded/steps_taken must be '
                           'integers'}
    if commanded < 1:
        return {'ok': False,
                'refusal': 'steps_commanded must be >= 1 — an empty '
                           'run verifies nothing'}
    if not (0 <= taken <= commanded):
        return {'ok': False,
                'refusal': f'steps_taken {taken} outside '
                           f'[0, {commanded}] — a motor cannot take '
                           f'more steps than were commanded'}
    cls = _class_for(manager, 'MotorVerificationRun')
    if cls is None:
        return {'ok': False,
                'refusal': 'MotorVerificationRun is not in the '
                           'object tree — is the motors module '
                           'enabled?'}
    rate = _design_rate_hz(design)
    missed = commanded - taken
    clock_error_s = round(missed / rate, 4)
    derivation_notes = []
    if duration_s is None:
        duration_s = round(commanded / rate, 4)
        derivation_notes.append(
            f'duration defaulted to commanded/rate '
            f'({commanded}/{rate} Hz) — measure it on real runs')
    existing = [r for r in _rows(manager, 'MotorVerificationRun')
                if getattr(r, 'design_ref', '') == design_name]
    row_name = f'{design_name}-run-{len(existing) + 1}'
    taken_names = {getattr(r, 'name', '')
                   for r in _rows(manager, 'MotorVerificationRun')}
    bump = len(existing) + 1
    while row_name in taken_names:
        bump += 1
        row_name = f'{design_name}-run-{bump}'
    all_notes = '; '.join(
        ([notes] if notes else []) + derivation_notes)
    cls(manager=manager, name=row_name, design_ref=design_name,
        kind=kind, steps_commanded=commanded, steps_taken=taken,
        duration_s=float(duration_s), clock_error_s=clock_error_s,
        notes=all_notes)
    return {'ok': True, 'run': {
                'name': row_name, 'design': design_name,
                'kind': kind, 'stepsCommanded': commanded,
                'stepsTaken': taken, 'missedSteps': missed,
                'durationS': float(duration_s),
                'clockErrorS': clock_error_s, 'notes': all_notes},
            'honesty': ('a sim run is provenance, not proof — only '
                        'measured rows count toward made-and-'
                        'measured'
                        if kind != 'measured' else
                        'measured run recorded — it now counts '
                        'toward made-and-measured')}


def verification_summary(manager, design_name):
    """Every recorded run for a design + the made-and-measured
    verdict the business gate reads: EARNED by measured rows only,
    never declared."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no MotorDesignDefinition named '
                           f'"{design_name}"'}
    runs = [r for r in _rows(manager, 'MotorVerificationRun')
            if getattr(r, 'design_ref', '') == design_name]
    entries = []
    for r in runs:
        entries.append({
            'name': getattr(r, 'name', ''),
            'kind': getattr(r, 'kind', ''),
            'stepsCommanded': getattr(r, 'steps_commanded', 0),
            'stepsTaken': getattr(r, 'steps_taken', 0),
            'durationS': getattr(r, 'duration_s', 0.0),
            'clockErrorS': getattr(r, 'clock_error_s', 0.0),
            'notes': getattr(r, 'notes', '')})
    entries.sort(key=lambda e: e['name'])
    measured = [e for e in entries if e['kind'] == 'measured']
    return {'ok': True, 'design': design_name, 'runs': entries,
            'count': len(entries),
            'measuredCount': len(measured),
            'simCount': len(entries) - len(measured),
            'madeAndMeasured': len(measured) > 0,
            'honesty': ('no measured run yet — the design stays '
                        'below made-and-measured no matter how many '
                        'sim replays are recorded'
                        if not measured else
                        f'{len(measured)} measured run(s) on '
                        f'record — clock error is the quality '
                        f'metric, read it, not just the flag')}
