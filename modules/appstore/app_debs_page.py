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
  - appstore.selftest_app_debs
"""

import html
import os

from objectTreeDecorators import treeObject, treeObjectInit

from appstore import app_deb_builder as builder
from appstore.downloads_shared import (
    EXPLAIN_DEB, EXPLAIN_DISK, EXPLAIN_PREPPED_VS_DEMAND,
    explainer_block, on_demand_provenance, wrap_page)

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

EXPLAIN_SHARED = (
    'What are the "shared payload" files some apps mention?',
    'When two apps contain identical files, those files are '
    'factored into one shared deb both apps depend on, so the '
    'content installs exactly once &mdash; the installer enforces '
    'it. Install the shared deb first; each app card links it '
    'when it applies.')


def _estimate_text(module):
    seconds = builder.estimate_seconds(module)
    if seconds is None:
        return ('never generated yet — the first run measures it')
    return f'usually ~{seconds:g} s'


def _module_card(module, entry, analysis):
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
    file_count = len(analysis['payloads'].get(module, []))
    return f'''
<li class="dl-card">
  <span class="dl-info">
    <span class="dl-name">{html.escape(module)}</span>
    {blurb}
    <span class="dl-meta">{file_count} files &middot; steps on
      download: {GENERATION_STEPS}</span>
    {shared_links}
    {on_demand_provenance(_estimate_text(module))}
  </span>
  <a class="dl" href="/downloads/apps/get/{html.escape(module)}"
     download>Download</a>
</li>'''


def render_page(instance_title='Polari', root=None):
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
        _module_card(module, entry, analysis)
        for module, entry in sorted(modules.items()))
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
{explainer_block([EXPLAIN_DEB, EXPLAIN_WAIT,
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
            add('/downloads/apps/shared/{debname}', self,
                suffix='shared')

    def on_get_page(self, request, response):
        builder.purge_expired()
        response.content_type = 'text/html; charset=utf-8'
        response.text = render_page()

    def on_get_get(self, request, response, module):
        builder.purge_expired()
        result = builder.generate(module)
        if not result.get('ok'):
            _refuse(response, result['refusal'])
            return
        _stream_deb(response, result['path'], result['file'])
        if builder.ttl_seconds() <= 0:
            # delete-after-delivery mode: no retry window asked for
            os.remove(result['path'])

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
