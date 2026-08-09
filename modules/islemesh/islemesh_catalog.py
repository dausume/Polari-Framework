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
]


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
