"""
@module appstore.appstore_ai

ai-0: AI tools as FIRST-CLASS store citizens (AI_TOOL_LINKAGES_PLAN
decisions 1-6). An AiToolDefinition row says WHAT an AI tool is
(hosting kind, API family), WHICH Polari seams it can plug into
(its linkage claims, each honestly `proven` or `feasible`), and its
sovereignty facts (internet_required / data_leaves_isle) — never
whether it is ready RIGHT NOW: live readiness joins at read time
from the managed reasoning config (appstore_ai_api).

The linkage vocabulary is CODE (tracked), like PROVIDER_REGISTRY:
each kind names its CONSUMER (the Polari seam/knob it wires) and
whether that seam exists today (`live`) or is a planned wire
(`unbuilt`) — feasibility claims are honest, never implied working.

@consumers
  - appstore.appstore_ai_api (/api/appstore/ai-tools)
  - islemesh.islemesh_catalog (ai-2: the derived store section)
  - polariServer defClassList (table + CRUDE)
  - appstore.selftest_appstore
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: Decision 2 — the hosting kinds, stated on every tile.
#: remote-intermediary = a thin binding to a remote server over the
#: internet (claude, codex/openai); local-hosted = a container on
#: the isle (LocalAI); built-in = ships with polari (the null
#: fallback rides along for honesty — always available, no LLM).
HOSTING_KINDS = ('remote-intermediary', 'local-hosted', 'built-in')

#: Which wire format the tool speaks (maps to the reasoning
#: providers; 'none' = not an API at all, e.g. the built-in null).
API_FAMILIES = ('anthropic', 'openai', 'openai-compatible', 'none')

#: Decision 4 — per-linkage claim statuses. `proven` = the wire is
#: exercised code today; `feasible` = the wire exists but this pair
#: is unproven. Live readiness is a SEPARATE fact (joined at read).
LINKAGE_STATUSES = ('proven', 'feasible')

#: Decision 3 — the linkage VOCABULARY: the places an AI can plug
#: into Polari, as named kinds. Each names its consumer seam + knob
#: and whether the Polari side of the wire exists (`seam`: 'live' |
#: 'unbuilt'). A tool's linkages_json may only claim kinds from here.
AI_LINKAGES = {
    'reasoning-chat': {
        'title': 'Assistant chat (reasoning)',
        'consumer': 'the in-app assistant seam '
                    '(polariApiServer.reasoning_provider)',
        'knob': 'POLARI_REASONING_PROVIDER / the managed reasoning '
                'config (/ai/providers select)',
        'seam': 'live',
    },
    'tool-calling': {
        'title': 'Gated tool-calling (proposals)',
        'consumer': 'the assistant\'s gated proposals '
                    '(polariApiServer.ai_tools — propose-then-'
                    'confirm, same wire as reasoning-chat)',
        'knob': 'rides the reasoning-chat selection',
        'seam': 'live',
    },
    'stt': {
        'title': 'Speech-to-text',
        'consumer': 'assistant panel voice input — today browser '
                    'Web Speech (Chrome STT is CLOUD-backed); the '
                    'sovereign path is /v1/audio/transcriptions',
        'knob': 'none yet (ai-4 builds the provider-backed path)',
        'seam': 'unbuilt',
    },
    'tts': {
        'title': 'Text-to-speech',
        'consumer': 'assistant panel voice output — today browser '
                    'Web Speech; the sovereign path is '
                    '/v1/audio/speech',
        'knob': 'none yet (ai-4 builds the provider-backed path)',
        'seam': 'unbuilt',
    },
    'embeddings': {
        'title': 'Embeddings',
        'consumer': 'future search over rows (/v1/embeddings) — no '
                    'Polari consumer exists yet',
        'knob': 'none yet',
        'seam': 'unbuilt',
    },
    'vision': {
        'title': 'Vision (image understanding)',
        'consumer': 'image understanding in the assistant — no '
                    'Polari seam sends an image yet',
        'knob': 'none yet',
        'seam': 'unbuilt',
    },
    '3d-reconstruction': {
        'title': '3D reconstruction',
        'consumer': 'the scanning revival engines (free-splatter'
                    '.cpp / depth-anything.cpp as LocalAI sibling '
                    'ports) — the scanning arc is SHELVED on '
                    'dev-scan-1',
        'knob': 'none yet',
        'seam': 'unbuilt',
    },
    'realtime-voice': {
        'title': 'Realtime voice (speech-to-speech)',
        'consumer': 'assistant speech-to-speech (the Realtime API) '
                    '— no Polari seam exists yet',
        'knob': 'none yet',
        'seam': 'unbuilt',
    },
}


class AiToolDefinition(treeObject):
    """One AI tool as a store citizen: hosting + API family + its
    honest linkage claims + sovereignty facts. Live readiness is
    NEVER stored here — it joins at read time from the managed
    reasoning config (decision 4)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('claude', 'localai').
        name: str = '',
        title: str = '',
        description: str = '',
        # HOSTING_KINDS entry.
        hosting: str = 'remote-intermediary',
        # API_FAMILIES entry.
        api_family: str = 'none',
        # PROVIDER_REGISTRY key when this tool IS a reasoning
        # provider ('' otherwise) — the join key for live readiness.
        provider_name: str = '',
        # JSON list of {kind, status, note} — kind from AI_LINKAGES,
        # status from LINKAGE_STATUSES.
        linkages_json: str = '[]',
        # Decision 6 — sovereignty stated on every tile.
        internet_required: bool = False,
        data_leaves_isle: bool = False,
        # API domain (remote) or container image (local-hosted);
        # '' for built-in.
        source_ref: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.hosting = hosting
        self.api_family = api_family
        self.provider_name = provider_name
        self.linkages_json = linkages_json
        self.internet_required = internet_required
        self.data_leaves_isle = data_leaves_isle
        self.source_ref = source_ref
        self.published = published
        self.is_prior = is_prior
        self.notes = notes


