"""
@module appstore.app_debs_page

dl-4: /downloads/apps — every module in the live registry as an
installable deb, GENERATED ON REQUEST (never stored by default; the
deb is a duplicate of content the instance already holds). The page
lists the REGISTRY, not files on disk: clicking Download triggers
generation, the deb streams to the requester, and the server copy
lives only for the retry TTL. polari-complete on /downloads stays
the ONE pre-prepped download; everything here says "generated on
demand" and quotes an HONEST wait estimate from recorded
DebGenerationRecord history ("never generated yet — first run
measures it" before any exists).

Transparency (plan §Transparency): per-item provenance lines, the
named generation steps spelled out BEFORE the click (no bare
spinners anywhere — the browser's own download UI covers the wait),
named refusals rendered as sentences, and what-is-this explainers
including the honest admit gap: installed payloads stage under
/var/lib/polari/apps/ and go LIVE through the dynamic-modules
machinery (dev-dyn-1, its own merge gate) — until that merges,
admission is a manual step on the instance.

Zero JS, server-rendered, logged-out friendly — same shell as
/downloads (downloads_shared).

@consumers
  - polariServer (route registration via the appstore gate)
  - appstore.app_debs_selftest
"""

import html
import os
import time

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.custom import app_deb_builder as builder
from appstore.custom import module_requirements as modreqs
from appstore.custom.downloads_shared import (
    EXPLAIN_DEB, EXPLAIN_DISK, EXPLAIN_PREPPED_VS_DEMAND,
    explainer_block, human_size, on_demand_provenance, wrap_page)

GENERATION_STEPS = ('analyze shared payload &rarr; package module '
                    'files &rarr; write manifest &rarr; assemble '
                    'deb &rarr; stream to you')

EXPLAIN_WAIT = (
    'Why is there a short wait after I click?',
    'These debs are not kept on the server — each one is packaged '
    'fresh at the moment you ask (' + GENERATION_STEPS + '), then '
    'removed again after a short retry window. The wait shown on '
    'each card is the median of that app\'s recorded generation '
    'times — measured, never invented.')

EXPLAIN_ADMIT = (
    'How does an installed app become live?',
    'Installing an app deb stages its code and data under '
    '<code>/var/lib/polari/apps/</code>. The running instance '
    'admits staged apps through the dynamic-modules machinery, '
    'which is still in review &mdash; until it lands, an '
    'administrator has to admit the module on the instance '
    'manually. This page will say so until that changes; nothing '
    'happens invisibly.')

EXPLAIN_FLAVORS = (
    'Online deb vs offline deb — which do I want?',
    '<strong>Online</strong> is small: it carries the app itself, '
    'and the libraries it needs are fetched from the internet '
    'when the app is set up — each card lists those libraries '
    'and their measured sizes, so nothing downloads invisibly. '
    '<strong>Offline</strong> carries the pip libraries INSIDE '
    'the deb (bigger, slower to generate — wheels are fetched at '
    'build time), for machines that will have no internet. '
    'System engines (e.g. a SPICE simulator) can never ride '
    'inside an app deb — they come from the distro\'s packages '
    'or the offline install media, and each card names them.')

EXPLAIN_SHARED = (
    'What are the "shared payload" files some apps mention?',
    'When two apps contain identical files, those files are '
    'factored into one shared deb both apps depend on, so the '
    'content installs exactly once &mdash; the installer enforces '
    'it. Install the shared deb first; each app card links it '
    'when it applies.')


def _estimate_text(module, flavor='online'):
    seconds = builder.estimate_seconds(module, flavor=flavor)
    if seconds is None:
        return ('never generated yet — the first run measures it')
    return f'usually ~{seconds:g} s'


def _requirements_lines(module, payload_bytes):
    """The honest space accounting: app payload + measured library
    closure + engines — file counts say nothing about what an app
    really needs to operate."""
    reqs = modreqs.module_requirements(module)
    parts = [f'app payload {human_size(payload_bytes)}']
    libs = reqs['libraries']
    if libs:
        text = (f'{len(libs)} librar'
                + ('y' if len(libs) == 1 else 'ies')
                + f' ({human_size(reqs["librariesBytes"])} '
                'measured'
                + (f', {reqs["librariesUnmeasured"]} unmeasured '
                   'here' if reqs['librariesUnmeasured'] else '')
                + ')')
        parts.append(text)
    else:
        parts.append('no extra libraries')
    if reqs['polariRequires']:
        parts.append('needs modules: '
                     + ', '.join(reqs['polariRequires']))
    line = ('<span class="dl-meta">'
            + html.escape(' · '.join(parts)) + '</span>')
    if reqs['engines']:
        engine_bits = []
        for engine in reqs['engines']:
            size = (f' {human_size(engine["bytes"])}'
                    if engine.get('bytes') else '')
            state = ('' if engine['present']
                     else ' — not on this server')
            engine_bits.append(
                f'{engine["name"]} ({engine["kind"]}{size}'
                f'{state})')
        line += ('<span class="dl-meta">engines: '
                 + html.escape('; '.join(engine_bits))
                 + ' — system engines come from the distro or '
                 'offline media, never inside an app deb</span>')
    return line, reqs


