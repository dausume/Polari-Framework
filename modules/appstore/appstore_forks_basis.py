"""
@module appstore.appstore_forks_basis

ai-9 (Dustin: "do we have forks of the projects we would need to
self-host... and a page for notating all of that"): the FORK-PIN
LEDGER — every upstream this project pins as a fork under
github.com/dausume/, as dated rows. The fork-as-pin rule exists
because upstream can relicense (the rns lesson: relicensed
GPLv3-INCOMPATIBLE 2025-04-15); a fork cannot be retroactively
changed. verified_at is the date the fork's EXISTENCE was last
checked against GitHub — the ai-7 dated-price discipline applied
to software.

Statuses are honest: 'forked' (pin exists, verified),
'delete-pending' (forked in error, awaiting Dustin's delete — the
CLI token lacks delete_repo), 'not-pinned' (a dependency we rely
on WITHOUT our own pin yet — named so the gap is visible, never
implied covered).

@consumers
  - appstore.appstore_ai_api (/api/appstore/ai-tools/fork-pins)
  - polari-platform-angular /ai-hosting (the software section)
  - polariServer defClassList (table + CRUDE)
  - appstore.appstore_selftest
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: What role a pin plays in the self-host stack.
FORK_ROLES = ('server', 'text', 'speech-in', 'speech-out',
              'meeting-audio', 'vision', '3d', 'mesh', 'other')

FORK_STATUSES = ('forked', 'delete-pending', 'not-pinned')


class ForkPin(treeObject):
    """One pinned (or honestly not-pinned) upstream."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key = repo name ('LocalAI').
        name: str = '',
        title: str = '',
        upstream_url: str = '',
        fork_url: str = '',
        # Code license (weights carry their own — check both).
        license: str = '',
        # FORK_ROLES entry.
        role: str = 'other',
        # FORK_STATUSES entry.
        status: str = 'forked',
        # Runs usefully on CPU (the 6338N-class question).
        cpu_ok: bool = False,
        # What it serves in polari terms.
        needed_for: str = '',
        # When the fork's existence was last VERIFIED on GitHub.
        verified_at: str = '',
        notes: str = '',
        published: bool = True,
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.title = title
        self.upstream_url = upstream_url
        self.fork_url = fork_url
        self.license = license
        self.role = role
        self.status = status
        self.cpu_ok = cpu_ok
        self.needed_for = needed_for
        self.verified_at = verified_at
        self.notes = notes
        self.published = published
        self.is_prior = is_prior


def fork_pins_payload(rows):
    """The page payload: pins grouped nothing — a flat dated list
    the UI groups by role. Pure over rows (objects or dicts)."""
    def field(row, name, default=''):
        if isinstance(row, dict):
            return row.get(name, default)
        return getattr(row, name, default)
    pins = []
    for r in rows:
        if not field(r, 'published', True):
            continue
        pins.append({
            'name': field(r, 'name'),
            'title': field(r, 'title'),
            'upstream_url': field(r, 'upstream_url'),
            'fork_url': field(r, 'fork_url'),
            'license': field(r, 'license'),
            'role': field(r, 'role'),
            'status': field(r, 'status'),
            'cpu_ok': bool(field(r, 'cpu_ok', False)),
            'needed_for': field(r, 'needed_for'),
            'verified_at': field(r, 'verified_at'),
            'notes': field(r, 'notes'),
        })
    pins.sort(key=lambda p: (p['status'] != 'forked', p['role'],
                             p['name']))
    return {
        'ok': True,
        'count': len(pins),
        'pins': pins,
        'honesty': ('verified_at is when each fork was last '
                    'CHECKED on GitHub; not-pinned rows are '
                    'dependencies we rely on without our own pin '
                    '— named gaps, not coverage'),
    }


_VERIFIED = '2026-08-16'  # roster checked live via the GitHub API


def _pin(name, title, upstream, license, role, cpu_ok, needed_for,
         notes='', status='forked'):
    return {
        'name': name, 'title': title,
        'upstream_url': upstream,
        'fork_url': ('https://github.com/dausume/%s' % name
                     if status != 'not-pinned' else ''),
        'license': license, 'role': role, 'status': status,
        'cpu_ok': cpu_ok, 'needed_for': needed_for,
        'verified_at': _VERIFIED, 'notes': notes,
        'published': True, 'is_prior': True,
    }