def tool_report(row, provider_status=None, active_provider=''):
    """ai-1: one tool row joined with the vocabulary + LIVE
    readiness. Pure — row may be an object or a dict; readiness is
    the caller's provider_status dict (None when the tool is not a
    reasoning provider, or when reasoning_config is unavailable in
    this context — both stated, never guessed)."""
    def field(name, default=''):
        if isinstance(row, dict):
            return row.get(name, default)
        return getattr(row, name, default)

    try:
        linkages = json.loads(field('linkages_json', '[]') or '[]')
    except ValueError:
        linkages = []
    for link in linkages:
        vocab = AI_LINKAGES.get(link.get('kind'), {})
        link['consumer'] = vocab.get('consumer',
                                     '(unknown linkage kind)')
        link['seam'] = vocab.get('seam', 'unknown')
        link['knob'] = vocab.get('knob', '')

    provider = field('provider_name')
    readiness = None
    if provider and provider_status:
        readiness = {
            'sdk_installed': provider_status.get('sdk_installed'),
            'has_credential': provider_status.get('has_credential'),
            'needs_base_url': provider_status.get('needs_base_url'),
            'ready': provider_status.get('ready'),
            'needs': provider_status.get('needs', []),
            'settings': provider_status.get('settings', {}),
        }
    if readiness is not None:
        readiness_note = ''
    elif not provider:
        readiness_note = ('not a reasoning provider — no live '
                          'readiness probe')
    else:
        readiness_note = ('reasoning_config unavailable in this '
                          'context')

    report = {
        'name': field('name'),
        'title': field('title'),
        'description': field('description'),
        'hosting': field('hosting'),
        'api_family': field('api_family'),
        'provider_name': provider,
        'internet_required': bool(field('internet_required', False)),
        'data_leaves_isle': bool(field('data_leaves_isle', False)),
        'source_ref': field('source_ref'),
        'linkages': linkages,
        'readiness': readiness,
        'readiness_note': readiness_note,
        'active': bool(provider) and provider == active_provider,
        'published': bool(field('published', True)),
    }
    # Decision 6 / open question 1: badge + knob (knob-and-suggestion
    # discipline), never a forced gate unless Dustin decides so.
    if field('hosting') == 'remote-intermediary':
        report['privacy_recommendation'] = (
            'data leaves the isle — route through the privacy-'
            'filter gate once it is hosted (recommendation badge; '
            'forcing it is an open question for Dustin)')
    return report
