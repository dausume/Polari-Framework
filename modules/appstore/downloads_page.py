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

dl-3 (2026-08-24): when the TRUE MERGED `polari-complete` deb is
staged it renders as "Option A — one file installs everything"
(the ONE pre-prepped headline installer, marked as such), and the
piecewise list demotes to "Option B". With no combined deb staged
the page keeps the dl-1b single-list layout. Every variant carries
the transparency explainers (downloads_shared).

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

import datetime
import html
import os
import re

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.downloads_shared import (
    EXPLAIN_DEB, EXPLAIN_DISK, EXPLAIN_INTERNET,
    EXPLAIN_PREPPED_VS_DEMAND, explainer_block, human_size,
    prepped_provenance, wrap_page)

_VERSION_RE = re.compile(
    r'^(?P<name>[a-z0-9][a-z0-9+.-]*)_(?P<version>[^_]+)_'
    r'(?P<arch>[a-z0-9]+)\.deb$')

#: The click-order matters: each deb's LOCAL dependency must already
#: be installed (GUI installers resolve distro deps online, but not
#: sibling downloads). Anything staged but not listed here is shown
#: after the ordered set.
INSTALL_ORDER = ['isle-mesh-cli', 'polari-shell-core',
                 'isle-app-store', 'polari-isle']

#: The TRUE MERGED all-in-one deb (dl-3): Provides/Conflicts every
#: member, so a user picks Option A OR Option B — never both.
COMBINED_NAME = 'polari-complete'

