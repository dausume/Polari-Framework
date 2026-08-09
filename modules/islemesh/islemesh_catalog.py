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
        'name': 'polari', 'title': 'Polari',
        'description': 'The Polari research OS, as a native-feeling '
                       'shell over its .isle web UI.',
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
        'name': 'odoo', 'title': 'Odoo (business ops)',
        'description': 'Odoo ERP deployed to the isle and wired as '
                       'a Polari business-ops ENGINE automatically.',
        'kind': 'mesh-app', 'source_ref': 'odoo:16',
        'service': 'odoo', 'port': 8069,
        'provides_engine': 'business-ops', 'category': 'engine',
        'source': 'official',
    },
]


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
