"""
@module climate.sim_binding_basis

co2-9 — THE PROOF THAT THESE ARE OBJECTS, NOT A PAGE.

`AtmosphereDefinition.outside_co2_ppm` (aquaponics) is a seeded
constant: 420.0. A greenhouse simulation running on it is running
on a number somebody typed. This module points it at the INGESTED
Mauna Loa record instead, so the ambient CO2 in a plant-growth
simulation is the CO2 the world actually had.

DIRECTION MATTERS. The binding lives here and PUSHES, rather than
aquaponics pulling from climate, for three reasons:

1. `climate` already requires `aquaponics` (it reuses the
   steady-state gas balance). A pull would make that circular.
2. `AtmosphereDefinition` needs no new field, so the seed
   field-addition gotcha never fires.
3. `pol modules drop climate` leaves aquaponics working exactly
   as it did before - the atmosphere rows keep whatever value was
   last written, and the binding rows that explain it go away
   with the module that made them.

WHAT A BINDING PROMISES, AND WHAT IT DOES NOT. It writes a
MEASURED value in place of a guessed one and records what it
replaced. It does NOT claim the greenhouse is in Hawaii: Mauna
Loa is a clean-air baseline, and a real greenhouse sits in a
local airshed that is usually higher. The binding says so on the
row rather than letting the precision of the number imply a
precision of place.

The seeded constant stays the FALLBACK. If the series has not
been ingested, the binding refuses and the simulation runs on the
constant it always used - never on a half-applied binding.

@consumers climate.climate_api, climate.climate_selftest,
polariServer
"""

import datetime

from objectTreeDecorators import treeObject, treeObjectInit

from composition.custom.data_refs import rows
from composition.custom.seed_upsert import upsert_seed_pairs

PROV = 'co2-9'

#: 'latest'      — the most recent observation in the series
#: 'year'        — the observation at a stated year (for
#:                 reproducing a historical run)
#: 'preindustrial' — the pre-industrial baseline, for a
#:                 counterfactual "what would this greenhouse have
#:                 done in 1750" run
BINDING_MODES = ('latest', 'year', 'preindustrial')


