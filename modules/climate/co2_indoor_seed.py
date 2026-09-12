"""
@module climate.co2_indoor_seed

THE COUPLED INDOOR MODEL (CO2_HEALTH_PLAN.md §7) — and ONE equation
serving two disciplines.

KEY: the indoor CO2 mass balance ALREADY EXISTED in this codebase.
aquaponics.environment_gas_exchange solves the steady state for a
crop that DEPLETES CO2 from a ventilated volume:

    steady = outside_ppm - demand / ventilation_capacity

A room full of PEOPLE is that same equation with the sign flipped:

    steady = outside_ppm + emission / ventilation_capacity

So this module does NOT write a second CO2 mass balance. It writes
the GENERALIZED SIGNED-SOURCE solver both callers can use —
`steady_state_ppm`, where a POSITIVE source is an emission (people,
a flame, a fermenter) and a NEGATIVE source is a depletion (a crop).
`guard_two_callers` is the standing proof that the greenhouse and
the classroom are one equation: the offsets must be exact mirrors.

The per-person emission rate is a NAMED PRIOR, not a measurement.
`person_co2_mg_per_day` derives it from the commonly cited relation
of about 0.0052 L/s per met per unit DuBois body-surface-area —
roughly 0.3 L/min at 1.2 met for an average adult — and its
replaces_with is 'measure with a CO2 meter in a room of known
volume and occupancy'. Every room archetype seeded here carries the
same retirement condition. An archetype is a starting point for a
question, never an answer about a real room.

@consumers climate.co2_projection, climate.climate_views_seed,
climate.climate_api, aquaponics.custom.atmosphere_analysis (may adopt
steady_state_ppm), polariServer (seed pass)
"""

from aquaponics.custom.atmosphere_analysis import CO2_MG_PER_M3_PER_PPM
from moduleService.seed_upsert import upsert_seed_pairs
from climate.climate_basis import IndoorSpaceProfile

#: CO2 gas density, ~1.80 g/L at 25 C and 101 kPa. NOT the same
#: constant as CO2_MG_PER_M3_PER_PPM (1.8 mg/m3 per ppm) — that one
#: converts a mixing ratio to a mass concentration in air; this one
#: is the density of the pure gas a person exhales. They collide
#: numerically at 1.8 by coincidence of units, and using either in
#: the other's place is a silent 1000x class of error.
CO2_G_PER_L = 1.80

#: Adult CO2 generation is commonly taken as ~0.0052 L/s per met
#: per unit DuBois body-surface-area, i.e. roughly 0.3 L/min at
#: 1.2 met for an average adult — so ~0.25 L/min at 1 met. A NAMED
#: PRIOR: replaces_with = 'measure with a CO2 meter in a room of
#: known volume and occupancy'.
CO2_L_PER_MIN_PER_MET = 0.25

_MIN_PER_DAY = 60.0 * 24.0

#: Every archetype below retires the same way.
_MEASURE_IT = ('measure this room with a CO2 meter (volume, '
               'occupancy and ACH together)')


def person_co2_mg_per_day(activity_met=1.2,
                          l_per_min_at_1_met=CO2_L_PER_MIN_PER_MET):
    """One adult's CO2 emission, mg/day, scaled linearly by met.

    A PRIOR, not a measurement. Returns 0.0 rather than raising for
    unusable inputs — a caller that gets 0.0 emission from a
    populated room has been told something is wrong with its
    inputs, not handed a plausible lie.
    """
    try:
        met = float(activity_met)
        l_min = float(l_per_min_at_1_met)
    except (TypeError, ValueError):
        return 0.0
    if met <= 0.0 or l_min <= 0.0:
        return 0.0
    return l_min * met * _MIN_PER_DAY * CO2_G_PER_L * 1000.0


def steady_state_ppm(outside_ppm, source_mg_per_day, volume_m3,
                     air_changes_per_hour):
    """Steady-state indoor CO2 for a SIGNED source in a ventilated
    volume — the one equation, both callers.

    POSITIVE source_mg_per_day = emission (people) and raises the
    steady state above outdoor; NEGATIVE = depletion (a crop) and
    lowers it. The aquaponics form is this function with a negative
    source.
    """
    try:
        outside = float(outside_ppm)
        source = float(source_mg_per_day)
        volume = float(volume_m3)
        ach = float(air_changes_per_hour)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'outside_ppm, source_mg_per_day, '
                           'volume_m3 and air_changes_per_hour must '
                           'all be numbers'}
    if volume <= 0.0:
        return {'ok': False,
                'refusal': 'volume_m3 must be > 0 — a source with '
                           'no air to mix into has no concentration '
                           'at all, let alone a steady one'}
    if ach <= 0.0:
        return {'ok': False,
                'refusal': 'air_changes_per_hour must be > 0 — a '
                           'SEALED room has NO steady state: with '
                           'no ventilation the concentration '
                           'accumulates (or depletes) without '
                           'bound, so the honest answer is a '
                           'time-to-level, not a level. The sealed '
                           'case is a different question and needs '
                           'the transient solver, not this one'}
    vent_mg_per_ppm_day = (ach * volume * 24.0
                           * CO2_MG_PER_M3_PER_PPM)
    offset = source / vent_mg_per_ppm_day
    return {
        'ok': True,
        'steadyStatePpm': outside + offset,
        'ventilationCapacityMgPerPpmDay': vent_mg_per_ppm_day,
        'offsetPpm': offset,
        'outsidePpm': outside,
    }


