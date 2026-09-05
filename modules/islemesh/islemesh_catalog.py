"""
@module islemesh.islemesh_catalog

Catalog seed + install-plan logic for the general isle app store
(handoff §20.1/§20.3). The catalog is BROWSABLE ROWS; installation
runs on the host (`isle store install`), so this module only
produces the PLAN — the ordered host commands an install would run
— never executes docker itself (the mover-on-host discipline).

Entries model the two PROVEN variants: mesh-apps (the
`isle app deploy` pipeline) and polari-apps (the shared-shell
launcher .deb). One kind → one install-plan builder.

@consumers
  - islemesh.islemesh_api (/api/islemesh/catalog*)
  - polari-cli / isle store (reads the plan, runs it on the host)
  - islemesh.selftest_islemesh
"""

#: Seed listings — the apps the arc has actually stood up, so the
#: store shows a real catalog from day one (never seeded is_mock).
SEED_CATALOG = [
    {
        'name': 'polari', 'title': 'Polari (launcher)',
        'description': 'A DOOR, not a deployment: installs a '
                       'native desktop window onto the isle\'s '
                       'CORE polari instance (polari.isle). Runs '
                       'nothing new — what it opens, and which '
                       'modules that instance carries, is shown '
                       'under its running instances.',
        'kind': 'polari-app', 'source_ref': 'https://polari.isle',
        'provides_engine': '', 'category': 'platform',
        'source': 'official',
    },
    {
        'name': 'whoami', 'title': 'whoami (demo)',
        'description': 'A tiny HTTP echo — the arbitrary-compose '
                       'app that proves any container becomes an '
                       '.isle app.',
        'kind': 'mesh-app', 'source_ref': 'traefik/whoami:latest',
        'service': 'whoami', 'port': 80, 'category': 'demo',
        'source': 'official',
    },
    {
        'name': 'polari-instance', 'title': 'Polari (new instance)',
        'description': 'A RUNTIME, not a door: deploys another '
                       'whole polari (backend + frontend) onto '
                       'this device as a mesh-app, serving its own '
                       '<name>.isle domains with the MODULES you '
                       'choose at deploy. Coarse-grained scaling — '
                       'component-level (extra backends only) and '
                       'module-collection apps are the next arc.',
        'kind': 'polari-instance',
        'source_ref': 'prf-backend:staging + prf-frontend:staging',
        'category': 'platform', 'source': 'official',
    },
    {
        'name': 'odoo', 'title': 'Odoo (business ops)',
        'description': 'Odoo ERP deployed to the isle and wired as '
                       'a Polari business-ops ENGINE automatically.',
        'kind': 'mesh-app', 'source_ref': 'odoo:16',
        'service': 'odoo', 'port': 8069,
        'provides_engine': 'business-ops', 'category': 'engine',
        'source': 'official',
    },
    # sep-4 (decision 9): every compute engine gets its own tile —
    # deploying one binds consumers automatically via the
    # EngineProviderBinding row (the msci/cad _BINDERS).
    {
        'name': 'msci-engines',
        'title': 'Materials-science engines (DFT / FEM)',
        'description': 'The compiled-extension science worker '
                       '(pyscf, pymatgen, sfepy, scikit-fem) as an '
                       'isle app; every Polari instance\'s '
                       'materials seams resolve it automatically '
                       'once deployed. Data page: /engines/msci.',
        'kind': 'mesh-app',
        'source_ref': 'docker-compose.msci-engines.yml',
        'service': 'prf-msci-engines', 'port': 9500,
        'provides_engine': 'msci', 'category': 'engine',
        'source': 'official',
    },
    {
        'name': 'cad-engines',
        'title': 'CAD engines (trimesh / FreeCAD)',
        'description': 'The mesh/CAD worker (trimesh + optional '
                       'FreeCAD/OpenCASCADE) as an isle app; '
                       'mathshapes seams resolve it automatically '
                       'once deployed. Data page: /engines/cad.',
        'kind': 'mesh-app',
        'source_ref': 'docker-compose.cad-engines.yml',
        'service': 'prf-cad-engines', 'port': 9600,
        'provides_engine': 'cad', 'category': 'engine',
        'source': 'official',
    },
]


