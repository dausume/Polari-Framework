"""
@module hwnocode.custom.offline_project

The light demo's Java bridge project, generated WITHOUT a running server: the same `java_bridge.generate_project` the
server uses, fed by an in-memory stand-in for the rows it reads (the pinned LightState contract in
board/custom/contracts, the seeded bridge row, the seeded enum mappings and the seeded binding). Used by the demo-bundle
export when it runs from the command line, where no server (and no database) is at hand. The generation is
deterministic: the same inputs give the same files.
"""
import json
import os
import types

from grpcbridge.custom import java_bridge as JB
from grpcbridge.custom import wire_contract as WC


def _row(**fields):
    fields.pop('manager', None)
    return types.SimpleNamespace(**fields)


def _pinned(cls):
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(here, 'board', 'custom', 'contracts', '%s.v1.json' % cls)) as f:
        return json.load(f)


def light_manager(grpc_target='', serial_device=''):
    """(manager, bridge row) standing in for the server's rows for the uno-light bridge."""
    from grpcbridge.mapping_basis import SEED_ENUM_MAPPINGS, SEED_LIGHT_BRIDGE
    pinned = _pinned('LightState')
    mgr = types.SimpleNamespace(objectTables={}, objectTypingDict={}, db=None)
    exposure = _row(name='LightState-grpc-exposure', subject_class='LightState', enabled=True, contract_status='current',
                    proto_version=int(pinned['contract_version']), contract_hash=pinned['contract_hash'])
    version = _row(name='LightState-v1', subject_class='LightState', version=int(pinned['contract_version']),
                   field_map_json=json.dumps(pinned['field_map']))
    fields = dict(SEED_LIGHT_BRIDGE)
    if grpc_target:
        fields['grpc_target'] = grpc_target
    if serial_device:
        fields['serial_device'] = serial_device
    fields['grpc_enabled'] = True
    bridge = _row(**fields)
    mgr.objectTables.update({
        'GrpcExposure': {exposure.name: exposure}, 'ProtoContractVersion': {version.name: version},
        'HardwareBridgeDefinition': {bridge.name: bridge}, 'WireContract': {},
        'EnumMapping': {r['name']: _row(**r) for r in SEED_ENUM_MAPPINGS if r['object_class'] == 'LightState'}})
    from hwnocode.custom import light_solutions as LS
    b = LS.binding_row()
    if serial_device:           # the bundle is for a real board: the binding points at its serial port, not the twin's link
        b = dict(b, port=serial_device)
    mgr.objectTables['HardwareInterfaceBinding'] = {b['name']: _row(**b)}
    return mgr, bridge


def light_project(grpc_target='', serial_device=''):
    """generate_project's report for the uno-light bridge (grpc.enabled=true, the given target / serial port in the
    properties)."""
    mgr, bridge = light_manager(grpc_target, serial_device)
    return JB.generate_project(mgr, bridge, row_factory=_row)
