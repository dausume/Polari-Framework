"""
@module appstore.appstore_seed

Store-entry seeds. Deliberately only TWO rows: the whole-instance
shell every instance can serve, and one scope='app' exemplar bound
to a seeded PolariAppDefinition. The catalog DERIVES installability
for every other PolariAppDefinition row — un-shelled apps list with
installable=False + the affordance to publish one, so seeding a
shell per app would be duplicate state, not coverage.

Seeded through moduleService.seed_upsert (is_prior discipline): rows a
person edits (is_prior=False) are never touched again.

ai-0 adds SEED_AI_TOOLS: the four tools Dustin named, with honest
per-linkage claims (appstore_ai holds the vocabulary + class).
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

#: ai-0 — the four tools Dustin named (plan decision 2): the
#: built-in null rides along for honesty; claude + openai are
#: remote intermediaries (openai covers Codex — one row, both ride
#: the same provider, plan open question 2); localai is the
#: local-hosted family. Linkage claims are honest: `proven` = the
#: wire is exercised code today, `feasible` = the wire exists but
#: this pair is unproven. Live readiness joins at read time.
SEED_AI_TOOLS = [
    {
        'name': 'null',
        'title': 'Built-in responder (no LLM)',
        'description': 'The deterministic node-aware responder '
                       'polari ships with — always available, no '
                       'model, nothing leaves the process. Listed '
                       'for honesty: the assistant works without '
                       'any AI tool installed.',
        'hosting': 'built-in',
        'api_family': 'none',
        'provider_name': 'null',
        'linkages_json': '[{"kind": "reasoning-chat", '
                         '"status": "proven", '
                         '"note": "deterministic replies, no LLM"}]',
        'internet_required': False,
        'data_leaves_isle': False,
        'source_ref': '',
        'published': True,
        'is_prior': True,
        'notes': 'seed: the always-ready fallback',
    },
    {
        'name': 'claude',
        'title': 'Claude (Anthropic)',
        'description': 'A REMOTE INTERMEDIARY: a thin binding that '
                       'talks to Anthropic\'s servers over the '
                       'internet. Nothing runs locally; the '
                       'credential is entered by a human via '
                       '/ai/providers set_auth, never stored in '
                       'git or an AI channel.',
        'hosting': 'remote-intermediary',
        'api_family': 'anthropic',
        'provider_name': 'anthropic',
        'linkages_json': '['
                         '{"kind": "reasoning-chat", '
                         '"status": "proven", '
                         '"note": "AnthropicReasoningProvider"}, '
                         '{"kind": "tool-calling", '
                         '"status": "proven", '
                         '"note": "gated proposals via '
                         'ai_tools.anthropic_tools"}, '
                         '{"kind": "vision", '
                         '"status": "feasible", '
                         '"note": "the messages API accepts '
                         'images; no polari seam sends one yet"}'
                         ']',
        'internet_required': True,
        'data_leaves_isle': True,
        'source_ref': 'https://api.anthropic.com',
        'published': True,
        'is_prior': True,
        'notes': 'seed: remote intermediary — privacy-filter '
                 'recommended upstream (decision 6)',
    },
    {
        'name': 'openai',
        'title': 'OpenAI (Codex / GPT)',
        'description': 'A REMOTE INTERMEDIARY covering Codex and '
                       'the GPT models — one row, both ride the '
                       'same provider. Nothing runs locally; the '
                       'credential is entered by a human via '
                       '/ai/providers set_auth.',
        'hosting': 'remote-intermediary',
        'api_family': 'openai',
        'provider_name': 'openai',
        'linkages_json': '['
                         '{"kind": "reasoning-chat", '
                         '"status": "proven", '
                         '"note": "OpenAIReasoningProvider"}, '
                         '{"kind": "tool-calling", '
                         '"status": "proven", '
                         '"note": "gated proposals via '
                         'ai_tools.openai_tools"}, '
                         '{"kind": "stt", "status": "feasible", '
                         '"note": "whisper API; the /ai/voice seam '
                         'is built (ai-4) — pair unproven until a '
                         'credentialed live call"}, '
                         '{"kind": "tts", "status": "feasible", '
                         '"note": "speech API; same — seam built, '
                         'pair unproven"}, '
                         '{"kind": "embeddings", '
                         '"status": "feasible", '
                         '"note": "no polari consumer yet"}'
                         ']',
        'internet_required': True,
        'data_leaves_isle': True,
        'source_ref': 'https://api.openai.com',
        'published': True,
        'is_prior': True,
        'notes': 'seed: remote intermediary — privacy-filter '
                 'recommended upstream (decision 6)',
    },
    {
        'name': 'localai',
        'title': 'LocalAI (self-hosted)',
        'description': 'The LOCAL-HOSTED family: an MIT-licensed '
                       'OpenAI-compatible server run as an isle '
                       'app — CPU-ok, fully offline once models '
                       'are cached; your data never leaves the '
                       'isle. Backs the assistant through the '
                       'openai_compatible provider (CONFIG, not '
                       'code) and carries the audio/embeddings/'
                       'vision/3D backend family.',
        'hosting': 'local-hosted',
        'api_family': 'openai-compatible',
        'provider_name': 'openai_compatible',
        'linkages_json': '['
                         '{"kind": "reasoning-chat", '
                         '"status": "proven", '
                         '"note": "via the openai_compatible '
                         'provider wire; a LocalAI container has '
                         'not yet been deployed on this isle — '
                         'readiness tells the live truth"}, '
                         '{"kind": "tool-calling", '
                         '"status": "proven", '
                         '"note": "same OpenAI wire format"}, '
                         '{"kind": "stt", "status": "feasible", '
                         '"note": "/v1/audio/transcriptions '
                         '(whisper/parakeet backends); the '
                         '/ai/voice seam is built (ai-4) — pair '
                         'unproven until a live LocalAI"}, '
                         '{"kind": "tts", "status": "feasible", '
                         '"note": "/v1/audio/speech; same — seam '
                         'built, pair unproven"}, '
                         '{"kind": "embeddings", '
                         '"status": "feasible", '
                         '"note": "/v1/embeddings"}, '
                         '{"kind": "vision", '
                         '"status": "feasible", '
                         '"note": "multimodal backends"}, '
                         '{"kind": "3d-reconstruction", '
                         '"status": "feasible", '
                         '"note": "free-splatter.cpp / '
                         'depth-anything.cpp sibling ports; '
                         'scanning arc SHELVED"}'
                         ']',
        'internet_required': False,
        'data_leaves_isle': False,
        'source_ref': 'localai/localai:latest',
        # ai-6: hosting profiles — GUIDANCE grounded in the
        # evaluation (3-8B quantized runs on CPU at modest speed;
        # models are gigabytes each on disk), not guarantees.
        'requirements_json': '{"profiles": ['
            '{"name": "minimal (3-8B quantized, CPU)", '
            '"cores": 4, "ram_mb": 8192, "disk_mb": 20480, '
            '"gpu": false, '
            '"note": "short assistant turns at modest tokens/sec; '
            'each model is ~2-8 GB on disk"}, '
            '{"name": "comfortable (larger/faster, GPU)", '
            '"cores": 8, "ram_mb": 16384, "disk_mb": 61440, '
            '"gpu": true, '
            '"note": "responsive chat + audio/vision backends; '
            '8 GB+ VRAM recommended"}]}',
        'published': True,
        'is_prior': True,
        'notes': 'seed: fork pin dausume/LocalAI '
                 '(LOCALAI_3D_BACKENDS_EVALUATION.md §4b); image '
                 'tag/GPU variant is a deploy-time choice',
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
