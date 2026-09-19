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

# The `actor` column on every observation ledger holds an opaque Keycloak subject id and never a name (his rule
# D18-1). `person` tells class-rows-table to show it shortened, with the whole id in the tooltip, and to resolve the
# names of the rows ON SCREEN in one batched call to the gated door POST /api/security/people while the page renders.
# A viewer who may not resolve names keeps seeing the short id; nothing is written back into a row either way.
ACTOR_FORMAT = 'actor:person'
#: ct-1's TraceTarget keys its person in `started_by` — the same rule, the same resolution at render time.
TRACE_ACTOR_FORMAT = 'started_by:person'


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
        *({'os': [_row(3, [_table('security-os-mac', 0, 6, 'MAC profiles — rendered per scenario, mode as loaded today', 'MacProfile', columns='scenario,app,kind,profile,mode,attach,state'),
                          _table('security-os-dac', 1, 6, 'DAC per app — declared vs live (drift when an audit run reports the containers)', 'DacPolicy', columns='scenario,app,kind,caps_add,writable,live_user,drift')]),
                  _row(4, [_table('security-os-groups', 0, 6, 'Permission groups — the sudoers verbs and the hardware groups', 'PermissionGroup', columns='name,purpose,installed,members,apps_needing'),
                          _table('security-os-trials', 1, 3, 'Hardware trials (none yet)', 'HardwareTrial', columns='app,method,accepted'),
                          _table('security-os-proposals', 2, 3, 'Proposals from harvests', 'SecurityProposal', columns='app,status,reading')])],
           'network': [_row(3, [_table('security-net-proxy', 0, 6, 'Proxy configurations — TLS, HSTS, headers, rate limits, guard', 'ProxyConfig', columns='route,env,server_names,tls_versions,hsts,rate_limits,guard_verdict'),
                               _table('security-net-certs', 1, 6, 'Service identities — issuer, hostnames, days left', 'ServiceIdentity', columns='service,manifest,issuer,issued,not_after,days_left')]),
                       _row(4, [_table('security-net-firewall', 0, 6, 'Firewall rule sets per scenario — rendered vs applied', 'FirewallRuleSet', columns='scenario,chain,rule_count,applied,sources_resolved'),
                               _table('security-net-snippets', 1, 6, 'Per-app proxy snippets (absent until sec-i-4)', 'ProxySnippet', columns='app,scope,state,template')])],
           'app': [_row(3, [_table('security-app-channels', 0, 7, 'Trust channels — transport, auth, key kind (a symmetric key on a user channel is a finding)', 'TrustChannel', columns='from_kind,to_kind,to_app,transport,auth,key_kind,scenario,finding'),
                           _table('security-app-authz', 1, 5, 'Who may call what — a view over accessControl and the CRUDE gate', 'AuthzRule', columns='resource,role,verbs,gate,notes')]),
                   _row(4, [_table('security-app-content', 0, 6, 'Content policies per class (derived from the typing; observe before enforce)', 'ContentPolicy', columns='app,target,mode,fields,violations_observed'),
                           _table('security-app-browser', 1, 6, 'Browser policies per frontend host (CSP, report-only first)', 'BrowserPolicy', columns='host,env,mode,frame,violations')])]}[view]),
        _row(5, [
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
            _sapi('security-ledger-summary', 0, 4, 'The ledger — per scenario: apps, fully complete, the most common blocking step', '/api/security/ledger', pick='summary'),
            _table('security-ledger', 1, 8, 'AppSecurityRecord — one row per app: steps complete / total and the first blocking step', 'AppSecurityRecord',
                   columns='scenario,app,kind,stanza_conforms,mac_mode,surface_applied,proxy_snippets,content_policy,steps_complete,steps_total,blocking'),
        ]),
        _row(3, [
            _table('security-domains', 0, 4, 'Domains (the three views)', 'SecurityDomain', columns='title,description,view_route'),
            _table('security-areas', 1, 8, 'Areas beneath the domains', 'SecurityArea', columns='domain,title,generated,description,docs_page'),
        ]),
    ]),
    _page('security-proxy', 'security-proxy', 'Proxy security — the edge and the agent: configurations, service identities, per-app snippets', 'ProxyConfig', [
        _row(0, [_table('security-proxy-configs', 0, 12, 'Proxy configurations', 'ProxyConfig', columns='route,env,template,server_names,upstreams,tls_versions,hsts,headers,rate_limits,guard_verdict')]),
        _row(1, [_table('security-proxy-certs', 0, 6, 'Service identities', 'ServiceIdentity', columns='service,manifest,issuer,hostnames,issued,not_after,days_left'),
                 _table('security-proxy-snippets', 1, 6, 'Per-app snippets', 'ProxySnippet', columns='app,scope,kind,state,template')]),
    ]),
    _page('security-firewall', 'security-firewall', 'Firewall security — DOCKER-USER and ufw per scenario, rendered vs applied', 'FirewallRuleSet', [
        _row(0, [_table('security-firewall-sets', 0, 12, 'Rule sets', 'FirewallRuleSet', columns='scenario,chain,rule_count,applied,sources_resolved,artifact')]),
        _row(1, [_sapi('security-firewall-net', 0, 12, 'The network view for this deployment', '/api/security/topology?view=network', pick='summary')], min_height=260),
    ]),
    _page('security-events', 'security-events', 'Security events — observe mode: what production would have denied, counted (dev posture only; empty in production)', 'SecurityEvent', [
        _row(0, [_sapi('security-observe-summary', 0, 12, 'This instance: posture, whether security observes or enforces, how many actions ran that production would deny, the contract (what warns vs what still refuses)',
                       '/api/security/events', pick='summary')], min_height=220),
        _row(1, [_table('security-events-table', 0, 12, 'SecurityEvent — one row per decision (control | action | target): outcome, reason, how many times, first/last seen', 'SecurityEvent',
                        columns='control,action,target,actor,app,outcome,reason,count,first_seen,last_seen,source', column_formats=ACTOR_FORMAT)]),
        _row(2, [_table('security-observations-table', 0, 8, 'PermissionObservation — dev mode: which roles / profiles performed which acts (class × verb), counted; the evidence app-level permission profiles are worked out from', 'PermissionObservation',
                        columns='groups,profiles,class_name,verb,verdict,count,actor,first_seen,last_seen', column_formats=ACTOR_FORMAT),
                 _sapi('security-derived-profiles', 1, 4, 'Derived profile suggestions — one proposed AppPermissionProfile per role set (classes touched, verbs used, the evidence); review and narrow before creating the row',
                       '/api/security/observations', pick='derived')], min_height=300),
        _row(3, [_table('security-usage-table', 0, 8, 'UsageObservation — role-play: the apps, pages, components, actions and endpoints each role USED, counted (the "functionality" half of the review)', 'UsageObservation',
                        columns='role,kind,item,app,page,count,actor,first_seen,last_seen', column_formats=ACTOR_FORMAT),
                 # ct-7 (design §8): the session states the TASK being performed, so the review reads as
                 # tasks → doors → objects × verbs → closure rather than as one flat class list.
                 _table('security-sessions-table', 1, 4, 'Role-play sessions — who acted as which role, on which TASK ("publish an article"), when; acts and usages attributed', 'ObservationSession',
                        columns='role,task,actor,active,started_at,ended_at,acts,usages', column_formats=ACTOR_FORMAT)], min_height=260),
        # ---- ct-1: causal tracing. ONE class at a time, dev posture only, budgets that disarm themselves.
        _row(4, [_sapi('security-trace-status', 0, 5, 'Causal tracing — the ONE class armed right now, its budgets and live counters, and the coverage: which classes have ever been traced',
                       '/api/security/observe/trace', hide='defaults,knob'),
                 _table('security-trace-targets', 1, 7, 'TraceTarget — one row per class ever traced: budgets, counters and why it stopped. A class with NO row here has not been traced, which is not the same as nothing reaching it', 'TraceTarget',
                        columns='class_name,active,started_by,started_at,stopped_at,stopped_because,traces_opened,edges_written,journal_written,dropped',
                        column_formats=TRACE_ACTOR_FORMAT)], min_height=280),
        _row(5, [_table('security-trace-edges', 0, 12, 'CausalEdge — Ledger A, the causal map: one counted row per cause → effect by means. Class level only; an instance id never appears here (the effect journal is where an instance is looked up)', 'CausalEdge',
                        columns='cause,effect,means,detail,count,min_depth,max_depth,run_as,target,first_seen,last_seen')]),
        # ---- ct-4: THE CLOSURE of the armed target's class, read from the same map. Structured panels over
        # the closure door (no raw JSON, no new component); every item carries its origin and its evidence.
        _row(6, [_sapi('security-closure-objects', 0, 7, 'The closure of the class armed right now — every class × verb it reaches, transitively: origin (declared / observed / closure), whether it is reached ONLY through a trigger running as definer, and the evidence behind each',
                       '/api/security/observe/closure', pick='objects'),
                 _sapi('security-closure-not-traced', 1, 5, 'NOT TRACED — classes this closure touches that have never been armed as a TraceTarget. "Not traced" is not the same as "nothing reaches it": arm one of these next and ask again',
                       '/api/security/observe/closure', pick='not_traced_detail')], min_height=300),
        _row(7, [_sapi('security-closure-solutions', 0, 6, 'The solutions the closure runs, and AS WHOM — a trigger runs its solution as the DEFINER, so an update permission can silently run somebody else\'s solution with somebody else\'s authority',
                       '/api/security/observe/closure', pick='solutions'),
                 _sapi('security-closure-events', 1, 6, 'The events the closure fires or publishes — trigger firings, emitted events and the STOMP topics the change is broadcast on',
                       '/api/security/observe/closure', pick='events')], min_height=280),
        _row(8, [_sapi('security-closure-flows', 0, 12, 'Where the objects GO — peer edges (shared-DB reads, lease writes, module bundles) and external sends, with the CLASSES that rode each one. Beyond the wrapper Polari cannot see, and does not pretend to',
                       '/api/security/observe/closure', pick='flows')], min_height=240),
        # ---- ct-9: the TRAFFIC POLICIES. Closed by default; the rows are derived from dev monitoring, ruled
        # on by a person, enforced in production. Configured tables over the rows themselves + one structured
        # panel over the suggestion list (no raw JSON, no new component).
        _row(9, [_sapi('security-traffic-suggestions', 0, 12, 'Traffic suggestions — the sends and the callers this instance OBSERVED that nobody has ruled on yet. This list IS the monitoring: confirm the ones that belong and deny the rest on the record, because under enforce everything unconfirmed is refused (closed by default)',
                       '/api/security/traffic', pick='suggestions')], min_height=280),
        _row(10, [_table('security-traffic-outbound', 0, 6, 'OutboundPolicy — what may leave this instance, per system and wire: the payload CLASSES observed crossing (never a payload, never a URL), the state, and the person who ruled. suggested = proposed and unruled, which is NOT a grant', 'OutboundPolicy',
                         columns='system_kind,system_name,means,payload_classes_json,state,count,confirmed_by,confirmed_at,derived_from,first_seen,last_seen',
                         column_formats='confirmed_by:person'),
                  _table('security-traffic-inbound', 1, 6, 'InboundPolicy — who may call this instance: a peer NAME, an Origin host, or a class such as anonymous — never a raw address — with the endpoint TEMPLATES it was seen at', 'InboundPolicy',
                         columns='source_kind,source,paths_json,state,count,confirmed_by,confirmed_at,derived_from,first_seen,last_seen',
                         column_formats='confirmed_by:person')], min_height=280),
        _row(11, [_sapi('security-traffic-declared', 0, 12, 'Declared flows — the CONFIRMED traffic policies as the object topology draws them: direction, the counterpart, the wire and the classes. An observed flow with no row here is drift',
                        '/api/security/traffic/declared', pick='flows')], min_height=240),
    ]),
    # ---- ct-5 (design §7): the FOURTH view. The other three answer "who can reach what"; this one answers
    # "where do the ROWS go". Configured structured panels over the same doors the other view pages use, plus
    # configured tables over the rows that back it — no new component, nothing raw.
    _page('security-objects', 'security-objects',
          'Objects — where the rows go: which CLASSES cross to which system, declared beside observed, and the drift between them',
          'SecurityTopologyEdge', [
              _row(0, [
                  _sapi('security-objects-summary', 0, 12,
                        'Object flow on this instance — every edge with its PAYLOAD (the classes it carries, and how often), its provenance (declared = a manifest app.flows entry or a traffic policy a person confirmed; observed = the causal map) and the system that decides it',
                        '/api/security/topology?view=objects', pick='summary'),
              ], min_height=300),
              _row(1, [
                  _sapi('security-objects-undeclared', 0, 6,
                        'OBSERVED, DECLARED BY NOTHING — classes seen crossing that no manifest app.flows entry and no confirmed traffic policy covers. A finding the first time something flows, never a block: dev warns (§17)',
                        '/api/security/objects/drift', pick='observed_not_declared'),
                  _sapi('security-objects-unexercised', 1, 6,
                        'DECLARED, NEVER OBSERVED — what somebody said may flow and the map has never recorded. Noise to prune, UNLESS its classes have never been traced, in which case the honest reading is NOT TRACED: arm one and ask again',
                        '/api/security/objects/drift', pick='declared_not_observed'),
              ], min_height=280),
              _row(2, [
                  _sapi('security-objects-by-app', 0, 7,
                        'Per app: how many observed flows nothing declares, how many declarations nothing exercises, and the trace coverage of the classes involved (none / partial / full)',
                        '/api/security/objects/drift', pick='by_app'),
                  _sapi('security-objects-not-traced', 1, 5,
                        'NOT TRACED — classes on this view that have never been armed as a TraceTarget. The map cannot say what they really send, and "not traced" is not the same as "nothing flows"',
                        '/api/security/objects/drift', pick='not_traced_detail'),
              ], min_height=280),
              _row(3, [
                  _sapi('security-objects-simulate', 0, 6,
                        'What leaves this instance as things stand today — every flow, its payload, and the system that decided it',
                        '/api/security/simulate?view=objects&actor=this%20instance', pick='steps'),
                  _sapi('security-objects-enforce', 1, 6,
                        'The same flows under ENFORCE — production, closed by default: only a traffic policy row a person confirmed lets anything leave',
                        '/api/security/simulate?view=objects&actor=this%20instance&mode=enforce', pick='steps'),
              ], min_height=280),
              _row(4, [
                  _sapi('security-objects-compare', 0, 12,
                        'The same flows across all four modes — stock (no policy at all), today (this instance\'s knob), complain (dev: warn, never block), enforce (production: closed by default)',
                        '/api/security/compare?view=objects', pick='rows'),
              ], min_height=260),
              _row(5, [
                  _sapi('security-objects-declared', 0, 6,
                        'DECLARED flows — the modules\' manifest app.flows stanzas (the app author\'s statement: a system KIND, never a host) and the traffic policy rows a person confirmed (the deployment\'s)',
                        '/api/security/objects/flows', pick='declared'),
                  _sapi('security-objects-observed', 1, 6,
                        'OBSERVED flows — what the causal map recorded crossing, while a TraceTarget was armed. One class at a time, dev posture only',
                        '/api/security/objects/flows', pick='observed'),
              ], min_height=280),
              _row(6, [
                  _table('security-objects-map', 0, 7,
                         'CausalEdge — the map these observed edges are read from: one counted row per cause → effect by means, with the classes in `detail`. Class level only; an instance id never appears here',
                         'CausalEdge', columns='cause,effect,means,detail,count,run_as,target,first_seen,last_seen'),
                  _table('security-objects-coverage', 1, 5,
                         'TraceTarget — the coverage: one row per class ever armed. A class with NO row here has not been traced, which is not the same as nothing flowing from it',
                         'TraceTarget', columns='class_name,active,started_by,started_at,stopped_at,stopped_because,edges_written,journal_written,dropped',
                         column_formats=TRACE_ACTOR_FORMAT),
              ], min_height=280),
              _row(7, [
                  _sapi('security-objects-nodes', 0, 12,
                        'The boundaries on this view: the app\'s own declaration, the traffic policy, the outbound wrapper (the edge of what Polari can see), the permission gate and the causal map',
                        '/api/security/topology?view=objects', pick='nodes'),
              ], min_height=240),
          ]),
    _view_page('os', 'OS', 'what can a process touch on the machine, and which system stops it', 'prf-backend'),
    _view_page('network', 'Network', 'how do bytes get in, between and out', 'internet'),
    _view_page('app', 'App', 'who gets access to what, through which means', 'visitor'),
]


