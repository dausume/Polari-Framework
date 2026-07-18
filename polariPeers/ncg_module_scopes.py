"""
@module polariPeers.ncg_module_scopes

ncg-7 (Dustin 2026-07-16): the ncg levels as POLARI MODULE OBJECTS —
PolariModule rows whose bundles can be STORED AWAY and DYNAMICALLY
LOADED into an already-running deployment. This module builds the
CLOSURE SCOPES (export_module's 'classRows' root) for each ncg
domain, so exporting a level is one call / one POST — the bundle
carries every row the level needs, in seed-dict shape, and
import_bundle seeds it into a live instance idempotently.

The closures are row-reference walks, mirroring what each domain's
compiler reads:
  logic design   -> its LogicBlockNode rows
  circuit        -> nets + components (+ referenced devices + cards)
  breadboards    -> placements + jumpers + pin bindings (+ devices)
  procedure      -> criteria + edges (+ votes + ballots)
  test pack      -> its cases

@consumers
  - polariPeers.peers_api (POST /api/modules/export {'scope': ...})
  - polariPeers.selftest_ncg_modules
"""


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _names(manager, class_name, field, wanted):
    return sorted(getattr(r, 'name', '')
                  for r in _rows(manager, class_name)
                  if getattr(r, field, '') in wanted)


def _device_closure(manager, component_rows):
    """Devices (and their versioned cards) referenced by 'device'
    components/placements — material provenance travels WITH the
    module."""
    devices = sorted({getattr(c, 'device_name', '')
                      for c in component_rows
                      if getattr(c, 'kind', '') == 'device'
                      and getattr(c, 'device_name', '')})
    cards = _names(manager, 'SpiceModelCard', 'device_name',
                   set(devices))
    return devices, cards


def logic_design_scope(manager, design_names, name=None,
                       description=''):
    """One or more logic designs + their nodes."""
    wanted = set(design_names)
    return {
        'name': name or f'hwdigital--{"+".join(sorted(wanted))}',
        'description': description or 'logic designs as a loadable '
                                      'module object (ncg-7)',
        'classRows': {
            'LogicBlockDesign': sorted(wanted),
            'LogicBlockNode': _names(manager, 'LogicBlockNode',
                                     'design_name', wanted),
        },
    }


def circuit_scope(manager, circuit_names, name=None, description=''):
    wanted = set(circuit_names)
    components = [c for c in _rows(manager,
                                   'CircuitComponentDefinition')
                  if getattr(c, 'circuit_name', '') in wanted]
    devices, cards = _device_closure(manager, components)
    class_rows = {
        'CircuitDefinition': sorted(wanted),
        'CircuitNetDefinition': _names(
            manager, 'CircuitNetDefinition', 'circuit_name', wanted),
        'CircuitComponentDefinition': sorted(
            getattr(c, 'name', '') for c in components),
    }
    if devices:
        class_rows['ElectronicDeviceDefinition'] = devices
    if cards:
        class_rows['SpiceModelCard'] = cards
    return {'name': name or f'circuit--{"+".join(sorted(wanted))}',
            'description': description or 'circuits as a loadable '
                                          'module object (ncg-7)',
            'classRows': class_rows}


def breadboard_scope(manager, board_names, name=None,
                     description=''):
    """Boards + placements + jumpers touching them + pin bindings
    whose targets are placed here (+ device closure)."""
    wanted = set(board_names)
    placements = [p for p in _rows(manager, 'ComponentPlacement')
                  if getattr(p, 'board_name', '') in wanted]
    placement_names = {getattr(p, 'name', '') for p in placements}
    jumpers = sorted(
        getattr(j, 'name', '') for j in _rows(manager, 'BoardJumper')
        if getattr(j, 'board_a', '') in wanted
        or getattr(j, 'board_b', '') in wanted)
    bindings = sorted(
        getattr(b, 'name', '')
        for b in _rows(manager, 'PinBindingDefinition')
        if getattr(b, 'target_name', '') in placement_names)
    devices, cards = _device_closure(manager, placements)
    class_rows = {
        'BreadboardDefinition': sorted(wanted),
        'ComponentPlacement': sorted(placement_names),
    }
    if jumpers:
        class_rows['BoardJumper'] = jumpers
    if bindings:
        class_rows['PinBindingDefinition'] = bindings
    if devices:
        class_rows['ElectronicDeviceDefinition'] = devices
    if cards:
        class_rows['SpiceModelCard'] = cards
    return {'name': name or f'boards--{"+".join(sorted(wanted))}',
            'description': description or 'populated breadboards as '
                                          'a loadable module object '
                                          '(ncg-7)',
            'classRows': class_rows}


def procedure_scope(manager, procedure_name, name=None,
                    description=''):
    """A decision procedure: criteria + edges + votes + ballots —
    the judicial content a court can load in."""
    wanted = {procedure_name}
    vote_names = _names(manager, 'LogicForkVote',
                        'decision_procedure_name', wanted)
    class_rows = {
        'LogicForkCriterion': _names(
            manager, 'LogicForkCriterion',
            'decision_procedure_name', wanted),
        'DecisionProcedureEdge': _names(
            manager, 'DecisionProcedureEdge',
            'decision_procedure_name', wanted),
    }
    if vote_names:
        class_rows['LogicForkVote'] = vote_names
        ballots = _names(manager, 'LogicForkBallot', 'vote_name',
                         set(vote_names))
        if ballots:
            class_rows['LogicForkBallot'] = ballots
    return {'name': name or f'procedure--{procedure_name}',
            'description': description or 'a decision procedure as '
                                          'a loadable module object '
                                          '(ncg-7)',
            'classRows': class_rows}


def test_pack_scope(manager, pack_name, name=None, description=''):
    return {
        'name': name or f'testpack--{pack_name}',
        'description': description or 'an authorable test pack as a '
                                      'loadable module object '
                                      '(ncg-7)',
        'classRows': {
            'NoCodeTestPack': [pack_name],
            'NoCodeTestCase': _names(manager, 'NoCodeTestCase',
                                     'pack_name', {pack_name}),
        },
    }


def suggest_ncg_module_scopes(manager):
    """Ready-to-export suggestions for the current ncg content —
    the export scope stays a knob, these are suggestions."""
    suggestions = []
    designs = sorted(getattr(r, 'name', '')
                     for r in _rows(manager, 'LogicBlockDesign'))
    if designs:
        suggestions.append(logic_design_scope(
            manager, designs, name='hwdigital-level'))
    circuits = sorted(getattr(r, 'name', '')
                      for r in _rows(manager, 'CircuitDefinition'))
    if circuits:
        suggestions.append(circuit_scope(
            manager, circuits, name='circuit-level'))
    boards = sorted(getattr(r, 'name', '')
                    for r in _rows(manager, 'BreadboardDefinition'))
    if boards:
        suggestions.append(breadboard_scope(
            manager, boards, name='breadboard-level'))
    procedures = sorted({
        getattr(r, 'decision_procedure_name', '')
        for r in _rows(manager, 'LogicForkCriterion')
        if getattr(r, 'decision_procedure_name', '')})
    for procedure in procedures:
        suggestions.append(procedure_scope(manager, procedure))
    packs = sorted(getattr(r, 'name', '')
                   for r in _rows(manager, 'NoCodeTestPack'))
    for pack in packs:
        suggestions.append(test_pack_scope(manager, pack))
    return suggestions
