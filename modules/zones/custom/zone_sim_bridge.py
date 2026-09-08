"""
@module zones.custom.zone_sim_bridge

Real Constraints -> Simulation (Dustin 2026-07-17): zones captured in
AR are "Real Constraints Mode" — the basis for running simulations
and mapping them into reality. This bridge is how a committed zone
becomes simulation input:

  zone_constraints        — the zone's reality as numbers: footprint
                            area, height, volume, perimeter,
                            calibration state, site/room membership.
  ensure_zone_sim_space   — a persisted SimSpaceDefinition
                            ('<zone>-space', xr_mode 'both') so the
                            zone IS a sim space (they will act as sim
                            spaces down the line); its configured
                            interface is the rooms/zones board.
  ensure_zone_ic_interface— an InitialConditionInterfaceDefinition
                            ('zone-ic--<zone>', choicePreset) whose
                            single choice applies the constraints as
                            setParams — so the real constraints flow
                            into the EXISTING validate -> create-run
                            -> step-0 override path (and the XR
                            CONDITIONS panel) with no new plumbing.

Idempotent by deterministic names; constraint values are re-derived
on every call (recapture/recalibration propagates).

@consumers zones.zones_api, XR zone capture ("Swap Modes")
@see /AR_ZONE_CAPTURE_PLAN.md
"""

import json

from scoring.worldview_elections_basis import _by_name
from zones.custom.zone_geometry import (estimate_zone, point_distances,
                                 _zone)


def _persist(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass  # in-memory managers (selftests) have no db


def _insert(manager, class_name, row):
    table = manager.objectTables.setdefault(class_name, {})
    if not any(existing is row for existing in table.values()):
        table[row.name] = row
    _persist(manager, row)
    return row


def zone_constraints(manager, zone_name):
    """The zone's reality as IC-shaped numbers."""
    zone = _zone(manager, zone_name)
    if zone is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'",
                'knownZones': sorted(
                    _by_name(manager, 'ZoneDefinition'))}
    estimate = estimate_zone(manager, zone_name)
    if not estimate.get('ok'):
        return {'ok': False,
                'error': 'zone has no usable estimate — capture '
                         'enough points first',
                'estimate': estimate}
    distances = point_distances(manager, zone_name)
    constraints = {
        'zone_footprint_area_m2': estimate.get(
            'groundAreaM2', estimate.get('surfaceAreaM2', 0.0)),
        'zone_height_m': estimate.get('heightM',
                                      estimate.get('planeHeightM',
                                                   0.0)),
        'zone_volume_m3': estimate.get('volumeM3', 0.0),
        'zone_perimeter_m': distances.get('perimeterM', 0.0)
        if distances.get('ok') else 0.0,
        'zone_scale_correction': estimate.get('scaleCorrection',
                                              1.0),
    }
    return {'ok': True, 'zone': zone_name,
            'model': estimate.get('model', ''),
            'calibrated': estimate.get('calibrated', False),
            'captureMode': getattr(zone, 'capture_mode', ''),
            'zoneRole': getattr(zone, 'zone_role', ''),
            'siteName': getattr(zone, 'site_name', ''),
            'roomZoneName': getattr(zone, 'room_zone_name', ''),
            'constraints': constraints,
            'warnings': estimate.get('warnings', [])}


