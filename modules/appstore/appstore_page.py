"""
@module appstore.appstore_page

The /display/app-store no-code page: pure DisplayDefinition data over
the two generic components (module_pages_seed idiom) — the catalog
and identity panels plus the enrollment/installation ledgers. A
future Angular store page replaces this; until then the store is
browsable with zero frontend work.
"""

from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_APPSTORE_PAGE_DISPLAYS = [
    _page(
        'app-store-home', 'app-store',
        'Polari App Store: installable shells over this instance '
        '(catalog + reachability identity), enrollment tokens and '
        'registered installs.',
        'AppShellDefinition',
        [
            # /api/appstore carries two record tables (shells, apps);
            # each gets its own STRUCTURED panel — no JSON wall.
            _row(0, [
                _sapi('appstore-catalog', 0, 4, 'Catalog: shells',
                      '/api/appstore', pick='shells'),
                _sapi('appstore-apps', 1, 4, 'Catalog: installable apps',
                      '/api/appstore', pick='apps'),
                _sapi('appstore-identity', 2, 4,
                      'Instance identity (the shell probe)',
                      '/api/appstore/identity'),
            ]),
            _row(1, [
                _table('appstore-shells', 0, 6, 'Shell definitions',
                       'AppShellDefinition'),
                _table('appstore-artifacts', 1, 6, 'Artifacts',
                       'ShellArtifact'),
            ]),
            _row(2, [
                _table('appstore-enrollments', 0, 6,
                       'Enrollments (hashes never shown)',
                       'ShellEnrollment',
                       columns='name,shell_name,username,status,'
                               'created_at,expires_at,redeemed_at'),
                _table('appstore-installs', 1, 6,
                       'Registered installs', 'ShellInstallation'),
            ]),
        ]),
]