class AtmosphereSeriesBinding(treeObject):
    """One simulation input bound to one measured series.

    The row is the audit trail: which target field, which series,
    which mode, what was written, WHAT IT REPLACED, and when.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', target_class='',
                 target_row='', target_field='', series_ref='',
                 mode='latest', year=0.0, enabled=True,
                 last_applied_value=0.0, replaced_value=0.0,
                 last_applied_at='', last_source_year=0.0,
                 refusal='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: the class whose row this binding writes into. Named as
        #: data so a binding is not a hard-coded reference to
        #: aquaponics - any simulation input can be bound.
        self.target_class = target_class
        self.target_row = target_row
        self.target_field = target_field
        self.series_ref = series_ref
        self.mode = mode if mode in BINDING_MODES else 'latest'
        self.year = year
        self.enabled = enabled
        self.last_applied_value = last_applied_value
        #: WHAT THE SEEDED CONSTANT WAS. Kept so the binding is
        #: reversible and so a reader can see how far the guess
        #: was from the measurement.
        self.replaced_value = replaced_value
        self.last_applied_at = last_applied_at
        self.last_source_year = last_source_year
        self.refusal = refusal
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


SEED_ATMOSPHERE_BINDINGS = [
    {
        'name': 'bind-open-greenhouse-outside-co2',
        'display_name': 'Open greenhouse ambient CO2 -> Mauna Loa '
                        'record',
        'target_class': 'AtmosphereDefinition',
        'target_row': 'open-greenhouse',
        'target_field': 'outside_co2_ppm',
        'series_ref': 'co2-mauna-loa-annual',
        'mode': 'latest', 'year': 0.0, 'enabled': True,
        'last_applied_value': 0.0, 'replaced_value': 0.0,
        'last_applied_at': '', 'last_source_year': 0.0,
        'refusal': '', 'is_prior': True, 'provenance_id': PROV,
        'notes': 'The first real binding: a greenhouse simulation '
                 'whose ambient CO2 is the measured record rather '
                 'than a typed 420.0. Mauna Loa is a clean-air '
                 'BASELINE - a real greenhouse sits in a local '
                 'airshed that usually reads higher, so this '
                 'binding improves the number without claiming to '
                 'have measured the site.',
    },
    {
        'name': 'bind-ventilated-tent-outside-co2',
        'display_name': 'Ventilated grow tent ambient CO2 -> '
                        'Mauna Loa record',
        'target_class': 'AtmosphereDefinition',
        'target_row': 'ventilated-grow-tent',
        'target_field': 'outside_co2_ppm',
        'series_ref': 'co2-mauna-loa-annual',
        'mode': 'latest', 'year': 0.0, 'enabled': True,
        'last_applied_value': 0.0, 'replaced_value': 0.0,
        'last_applied_at': '', 'last_source_year': 0.0,
        'refusal': '', 'is_prior': True, 'provenance_id': PROV,
        'notes': 'A tent draws its make-up air from the room it '
                 'stands in, not from outdoors - so for an INDOOR '
                 'tent this binding is a lower bound, and the '
                 'co2_indoor coupling is the honest source. Left '
                 'enabled because the outdoor record is still a '
                 'better floor than a constant.',
    },
]


def _now():
    return datetime.datetime.now(datetime.timezone.utc)\
            .strftime('%Y-%m-%dT%H:%M:%SZ')


def _named(manager, class_name, name):
    for row in rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def resolve_value(manager, binding):
    """What value does this binding want to write? -> {ok, value,
    sourceYear} or a refusal naming the ingest that opens it."""
    from climate.custom.series_ingest import series_points, series_status
    series_ref = getattr(binding, 'series_ref', '')
    status = series_status(manager, series_ref)
    if not status.get('ok'):
        return {'ok': False, 'refusal': status.get('refusal', '')}
    points = series_points(manager, series_ref)
    if not points:
        return {'ok': False,
                'refusal': (f'series {series_ref!r} reports '
                            f'ingested but has no observations')}
    mode = getattr(binding, 'mode', 'latest')
    if mode == 'latest':
        point = points[-1]
    elif mode == 'preindustrial':
        target = 1750.0
        point = min(points, key=lambda p: abs(p['year'] - target))
        if abs(point['year'] - target) > 100.0:
            return {'ok': False,
                    'refusal': (f'no observation within 100 years '
                                f'of {target:.0f} in '
                                f'{series_ref!r} - the '
                                f'instrumental record does not '
                                f'reach pre-industrial; bind the '
                                f'ice-core series for that')}
    elif mode != 'year':
        # The constructor coerces an unknown mode to 'latest', so
        # this is only reachable for a row hydrated without it -
        # and silently applying year-semantics with year=0.0 would
        # bind a simulation to whatever observation sits nearest
        # the year zero. Refuse by name instead.
        return {'ok': False,
                'refusal': (f'binding mode {mode!r} is not one of '
                            f'{", ".join(BINDING_MODES)}')}
    else:
        want = float(getattr(binding, 'year', 0.0) or 0.0)
        point = min(points, key=lambda p: abs(p['year'] - want))
        if abs(point['year'] - want) > 5.0:
            return {'ok': False,
                    'refusal': (f'nearest observation to {want:.0f} '
                                f'is {point["year"]:.0f}, more '
                                f'than 5 years away')}
    return {'ok': True, 'value': point['value'],
            'sourceYear': point['year'],
            'uncertainty': point.get('uncertainty', 0.0)}


def apply_binding(manager, binding, dry_run=False):
    """Write one binding. Refusals leave the target UNTOUCHED, so
    a simulation never runs on a half-applied binding."""
    name = getattr(binding, 'name', '?')
    if not getattr(binding, 'enabled', True):
        return {'ok': False, 'binding': name,
                'refusal': 'binding is disabled'}
    target = _named(manager, getattr(binding, 'target_class', ''),
                    getattr(binding, 'target_row', ''))
    if target is None:
        return {'ok': False, 'binding': name,
                'refusal': (f'no '
                            f'{getattr(binding, "target_class", "?")}'
                            f' row named '
                            f'{getattr(binding, "target_row", "?")!r}'
                            f' - is the owning module enabled?')}
    field = getattr(binding, 'target_field', '')
    if not hasattr(target, field):
        return {'ok': False, 'binding': name,
                'refusal': (f'target row has no field {field!r}')}

    resolved = resolve_value(manager, binding)
    if not resolved.get('ok'):
        binding.refusal = resolved.get('refusal', '')
        return {'ok': False, 'binding': name,
                'refusal': resolved.get('refusal', ''),
                'note': ('the target keeps its previous value - a '
                         'refused binding never half-applies')}

    previous = getattr(target, field, 0.0)
    new_value = resolved['value']
    if dry_run:
        return {'ok': True, 'binding': name, 'dryRun': True,
                'wouldWrite': new_value, 'currentValue': previous,
                'sourceYear': resolved['sourceYear']}

    setattr(target, field, new_value)
    binding.last_applied_value = new_value
    # Only record the ORIGINAL constant the first time, so a
    # re-apply cannot overwrite the provenance of what was there
    # before the first binding ever ran.
    if not getattr(binding, 'last_applied_at', ''):
        binding.replaced_value = previous
    binding.last_applied_at = _now()
    binding.last_source_year = resolved['sourceYear']
    binding.refusal = ''
    db = getattr(manager, 'db', None)
    if db is not None:
        for row in (target, binding):
            try:
                db.saveInstanceInDB(row)
            except Exception:
                pass
    return {'ok': True, 'binding': name,
            'target': f'{getattr(binding, "target_class", "")}.'
                      f'{getattr(binding, "target_row", "")}.'
                      f'{field}',
            'previousValue': previous, 'appliedValue': new_value,
            'delta': new_value - previous,
            'sourceYear': resolved['sourceYear'],
            'series': getattr(binding, 'series_ref', ''),
            'note': ('the simulation input is now a MEASUREMENT '
                     'with a source, not a seeded constant')}


def apply_all(manager, dry_run=False):
    """Apply every enabled binding. Reports refusals as results,
    never as silence."""
    out = [apply_binding(manager, b, dry_run=dry_run)
           for b in rows(manager, 'AtmosphereSeriesBinding')]
    applied = [r for r in out if r.get('ok')]
    return {'ok': True, 'applied': len(applied),
            'refused': len(out) - len(applied), 'results': out,
            'note': ('a refused binding leaves its target on the '
                     'seeded constant - that is the fallback '
                     'working, not a failure to report')}


def binding_report(manager):
    """What is bound to what, and what did it replace."""
    out = []
    for b in rows(manager, 'AtmosphereSeriesBinding'):
        out.append({
            'name': getattr(b, 'name', ''),
            'displayName': getattr(b, 'display_name', ''),
            'target': f'{getattr(b, "target_class", "")}.'
                      f'{getattr(b, "target_row", "")}.'
                      f'{getattr(b, "target_field", "")}',
            'series': getattr(b, 'series_ref', ''),
            'mode': getattr(b, 'mode', ''),
            'enabled': bool(getattr(b, 'enabled', True)),
            'appliedValue': getattr(b, 'last_applied_value', 0.0),
            'replacedValue': getattr(b, 'replaced_value', 0.0),
            'sourceYear': getattr(b, 'last_source_year', 0.0),
            'appliedAt': getattr(b, 'last_applied_at', ''),
            'refusal': getattr(b, 'refusal', ''),
            'notes': getattr(b, 'notes', ''),
        })
    return {'ok': True, 'bindings': out, 'count': len(out),
            'note': ('replacedValue is the seeded constant this '
                     'binding displaced - kept so the binding is '
                     'reversible and the gap between guess and '
                     'measurement stays visible')}


def seed_atmosphere_bindings(manager):
    return upsert_seed_pairs(manager, [
        ('AtmosphereSeriesBinding', AtmosphereSeriesBinding,
         SEED_ATMOSPHERE_BINDINGS),
    ], tag='ClimateBindingSeed')
