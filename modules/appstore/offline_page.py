"""
@module appstore.offline_page

dl-5: /downloads/offline — the no-internet install surface. The
real payload (apt dependency closure for the target Ubuntu release,
chunked to media size) is built by the off-1 pool builder
(AI-Notes/plans/OFFLINE_INSTALL_PLAN.md, its own session on a roomy
box); THIS page renders whatever that builder stages, and renders
an honest "not built yet — here is what it will be" page when
nothing is staged. Never a 404 wall, never an invented download.

Staging contract (what off-1 writes into POLARI_OFFLINE_DIR):
  chunks.json = {
    "target":    "Ubuntu 24.04 amd64",     # what the set installs on
    "builtAt":   "2026-08-24",             # when the pool was built
    "media":     "4.7 GB DVD",             # what each chunk fits on
    "chunks": [
      {"label": "Disk 1 — core debs",
       "files": [{"name": "chunk1.tar", "bytes": 123}, ...]},
      ...
    ]}
Files are served ONLY if the manifest names them (tighter than a
directory listing — the manifest is the truth), traversal-checked,
and streamed (offline chunks are multi-GB; never read into memory).
A malformed manifest renders a NAMED refusal, not a stack trace.

Ratified offline decisions (1+2): Ubuntu target, multi-disk/
multi-USB chunking; chunks can generate PIECE BY PIECE straight
onto the medium so no full pool need ever sit on the server.
Decisions 3 (signing anchor) + 4 (app images on medium) are OPEN —
the page says how verification stands rather than pretending.

@consumers
  - polariServer (route registration via the appstore gate)
  - appstore.selftest_offline
"""

import html
import json
import os

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.downloads_shared import (
    explainer_block, human_size, wrap_page)

EXPLAIN_OFFLINE = (
    'What is an offline install?',
    'A copy of everything the installer would normally fetch from '
    'the internet, prepared onto CDs/DVDs or USB sticks — so a '
    'computer with no connection at all can still install the '
    'suite. You download the pieces somewhere WITH internet, write '
    'them to the media, and carry them over.')

EXPLAIN_CHUNKS = (
    'Why several disks/sticks?',
    'The full offline payload is bigger than one disk, so it is '
    'split into chunks sized to your media. Each chunk below lists '
    'exactly which files belong on it and how big they are — copy '
    'each list onto its own disk or stick, label them, and the '
    'installer asks for them in order.')

EXPLAIN_VERIFY = (
    'How do I know the files are genuine?',
    'Honestly: the signing story for offline media is still being '
    'decided (it is an open design decision, not an oversight). '
    'Until it lands, download only from an instance you trust and '
    'keep the media under your control. This answer will change '
    'when the verification design ships.')


def offline_dir():
    configured = os.environ.get('POLARI_OFFLINE_DIR', '')
    if configured:
        return configured
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    return os.path.join(root, 'data', 'offline')


def load_manifest():
    """(manifest, refusal) — exactly one is None. Absent file =
    (None, None): the honest not-built-yet state, not an error."""
    path = os.path.join(offline_dir(), 'chunks.json')
    try:
        with open(path, encoding='utf-8') as fh:
            manifest = json.load(fh)
    except FileNotFoundError:
        return None, None
    except ValueError as error:
        return None, f'chunks.json is staged but unreadable: {error}'
    chunks = manifest.get('chunks')
    if not isinstance(chunks, list) or not chunks:
        return None, ('chunks.json is staged but lists no chunks — '
                      'the pool build did not finish')
    for chunk in chunks:
        if not isinstance(chunk.get('files'), list):
            return None, ('chunks.json has a chunk without a file '
                          'list — the pool build did not finish')
    return manifest, None


def manifest_files():
    """{name: bytes} across all chunks — the ONLY files this page
    will ever serve."""
    manifest, _ = load_manifest()
    if not manifest:
        return {}
    files = {}
    for chunk in manifest['chunks']:
        for entry in chunk['files']:
            name = entry.get('name', '')
            if name:
                files[name] = entry.get('bytes', 0)
    return files


def resolve_offline_file(filename):
    """Absolute path for a manifest-listed staged file, or None —
    the manifest is the truth, a stray file in the dir is never
    served."""
    if not filename or filename not in manifest_files():
        return None
    directory = os.path.realpath(offline_dir())
    path = os.path.realpath(os.path.join(directory, filename))
    if not path.startswith(directory + os.sep):
        return None
    return path if os.path.isfile(path) else None