SEED_INDOOR_SPACES = [
    {
        'name': 'bedroom-overnight-closed',
        'setting_ref': 'outdoor-urban-residential',
        'display_name': 'Bedroom, two sleepers, door and window '
                        'closed',
        'volume_m3': 30.0,
        'occupancy': 2.0,
        'activity_met': 0.8,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 0.3,
        'atmosphere_ref': '',
        'category': 'residential',
        'basis': 'ARCHETYPE, not a measurement: a typical small '
                 'bedroom volume with two sleeping adults and the '
                 'infiltration-only air change rate of a closed '
                 'modern room. The worst common case — lowest '
                 'ventilation, longest continuous exposure, and '
                 'the one room most people occupy for a third of '
                 'every day.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-5',
        'notes': 'If any archetype here is worth measuring first, '
                 'it is this one: the offset is largest and the '
                 'exposure is longest.',
    },
    {
        'name': 'classroom-occupied',
        'setting_ref': 'outdoor-urban-residential',
        'display_name': 'Classroom, 25 occupants, lesson in '
                        'progress',
        'volume_m3': 180.0,
        'occupancy': 25.0,
        'activity_met': 1.2,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 1.5,
        'atmosphere_ref': '',
        'category': 'education',
        'basis': 'ARCHETYPE, not a measurement: a standard '
                 'classroom volume at typical class size, seated '
                 'activity, with mixed mechanical and window '
                 'ventilation.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-5',
        'notes': 'High occupant density per unit volume — the '
                 'archetype where the ventilation knob moves the '
                 'answer most.',
    },
    {
        'name': 'open-plan-office',
        'setting_ref': 'outdoor-urban-core',
        'display_name': 'Open-plan office, 25 occupants',
        'volume_m3': 500.0,
        'occupancy': 25.0,
        'activity_met': 1.2,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 2.0,
        'atmosphere_ref': '',
        'category': 'workplace',
        'basis': 'ARCHETYPE, not a measurement: mechanically '
                 'ventilated open floor, seated desk work.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-5',
        'notes': 'Same headcount as the classroom in nearly three '
                 'times the volume with more ventilation — the '
                 'pair shows the offset is about air per person, '
                 'not headcount.',
    },
    {
        'name': 'car-cabin-recirculate',
        'setting_ref': 'outdoor-street-canyon',
        'display_name': 'Car cabin, two occupants, recirculation '
                        'on',
        'volume_m3': 3.0,
        'occupancy': 2.0,
        'activity_met': 1.0,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 6.0,
        'atmosphere_ref': '',
        'category': 'transport',
        'basis': 'ARCHETYPE, not a measurement: a small cabin '
                 'with climate control set to recirculate, so the '
                 'only fresh air is body leakage around the door '
                 'and vent seals. THE ACH WAS CORRECTED FROM 0.5 '
                 'TO 6.0 during co2-5: the solver returned a '
                 'steady state above 20000 ppm, which is far '
                 'above any published cabin measurement and would '
                 'have shipped a number readers quote. The '
                 'equation was right and the prior was wrong - '
                 'the implausible output is what exposed it. 6.0 '
                 'is still a PRIOR spanning the wide range real '
                 'cabins show with speed and seal condition, and '
                 'it is the row on this list most in need of a '
                 'meter.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-5',
        'notes': 'The smallest volume per person on this list and '
                 'the archetype least to be trusted. Its history '
                 'is the argument for keeping priors visible: a '
                 '0.5 ACH guess produced 20000 ppm, the '
                 'implausibility was caught before it shipped, '
                 'and the ACH was raised to 6.0. No measurement '
                 'has been taken - only the guess improved.',
    },
    {
        'name': 'public-building-well-ventilated',
        'setting_ref': 'outdoor-urban-core',
        'display_name': 'Public building, 50 occupants, '
                        'well ventilated',
        'volume_m3': 1000.0,
        'occupancy': 50.0,
        'activity_met': 1.4,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 4.0,
        'atmosphere_ref': '',
        'category': 'public',
        'basis': 'ARCHETYPE, not a measurement: a large hall with '
                 'designed mechanical ventilation, occupants '
                 'standing and moving.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-5',
        'notes': 'The good case, included so the page can show '
                 'that the indoor offset is a VENTILATION property '
                 'and not an inevitability.',
    },
    {
        'name': 'bedroom-window-ajar',
        'setting_ref': 'outdoor-urban-residential',
        'display_name': 'Bedroom, two sleepers, window ajar',
        'volume_m3': 30.0,
        'occupancy': 2.0,
        'activity_met': 0.8,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 2.0,
        'atmosphere_ref': '',
        'category': 'residential',
        'basis': 'THE SAME ROOM as bedroom-overnight-closed with '
                 'one window open a crack - identical volume, '
                 'identical occupants, ACH raised from 0.3 to 2.0.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-E',
        'notes': 'THE CONTROL FOR THE WHOLE PAGE. Every other '
                 'number here describes a problem; this row is the '
                 'intervention, and it is a window latch. Compare '
                 'it against the closed row to read the '
                 'ventilation knob directly.',
    },
    {
        'name': 'living-room-evening',
        'setting_ref': 'outdoor-urban-residential',
        'display_name': 'Living room, four people, evening',
        'volume_m3': 45.0,
        'occupancy': 4.0,
        'activity_met': 1.1,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 0.8,
        'atmosphere_ref': '',
        'category': 'residential',
        'basis': 'ARCHETYPE: a family room in a reasonably sealed '
                 'home, doors closed, no mechanical ventilation.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-E',
        'notes': 'RESPIRATION ONLY. A gas hob, a wood burner or an '
                 'unflued heater is a second, larger CO2 source '
                 'this model does not include - steady_state_ppm '
                 'takes a signed source term and would accept one, '
                 'but no combustion prior is seeded and inventing '
                 'one would be guessing.',
    },
    {
        'name': 'meeting-room-crowded',
        'setting_ref': 'outdoor-urban-core',
        'display_name': 'Small meeting room, 8 people, door shut',
        'volume_m3': 35.0,
        'occupancy': 8.0,
        'activity_met': 1.2,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 1.0,
        'atmosphere_ref': '',
        'category': 'workplace',
        'basis': 'ARCHETYPE: the highest occupant density per unit '
                 'volume in normal working life - a small room '
                 'sized for four holding eight, with the door shut '
                 'and ventilation designed for the smaller number.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-E',
        'notes': 'The office archetype most likely to be measured '
                 'in the wild, because it is where people notice '
                 'the stuffiness themselves.',
    },
    {
        'name': 'classroom-mechanically-ventilated',
        'setting_ref': 'outdoor-urban-residential',
        'display_name': 'Classroom, 25 occupants, mechanical '
                        'ventilation running',
        'volume_m3': 180.0,
        'occupancy': 25.0,
        'activity_met': 1.2,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 4.0,
        'atmosphere_ref': '',
        'category': 'education',
        'basis': 'THE SAME CLASSROOM with its ventilation actually '
                 'commissioned and running - ACH 1.5 to 4.0.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-E',
        'notes': 'The paired comparison that shows the difference '
                 'is a building-services decision, not a fact of '
                 'nature.',
    },
    {
        'name': 'gym-exercising',
        'setting_ref': 'outdoor-urban-core',
        'display_name': 'Gym floor, 15 people exercising',
        'volume_m3': 400.0,
        'occupancy': 15.0,
        'activity_met': 5.0,
        'co2_per_person_l_min': CO2_L_PER_MIN_PER_MET,
        'air_changes_per_hour': 3.0,
        'atmosphere_ref': '',
        'category': 'leisure',
        'basis': 'ARCHETYPE: moderate-to-vigorous exercise at '
                 'about 5 met, which raises CO2 output roughly '
                 'fourfold over seated work.',
        'replaces_with': _MEASURE_IT,
        'is_prior': True,
        'provenance_id': 'co2-E',
        'notes': 'THE ACTIVITY TERM, isolated: same order of '
                 'occupancy as a classroom in more than twice the '
                 'volume, yet comparable levels - because met '
                 'rate, not headcount, is doing the work. It is '
                 'also the one room where occupants are '
                 'deliberately hyperventilating, so the exposure '
                 'per person is higher than the room level alone '
                 'suggests.',
    },
]


