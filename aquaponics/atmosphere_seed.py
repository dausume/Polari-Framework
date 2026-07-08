"""
@cross-cutting
@module aquaponics.atmosphere_seed
@tags @xc:bindings

Demo atmospheres (aqp-5): an open greenhouse, a ventilated grow tent,
and a sealed chamber — so the gas-exchange coupling has an
open/ventilated/sealed spread to exercise. Idempotent-by-name.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_MODULE_PLAN.md
"""

SEED_ATMOSPHERES = [
    {
        'name': 'open-greenhouse',
        'display_name': 'Open greenhouse',
        'description': 'Passively ventilated greenhouse — open air '
                       'for gas purposes.',
        'controlled': False, 'volume_m3': 0.0,
        'co2_ppm': 420.0, 'o2_pct': 20.95,
        'temperature_c': 24.0, 'relative_humidity_pct': 65.0,
        'pressure_kpa': 101.3, 'outside_co2_ppm': 420.0,
        'air_exchange_per_hour': 10.0,
        'light_ppfd_umol_m2_s': 450.0, 'photoperiod_hours': 14.0,
        'provenance_id': 'aqp-5 open reference',
    },
    {
        'name': 'ventilated-grow-tent',
        'display_name': 'Ventilated grow tent',
        'description': 'A 1.2m^3 grow tent with modest ventilation — '
                       'the plant measurably draws CO2 down but the '
                       'fan sustains it above the floor.',
        'controlled': True, 'volume_m3': 1.2,
        'co2_ppm': 420.0, 'o2_pct': 20.95,
        'temperature_c': 25.0, 'relative_humidity_pct': 55.0,
        'pressure_kpa': 101.3, 'outside_co2_ppm': 420.0,
        'air_exchange_per_hour': 2.0,
        'light_ppfd_umol_m2_s': 350.0, 'photoperiod_hours': 16.0,
        'provenance_id': 'aqp-5 controlled reference',
    },
    {
        'name': 'sealed-chamber',
        'display_name': 'Sealed growth chamber',
        'description': 'A sealed 0.5m^3 chamber, no ventilation — CO2 '
                       'depletes toward the photosynthesis floor.',
        'controlled': True, 'volume_m3': 0.5,
        'co2_ppm': 800.0, 'o2_pct': 20.95,
        'temperature_c': 23.0, 'relative_humidity_pct': 70.0,
        'pressure_kpa': 101.3, 'outside_co2_ppm': 420.0,
        'air_exchange_per_hour': 0.0,
        'light_ppfd_umol_m2_s': 250.0, 'photoperiod_hours': 18.0,
        'provenance_id': 'aqp-5 sealed reference',
    },
]