def _chunk_section(index, chunk):
    rows = ''
    total = 0
    for entry in chunk['files']:
        name = entry.get('name', '')
        size = entry.get('bytes', 0)
        total += size
        staged = os.path.isfile(os.path.join(offline_dir(), name))
        link = (f'<a class="dl" href="/downloads/offline/'
                f'{html.escape(name)}" download>Download</a>'
                if staged else
                '<span class="prov prov-demand">not staged '
                'yet</span>')
        rows += f'''
<li class="dl-card">
  <span class="dl-info">
    <span class="dl-name"><code>{html.escape(name)}</code></span>
    <span class="dl-meta">{human_size(size)}</span>
  </span>
  {link}
</li>'''
    label = chunk.get('label', f'Chunk {index}')
    return f'''
<section class="step">
<h2><span class="step-no">{index}</span>{html.escape(label)}
    <span class="dl-meta">&middot; {human_size(total)}
    total</span></h2>
<ol class="dl-list">{rows}
</ol>
</section>'''


def render_page(instance_title='Polari'):
    title = html.escape(instance_title)
    manifest, refusal = load_manifest()
    if refusal:
        body = (f'<header class="hero"><h1>Offline install</h1>'
                f'</header><div class="card"><p>{html.escape(refusal)}'
                '.</p><p class="note">If you run this deployment: '
                're-run the offline pool build so '
                '<code>chunks.json</code> is complete.</p>'
                '<p class="note"><a href="/downloads">&larr; Back '
                'to Downloads</a></p></div>')
        return wrap_page(title, body, 'Offline install')
    if manifest is None:
        body = f'''
<header class="hero">
<h1>Install {title} with no internet</h1>
<p class="lede">Not built yet — honestly. Here is what this page
   will offer once it is.</p>
</header>
<section class="step">
<h2>What it will be</h2>
<p>Everything the normal install fetches from the internet,
   prepared as a set of files sized to CDs/DVDs or USB sticks
   (several disks — the payload is bigger than one). You will
   download each disk's file list on a connected computer, write
   the files to the media, and install on the offline machine
   from those — no connection needed there, ever.</p>
<p class="note">The pieces can be generated one at a time straight
   onto the medium, so even the server never needs the whole set
   on disk at once.</p>
</section>
{explainer_block([EXPLAIN_OFFLINE, EXPLAIN_CHUNKS,
                  EXPLAIN_VERIFY])}
<p class="note"><a href="/downloads">&larr; Back to
   Downloads</a></p>
'''
        return wrap_page(title, body, 'Offline install')
    target = manifest.get('target', '')
    built = manifest.get('builtAt', '')
    media = manifest.get('media', '')
    facts = ' &middot; '.join(html.escape(x) for x in
                              (target, f'built {built}' if built
                               else '', media) if x)
    chunks = ''.join(_chunk_section(i, chunk)
                     for i, chunk in
                     enumerate(manifest['chunks'], start=1))
    body = f'''
<header class="hero">
<h1>Install {title} with no internet</h1>
<p class="version">{facts}</p>
<p class="lede">Download each disk's files on a connected
   computer, write each numbered set to its own disk or USB
   stick, and label them — the offline installer asks for them
   in order.</p>
</header>
{chunks}
<section class="step">
<h2>Writing the media</h2>
<ol class="howto">
<li>Format each USB stick, or use a blank disk, one per numbered
    set above.</li>
<li>Copy every file of a set onto its medium — names unchanged,
    no folders.</li>
<li>Write the set number on the label. The installer asks for
    them by number.</li>
</ol>
</section>
{explainer_block([EXPLAIN_OFFLINE, EXPLAIN_CHUNKS,
                  EXPLAIN_VERIFY])}
<p class="note"><a href="/downloads">&larr; Back to
   Downloads</a></p>
'''
    return wrap_page(title, body, 'Offline install')


class OfflinePage(treeObject):
    """GET /downloads/offline (HTML) +
    GET /downloads/offline/{filename} (manifest-listed chunk
    files, streamed — chunks are multi-GB)."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/downloads/offline'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/downloads/offline', self, suffix='page')
            # :path converter — chunk files nest (repo/<deb>), a
            # single-segment template would 404 them.
            add('/downloads/offline/{filename:path}', self,
                suffix='file')

    def on_get_page(self, request, response):
        response.content_type = 'text/html; charset=utf-8'
        response.text = render_page()

    def on_get_file(self, request, response, filename):
        path = resolve_offline_file(filename)
        if path is None:
            response.status = '404 Not Found'
            response.content_type = 'text/plain; charset=utf-8'
            response.text = ('no such offline file — see '
                             '/downloads/offline for what this '
                             'instance stages')
            return
        response.content_type = 'application/octet-stream'
        response.downloadable_as = filename
        response.content_length = os.path.getsize(path)
        response.stream = open(path, 'rb')