def polari_app_options(app_rows, shell_rows, taken_names):
    """sep-3 (§43, decision 7): PolariAppDefinition rows PROJECTED
    into the store as OPTIONS — derived at read time, never persisted
    catalog rows, so app counts can balloon without the catalog
    growing state. Markers: standard (seeded), defined_at (this core
    holds the isle-level definitions), converted (a scope=app
    AppShellDefinition exists) + its shell name. Launcher debs
    MATERIALIZE at install time — options, not shelved artifacts.
    Pure function; rows may be objects or dicts via getattr."""
    def field(row, name, default=''):
        return getattr(row, name, default)
    shells_by_app = {}
    for s in shell_rows:
        if field(s, 'scope') == 'app' and field(s, 'app_name'):
            shells_by_app.setdefault(field(s, 'app_name'),
                                     field(s, 'name'))
    options = []
    for a in app_rows:
        name = field(a, 'name')
        if not name or name in taken_names:
            continue
        try:
            import json as _json
            modules = _json.loads(field(a, 'modules_json', '[]')
                                  or '[]')
        except ValueError:
            modules = []
        shell = shells_by_app.get(name, '')
        options.append({
            'name': name,
            'title': field(a, 'title'),
            'description': field(a, 'use_case')
            or field(a, 'description'),
            'kind': 'polari-app-option',
            'category': 'polari-app',
            'derived': True,
            'standard': bool(field(a, 'is_prior', False)),
            'defined_at': 'isle-core',
            'converted': bool(shell),
            'shell': shell,
            'modules': modules,
            'source': 'derived',
        })
    options.sort(key=lambda o: o['name'])
    return options


def ai_tool_options(tool_rows, taken_names):
    """ai-2 (decision 1): AiToolDefinition rows PROJECTED into the
    store as the DEDICATED AI section — derived at read time (the
    sep-3 pattern: rows stay in appstore, the section derives; never
    persisted catalog rows). Every entry states its hosting kind and
    sovereignty facts (decision 6) plus a linkage summary; the full
    readiness join lives on /api/appstore/ai-tools. Pure function;
    rows may be objects or dicts."""
    import json as _json

    def field(row, name, default=''):
        if isinstance(row, dict):
            return row.get(name, default)
        return getattr(row, name, default)
    options = []
    for t in tool_rows:
        name = field(t, 'name')
        if (not name or name in taken_names
                or not field(t, 'published', True)):
            continue
        try:
            linkages = _json.loads(field(t, 'linkages_json', '[]')
                                   or '[]')
        except ValueError:
            linkages = []
        options.append({
            'name': name,
            'title': field(t, 'title'),
            'description': field(t, 'description'),
            'kind': 'ai-tool',
            'category': 'ai',
            'derived': True,
            'hosting': field(t, 'hosting'),
            'api_family': field(t, 'api_family'),
            'provider_name': field(t, 'provider_name'),
            'internet_required': bool(field(t, 'internet_required',
                                            False)),
            'data_leaves_isle': bool(field(t, 'data_leaves_isle',
                                           False)),
            'source_ref': field(t, 'source_ref'),
            'linkages': [{'kind': l.get('kind', ''),
                          'status': l.get('status', '')}
                         for l in linkages],
            'detail': '/api/appstore/ai-tools/%s' % name,
            'source': 'derived',
        })
    options.sort(key=lambda o: o['name'])
    return options


