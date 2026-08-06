"""
@module appstore.appstore_seed

Store-entry seeds. Deliberately only TWO rows: the whole-instance
shell every instance can serve, and one scope='app' exemplar bound
to a seeded PolariAppDefinition. The catalog DERIVES installability
for every other PolariAppDefinition row — un-shelled apps list with
installable=False + the affordance to publish one, so seeding a
shell per app would be duplicate state, not coverage.

Seeded through composition.seed_upsert (is_prior discipline): rows a
person edits (is_prior=False) are never touched again.
"""

SEED_APP_SHELLS = [
    {
        'name': 'polari-instance-shell',
        'title': 'Polari',
        'description': 'The whole instance as an installable app: '
                       'a native shell (JavaFX + JCEF desktop; '
                       'WebView mobile) that connects to this '
                       'instance, logs in through Keycloak once, '
                       'and renders the full web UI from then on.',
        'scope': 'instance',
        'app_name': '',
        'platforms_json': '["gradle-project", "desktop-linux-x64", "android", "android-vr"]',
        'distribution': 'both',
        'branding_json': '{}',
        'start_route': '',
        'published': True,
        'is_prior': True,
        'notes': 'seed: the default shell every instance serves',
    },
    {
        'name': 'wax-print-shop-shell',
        'title': 'Wax Print Shop',
        'description': 'The wax-print-shop use-case app (tt-12) as '
                       'an installable shell — the scope=app '
                       'exemplar: same shell, navigation clamped to '
                       'one PolariAppDefinition.',
        'scope': 'app',
        'app_name': 'wax-print-shop',
        'platforms_json': '["gradle-project"]',
        'distribution': 'generated-project',
        'branding_json': '{}',
        'start_route': '',
        'published': True,
        'is_prior': True,
        'notes': 'seed: scope=app exemplar over a tt-12 app',
    },
]
