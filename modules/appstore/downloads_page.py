"""
@module appstore.downloads_page

The PUBLIC downloads page (dl-1, Dustin 2026-08-23): the page a
NORMAL user lands on from the internet demo, clicks Download, and
gets the installer debs plus click-only instructions — no terminal
anywhere in the flow. The debs pull their remaining dependencies
(docker, zenity, polkit, ...) from the distro's own repositories
during install — that is the INTERNET-INSTALL flavor; the
no-internet/media flavor is its own arc
(AI-Notes/plans/OFFLINE_INSTALL_PLAN.md).

Deliberately server-rendered HTML, zero JS, no SPA/auth in the
path: it must work logged-out, in any browser, and survive
right-click-save. ONE version is shown — whatever is staged; no
multi-version/LTS shelf (Dustin's scope call).

Staging knob: POLARI_DOWNLOADS_DIR (default <framework>/data/
downloads). Deployment stages the current bundle there (the
build-polari-isle-deb.sh output set). Empty dir = an honest
'nothing staged yet' page, never a 404 wall.

Security: filenames are served ONLY from the staged dir, only
*.deb, resolved + prefix-checked against traversal.

@consumers
  - polariServer (route registration via the appstore gate)
  - appstore.selftest_downloads
"""

import html
import os
import re

from objectTreeDecorators import treeObject, treeObjectInit

_VERSION_RE = re.compile(
    r'^(?P<name>[a-z0-9][a-z0-9+.-]*)_(?P<version>[^_]+)_'
    r'(?P<arch>[a-z0-9]+)\.deb$')

#: The click-order matters: each deb's LOCAL dependency must already
#: be installed (GUI installers resolve distro deps online, but not
#: sibling downloads). Anything staged but not listed here is shown
#: after the ordered set.
INSTALL_ORDER = ['isle-mesh-cli', 'polari-shell-core',
                 'isle-app-store', 'polari-isle']

#: Normal-user names + one-liners; a staged package outside this map
#: still renders (raw name, no blurb) — the page never hides a file.
PACKAGE_INFO = {
    'isle-mesh-cli': ('Isle Mesh — networking',
                      'Connects your computer to your isle\'s own '
                      'private network.'),
    'polari-shell-core': ('Polari Shell',
                          'The desktop window your apps open in.'),
    'isle-app-store': ('Isle App Store',
                       'The app you\'ll actually open — install '
                       'and manage everything from here.'),
    'polari-isle': ('Polari Isle — finisher',
                    'Ties the pieces together and finishes the '
                    'setup.'),
}


def downloads_dir():
    configured = os.environ.get('POLARI_DOWNLOADS_DIR', '')
    if configured:
        return configured
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    return os.path.join(root, 'data', 'downloads')


def staged_debs():
    """[{file, name, version, arch, size}] in install order."""
    directory = downloads_dir()
    found = {}
    try:
        for entry in sorted(os.listdir(directory)):
            match = _VERSION_RE.match(entry)
            if not match:
                continue
            path = os.path.join(directory, entry)
            if not os.path.isfile(path):
                continue
            found[match.group('name')] = {
                'file': entry,
                'name': match.group('name'),
                'version': match.group('version'),
                'arch': match.group('arch'),
                'size': os.path.getsize(path),
            }
    except FileNotFoundError:
        return []
    ordered = [found.pop(name) for name in INSTALL_ORDER
               if name in found]
    return ordered + list(found.values())


def resolve_download(filename):
    """Absolute path for a staged deb, or None (traversal, absent,
    or not a .deb all refuse identically)."""
    if not _VERSION_RE.match(filename or ''):
        return None
    directory = os.path.realpath(downloads_dir())
    path = os.path.realpath(os.path.join(directory, filename))
    if not path.startswith(directory + os.sep):
        return None
    return path if os.path.isfile(path) else None


def _human_size(size):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return (f'{size:.0f} {unit}' if unit == 'B'
                    else f'{size / 1.0:.1f} {unit}')
        size /= 1024.0
    return f'{size:.1f} GB'


def render_page(debs, instance_title='Polari'):
    """The full HTML document. Version headline = the store deb's
    (the user-facing app), falling back to the first staged."""
    title = html.escape(instance_title)
    if not debs:
        body = ('<header class="hero"><h1>Downloads</h1></header>'
                '<div class="card"><p>No installers are staged on '
                'this instance yet.</p>'
                '<p class="note">If you run this deployment: build '
                'the bundle (<code>./build-polari-isle-deb.sh</code>) '
                'and stage <code>.generated/debs/</code> into the '
                'downloads directory '
                '(<code>POLARI_DOWNLOADS_DIR</code>).</p></div>')
        return _wrap(title, body)
    headline = next((d for d in debs
                     if d['name'] == 'isle-app-store'), debs[0])
    cards = ''
    for index, d in enumerate(debs, start=1):
        display, blurb = PACKAGE_INFO.get(
            d['name'], (d['name'], ''))
        blurb_html = (f'<p class="blurb">{html.escape(blurb)}</p>'
                      if blurb else '')
        cards += f'''
<li class="dl-card">
  <span class="ordinal" aria-hidden="true">{index}</span>
  <span class="dl-info">
    <span class="dl-name">{html.escape(display)}</span>
    {blurb_html}
    <span class="dl-meta">version {html.escape(d["version"])}
      &middot; {_human_size(d["size"])}
      &middot; <code>{html.escape(d["file"])}</code></span>
  </span>
  <a class="dl" href="/downloads/{html.escape(d["file"])}"
     download>Download</a>
</li>'''
    body = f'''
<header class="hero">
<h1>Install {title} on your computer</h1>
<p class="version">Current version
   <strong>{html.escape(headline["version"])}</strong></p>
<p class="lede">Works on Ubuntu and other Debian-family Linux.
   Download the files below, then install them by clicking —
   no terminal needed. Your computer fetches everything else it
   needs from the internet during the install.</p>
</header>

<section class="step">
<h2><span class="step-no">1</span>Download these files</h2>
<ol class="dl-list">{cards}
</ol>
</section>

<section class="step">
<h2><span class="step-no">2</span>Install them, in the order
    listed</h2>
<ol class="howto">
<li>Open your <strong>Downloads</strong> folder.</li>
<li>Double-click the first file and choose
    <strong>Install</strong>. Wait for it to finish.</li>
<li>Repeat for each file, top to bottom — the order matters,
    because each one builds on the previous.</li>
<li>If double-clicking opens an archive viewer instead of an
    installer: right-click the file &rarr;
    <em>Open With</em> &rarr; <em>Software Install</em>.</li>
</ol>
</section>

<section class="step">
<h2><span class="step-no">3</span>First start</h2>
<p>Open <strong>Isle App Store</strong> from your applications
   menu. It will walk you through creating your own isle or
   joining an existing one — passwords are asked by the system
   itself, never typed into a terminal.</p>
</section>

<p class="note">Installing from a CD/DVD or USB stick with no
   internet is a separate download — not available yet.</p>
'''
    return _wrap(title, body)


