"""
@module vpn.vpn_seed

The no-code half of the propose forms: one AnalysisDefinition
(`vpn-proposal` -> vpn.vpn_proposals:propose) and one
SolutionDefinition per proposal kind (`vpn-propose-<kind>`), each
FormSubscription -> AnalysisCall (pick proposals) -> AnalysisCall
(pick message) -> GenerateEvent VpnProposal (dedupe by name) ->
EmitFrontendEvent refreshDisplay with the message — the mealplan
form contract, so a refusal reads back on the form and writes
nothing.

`seed_vpn_nocode(manager)` upserts them (composition's upsert path
when present; insert-by-name otherwise) — called from polariServer's
seed pass when the vpn module is available.
"""

import json

from polariNoCode import graph_builder as gb

_CALLABLE = 'vpn.vpn_proposals:propose'

#: Form field -> analysis param, per kind (the form's extraVariables
#: are the solution context; every param rides gb.var_src).
_FIELDS = {
    'network': ('device', 'network_name', 'provider', 'app_kind', 'mode',
                'cidr', 'listen_port', 'forward_allowed', 'masquerade'),
    'peer': ('device', 'network_name', 'peer_name', 'kind', 'public_key',
             'endpoint', 'carried_cidrs'),
    'rule': ('device', 'network_name', 'from_tag', 'to_target', 'action',
             'ports', 'order'),
    'link': ('device', 'network_name', 'remote_device', 'remote_network',
             'remote_gateway_public_key', 'remote_cidrs', 'agreement_id',
             'relay_kind', 'remote_endpoint'),
    'exposure': ('device', 'network_name', 'app_name', 'role'),
    'revoke': ('device', 'target', 'name', 'network_name', 'reason'),
}

SEED_VPN_ANALYSES = [
    {'name': 'vpn-proposal', 'domain': 'vpn', 'callable_ref': _CALLABLE,
     'description': 'Validate a VPN proposal against the mirror (networks, '
                    'peers, the netledger, gateway presence) and return the '
                    'VpnProposal row to write + a plain-words message; '
                    'refuses any key material. Never mutates mirror rows.',
     'params_json': json.dumps({'device': 'isle hostname',
                                'kind': '|'.join(_FIELDS),
                                '...': 'the kind\'s fields'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'vpn-1'},
]


def _solution(name, definition, description):
    return {'name': name, 'function_name': name.replace('-', '_'),
            'target_runtime': 'python_backend',
            'definition': json.dumps(definition),
            'contract_json': json.dumps({'description': description,
                                         'executionRights': 'definer'})}


def _propose_solution(kind):
    name = 'vpn-propose-%s' % kind
    params = {f: gb.var_src(f) for f in _FIELDS[kind]}
    params['kind'] = gb.lit_src(kind)
    params['proposed_by'] = gb.lit_src('display/vpn form')
    graph = gb.solution(
        name,
        gb.node('Start', 'FormSubscription', {}, outs=[['Validate']]),
        gb.node('Validate', 'AnalysisCall',
                {'analysis': 'vpn-proposal', 'params': params,
                 'pick': 'proposals', 'resultVariable': 'proposals'},
                outs=[['Message']]),
        gb.node('Message', 'AnalysisCall',
                {'analysis': 'vpn-proposal', 'params': params,
                 'pick': 'message', 'resultVariable': 'message'},
                outs=[['Write']]),
        gb.node('Write', 'GenerateEvent',
                {'targetClassName': 'VpnProposal',
                 'eventsFrom': gb.var_src('proposals'), 'dedupeBy': 'name',
                 'fields': {}}, outs=[['Refresh']]),
        gb.node('Refresh', 'EmitFrontendEvent',
                {'eventName': 'refreshDisplay',
                 'payload': {'written': gb.var_src('generatedEventBatch'),
                             'message': gb.var_src('message')}}),
    )
    return _solution(
        name, graph,
        'The "%s" propose form: validated VpnProposal row for the isle\'s '
        'inbox; the message names what was proposed or why it was refused.'
        % kind)


SEED_VPN_SOLUTIONS = [_propose_solution(kind) for kind in _FIELDS]


def seed_vpn_nocode(manager):
    """Upsert the analysis + solutions. Returns the upsert reports
    (composition path) or a one-line insert report."""
    from polariApiServer.displayDefinition import DisplayDefinition
    from polariApiServer.solutionDefinition import SolutionDefinition
    from polariNoCode.analysis_calls import AnalysisDefinition
    from vpn.vpn_page import SEED_VPN_PAGE_DISPLAYS
    # The page rides the UPSERT too: the plain seed pass is insert-by-
    # name, so a row added to /display/vpn (vpn-3's agreements row)
    # never reaches a live instance that already has the page (the
    # seed-field-addition gotcha, caught live 2026-09-03).
    pairs = [('AnalysisDefinition', AnalysisDefinition, SEED_VPN_ANALYSES),
             ('SolutionDefinition', SolutionDefinition, SEED_VPN_SOLUTIONS),
             ('DisplayDefinition', DisplayDefinition, SEED_VPN_PAGE_DISPLAYS)]
    try:
        from composition.seed_upsert import upsert_seed_pairs
    except ImportError:
        upsert_seed_pairs = None
    if upsert_seed_pairs is not None:
        return upsert_seed_pairs(manager, pairs, tag='VpnNocodeSeed')
    # insert-by-name fallback (no composition on this instance)
    tables = getattr(manager, 'objectTables', {}) or {}
    inserted = []
    for class_name, cls, seeds in pairs:
        existing = {getattr(r, 'name', '')
                    for r in (tables.get(class_name) or {}).values()}
        for seed in seeds:
            if seed['name'] in existing:
                continue
            row = cls(manager=manager, **seed)
            try:
                manager.db.saveInstanceInDB(row)
            except Exception:  # noqa: BLE001
                pass
            inserted.append(seed['name'])
    return [{'class': 'VpnNocode', 'inserted': inserted, 'updated': []}]