#: Normal-user names + one-liners; a staged package outside this map
#: still renders (raw name, no blurb) — the page never hides a file.
PACKAGE_INFO = {
    COMBINED_NAME: ('Polari Complete — everything in one file',
                    'The whole suite as a single installer — all '
                    'four pieces below, merged into one file.'),
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

#: /downloads-specific explainer alongside the shared set. Two
#: phrasings: the piecewise-only page has no "options" to refer to.
_ORDER_ANSWER = (
    'Each piece builds on the one before it. Your computer\'s '
    'installer checks that the earlier pieces are already in place '
    'but cannot download them for you &mdash; so going top to '
    'bottom is what makes every install succeed on the first try.')
EXPLAIN_ORDER = ('Why does the install order matter?',
                 _ORDER_ANSWER)
EXPLAIN_ORDER_TWO_OPTION = (
    'Why does the install order matter in Option B?',
    _ORDER_ANSWER + ' Option A avoids the question entirely: one '
    'file, one install.')


def downloads_dir():
    configured = os.environ.get('POLARI_DOWNLOADS_DIR', '')
    if configured:
        return configured
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    return os.path.join(root, 'data', 'downloads')


def staged_debs():
    """[{file, name, version, arch, size, built}] — install order
    first, then extras (the combined deb rides in the extras;
    render_page pulls it out by name)."""
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
                'built': datetime.date.fromtimestamp(
                    os.path.getmtime(path)).isoformat(),
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


def _card(deb, badge_html):
    display, blurb = PACKAGE_INFO.get(deb['name'], (deb['name'], ''))
    blurb_html = (f'<p class="blurb">{html.escape(blurb)}</p>'
                  if blurb else '')
    return f'''
<li class="dl-card">
  {badge_html}
  <span class="dl-info">
    <span class="dl-name">{html.escape(display)}</span>
    {blurb_html}
    <span class="dl-meta">version {html.escape(deb["version"])}
      &middot; {human_size(deb["size"])}
      &middot; <code>{html.escape(deb["file"])}</code></span>
    {prepped_provenance(deb["built"])}
  </span>
  <a class="dl" href="/downloads/{html.escape(deb["file"])}"
     download>Download</a>
</li>'''


def _explainers(two_option=False):
    order = (EXPLAIN_ORDER_TWO_OPTION if two_option
             else EXPLAIN_ORDER)
    return explainer_block([EXPLAIN_DEB, order,
                            EXPLAIN_PREPPED_VS_DEMAND,
                            EXPLAIN_INTERNET, EXPLAIN_DISK])


def _footer_notes():
    return ('<p class="note">Installing from a CD/DVD or USB stick '
            'with no internet is a separate download — not '
            'available yet.</p>')


def _first_start(step_no=''):
    badge = (f'<span class="step-no">{step_no}</span>' if step_no
             else '')
    return f'''
<section class="step">
<h2>{badge}First start</h2>
<p>Open <strong>Isle App Store</strong> from your applications
   menu. It will walk you through creating your own isle or
   joining an existing one — passwords are asked by the system
   itself, never typed into a terminal.</p>
</section>'''


def _piecewise_cards(pieces):
    cards = ''
    for index, deb in enumerate(pieces, start=1):
        cards += _card(deb, f'<span class="ordinal" '
                            f'aria-hidden="true">{index}</span>')
    return cards


def _render_two_option(title, headline, combined, pieces):
    option_b = ''
    if pieces:
        option_b = f'''
<section class="step">
<p class="option-tag">Option B</p>
<h2>Piece by piece</h2>
<p class="option-note">The same software split into its parts —
   use this if you want only some pieces or need to reinstall
   one. Skip it if you used Option A: the two can't be installed
   together, and the installer will say so if you try.</p>
<ol class="dl-list">{_piecewise_cards(pieces)}
</ol>
<ol class="howto">
<li>Download the files, then open your
    <strong>Downloads</strong> folder.</li>
<li>Double-click the first file and choose
    <strong>Install</strong>. Wait for it to finish.</li>
<li>Repeat for each file, top to bottom — the order matters,
    because each one builds on the previous.</li>
<li>If double-clicking opens an archive viewer instead of an
    installer: right-click the file &rarr;
    <em>Open With</em> &rarr; <em>Software Install</em>.</li>
</ol>
</section>'''
    body = f'''
<header class="hero">
<h1>Install {title} on your computer</h1>
<p class="version">Current version
   <strong>{html.escape(headline["version"])}</strong></p>
<p class="lede">Works on Ubuntu and other Debian-family Linux.
   Install by clicking — no terminal needed. Your computer
   fetches everything else it needs from the internet during
   the install.</p>
</header>

<section class="step">
<p class="option-tag">Option A &middot; recommended</p>
<h2>One file installs everything</h2>
<ol class="dl-list">
<li class="dl-card hero-card">
  <span class="dl-info">
    <span class="dl-name">{html.escape(
        PACKAGE_INFO[COMBINED_NAME][0])}</span>
    <p class="blurb">{html.escape(
        PACKAGE_INFO[COMBINED_NAME][1])}</p>
    <span class="dl-meta">version
      {html.escape(combined["version"])}
      &middot; {human_size(combined["size"])}
      &middot; <code>{html.escape(combined["file"])}</code></span>
    {prepped_provenance(combined["built"])}
  </span>
  <a class="dl" href="/downloads/{html.escape(combined["file"])}"
     download>Download</a>
</li>
</ol>
<ol class="howto">
<li>Download the file, then double-click it in your
    <strong>Downloads</strong> folder and choose
    <strong>Install</strong>.</li>
<li>That's the whole install — this one file contains
    everything.</li>
<li>If double-clicking opens an archive viewer instead of an
    installer: right-click the file &rarr;
    <em>Open With</em> &rarr; <em>Software Install</em>.</li>
</ol>
</section>
{option_b}
{_first_start()}
{_explainers(two_option=True)}
{_footer_notes()}
'''
    return wrap_page(title, body)


def _render_piecewise_only(title, headline, pieces):
    """The dl-1b layout — no combined deb staged."""
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
<ol class="dl-list">{_piecewise_cards(pieces)}
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
{_first_start('3')}
{_explainers()}
{_footer_notes()}
'''
    return wrap_page(title, body)


def render_page(debs, instance_title='Polari'):
    """The full HTML document. Version headline = the store deb's
    (the user-facing app), falling back to the combined deb, then
    the first staged."""
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
        return wrap_page(title, body)
    combined = next((d for d in debs if d['name'] == COMBINED_NAME),
                    None)
    pieces = [d for d in debs if d['name'] != COMBINED_NAME]
    headline = next((d for d in debs
                     if d['name'] == 'isle-app-store'),
                    combined or debs[0])
    if combined:
        return _render_two_option(title, headline, combined, pieces)
    return _render_piecewise_only(title, headline, pieces)


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