def ai_tool_install_plan(option):
    """ai-2: the install path per HOSTING KIND. built-in → nothing;
    remote-intermediary → the /ai/providers binding flow (the
    credential is entered by a HUMAN — never through an AI channel,
    never into git); local-hosted → the isle app deploy whose
    --engine declaration the ai-3 binder wires automatically."""
    hosting = option.get('hosting', '')
    name = option.get('name', '')
    provider = option.get('provider_name', '')
    if hosting == 'built-in':
        return {'ok': True, 'steps': [],
                'note': 'built in — always available, nothing to '
                        'install'}
    if hosting == 'remote-intermediary':
        return {'ok': True, 'steps': [
            'POST /ai/providers {"action": "select", '
            '"provider": "%s"}' % provider,
            'POST /ai/providers {"action": "set_auth", '
            '"provider": "%s", "secret": <entered by a human — '
            'never via the AI channel, never into git>}' % provider,
            'POST /ai/providers {"action": "validate", '
            '"provider": "%s"}' % provider,
        ], 'note': 'a thin binding to a remote server over the '
                   'internet — installing = selecting + '
                   'authenticating the provider; data leaves the '
                   'isle (privacy-filter recommended upstream)'}
    if hosting == 'local-hosted':
        image = option.get('source_ref', '')
        return {'ok': True, 'steps': [
            'isle app deploy %s --image %s --service %s '
            '--port 8080 --engine reasoning' % (name, image, name),
        ], 'note': 'deploys %s as an .isle app; the reasoning '
                   'binder auto-wires every polari instance\'s '
                   'assistant to it (ai-3), no redeploy' % name}
    return {'ok': False, 'steps': [],
            'note': 'unknown hosting kind %r' % hosting}


def option_install_plan(option):
    """The convert/install path for one derived app option — ONE
    command either way (`pol apps shell <name>` is idempotent: row
    reused when it exists, registration re-emitted, deb rebuilt)."""
    name = option.get('name', '')
    steps = ['pol apps shell %s' % name]
    if option.get('converted'):
        note = ('launcher row exists (%s) — re-emits the '
                'registration and rebuilds the deb at install time'
                % option.get('shell', ''))
    else:
        note = ('creates the scope=app AppShellDefinition row, '
                'emits the registration, and builds the launcher '
                'deb AT INSTALL TIME (options, never a shelf of '
                'pre-built artifacts)')
    return {'ok': True, 'steps': steps, 'note': note}


def modules_of(row):
    """The MODULES a polari instance runs, from its schema-tolerant
    modes strings ('modules:a,b,c'). [] when unreported."""
    for mode in (row.get('modes') or []):
        m = str(mode)
        if m.startswith('modules:'):
            return sorted(x for x in m[len('modules:'):].split(',')
                          if x)
    return []


def instances_of(app_rows, entry_name):
    """Running INSTANCES of one catalog entry across the isle, from
    per-device app rows (each: name / device_name / domain /
    is_mock). Matches the entry's name or a duplicate suffix
    ('whoami', 'whoami-2', ...). Duplicates are DELIBERATE —
    scaling is a genuine need (polari itself) — this is the
    tracking half: how many, on which devices. Pure function."""
    import re
    pattern = re.compile(r'^%s(-\d+)*$' % re.escape(entry_name))
    found = []
    for row in app_rows:
        if row.get('is_mock'):
            continue
        app_name = row.get('name', '')
        if pattern.match(app_name):
            found.append({'app': app_name,
                          'device': row.get('device_name', ''),
                          'domain': row.get('domain', ''),
                          'modules': modules_of(row)})
    found.sort(key=lambda i: (i['app'], i['device']))
    return found