def seed_indoor_spaces(manager):
    return upsert_seed_pairs(
        manager,
        [('IndoorSpaceProfile', IndoorSpaceProfile,
          SEED_INDOOR_SPACES)],
        tag='ClimateIndoorSeed')


def _f(row, attr, default=0.0):
    try:
        return float(getattr(row, attr, default))
    except (TypeError, ValueError):
        return default


def space_source_mg_per_day(space_row):
    """(total mg/day for the room, mg/day per person)."""
    per_person_l_min = _f(space_row, 'co2_per_person_l_min')
    if per_person_l_min <= 0.0:
        per_person_l_min = CO2_L_PER_MIN_PER_MET
    per_person = person_co2_mg_per_day(
        activity_met=_f(space_row, 'activity_met', 1.2),
        l_per_min_at_1_met=per_person_l_min)
    return per_person * _f(space_row, 'occupancy'), per_person


def space_offset(space_row, outside_ppm):
    """This room's steady-state indoor ppm and its offset above the
    outdoor background. Refusals are returned verbatim."""
    volume = _f(space_row, 'volume_m3')
    ach = _f(space_row, 'air_changes_per_hour')
    source, per_person = space_source_mg_per_day(space_row)
    solved = steady_state_ppm(outside_ppm, source, volume, ach)
    if not solved.get('ok'):
        return solved
    return {
        'ok': True,
        'space': getattr(space_row, 'name', ''),
        'displayName': getattr(space_row, 'display_name', '')
        or getattr(space_row, 'name', ''),
        'outsidePpm': solved['outsidePpm'],
        'indoorPpm': solved['steadyStatePpm'],
        'offsetPpm': solved['offsetPpm'],
        'occupancy': _f(space_row, 'occupancy'),
        'activityMet': _f(space_row, 'activity_met', 1.2),
        'volumeM3': volume,
        'airChangesPerHour': ach,
        'perPersonMgPerDay': per_person,
        'sourceMgPerDay': source,
        'ventilationCapacityMgPerPpmDay':
            solved['ventilationCapacityMgPerPpmDay'],
        'note': 'Steady state, not a peak: a room reaches this '
                'after several air-change times, and the '
                'per-person emission is a PRIOR (replaces_with: '
                'measure with a CO2 meter in a room of known '
                'volume and occupancy).',
    }