def seed_security_pages(manager):
    """CONVERGE the security pages, rather than insert-by-name.

    The core display seed only INSERTS a DisplayDefinition that is missing, so on an instance that already has these
    pages a change to a page's `definition` never lands — §54's `actor:person` columns were seeded into the code and
    the live stack went on serving the old definition (the seed field-addition gotcha, hit again). `upsert_seed_rows`
    diffs the fields and leaves a row alone when `is_prior` is False, so a page somebody has customized here is still
    theirs."""
    from moduleService.seed_upsert import upsert_seed_pairs
    from polariApiServer.displayDefinition import DisplayDefinition
    return upsert_seed_pairs(manager, [
        ('DisplayDefinition', DisplayDefinition, SEED_SECURITY_PAGE_DISPLAYS),
    ], tag='SecurityPagesSeed')


def start_page_converge(manager, polServer=None, wait_s=300, rows_wait_s=120, tick=2.0):
    """Run `seed_security_pages` once, AFTER the tree's display rows are restored.

    Same reasoning as the PII scrub beside it: the endpoint constructor runs while falcon's routes are built, long
    before lazy boot's Phase B restores DisplayDefinition, so converging inline would walk an empty table and simply
    insert everything again on the next boot. Daemon thread, never raises into the boot."""
    import threading
    import time

    def _rows():
        return len((getattr(manager, 'objectTables', None) or {}).get('DisplayDefinition', {}) or {})

    def _run():
        start = time.time()
        while time.time() - start < wait_s:
            registry = getattr(polServer, 'bootRegistry', None)
            try:
                pending = bool(registry.is_data_pending('security')) if registry is not None else False
            except Exception:
                pending = False
            if not pending and (_rows() or time.time() - start >= rows_wait_s):
                break
            time.sleep(tick)
        try:
            for r in seed_security_pages(manager):
                if r.get('inserted') or r.get('updated'):
                    print('[SecurityPagesSeed] %s: +%d ~%d' % (r['class'], len(r.get('inserted', [])), len(r.get('updated', []))), flush=True)
        except Exception as exc:
            print('[SecurityPagesSeed] failed: %s' % exc, flush=True)

    t = threading.Thread(target=_run, name='security-pages-converge', daemon=True)
    t.start()
    return t
