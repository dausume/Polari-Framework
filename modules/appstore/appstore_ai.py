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
        'consumer': 'assistant voice input via /ai/voice/transcribe '
                    '(the provider\'s /v1/audio/transcriptions); '
                    'browser Web Speech is the STATED fallback '
                    '(Chrome STT is cloud-backed)',
        'knob': 'rides the active reasoning provider (openai / '
                'openai_compatible only); stt_model setting',
        'seam': 'live',
    },
    'tts': {
        'title': 'Text-to-speech',
        'consumer': 'assistant voice output via /ai/voice/speak '
                    '(the provider\'s /v1/audio/speech); browser '
                    'speechSynthesis is the fallback',
        'knob': 'rides the active reasoning provider; tts_model / '
                'tts_voice settings',
        'seam': 'live',
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


#: ai-6 (Dustin): when the isle realistically CANNOT host a tool,
#: say so and show the remote-hosting paths — where the user rents
#: infrastructure, hosts the model there, and connects it back to
#: polari (still the openai_compatible provider + a base_url).
#: Sovereignty is TIERED and stated: 'your-cloud' = your rented
#: machine (data leaves the isle but stays on infra you control);
#: 'intermediary' = another party processes your data (the
#: privacy-filter recommendation applies). NEVER price quotes here
#: — prices go stale; honesty says "check current pricing".
CLOUD_HOSTING_OPTIONS = [
    {
        'name': 'gpu-vps',
        'title': 'Rented GPU server '
                 '(e.g. RunPod, Vast.ai, Lambda, Hetzner GPU)',
        'sovereignty': 'your-cloud',
        'how': 'deploy the SAME LocalAI container there, then '
               'connect it in the store: openai_compatible with '
               'base_url = your server\'s https endpoint (key '
               'optional if you firewall it to yourself)',
        'note': 'fast models incl. larger ones; your rented '
                'machine — data leaves the isle but stays on '
                'infrastructure you control. Check current '
                'pricing with the provider.',
    },
    {
        'name': 'cpu-vps',
        'title': 'Ordinary VPS (CPU-only)',
        'sovereignty': 'your-cloud',
        'how': 'same LocalAI container, CPU tag — exactly like '
               'local CPU hosting, just on rented hardware',
        'note': 'good for small quantized models (3-8B) at modest '
                'speed; the cheapest self-controlled path.',
    },
    {
        'name': 'managed-endpoint',
        'title': 'Managed open-model endpoint (e.g. OpenRouter)',
        'sovereignty': 'intermediary',
        'how': 'select openai_compatible with their base_url + '
               'your key in the bind flow',
        'note': 'NOT self-hosting — another party processes your '
                'data (the privacy-filter recommendation applies); '
                'listed for completeness and honesty.',
    },
]


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
        # ai-6: what HOSTING this tool takes, as data —
        # {"profiles": [{name, cores, ram_mb, disk_mb, gpu, note}]}.
        # '' = nothing to host (remote intermediaries, built-in).
        # Guidance, not guarantees — notes say what each profile
        # actually buys.
        requirements_json: str = '',
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
        self.requirements_json = requirements_json
        self.published = published
        self.is_prior = is_prior
        self.notes = notes


def host_check(requirements, machines):
    """ai-6: the honest hosting gauge. Pure — `requirements` is the
    parsed requirements_json ({'profiles': [...]}), `machines` the
    res-1 inventory nodes (camelCase dicts). Verdict per machine x
    profile with the FAILING NUMBERS shown; GPU is honestly
    'untracked' (res-1 has no GPU column — an unknown, never a
    guessed yes). `realistic` = some machine fully fits some
    profile; 'tight' (RAM exists but currently in use) is stated,
    not rounded up to a yes."""
    profiles = (requirements or {}).get('profiles') or []
    if not profiles:
        return {'ok': False,
                'error': 'this tool declares no hosting '
                         'requirements — nothing to gauge'}
    checked, unknown = [], []
    best = None
    any_fit, any_tight = False, False
    for m in machines:
        if not m.get('hasSpecs'):
            unknown.append(m.get('name', '?'))
            continue
        rows = []
        for p in profiles:
            detail = []
            verdict = 'fits'
            cores = m.get('logicalCpus') or 0
            if cores < (p.get('cores') or 0):
                verdict = 'no'
                detail.append('cores: %s < %s needed'
                              % (cores, p['cores']))
            total = m.get('totalRamMb') or 0
            avail = m.get('availableRamMb') or 0
            need_ram = p.get('ram_mb') or 0
            if total < need_ram:
                verdict = 'no'
                detail.append('RAM: %.0f MB total < %s MB needed'
                              % (total, need_ram))
            elif avail < need_ram and verdict != 'no':
                verdict = 'tight'
                detail.append('RAM: %s MB needed, only %.0f MB '
                              'free right now (total %.0f MB — '
                              'freeing memory would fit it)'
                              % (need_ram, avail, total))
            free_disk = m.get('freeDiskMb') or 0
            need_disk = p.get('disk_mb') or 0
            if free_disk < need_disk:
                verdict = 'no'
                detail.append('disk: %.0f MB free < %s MB needed '
                              '(models are large)'
                              % (free_disk, need_disk))
            if p.get('gpu') and verdict != 'no':
                # ai-7: a machine dict may DECLARE its GPU (rented
                # options do); res-1 machines don't carry the key —
                # for them the honest answer stays 'untracked'.
                declared = m.get('gpu')
                if declared is True:
                    pass  # requirement satisfied, verdict stands
                elif declared is False:
                    verdict = 'no'
                    detail.append('needs a GPU — this option '
                                  'declares none')
                else:
                    verdict = 'unknown-gpu'
                    detail.append('needs a GPU — the resource '
                                  'inventory does not track GPUs, '
                                  'so this cannot be confirmed '
                                  'here')
            rows.append({'profile': p.get('name', ''),
                         'verdict': verdict, 'detail': detail})
            if verdict == 'fits':
                any_fit = True
                if best is None:
                    best = {'machine': m.get('name', ''),
                            'profile': p.get('name', '')}
            elif verdict == 'tight':
                any_tight = True
        checked.append({
            'name': m.get('name', ''),
            'source': m.get('resourceSource', ''),
            'observedAt': m.get('resourceObservedAt', ''),
            'profiles': rows,
        })
    if any_fit:
        note = ('realistic — %s can host the "%s" profile'
                % (best['machine'], best['profile']))
    elif any_tight:
        note = ('tight — the hardware exists but is busy; free '
                'RAM/disk or pick a quieter box, else host '
                'remotely (options below)')
    elif checked:
        note = ('NOT realistic on any observed machine — host the '
                'model remotely (your rented server, options '
                'below) and connect it to polari by base_url')
    else:
        note = ('no machine has OBSERVED resources — refresh the '
                'resource inventory (/api/topology/resources) '
                'before trusting any verdict')
    return {
        'ok': True,
        'requirements': profiles,
        'machines': checked,
        'unknown_machines': unknown,
        'realistic': any_fit,
        'tight': (not any_fit) and any_tight,
        'best': best,
        'note': note,
        'cloud_recommended': not any_fit,
        'cloud': CLOUD_HOSTING_OPTIONS,
    }


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

    try:
        requirements = json.loads(field('requirements_json', '')
                                  or '{}')
    except ValueError:
        requirements = {}

    report = {
        'name': field('name'),
        'title': field('title'),
        'description': field('description'),
        'hosting': field('hosting'),
        'api_family': field('api_family'),
        'provider_name': provider,
        'requirements': requirements.get('profiles', []),
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