def ensure_zone_sim_space(manager, zone_name):
    """The zone AS a sim space: a persisted SimSpaceDefinition named
    '<zone>-space' (pot_scene precedent, but a real durable row —
    zones are captured reality, not derived visuals)."""
    report = zone_constraints(manager, zone_name)
    if not report.get('ok'):
        return report
    from simSpace.sim_space_definition import SimSpaceDefinition
    space_name = f'{zone_name}-space'
    description = (
        'Captured real-world zone (Real Constraints Mode): '
        f"{report['captureMode']} capture, "
        f"area {report['constraints']['zone_footprint_area_m2']:.3f}"
        ' m², volume '
        f"{report['constraints']['zone_volume_m3']:.3f} m³. Zone "
        'geometry renders in the capture view; this space carries '
        'the zone identity for simulations mapped into reality.')
    interfaces = json.dumps([{
        'componentName': 'zones-board', 'inputs': {},
        'label': 'Rooms / zones board'}])
    existing = _by_name(manager, 'SimSpaceDefinition').get(space_name)
    if existing is not None:
        existing.description = description
        existing.configured_interfaces_json = interfaces
        _persist(manager, existing)
        return {'ok': True, 'simSpace': space_name,
                'created': False}
    row = SimSpaceDefinition(
        name=space_name,
        description=description,
        dimensionality='3d',
        coordinate_system='math',
        definition=json.dumps({'freestandingOnly': True,
                               'freestanding': []}),
        category='zones',
        owning_module='zones',
        xr_mode='both',
        xr_framing='inside',
        configured_interfaces_json=interfaces,
        manager=manager)
    _insert(manager, 'SimSpaceDefinition', row)
    return {'ok': True, 'simSpace': space_name, 'created': True}


def ensure_zone_ic_interface(manager, zone_name,
                             target_simulation_ref='',
                             target_class_name=''):
    """Real constraints as initial conditions: a choicePreset IC
    interface whose one choice applies the zone's numbers as
    setParams through the existing run-override path."""
    report = zone_constraints(manager, zone_name)
    if not report.get('ok'):
        return report
    from simulations.initial_condition_interface_definition import (
        InitialConditionInterfaceDefinition,
    )
    ic_name = f'zone-ic--{zone_name}'
    config = {
        'label': f'Real constraints — {zone_name}',
        'choices': [{
            'key': 'apply-real-constraints',
            'label': f'Apply captured constraints ({zone_name})',
            'description': (
                f"{report['captureMode']} capture"
                + (', calibrated' if report['calibrated']
                   else ', UNCALIBRATED')
                + f", model {report['model']}"),
            'setParams': report['constraints'],
        }],
        'derivedParams': {},
    }
    existing = _by_name(
        manager, 'InitialConditionInterfaceDefinition').get(ic_name)
    if existing is not None:
        existing.config_json = json.dumps(config)
        if target_simulation_ref:
            existing.target_simulation_ref = target_simulation_ref
        if target_class_name:
            existing.target_class_name = target_class_name
        _persist(manager, existing)
        return {'ok': True, 'icInterface': ic_name,
                'created': False, 'constraints':
                report['constraints']}
    row = InitialConditionInterfaceDefinition(
        name=ic_name,
        description=('Captured real-world constraints from AR zone '
                     f"'{zone_name}' — Real Constraints Mode output, "
                     'consumed as simulation initial conditions.'),
        target_simulation_ref=target_simulation_ref,
        target_class_name=target_class_name,
        interface_kind='choicePreset',
        config_json=json.dumps(config),
        enabled=True,
        manager=manager)
    _insert(manager, 'InitialConditionInterfaceDefinition', row)
    return {'ok': True, 'icInterface': ic_name, 'created': True,
            'constraints': report['constraints']}


def zone_to_simulation(manager, zone_name, target_simulation_ref='',
                       target_class_name=''):
    """The Swap-Modes act: Real Constraints -> Simulation. Ensures
    the zone's sim-space identity + its IC interface in one call.
    The IC target defaults to the simulation the zone is TIED to."""
    if not target_simulation_ref:
        zone = _zone(manager, zone_name)
        if zone is not None:
            target_simulation_ref = getattr(zone, 'simulation_ref',
                                            '')
    space = ensure_zone_sim_space(manager, zone_name)
    if not space.get('ok'):
        return space
    ic = ensure_zone_ic_interface(manager, zone_name,
                                  target_simulation_ref,
                                  target_class_name)
    if not ic.get('ok'):
        return ic
    return {'ok': True, 'zone': zone_name,
            'simSpace': space['simSpace'],
            'simSpaceCreated': space['created'],
            'icInterface': ic['icInterface'],
            'icInterfaceCreated': ic['created'],
            'constraints': ic['constraints']}