def ventilation_knob(space_row, outside_ppm, factor=2.0):
    """What `factor` x the ventilation buys, in ppm. The knob the
    page needs so the reader can act instead of only worry."""
    try:
        mult = float(factor)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'factor must be a number'}
    if mult <= 0.0:
        return {'ok': False,
                'refusal': 'factor must be > 0 — a factor of zero '
                           'seals the room, and a sealed room has '
                           'no steady state to compare against'}
    volume = _f(space_row, 'volume_m3')
    base_ach = _f(space_row, 'air_changes_per_hour')
    source, _per_person = space_source_mg_per_day(space_row)
    base = steady_state_ppm(outside_ppm, source, volume, base_ach)
    if not base.get('ok'):
        return base
    new_ach = base_ach * mult
    new = steady_state_ppm(outside_ppm, source, volume, new_ach)
    if not new.get('ok'):
        return new
    return {
        'ok': True,
        'baseAch': base_ach,
        'newAch': new_ach,
        'basePpm': base['steadyStatePpm'],
        'newPpm': new['steadyStatePpm'],
        'deltaPpm': new['steadyStatePpm'] - base['steadyStatePpm'],
    }


def guard_two_callers(outside_ppm=420.0, volume_m3=100.0, ach=1.0,
                      magnitude_mg_day=5.0e5):
    """THE GUARD: the greenhouse and the classroom are the SAME
    equation.

    A positive source (people emitting) and a negative source (a
    crop depleting) of equal magnitude must produce offsets that
    are exact mirrors about the outdoor background. If they ever
    stop mirroring, someone has written a second mass balance —
    which is the duplication this module exists to prevent.
    """
    plus = steady_state_ppm(outside_ppm, magnitude_mg_day,
                            volume_m3, ach)
    minus = steady_state_ppm(outside_ppm, -magnitude_mg_day,
                             volume_m3, ach)
    if not plus.get('ok'):
        return plus
    if not minus.get('ok'):
        return minus
    plus_offset = plus['steadyStatePpm'] - plus['outsidePpm']
    minus_offset = minus['steadyStatePpm'] - minus['outsidePpm']
    symmetric = abs(plus_offset + minus_offset) <= 1e-9
    return {
        'ok': bool(symmetric),
        'plusOffset': plus_offset,
        'minusOffset': minus_offset,
        'symmetric': bool(symmetric),
        'note': 'one equation, two callers - a sign flip is the '
                'only difference between a crop depleting CO2 and '
                'people emitting it',
    }