def _module_card(module, entry, analysis, flavor='online'):
    description = entry.get('description', '')
    blurb = (f'<p class="blurb">{html.escape(description)}</p>'
             if description else '')
    refusal = analysis['refusals'].get(module)
    if not entry.get('downloaded') or refusal:
        reason = refusal or ('registered but its code is not '
                             'downloaded on this instance')
        return f'''
<li class="dl-card">
  <span class="dl-info">
    <span class="dl-name">{html.escape(module)}</span>
    {blurb}
    <span class="prov prov-demand">Not available here —
      {html.escape(reason)}.</span>
  </span>
</li>'''
    shared_links = ''
    shared_names = analysis['sharedByModule'].get(module, [])
    if shared_names:
        links = ', '.join(
            f'<a href="/downloads/apps/shared/{html.escape(name)}">'
            f'{html.escape(name)}</a>' for name in shared_names)
        shared_links = (f'<span class="dl-meta">Install first '
                        f'(shared payload): {links}</span>')
    payload_bytes = sum(
        size for _, _, size, _
        in analysis['payloads'].get(module, []))
    req_lines, _ = _requirements_lines(module, payload_bytes)
    mode_note = ('<span class="dl-meta">this flavor carries the '
                 'pip libraries inside the deb</span>'
                 if flavor == 'offline' else '')
    ready = builder.pool_file_for(module, flavor)
    job = builder.generation_job(module, flavor)
    if ready:
        dl_est = builder.download_estimate_seconds(ready['bytes'])
        dl_text = (('download usually &lt;1 s' if dl_est < 1 else
                    f'download usually ~{dl_est:g} s')
                   if dl_est is not None else
                   'no download timing data yet — the first one '
                   'measures it')
        state = (f'<span class="prov prov-prepped">READY — '
                 f'generated {ready["ageSeconds"] // 60} min ago, '
                 f'held for the retry window · '
                 f'{human_size(ready["bytes"])} · '
                 f'{html.escape(dl_text)}</span>')
        button = (f'<a class="dl" href="/downloads/apps/file/'
                  f'{html.escape(ready["file"])}" download>'
                  'Download</a>')
    elif job and job['state'] == 'running':
        state = (f'<span class="prov prov-demand">GENERATING NOW '
                 f'— {html.escape(job["step"])}</span>')
        button = (f'<a class="dl" href="/downloads/apps/status/'
                  f'{html.escape(module)}?flavor={flavor}">'
                  'View progress</a>')
    else:
        state = on_demand_provenance(_estimate_text(module,
                                                    flavor))
        button = (f'<a class="dl" href="/downloads/apps/status/'
                  f'{html.escape(module)}?flavor={flavor}">'
                  'Generate &amp; download</a>')
    return f'''
<li class="dl-card">
  <span class="dl-info">
    <span class="dl-name">{html.escape(module)}</span>
    {blurb}
    {req_lines}
    <span class="dl-meta">steps on download:
      {GENERATION_STEPS}</span>
    {shared_links}{mode_note}
    {state}
  </span>
  {button}
</li>'''


