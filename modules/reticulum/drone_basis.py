"""
@module reticulum.drone_basis

DRONE BRIDGE RELAYS (ret-1f addendum, Dustin 2026-08-13): a drone
carrying a radio payload can INTERMITTENTLY bridge a coverage gap —
fly out, loiter on station as a relay, fly home, recharge, repeat.
The sim answers whether that is feasible for a given gap and what
the duty cycle honestly looks like; the link is PERIODIC by nature
and pairs with store-and-forward (ret-7) for the dark intervals.

  DroneBridgeProfile   a drone+payload as a row: battery, cruise,
                       endurance, recharge, which radio it carries.
                       `flight_rules_confirmed` is the OPERATOR's
                       own assertion (the OperatorLicense idiom):
                       the software records it, REFUSES to plan
                       flights without it naming what is missing,
                       and makes NO legal claims — airspace rules
                       (line-of-sight, altitude, registration) are
                       jurisdiction-specific and the operator's to
                       confirm.

  drone_bridge_plan()  pure math: transit each way, on-station time
                       after a loiter reserve, bridges per day from
                       the charge cycle, duty cycle — every number's
                       basis in the evidence dict, refusals named.

@consumers reticulum.meshsim_placement (gapBridges),
           reticulum.reticulum_api (droneProfiles resolution)
@see modules/reticulum/operator_basis.py (the assertion idiom),
     plan §5q
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.meshsim_basis import TERRAIN_DISCLAIMER


def drone_bridge_plan(gap_distance_m, profile, loiter_reserve_pct=20):
    """Can THIS drone bridge THIS gap, and for how long per sortie?
    Returns {'ok': True, ...numbers + evidence} or {'ok': False,
    'refusal': {evidence, knob, action}}. The flight-rules assertion
    gates everything — a plan that assumes the airspace is a plan
    that gets someone fined."""
    if not profile.get('flight_rules_confirmed'):
        return {'ok': False, 'refusal': {
            'evidence': 'flight_rules_confirmed is False on profile '
                        '%r — no operator has asserted that flying '
                        'this bridge is permitted where it would fly'
                        % (profile.get('name'),),
            'knob': 'DroneBridgeProfile.flight_rules_confirmed (the '
                    'operator\'s own assertion, recorded with the '
                    'row; the software makes no legal claims)',
            'action': 'confirm the airspace rules for the actual '
                      'location (line-of-sight, altitude, '
                      'registration), record the assertion, then '
                      'plan',
        }}
    cruise = float(profile.get('cruise_speed_ms') or 0)
    endurance = float(profile.get('endurance_min') or 0)
    recharge = float(profile.get('recharge_min') or 0)
    if cruise <= 0 or endurance <= 0:
        return {'ok': False, 'refusal': {
            'evidence': 'profile lacks cruise speed or endurance — '
                        'no basis to plan',
            'knob': 'DroneBridgeProfile cruise_speed_ms / '
                    'endurance_min',
            'action': 'fill the row from the aircraft\'s actual '
                      'numbers (declared), then measure (ret-6 '
                      'spirit)',
        }}
    transit_min = (gap_distance_m / cruise) / 60.0
    reserve_min = endurance * loiter_reserve_pct / 100.0
    on_station = endurance - 2 * transit_min - reserve_min
    if on_station <= 0:
        return {'ok': False, 'refusal': {
            'evidence': 'gap %.0f m needs %.1f min transit each way; '
                        'with a %d%% reserve (%.1f min) nothing of '
                        'the %.0f min endurance remains on station'
                        % (gap_distance_m, transit_min,
                           loiter_reserve_pct, reserve_min,
                           endurance),
            'knob': 'a closer launch point, a faster/longer-endurance '
                    'profile, or a permanent node instead',
            'action': 'this gap is beyond an intermittent bridge — '
                      'place a node (sim A) or accept the dark',
        }}
    cycle_min = endurance + recharge
    bridges_per_day = int(1440 // cycle_min) if cycle_min > 0 else 0
    duty_pct = round(100.0 * on_station / cycle_min, 1) \
        if cycle_min > 0 else 0.0
    return {
        'ok': True,
        'intermittent': True,
        'transitMinEachWay': round(transit_min, 1),
        'onStationMin': round(on_station, 1),
        'cycleMin': round(cycle_min, 1),
        'bridgesPerDay': bridges_per_day,
        'dutyCyclePct': duty_pct,
        'note': ('a PERIODIC link: on station %.1f min of every '
                 '%.0f min cycle (%.1f%%). The dark intervals are '
                 'store-and-forward territory (ret-7) — queue for '
                 'the drone, burst while it loiters.'
                 % (on_station, cycle_min, duty_pct)),
        'evidence': {
            'gapDistanceM': gap_distance_m,
            'cruiseSpeedMs': cruise,
            'enduranceMin': endurance,
            'rechargeMin': recharge,
            'loiterReservePct': loiter_reserve_pct,
            'payloadDrawW': profile.get('payload_draw_w'),
            'payloadNote': 'payload draw recorded but NOT modelled '
                           'into endurance — derate is a measurement '
                           '(ret-6 spirit), not an estimate',
        },
        'assumptions': [
            'endurance/cruise are the profile\'s DECLARED numbers',
            'still-air transit; wind is terrain\'s sibling and '
            'equally unmodelled',
            TERRAIN_DISCLAIMER,
        ],
    }


class DroneBridgeProfile(treeObject):
    """One drone+payload configuration. flight_rules_confirmed
    defaults False and every plan against it refuses until the
    operator's assertion is recorded — the OperatorLicense idiom."""

    @treeObjectInit
    def __init__(self, name='', display_name='', battery_wh=0.0,
                 cruise_speed_ms=0.0, endurance_min=0.0,
                 recharge_min=0.0, payload_radio_model='',
                 payload_draw_w=0.0, flight_rules_confirmed=False,
                 confirmed_by='', confirmed_at='',
                 fidelity='declared', evidence_json='[]', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.battery_wh = battery_wh
        self.cruise_speed_ms = cruise_speed_ms
        self.endurance_min = endurance_min
        self.recharge_min = recharge_min
        # which DeviceModel row rides along as the relay radio.
        self.payload_radio_model = payload_radio_model
        self.payload_draw_w = payload_draw_w
        # the operator's OWN assertion that flying this bridge is
        # permitted where it flies — recorded with who/when, never
        # validated online, never a software legal claim.
        self.flight_rules_confirmed = flight_rules_confirmed
        self.confirmed_by = confirmed_by
        self.confirmed_at = confirmed_at
        self.fidelity = fidelity
        self.evidence_json = evidence_json
        self.notes = notes


#: One REFERENCE profile from Mavic-3-class published figures —
#: planning numbers, not a purchasable recommendation, and
#: flight_rules_confirmed stays False on purpose: the first plan a
#: user runs SHOWS the assertion refusal, which is the row teaching
#: the rule.
SEED_DRONE_BRIDGE_PROFILES = [
    {
        'name': 'generic-quadcopter-bridge',
        'display_name': 'Generic prosumer quadcopter bridge relay '
                        '(Mavic-3-class reference)',
        'battery_wh': 77.0,
        'cruise_speed_ms': 12.0,
        'endurance_min': 35.0,
        'recharge_min': 80.0,
        'payload_radio_model': 'generic-wifi-halow',
        'payload_draw_w': 4.0,
        'flight_rules_confirmed': False,
        'fidelity': 'declared',
        'evidence_json': json.dumps([
            {'fact': '77 Wh battery, 46 min max flight (no payload, '
                     'still air) — 35 min used here as the planning '
                     'endurance with a radio payload',
             'source': 'https://store.dji.com/product/dji-mavic-3-'
                       'intelligent-flight-battery + '
                       'https://www.dji.com/mavic-3-classic/specs '
                       '(fetched 2026-08-13)'},
            {'fact': 'cruise 12 m/s (DJI efficiency tests run '
                     '32.4-50.4 kph ≈ 9-14 m/s)',
             'source': 'https://www.dji.com/mavic-3-classic/specs'},
            {'fact': 'recharge ~70-96 min depending on charger — '
                     '80 min planning figure',
             'source': 'https://store.dji.com/product/dji-mavic-3-'
                       'intelligent-flight-battery'},
            {'fact': 'payload draw ~4 W (HaLow/LoRa module class) — '
                     'recorded, not yet modelled into endurance',
             'source': 'typical 802.11ah module draw; measure at '
                       'ret-6'},
        ]),
        'notes': 'REFERENCE CLASS — Mavic-3-class published figures '
                 'for planning, not a purchasable recommendation. '
                 'flight_rules_confirmed is FALSE on purpose: plans '
                 'refuse until the operator records their own '
                 'airspace assertion (line-of-sight, altitude, '
                 'registration are jurisdiction-specific and yours '
                 'to confirm).',
    },
]