def _wrap(title, body):
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Downloads</title>
<style>
 :root{{--bg:#fcfcfb;--card:#ffffff;--ink:#1d1d1c;--ink2:#5d5d58;
   --line:#e4e4df;--accent:#2a78d6;--accent-ink:#ffffff;
   --chip:#f1f1ec}}
 @media (prefers-color-scheme: dark){{
   :root{{--bg:#1a1a19;--card:#232322;--ink:#ececea;--ink2:#a5a5a0;
     --line:#3a3a38;--accent:#3987e5;--accent-ink:#ffffff;
     --chip:#2d2d2b}}}}
 *{{box-sizing:border-box}}
 body{{font-family:system-ui,sans-serif;max-width:46rem;
   margin:0 auto;padding:2.5rem 1.25rem 3rem;line-height:1.55;
   color:var(--ink);background:var(--bg)}}
 h1{{font-size:1.7rem;margin:0 0 .5rem;line-height:1.25}}
 h2{{font-size:1.12rem;margin:0 0 .8rem;display:flex;
   align-items:center;gap:.6rem}}
 code{{background:var(--chip);padding:.08rem .35rem;
   border-radius:4px;font-size:.86em}}
 .hero{{margin-bottom:2rem}}
 .version{{margin:.1rem 0 .9rem;color:var(--ink2)}}
 .version strong{{color:var(--ink);background:var(--chip);
   border:1px solid var(--line);border-radius:999px;
   padding:.12rem .7rem;margin-left:.25rem}}
 .lede{{margin:0;color:var(--ink2)}}
 .step{{background:var(--card);border:1px solid var(--line);
   border-radius:12px;padding:1.1rem 1.25rem;margin:0 0 1.1rem}}
 .step-no{{flex:none;width:1.7rem;height:1.7rem;border-radius:50%;
   background:var(--accent);color:var(--accent-ink);
   font-size:.95rem;font-weight:700;display:inline-flex;
   align-items:center;justify-content:center}}
 ol.dl-list{{list-style:none;margin:0;padding:0}}
 .dl-card{{display:flex;align-items:center;gap:.9rem;
   padding:.8rem .2rem;border-top:1px solid var(--line)}}
 .dl-card:first-child{{border-top:0}}
 .ordinal{{flex:none;width:1.5rem;height:1.5rem;border-radius:50%;
   border:2px solid var(--accent);color:var(--accent);
   font-size:.82rem;font-weight:700;display:inline-flex;
   align-items:center;justify-content:center}}
 .dl-info{{flex:1;min-width:0;display:flex;flex-direction:column;
   gap:.1rem}}
 .dl-name{{font-weight:650}}
 .blurb{{margin:0;color:var(--ink2);font-size:.92em}}
 .dl-meta{{color:var(--ink2);font-size:.82em;
   overflow-wrap:anywhere}}
 a.dl{{flex:none;background:var(--accent);color:var(--accent-ink);
   text-decoration:none;font-weight:650;padding:.5rem 1.1rem;
   border-radius:8px}}
 a.dl:hover{{filter:brightness(1.08)}}
 ol.howto{{margin:0;padding-left:1.3rem}}
 ol.howto li{{margin:.4rem 0}}
 .note{{color:var(--ink2);font-size:.9em}}
 @media (max-width:480px){{
   .dl-card{{flex-wrap:wrap}}
   .dl-info{{flex-basis:calc(100% - 2.4rem)}}
   a.dl{{margin-left:2.4rem}}}}
</style></head><body>{body}</body></html>'''


class DownloadsPage(treeObject):
    """GET /downloads (HTML) + GET /downloads/{filename} (deb)."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/downloads'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/downloads', self, suffix='page')
            add('/downloads/{filename}', self, suffix='file')

    def on_get_page(self, request, response):
        response.content_type = 'text/html; charset=utf-8'
        response.text = render_page(staged_debs())

    def on_get_file(self, request, response, filename):
        path = resolve_download(filename)
        if path is None:
            response.status = '404 Not Found'
            response.content_type = 'text/plain; charset=utf-8'
            response.text = ('no such installer — see /downloads '
                             'for what this instance serves')
            return
        response.content_type = 'application/vnd.debian.binary-package'
        response.downloadable_as = filename
        with open(path, 'rb') as fh:
            response.data = fh.read()
