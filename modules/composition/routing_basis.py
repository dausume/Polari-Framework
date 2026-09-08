"""
@module composition.routing_basis

arch-4: PROCESS HISTORY as data, and PROMOTION as a recorded,
audited OPERATION — never a relabelling.

The routing (practice: the traveler) is the ordered operation list
that builds a construction variant. Step COUNT derives from it.
Every operation declares the CAPABILITY RUNG it assumes (techtree
ladder, the mag-22 lesson: an optimisation that hides its rung is
inadmissible) and WHAT ITS SPEC IS FOR (rate/yield/tolerance/
physics — handover §3.8: industrial requirements are re-derived
against our volume, not inherited).

A PROMOTE operation is the schema's answer to handover §1.1: it
consumes the source assembly's separable interfaces, names the
interface set it fuses, emits a NEW identity with genealogy, and
records modes deleted / modes introduced / repairability spent. The
audit enforces the Boothroyd-Dewhurst gate (practice map §2): an
interface whose members must move relative to each other, or must
separate for service, may NOT be fused — and the seeds carry the
mag-26 snap interface as exactly such a refusal case.

Nothing here EXECUTES a promotion on live rows: rows are seeded or
human-made, the engine audits and reports (knobs-and-suggestions —
mag-12's suggestion-over-evidence discipline).

@consumers polariServer seed passes, composition.composition_seed,
composition.composition_selftest
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from composition.custom.data_refs import named, resolve_named, rows
from composition.node_basis import owned_interfaces

OPERATION_KINDS = ('shape', 'join', 'condition-change', 'promote')

#: What an operation's specification is FOR — so it can be
#: re-derived at our actual volume (batch anneal vs in-line).
PURPOSE_CLASSES = ('physics', 'tolerance', 'yield', 'rate')


class RoutingDefinition(treeObject):
    """The ordered process that builds one construction variant."""

    @treeObjectInit
    def __init__(self, name='', display_name='', variant_ref='',
                 per_unit='part', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: ConstructionVariantDefinition this routing builds.
        self.variant_ref = variant_ref
        #: What one pass of the routing produces ('part' | 'layer'
        #: — the layered stator runs its routing PER LAYER).
        self.per_unit = per_unit
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class RoutingOperation(treeObject):
    """One step. kind='promote' carries the full promotion record."""

    @treeObjectInit
    def __init__(self, name='', display_name='', routing_ref='',
                 sequence=0, kind='shape', summary='',
                 capability_rung_ref='', purpose_class='physics',
                 consumes_interface_refs_json='[]',
                 fused_interface_refs_json='[]', emits_node_ref='',
                 modes_deleted_refs_json='[]',
                 modes_introduced_refs_json='[]',
                 reversibility_spent='',
                 dfa_justification_json='{}', qualifying_act='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.routing_ref = routing_ref
        self.sequence = sequence
        self.kind = kind if kind in OPERATION_KINDS else 'shape'
        self.summary = summary
        #: Techtree ladder rung this op ASSUMES (e.g. 'W2'). ''
        #: makes the whole routing inadmissible — loudly.
        self.capability_rung_ref = capability_rung_ref
        self.purpose_class = (purpose_class
                              if purpose_class in PURPOSE_CLASSES
                              else 'physics')
        # ---- promote-kind record (empty on other kinds) ----
        #: Source-assembly separable interfaces this promotion
        #: DELETES ([] when promoting an in-process winding that
        #: never existed as a separate assembly row).
        self.consumes_interface_refs_json = \
            consumes_interface_refs_json
        #: THE NAMED INTERFACE SET the promotion fuses — must be
        #: bound (designed_separable=False) rows on the emitted
        #: node. Promotion attaches HERE, never to a whole assembly.
        self.fused_interface_refs_json = fused_interface_refs_json
        #: The NEW identity (CompositionNode) this promotion mints.
        self.emits_node_ref = emits_node_ref
        self.modes_deleted_refs_json = modes_deleted_refs_json
        self.modes_introduced_refs_json = modes_introduced_refs_json
        #: What repairability the promotion spends, in words a
        #: lifecycle-cost model can act on.
        self.reversibility_spent = reversibility_spent
        #: {interface: {moves_relative, different_material,
        #:  separable_for_service, why}} — the Boothroyd-Dewhurst
        #: answers, per fused interface. The gate.
        self.dfa_justification_json = dfa_justification_json
        #: The named experiment that earns the promoted part its
        #: realization (never a relabelled row).
        self.qualifying_act = qualifying_act
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


def _loads(text, default):
    try:
        return json.loads(text or '')
    except (TypeError, ValueError):
        return default


def routing_operations(manager, routing_name):
    ops = [o for o in rows(manager, 'RoutingOperation')
           if getattr(o, 'routing_ref', '') == routing_name]
    return sorted(ops, key=lambda o: getattr(o, 'sequence', 0))


def routing_report(manager, routing_name):
    """Ordered steps, derived count, assumed rungs — and
    admissibility: a routing with an unstated rung is not a plan,
    it is a hope (the mag-22 lesson)."""
    routing, refusal = resolve_named(manager, 'RoutingDefinition',
                                     routing_name)
    if refusal:
        return {'ok': False, **refusal}
    ops = routing_operations(manager, routing_name)
    if not ops:
        return {'ok': False, 'routing': routing_name,
                'refusal': 'routing has no operations — a build '
                           'with no steps builds nothing',
                'suggestion': {'knob': 'RoutingOperation',
                               'action': 'add the ordered steps'}}
    unstated = [getattr(o, 'name', '') for o in ops
                if not getattr(o, 'capability_rung_ref', '')]
    rungs = sorted({getattr(o, 'capability_rung_ref', '')
                    for o in ops if getattr(o, 'capability_rung_ref',
                                            '')})
    return {
        'ok': True, 'routing': routing_name,
        'perUnit': getattr(routing, 'per_unit', 'part'),
        'stepCount': len(ops),
        'steps': [{'sequence': getattr(o, 'sequence', 0),
                   'name': getattr(o, 'name', ''),
                   'kind': getattr(o, 'kind', ''),
                   'summary': getattr(o, 'summary', ''),
                   'rung': getattr(o, 'capability_rung_ref', ''),
                   'purposeClass': getattr(o, 'purpose_class', '')}
                  for o in ops],
        'assumedRungs': rungs,
        'promoteSteps': [getattr(o, 'name', '') for o in ops
                         if getattr(o, 'kind', '') == 'promote'],
        'admissible': not unstated,
        'admissibilityNote': (
            f'INADMISSIBLE: operations {unstated} state no '
            f'capability rung. A design must declare the rung it '
            f'assumes — mag-22 silently carried an HPHT press this '
            f'way.' if unstated else
            f'every step declares its rung ({", ".join(rungs)})'),
    }


def audit_promotion(manager, op_name):
    """Everything a promotion must have named, checked against the
    rows it names. Refusals are specific: which interface, which
    criterion, which missing mode."""
    op, refusal = resolve_named(manager, 'RoutingOperation', op_name)
    if refusal:
        return {'ok': False, **refusal}
    if getattr(op, 'kind', '') != 'promote':
        return {'ok': False, 'operation': op_name,
                'refusal': f'"{op_name}" is kind '
                           f'"{getattr(op, "kind", "")}" — only a '
                           f'promote operation carries a promotion '
                           f'record to audit'}
    problems = []
    emits = getattr(op, 'emits_node_ref', '')
    node, node_refusal = resolve_named(manager, 'CompositionNode',
                                       emits)
    if node_refusal:
        return {'ok': False, 'operation': op_name,
                'refusal': f'emitted node does not resolve: '
                           f'{node_refusal["refusal"]}'}
    fused = _loads(getattr(op, 'fused_interface_refs_json', ''), [])
    consumed = _loads(getattr(op, 'consumes_interface_refs_json',
                              ''), [])
    if not fused:
        problems.append('names NO fused interface set — promotion '
                        'attaches to a named interface set, never '
                        'to a whole assembly (mag-26)')
    owned = {getattr(i, 'name', ''): i
             for i in owned_interfaces(manager, emits)}
    for ref in fused:
        iface = owned.get(ref)
        if iface is None:
            problems.append(f'fused interface "{ref}" is not owned '
                            f'by the emitted node "{emits}"')
        elif getattr(iface, 'designed_separable', True):
            problems.append(f'fused interface "{ref}" is marked '
                            f'designed_separable=True — a fused '
                            f'joint that claims to come apart is a '
                            f'contradiction, not a variant')
    # Genealogy: consumed interfaces must belong to the node the
    # emitted identity descends from.
    source = getattr(node, 'genealogy_ref', '')
    if consumed and not source:
        problems.append('consumes source interfaces but the emitted '
                        'node has no genealogy_ref — a promoted '
                        'part that does not name what it came from '
                        'is indistinguishable from an assembly '
                        'drawn badly')
    deleted_expected = set()
    for ref in consumed:
        iface = named(manager, 'InterfaceDefinition', ref)
        if iface is None:
            problems.append(f'consumed interface "{ref}" does not '
                            f'resolve')
            continue
        if source and getattr(iface, 'node_ref', '') != source:
            problems.append(f'consumed interface "{ref}" belongs to '
                            f'"{getattr(iface, "node_ref", "")}", '
                            f'not to the genealogy source '
                            f'"{source}"')
        deleted_expected |= set(_loads(
            getattr(iface, 'failure_mode_refs_json', ''), []))
    # Modes: deleted must cover what the consumed interfaces carried;
    # introduced must be owned by the emitted node as bulk debt.
    deleted = set(_loads(getattr(op, 'modes_deleted_refs_json', ''),
                         []))
    introduced = set(_loads(getattr(op, 'modes_introduced_refs_json',
                                    ''), []))
    if deleted_expected - deleted:
        problems.append(f'consumed interfaces carried modes the '
                        f'record does not claim deleted: '
                        f'{sorted(deleted_expected - deleted)} — '
                        f'a promotion must name what it deletes')
    node_bulk = set(_loads(getattr(node,
                                   'bulk_failure_mode_refs_json',
                                   ''), []))
    if introduced - node_bulk:
        problems.append(f'claims to introduce modes the emitted '
                        f'node does not carry as bulk debt: '
                        f'{sorted(introduced - node_bulk)} — the '
                        f'node must own what the promotion bought '
                        f'it with')
    if not getattr(op, 'reversibility_spent', ''):
        problems.append('does not state the repairability it '
                        'spends — that is a lifecycle-cost term, '
                        'not a footnote')
    if not getattr(op, 'qualifying_act', ''):
        problems.append('names no qualifying act — reachable is not '
                        'achieved, and the difference is a specific '
                        'experiment somebody has to perform (§3.9)')
    # THE GATE: Boothroyd-Dewhurst, per fused interface.
    dfa = _loads(getattr(op, 'dfa_justification_json', ''), {})
    gate = []
    for ref in fused:
        answers = dfa.get(ref)
        if not isinstance(answers, dict):
            problems.append(f'no DFA justification for fused '
                            f'interface "{ref}" — the three '
                            f'consolidation questions are the gate, '
                            f'and they were not answered')
            continue
        blockers = []
        if answers.get('moves_relative'):
            blockers.append('its members must MOVE relative to '
                            'each other')
        if answers.get('separable_for_service'):
            blockers.append('it must SEPARATE for service')
        gate.append({'interface': ref,
                     'differentMaterial':
                         bool(answers.get('different_material')),
                     'why': answers.get('why', ''),
                     'blocked': bool(blockers),
                     'blockers': blockers})
        why = answers.get('why', '(no reason given)')
        for b in blockers:
            problems.append(f'DFA gate REFUSES fusing "{ref}": {b} '
                            f'— {why}')
    return {
        'ok': not problems, 'operation': op_name,
        'emits': emits, 'genealogySource': source,
        'fusedInterfaceSet': fused,
        'consumedInterfaces': consumed,
        'modesDeleted': sorted(deleted),
        'modesIntroduced': sorted(introduced),
        'reversibilitySpent': getattr(op, 'reversibility_spent', ''),
        'qualifyingAct': getattr(op, 'qualifying_act', ''),
        'dfaGate': gate,
        'problems': problems,
        'trade': ('promotion trades interface failure modes for '
                  'bulk ones, and spends repairability to do it — '
                  'both sides are on this record'),
    }


def variant_step_counts(manager, functional_name):
    """Process step count PER VARIANT, derived from routings —
    the 1 / 3 / 4 cost axis of mag-26, never stamped."""
    out = []
    for v in rows(manager, 'ConstructionVariantDefinition'):
        if getattr(v, 'functional_ref', '') != functional_name:
            continue
        routing_ref = getattr(v, 'routing_ref', '')
        if not routing_ref:
            out.append({'variant': getattr(v, 'name', ''),
                        'stepCount': None,
                        'note': 'routing-unstated'})
            continue
        rep = routing_report(manager, routing_ref)
        out.append({'variant': getattr(v, 'name', ''),
                    'routing': routing_ref,
                    'stepCount': rep.get('stepCount'),
                    'perUnit': rep.get('perUnit'),
                    'admissible': rep.get('admissible'),
                    'promoteSteps': rep.get('promoteSteps', [])})
    return {'ok': True, 'functional': functional_name,
            'variants': out}