SEED_FORK_PINS = [
    # ---- the server (THE pin for CPU self-hosting) ----
    _pin('LocalAI', 'LocalAI — the self-host server',
         'https://github.com/mudler/LocalAI', 'MIT', 'server',
         True,
         'the local-hosted AI tool: reasoning-chat, tool-calling, '
         'stt/tts, embeddings — the openai_compatible provider\'s '
         'target',
         'THE pin a 6338N-class machine needs; core inference '
         'backends (llama.cpp/whisper.cpp) ride ITS backend '
         'mechanism — see the not-pinned rows'),
    # ---- text ----
    _pin('privacy-filter.cpp', 'Privacy filter',
         'https://github.com/localai-org/privacy-filter.cpp',
         'MIT/Apache family', 'text', True,
         'the recommended gate before text leaves the isle '
         '(remote intermediaries)'),
    _pin('vllm.cpp', 'vllm.cpp — batch text serving',
         'https://github.com/localai-org/vllm.cpp',
         'Apache-2.0', 'text', False,
         'high-throughput text serving (mainly GPU; CPU modes '
         'modest)'),
    # ---- speech in/out (voice sovereignty backends) ----
    _pin('parakeet.cpp', 'Parakeet STT',
         'https://github.com/localai-org/parakeet.cpp',
         'Apache family', 'speech-in', True,
         '/v1/audio/transcriptions inside LocalAI (ai-4 voice)'),
    _pin('moss-transcribe.cpp', 'MOSS transcription',
         'https://github.com/localai-org/moss-transcribe.cpp',
         'Apache/CC-BY-4.0 family', 'speech-in', True,
         'meetings transcription (the future meetings-stt seam)'),
    _pin('moss-tts.cpp', 'MOSS TTS',
         'https://github.com/localai-org/moss-tts.cpp',
         'Apache/CC-BY-4.0 family', 'speech-out', True,
         '/v1/audio/speech inside LocalAI (ai-4 voice)'),
    _pin('voxtral-tts.c', 'Voxtral TTS',
         'https://github.com/localai-org/voxtral-tts.c',
         'Apache family', 'speech-out', True,
         'TTS alternative'),
    # ---- meeting-audio companions ----
    _pin('voice-detect.cpp', 'Voice activity detection',
         'https://github.com/localai-org/voice-detect.cpp',
         'MIT/Apache family', 'meeting-audio', True,
         'meetings: who is speaking / when'),
    _pin('ced.cpp', 'CED audio events',
         'https://github.com/localai-org/ced.cpp',
         'MIT/Apache family', 'meeting-audio', True,
         'meetings: audio event detection'),
    _pin('LocalVQE', 'LocalVQE voice quality',
         'https://github.com/localai-org/LocalVQE',
         'MIT/Apache family', 'meeting-audio', True,
         'meetings: voice quality enhancement'),
    # ---- vision / 3D (the scan-revival engines) ----
    _pin('depth-anything.cpp', 'Depth Anything 3 (metric scenes)',
         'https://github.com/mudler/depth-anything.cpp',
         'MIT (weights: Apache VARIANTS ONLY — 1.0-large is NC)',
         '3d', True,
         'scan revival rev-5: rooms/scenes — dense metric depth '
         '+ poses; glb/COLMAP/PLY export'),
    _pin('free-splatter.cpp', 'FreeSplatter (pose-free objects)',
         'https://github.com/localai-org/free-splatter.cpp',
         'Apache-2.0 (code + weights)', '3d', True,
         'scan revival rev-4 THE engine: 3-4 photos of an object '
         '-> gaussians, no rig, CPU ~14s/pass'),
    _pin('trellis2cpp', 'TRELLIS.2 (image -> mesh)',
         'https://github.com/localai-org/trellis2cpp',
         'MIT (DINOv3 encoder weights need a read)', '3d', False,
         'asset GENERATION (not measurement) — GPU-bound, out of '
         'scan scope by decision'),
    _pin('rf-detr.cpp', 'RF-DETR detection',
         'https://github.com/localai-org/rf-detr.cpp',
         'Apache family', 'vision', True,
         'object detection (future vision linkage)'),
    _pin('animate-any-mesh.cpp', 'Animate Any Mesh',
         'https://github.com/localai-org/animate-any-mesh.cpp',
         'Apache family (weights re-check at adoption)', 'mesh',
         False, 'mesh animation (future)'),
    # ---- forked in error: Dustin's delete pending ----
    _pin('magpie-tts.cpp', 'Magpie TTS (DELETE)',
         'https://github.com/localai-org/magpie-tts.cpp',
         'NVIDIA Open Model License (gated)', 'speech-out', False,
         'nothing — criteria-failing',
         'forked before the criteria clarification; delete needs '
         'gh delete_repo scope (Dustin)', status='delete-pending'),
    _pin('vibevoice.cpp', 'VibeVoice (DELETE)',
         'https://github.com/localai-org/vibevoice.cpp',
         'MIT code but "research purpose" model card', 'speech-out',
         False, 'nothing — ambiguity we do not build a business on',
         'delete pending (Dustin)', status='delete-pending'),
    _pin('face-detect.cpp', 'Face detect (DELETE)',
         'https://github.com/localai-org/face-detect.cpp',
         'n/a', 'vision', False,
         'nothing — no fit + privacy posture',
         'delete pending (Dustin)', status='delete-pending'),
    # ---- named gaps: relied on WITHOUT our own pin ----
    _pin('llama.cpp', 'llama.cpp (LLM inference core)',
         'https://github.com/ggml-org/llama.cpp', 'MIT',
         'server', True,
         'the actual LLM engine inside LocalAI — rides the '
         'LocalAI fork\'s backend mechanism',
         'no dausume/ pin of our own yet — decide whether the '
         'LocalAI fork\'s pinning suffices', status='not-pinned'),
    _pin('whisper.cpp', 'whisper.cpp (STT core)',
         'https://github.com/ggml-org/whisper.cpp', 'MIT',
         'speech-in', True,
         'the STT engine inside LocalAI — same backend mechanism',
         'same open pin decision as llama.cpp',
         status='not-pinned'),
]
