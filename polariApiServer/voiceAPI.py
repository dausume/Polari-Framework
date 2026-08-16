#    Copyright (C) 2020  Dustin Etts
#    GNU GPLv3 — see LICENSE.

"""ai-4: the sovereign voice seam — provider-backed STT/TTS.

GET  /ai/voice                    -> per-direction availability, honest:
                                     which provider serves it, or WHY not
                                     + the stated browser fallback
POST /ai/voice/transcribe         -> audio body (Content-Type audio/*)
                                     -> {ok, text}          (STT)
POST /ai/voice/speak {text}       -> audio bytes            (TTS)

Voice rides the ACTIVE reasoning provider's OpenAI-compatible audio
endpoints (/v1/audio/transcriptions, /v1/audio/speech) — LocalAI
serves both locally (whisper/TTS backends), so with a local provider
the whole voice round-trip stays on the isle. Providers with no
audio API (null, anthropic) refuse honestly and the assistant panel
falls back to browser Web Speech, STATED as cloud-backed (Chrome's
STT ships audio to Google).

Models/voice are knobs on the provider's settings (stt_model,
tts_model, tts_voice — /ai/providers select merges them); defaults
are the OpenAI names LocalAI aliases. Audio content is NEVER logged
or stored; no metering here yet (conflating voice with reasoning
chat in the 'reasoning' usage windows would mislead — a 'voice'
engine entry is future work, stated not implied).
"""

import falcon

from objectTreeDecorators import *

from polariApiServer import reasoning_config

#: Defaults for the OpenAI-compatible audio wire; LocalAI accepts
#: these as model aliases when the matching backends are installed.
DEFAULT_STT_MODEL = 'whisper-1'
DEFAULT_TTS_MODEL = 'tts-1'
DEFAULT_TTS_VOICE = 'alloy'

#: The stated fallback — shown to the user, never silently used.
BROWSER_FALLBACK = ('browser Web Speech (Chrome STT is cloud-'
                    'backed — audio leaves the device)')


def voice_status():
    """Per-direction availability from the ACTIVE provider. Pure
    read; refusals name their reason."""
    cfg = reasoning_config.active_config()
    provider = cfg.get('provider', 'null')
    settings = cfg.get('settings', {}) or {}
    status = reasoning_config.provider_status(provider)
    spec = reasoning_config.PROVIDER_REGISTRY.get(provider, {})

    if provider not in ('openai', 'openai_compatible'):
        why = ('the active provider %r has no audio API — voice '
               'needs an OpenAI-compatible provider (openai, or '
               'openai_compatible e.g. LocalAI)' % provider)
        avail = {'available': False, 'why': why}
        stt, tts = dict(avail), dict(avail)
    elif not status.get('ready'):
        why = ('provider %r not ready: %s'
               % (provider, '; '.join(status.get('needs', []))
                  or 'unknown'))
        stt, tts = ({'available': False, 'why': why},
                    {'available': False, 'why': why})
    else:
        stt = {'available': True,
               'model': settings.get('stt_model', DEFAULT_STT_MODEL)}
        tts = {'available': True,
               'model': settings.get('tts_model', DEFAULT_TTS_MODEL),
               'voice': settings.get('tts_voice',
                                     DEFAULT_TTS_VOICE)}
    # sovereignty is a stated FACT: local only when the audio goes
    # to a base_url (a server the admin points at), not api.openai.com
    sovereign = (provider == 'openai_compatible'
                 and bool(settings.get('base_url')))
    return {
        'ok': True,
        'provider': provider,
        'stt': stt,
        'tts': tts,
        'sovereign': sovereign,
        'sovereignty_note': (
            'audio goes to the configured base_url — on-isle when '
            'that server is (LocalAI)' if sovereign else
            'audio leaves the isle (remote provider)' if
            stt.get('available') else
            'no provider-backed voice — the browser fallback is '
            'cloud-backed for STT'),
        'fallback': BROWSER_FALLBACK,
        'description': spec.get('description', ''),
    }


def _client():
    """The OpenAI-wire client for the active provider (the
    OpenAIReasoningProvider construction rules)."""
    import openai
    cfg = reasoning_config.active_config()
    provider = cfg['provider']
    settings = cfg.get('settings', {}) or {}
    secret = reasoning_config.get_secret(provider)
    kwargs = {}
    if secret:
        kwargs['api_key'] = secret
    elif settings.get('base_url'):
        kwargs['api_key'] = 'not-needed'  # local servers ignore it
    if settings.get('base_url'):
        kwargs['base_url'] = settings['base_url']
    return openai.OpenAI(**kwargs), settings


class voiceAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/ai/voice'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/ai/voice', self, suffix='status')
            add('/ai/voice/transcribe', self, suffix='transcribe')
            add('/ai/voice/speak', self, suffix='speak')

    def _refuse(self, response, error, status=falcon.HTTP_400):
        response.status = status
        response.media = {'ok': False, 'error': error,
                          'fallback': BROWSER_FALLBACK}
        response.set_header('Powered-By', 'Polari')

    def on_get_status(self, request, response):
        response.media = voice_status()
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')

    def on_post_transcribe(self, request, response):
        status = voice_status()
        if not status['stt']['available']:
            return self._refuse(response, status['stt']['why'])
        audio = request.bounded_stream.read()
        if not audio:
            return self._refuse(response,
                                'empty body — POST the audio bytes '
                                'with an audio/* Content-Type')
        # filename extension steers server-side decoding; derive it
        # from the Content-Type (MediaRecorder sends audio/webm).
        ctype = (request.content_type or 'audio/webm').split(';')[0]
        ext = ctype.split('/')[-1] or 'webm'
        try:
            client, settings = _client()
            result = client.audio.transcriptions.create(
                model=settings.get('stt_model', DEFAULT_STT_MODEL),
                file=('speech.%s' % ext, audio, ctype))
            text = getattr(result, 'text', '') or ''
        except Exception as exc:  # noqa: BLE001 — refuse honestly
            return self._refuse(
                response, 'transcription failed: %s: %s'
                % (type(exc).__name__, exc))
        response.media = {'ok': True, 'text': text}
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')

    def on_post_speak(self, request, response):
        status = voice_status()
        if not status['tts']['available']:
            return self._refuse(response, status['tts']['why'])
        try:
            body = request.get_media() or {}
        except Exception as err:
            return self._refuse(response,
                                'expected JSON body: %s' % err)
        text = (body.get('text') or '').strip()
        if not text:
            return self._refuse(response,
                                "speak requires 'text'")
        try:
            client, settings = _client()
            result = client.audio.speech.create(
                model=settings.get('tts_model', DEFAULT_TTS_MODEL),
                voice=body.get('voice')
                or settings.get('tts_voice', DEFAULT_TTS_VOICE),
                input=text)
            audio = result.read() if hasattr(result, 'read') \
                else getattr(result, 'content', b'')
        except Exception as exc:  # noqa: BLE001 — refuse honestly
            return self._refuse(
                response, 'speech synthesis failed: %s: %s'
                % (type(exc).__name__, exc))
        response.data = audio
        response.content_type = 'audio/mpeg'
        response.status = falcon.HTTP_200
        response.set_header('Powered-By', 'Polari')