def render_page(instance_title='Polari', root=None,
                flavor='online'):
    flavor = flavor if flavor in ('online', 'offline') else 'online'
    title = html.escape(instance_title)
    modules = builder.registry_modules(root)
    if not modules:
        body = ('<header class="hero"><h1>Apps</h1></header>'
                '<div class="card"><p>No modules are registered on '
                'this instance yet, so there is nothing to '
                'generate.</p>'
                '<p class="note"><a href="/downloads">&larr; Back '
                'to Downloads</a></p></div>')
        return wrap_page(title, body, 'Apps')
    analysis = builder.analyze(root)
    cards = ''.join(
        _module_card(module, entry, analysis, flavor)
        for module, entry in sorted(modules.items()))
    tab = lambda f, label: (            # noqa: E731
        f'<a class="tab{" tab-on" if flavor == f else ""}" '
        f'href="/downloads/apps?flavor={f}">{label}</a>')
    tabs = ('<nav class="tabs">'
            + tab('online', 'Online installs')
            + tab('offline', 'Offline installs')
            + '</nav>'
            + ('<p class="option-note">Offline debs carry each '
               'app\'s pip libraries inside — bigger and slower '
               'to generate, for machines with no internet. '
               'System engines still come from the distro or the '
               'offline media.</p>'
               if flavor == 'offline' else
               '<p class="option-note">Online debs are small — '
               'each app\'s libraries are fetched from the '
               'internet when it is set up, exactly as listed on '
               'its card.</p>'))
    body = f'''
<header class="hero">
<h1>Add individual apps to {title}</h1>
<p class="lede">Every module this instance knows is available as
   its own installable file — packaged fresh when you ask for it.
   Nothing sits pre-built on the server: your click starts the
   build, the file streams to you, and the server's copy is
   removed again after a short retry window.</p>
</header>

<section class="step">
<h2>Apps</h2>
{tabs}
<ol class="dl-list">{cards}
</ol>
</section>

<section class="step">
<h2>Installing</h2>
<ol class="howto">
<li>Click <strong>Download</strong> — your browser waits briefly
    while the file is packaged (each card says how long that
    usually takes), then saves it.</li>
<li>If the card lists a shared-payload file, download and
    install that one first.</li>
<li>Double-click the downloaded file and choose
    <strong>Install</strong>. The app stages onto your computer;
    the card explainers below say how it becomes live.</li>
</ol>
</section>
{explainer_block([EXPLAIN_DEB, EXPLAIN_FLAVORS, EXPLAIN_WAIT,
                  EXPLAIN_PREPPED_VS_DEMAND, EXPLAIN_SHARED,
                  EXPLAIN_ADMIT, EXPLAIN_DISK])}
<p class="note"><a href="/downloads">&larr; Back to Downloads</a>
   — the one-file installer there is pre-prepped and downloads
   instantly.</p>
'''
    return wrap_page(title, body, 'Apps')


def _refuse(response, sentence, status='404 Not Found'):
    response.status = status
    response.content_type = 'text/plain; charset=utf-8'
    response.text = sentence


def _stream_deb(response, path, filename):
    response.content_type = 'application/vnd.debian.binary-package'
    response.downloadable_as = filename
    with open(path, 'rb') as fh:
        response.data = fh.read()


