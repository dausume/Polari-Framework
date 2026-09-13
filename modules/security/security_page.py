"""
@module security.security_page

/display/security            the overview: the three domains, the scenario in force, the systems with provenance
/display/security-os         what a process can touch, hop by hop, and which system decides (the OS view)
/display/security-network    how bytes get in, between and out (the network view)
/display/security-app        who gets access to what through which means (the app view)
Configured tables + structured panels only (no raw JSON on screens). Each view page shows the scenario this
deployment IS (the API's default), a simulation for a typical actor, the same view compared across every
scenario, and the edge rows for the configured table.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

EDGE_COLS = 'scenario,source,means,target,verdict,decided_by,provenance,why'


def _view_page(view, title, question, actor):
    return _page(f'security-{view}', f'security-{view}', f'{title} — {question}', 'SecurityTopologyEdge', [
        _row(0, [
            _sapi(f'security-{view}-summary', 0, 12, f'{title} view — this deployment\'s scenario: every reach attempt, its verdict and the system that decided',
                  f'/api/security/topology?view={view}', pick='summary'),
        ], min_height=260),
        _row(1, [
            _sapi(f'security-{view}-simulate', 0, 6, f'Simulation — what "{actor}" can reach here, hop by hop, as this machine IS today',
                  f'/api/security/simulate?view={view}&actor={actor}', pick='steps'),
            _sapi(f'security-{view}-enforce', 1, 6, f'The same actor if every Polari ring were enforced',
                  f'/api/security/simulate?view={view}&actor={actor}&mode=enforce', pick='steps'),
        ], min_height=260),
        _row(2, [
            _sapi(f'security-{view}-compare', 0, 12, 'The same view across every scenario — verdict (deciding system) per scenario',
                  f'/api/security/compare?view={view}', pick='rows'),
        ], min_height=260),
        _row(3, [
            _sapi(f'security-{view}-nodes', 0, 5, 'Boundaries in this view: what each system is and who provides it',
                  f'/api/security/topology?view={view}', pick='nodes'),
            _table(f'security-{view}-edges', 1, 7, 'Edge rows (every scenario, as applied today)', 'SecurityTopologyEdge', columns=EDGE_COLS),
        ]),
    ])


def _panel(item_id, index, segments, title, name, inputs):
    return {'id': item_id, 'index': index, 'type': 'component', 'rowSegmentsUsed': segments, 'gridColumnStart': None,
            'title': title, 'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': name, 'inputs': inputs}, 'item': None, 'nestedRows': []}


SEED_SECURITY_PAGE_DISPLAYS = [
    _page('security-threats', 'security-threats', 'Security threats — each threat played through the topology until a policy blocks it, and the counterexample that gets in legitimately', 'SecurityThreat', [
        _row(0, [
            _panel('security-threat-sim', 0, 12, 'Threat simulation — watch a threat cross the boundaries (red) and the legitimate path beside it (green); switch the mode to see stock docker, today, a warn-only apply, or every ring enforced',
                   'security-threat-sim', {'path': '/api/security/threats', 'scenario': '', 'mode': 'today'}),
        ], min_height=520),
        _row(1, [
            _sapi('security-threats-list', 0, 12, 'Every threat on this deployment: verdict, the policy that blocked it, the counterexample',
                  '/api/security/threats', pick='threats', hide='path,counter'),
        ], min_height=260),
        _row(2, [
            _table('security-threat-rows', 0, 12, 'Threat rows (every scenario, as applied today)', 'SecurityThreat',
                   columns='scenario,view,title,verdict,blocked_by,counter_group,counter_means,counter_verdict'),
        ]),
    ]),
    _page('security', 'security', 'Security — the three domains, the scenario in force, and every protecting system with its provenance', 'SecurityControl', [
        _row(0, [
            _sapi('security-overview', 0, 6, 'This deployment: scenario, the three views, how to read provenance', '/api/security', hide='systems'),
            _sapi('security-scenarios', 1, 6, 'The scenarios: route, how the MAC ring attaches, whether modules are containers, guests and hardware',
                  '/api/security/scenarios', pick='scenarios'),
        ], min_height=240),
        _row(1, [
            _table('security-controls', 0, 12, 'Every protecting system per scenario — provenance (stock docker / qemu / polari) and state today',
                   'SecurityControl', columns='scenario,domain,area,title,provenance,state,evidence'),
        ]),
        _row(2, [
            _table('security-domains', 0, 4, 'Domains (the three views)', 'SecurityDomain', columns='title,description,view_route'),
            _table('security-areas', 1, 8, 'Areas beneath the domains', 'SecurityArea', columns='domain,title,generated,description,docs_page'),
        ]),
    ]),
    _view_page('os', 'OS', 'what can a process touch on the machine, and which system stops it', 'prf-backend'),
    _view_page('network', 'Network', 'how do bytes get in, between and out', 'internet'),
    _view_page('app', 'App', 'who gets access to what, through which means', 'visitor'),
]