def resolve_app_placement(app_name, modules_needed, instances):
    """The APP-PLACEMENT RESOLVER (Dustin): a polari-app is a MODULE
    COLLECTION; installing it means ENSURING every module is live on
    SOME instance across the isle (one or several — the app works
    either way). Pure: given the app's modules and the current
    placement, return what's satisfied, what's missing, and a PLAN
    (isle verbs the human runs — propose-then-apply).

    instances: [{name, device, modules:[...]}, ...] (deployed polari
    instances; the core is name 'polari').
    """
    placed = {}  # module -> [instance names that carry it]
    for inst in instances:
        for m in (inst.get('modules') or []):
            placed.setdefault(m, []).append(inst.get('name', ''))

    satisfied, missing = [], []
    for m in modules_needed:
        if placed.get(m):
            satisfied.append({'module': m, 'instances': placed[m]})
        else:
            missing.append(m)

    # target for the missing ones: prefer a DEPLOYED instance that
    # already carries some of this app's modules (co-locate), else
    # the deployed instance with the fewest modules (spread load),
    # else suggest a new instance. The core is a valid host too.
    deployed = [i for i in instances]
    plan = []
    if missing:
        best = None
        if deployed:
            def score(i):
                mods = set(i.get('modules') or [])
                return (-len(mods & set(modules_needed)),
                        len(mods))
            best = sorted(deployed, key=score)[0].get('name', '')
        for m in missing:
            if best:
                plan.append({
                    'action': 'add-module', 'module': m,
                    'target': best,
                    'cmd': 'isle polari module add %s --to %s'
                           % (m, best)})
            else:
                plan.append({
                    'action': 'deploy-instance', 'module': m,
                    'target': '(new)',
                    'cmd': 'isle polari instance deploy --modules %s'
                           % m})
    return {
        'app': app_name,
        'modules_needed': list(modules_needed),
        'satisfied': satisfied,
        'missing': missing,
        'complete': not missing,
        'plan': plan,
    }


def install_plan(entry):
    """Build the ordered host commands to install one entry (a dict
    of its fields). Returns {'ok', 'steps': [cmd,...], 'note'} — the
    isle CLI runs `steps` on the host. No side effects here."""
    kind = entry.get('kind', '')
    name = entry.get('name', '')
    ref = entry.get('source_ref', '')
    if kind == 'mesh-app':
        # arbitrary compose/image → the deploy pipeline
        args = ['isle app deploy %s' % name]
        # a compose REF is a file path (.yml/.yaml) or a URL;
        # anything else is an IMAGE (the CLI synthesizes a one-
        # service compose). 'odoo:16' and 'traefik/whoami:latest'
        # are both images; 'stack.yml' / 'https://…' are compose.
        if ref.endswith(('.yml', '.yaml')) or '://' in ref:
            args.append('--compose %s' % ref)
        else:
            args.append('--image %s' % ref)
        if entry.get('service'):
            args.append('--service %s' % entry['service'])
        if entry.get('port'):
            args.append('--port %d' % entry['port'])
        if entry.get('domain'):
            args.append('--domain %s' % entry['domain'])
        if entry.get('provides_engine'):
            args.append('--engine %s' % entry['provides_engine'])
        return {'ok': True, 'steps': [' '.join(args)],
                'note': 'deploys %s as an .isle app%s' % (
                    name, ' (+ engine %s)' % entry['provides_engine']
                    if entry.get('provides_engine') else '')}
    if kind == 'polari-app':
        # ONE command: build + install a native launcher sharing the
        # one polari-shell-core runtime (feels native, §32). The
        # verb ensures the shared core first.
        title = entry.get('title', name)
        return {'ok': True, 'steps': [
            'isle shell launcher --name %s --title %r --url %s '
            '--install' % (name, title, ref),
        ], 'note': 'installs %s as a NATIVE-feeling app (shares '
                   'polari-shell-core)' % title}
    if kind == 'polari-instance':
        # a NEW polari instance deployed as a mesh-app on THIS
        # device (the topology-manipulation-as-install seam): the
        # verb auto-names it (polari-2, ...), pulls prf images from
        # the mesh registry if absent, registers <name>.isle +
        # api.<name>.isle behind the local agent.
        return {'ok': True, 'steps': [
            'isle polari instance deploy --modules islemesh',
        ], 'note': 'deploys a NEW polari instance (backend + '
                   'frontend) behind THIS device\'s agent — add '
                   '--name/--modules to customize'}
    if kind == 'polari-module':
        # a polari module installed into the local instance via the
        # module .deb (mac-8) or, until the deb repo lands, the
        # topology assign path.
        mod = ref or name
        return {'ok': True, 'steps': [
            'isle module install %s' % mod,
        ], 'note': 'installs the %s polari module' % mod}
    return {'ok': False, 'steps': [],
            'note': 'unknown catalog kind %r' % kind}