class AppDebsPage(treeObject):
    """GET /downloads/apps (HTML) +
    GET /downloads/apps/get/{module} (generate + stream) +
    GET /downloads/apps/shared/{debname} (shared-payload deb)."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/downloads/apps'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/downloads/apps', self, suffix='page')
            add('/downloads/apps/get/{module}', self, suffix='get')
            add('/downloads/apps/get-offline/{module}', self,
                suffix='get_offline')
            add('/downloads/apps/status/{module}', self,
                suffix='status')
            add('/downloads/apps/file/{filename}', self,
                suffix='file')
            add('/downloads/apps/shared/{debname}', self,
                suffix='shared')

    def on_get_page(self, request, response):
        builder.purge_expired()
        response.content_type = 'text/html; charset=utf-8'
        response.text = render_page(
            flavor=request.params.get('flavor', 'online'))

    def _generate_and_stream(self, response, module, flavor):
        builder.purge_expired()
        result = builder.generate(module, flavor=flavor)
        if not result.get('ok'):
            _refuse(response, result['refusal'])
            return
        _stream_deb(response, result['path'], result['file'])
        if builder.ttl_seconds() <= 0:
            # delete-after-delivery mode: no retry window asked for
            os.remove(result['path'])

    def on_get_get(self, request, response, module):
        self._generate_and_stream(response, module, 'online')

    def on_get_get_offline(self, request, response, module):
        self._generate_and_stream(response, module, 'offline')

    def on_get_status(self, request, response, module):
        """dl-8: the click lands HERE — immediate confirmation,
        live named-step progress (meta-refresh, zero JS), then the
        file hands over when ready. Same flow for both flavors."""
        flavor = request.params.get('flavor', 'online')
        flavor = flavor if flavor in ('online', 'offline') \
            else 'online'
        if module not in builder.registry_modules():
            _refuse(response,
                    f'"{module}" is not in the module registry')
            return
        job = builder.start_generation(module, flavor)
        title = html.escape(module)
        back = ('<p class="note"><a href="/downloads/apps?flavor='
                f'{flavor}">&larr; Back to Apps</a></p>')
        head = ''
        if job['state'] == 'running':
            elapsed = int(time.time() - job['startedAt'])
            head = '<meta http-equiv="refresh" content="2">'
            body = ('<header class="hero">'
                    '<p class="option-tag">⚙ GENERATING</p>'
                    f'<h1>Generating the '
                    f'{flavor} deb for {title}&hellip;</h1>'
                    '<p class="lede">Your download was initiated '
                    '— this page updates every 2 seconds and the '
                    'file hands over when ready.</p></header>'
                    '<section class="step"><h2>Progress</h2>'
                    f'<p>Current step: <strong>'
                    f'{html.escape(job["step"])}</strong></p>'
                    f'<p class="dl-meta">{elapsed}s elapsed '
                    f'&middot; {html.escape(_estimate_text(module, flavor))}'
                    '</p></section>' + back)
        elif job['state'] == 'done':
            filename = job['result']['file']
            url = f'/downloads/apps/file/{filename}'
            head = ('<meta http-equiv="refresh" '
                    f'content="0;url={url}">')
            dl_est = builder.download_estimate_seconds(
                job['result']['bytes'])
            dl_text = (('usually <1 s' if dl_est < 1 else
                        f'usually ~{dl_est:g} s at your typical '
                        'speed')
                       if dl_est is not None else
                       'no download timing data yet — this one '
                       'measures it')
            body = ('<header class="hero">'
                    '<p class="option-tag">⬇ DOWNLOADING</p>'
                    f'<h1>{title} ({flavor}) is ready — '
                    'downloading now</h1>'
                    '<p class="lede">Generation finished; the '
                    'download starts by itself — if it doesn\'t, '
                    f'<a href="{url}" download>click here</a>. '
                    'The file stays available for a short retry '
                    'window, then the server copy is removed.'
                    '</p></header>'
                    f'<p class="note">{html.escape(filename)} '
                    f'&middot; generated in '
                    f'{job["result"]["seconds"]}s &middot; '
                    f'{html.escape(dl_text)}</p>' + back)
        else:
            body = (f'<header class="hero"><h1>Could not '
                    f'generate {title}</h1></header>'
                    '<section class="step"><p>'
                    f'{html.escape(job["result"]["refusal"])}'
                    '</p></section>' + back)
        response.content_type = 'text/html; charset=utf-8'
        response.text = wrap_page(title, body, 'Generating',
                                  head_extra=head)

    def on_get_file(self, request, response, filename):
        path = builder.resolve_pool_file(filename)
        if path is None:
            _refuse(response,
                    'no such generated deb — it may have aged '
                    'out; start again from /downloads/apps')
            return
        # dl-9: stream + MEASURE the transfer — the WSGI server
        # closes the stream when the client has the last byte, so
        # close() timestamps a real download duration.
        size = os.path.getsize(path)
        response.content_type = (
            'application/vnd.debian.binary-package')
        response.downloadable_as = filename
        response.content_length = size
        response.stream = _TimedStream(path, filename, size)


    def on_get_shared(self, request, response, debname):
        builder.purge_expired()
        analysis = builder.analyze()
        group = analysis['shared'].get(debname)
        if group is None:
            _refuse(response,
                    f'"{debname}" is not a shared payload this '
                    'instance generates — see /downloads/apps')
            return
        os.makedirs(builder.pool_dir(), exist_ok=True)
        filename = builder.build_shared_deb(
            debname, group, builder.pool_dir())
        path = os.path.join(builder.pool_dir(), filename)
        _stream_deb(response, path, filename)
        if builder.ttl_seconds() <= 0:
            os.remove(path)


class _TimedStream:
    """File wrapper whose close() records the measured download
    into the generation ledger (builder.record_download). The WSGI
    server closes it once the client holds the last byte, so the
    duration is a real transfer measurement."""

    def __init__(self, path, filename, size):
        self._fh = open(path, 'rb')
        self._filename = filename
        self._size = size
        self._started = time.time()
        self._closed = False

    def read(self, n=-1):
        return self._fh.read(n)

    def close(self):
        if not self._closed:
            self._closed = True
            elapsed = time.time() - self._started
            if elapsed > 0:
                builder.record_download(self._filename,
                                        self._size, elapsed)
        self._fh.close()
