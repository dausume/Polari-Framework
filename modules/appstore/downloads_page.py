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
        body = ('<h1>Downloads</h1>'
                '<p>No installers are staged on this instance '
                'yet.</p>'
                '<p>If you run this deployment: build the bundle '
                '(<code>./build-polari-isle-deb.sh</code>) and '
                'stage <code>.generated/debs/</code> into the '
                'downloads directory '
                '(<code>POLARI_DOWNLOADS_DIR</code>).</p>')
        return _wrap(title, body)
    headline = next((d for d in debs
                     if d['name'] == 'isle-app-store'), debs[0])
    rows = ''.join(
        f'<tr><td><a class="dl" href="/downloads/'
        f'{html.escape(d["file"])}" download>'
        f'{html.escape(d["name"])}</a></td>'
        f'<td>{html.escape(d["version"])}</td>'
        f'<td>{_human_size(d["size"])}</td></tr>'
        for d in debs)
    body = f'''
<h1>Install {title} on your computer</h1>
<p class="version">Current version:
   <strong>{html.escape(headline["version"])}</strong></p>
<p>Works on Ubuntu and other Debian-family Linux. Download the
   files below, then install them by clicking — no terminal
   needed. Your computer fetches everything else it needs from
   the internet during the install.</p>
<h2>Step 1 — download these files</h2>
<table>
<tr><th>File</th><th>Version</th><th>Size</th></tr>
{rows}
</table>
<h2>Step 2 — install them, in the order listed</h2>
<ol>
<li>Open your <strong>Downloads</strong> folder.</li>
<li>Double-click the first file and choose
    <strong>Install</strong>. Wait for it to finish.</li>
<li>Repeat for each file, top to bottom — the order matters,
    because each one builds on the previous.</li>
<li>If double-clicking opens an archive viewer instead of an
    installer: right-click the file &rarr;
    <em>Open With</em> &rarr; <em>Software Install</em>.</li>
</ol>
<h2>Step 3 — first start</h2>
<p>Open <strong>Isle App Store</strong> from your applications
   menu. It will walk you through creating your own isle or
   joining an existing one — passwords are asked by the system
   itself, never typed into a terminal.</p>
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
 body{{font-family:system-ui,sans-serif;max-width:44rem;
      margin:2rem auto;padding:0 1rem;line-height:1.55;color:#222}}
 code{{background:#f4f4f4;padding:.1rem .35rem;border-radius:4px}}
 table{{border-collapse:collapse;width:100%;margin:.5rem 0}}
 th{{text-align:left;border-bottom:2px solid #ccc;
    padding:.3rem .6rem}}
 td{{padding:.35rem .6rem;border-bottom:1px solid #eee}}
 a.dl{{font-weight:600}}
 .version{{font-size:1.1em}}
 .note{{color:#666;font-size:.9em}}
 ol li{{margin:.35rem 0}}
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
