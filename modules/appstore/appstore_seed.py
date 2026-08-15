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

#: sep-5 exemplar behaviors — the plan's own examples as rows. Pure
#: configuration; each names the native half it would need, and the
#: shelved/unbuilt state of that half is SAID, never implied working.
SEED_EDGE_BEHAVIORS = [
    {
        'name': 'lora-radio-attach',
        'title': 'Attach the isle\'s LoRa radio',
        'description': 'Grants the shell the reticulum radio '
                       'passthrough seam (plan §5l: the helper '
                       'holds the privilege, never the shell). '
                       'Devices resolve by DeviceLink '
                       'correspondence, never by raw paths.',
        'kind': 'device',
        'config_json': '{"deviceCorrespondence": "DeviceLink", '
                       '"declaredKind": "lora-radio", '
                       '"exclusive": true}',
        'requires_native': 'radio-passthrough',
        'published': True,
        'is_prior': True,
        'notes': 'seed: native half unbuilt — declaring this today '
                 'gates to an honest refusal naming it',
    },
    {
        'name': 'camera-capture',
        'title': 'Capture from a local camera',
        'description': 'Grants the shell local camera capture (the '
                       'scan arc\'s :capture-desktop precedent — '
                       'that Gradle module is SHELVED on dev-scan-1 '
                       'with the scanning arc).',
        'kind': 'device',
        'config_json': '{"device": "uvc-camera", '
                       '"directPlugOnly": true}',
        'requires_native': 'capture-desktop',
        'published': True,
        'is_prior': True,
        'notes': 'seed: native half shelved with scanning',
    },
    {
        'name': 'isle-wifi-join',
        'title': 'Join a named isle network',
        'description': 'Grants the shell the network-merge seam: '
                       'may join the configured SSID (the "merge '
                       'polari, devices, and networks" example). '
                       'Pure configuration — no native module yet.',
        'kind': 'network',
        'config_json': '{"ssid": "", "band": "any"}',
        'requires_native': '',
        'published': True,
        'is_prior': True,
        'notes': 'seed: ssid is per-isle data, set on a copy',
    },
]

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
        'capabilities_json': '[]',
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
        'capabilities_json': '[]',
        'published': True,
        'is_prior': True,
        'notes': 'seed: scope=app exemplar over a tt-12 app',
    },
]
