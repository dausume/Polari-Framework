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
from appstore.custom.app_forms import manifest_app
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
    'kept at least three slow-connection downloads long, then only evicted when room is needed, and freed after a day untouched. The wait shown on '
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


def _hardware_notice(module):
    """His rule 2026-09-12: a hardware app's Polari side may be installed here
    (useful for development) but the user must be told when the hardware half
    cannot work on this deployment (moduleService/hardware_reach.py)."""
    try:
        import json
        import os
        from moduleService.manifests import manifest_path
        from moduleService.hardware_reach import hardware_notice
        p = manifest_path(module)
        if p and os.path.isfile(p):
            return hardware_notice(json.load(open(p, encoding='utf-8')))
    except Exception:
        pass
    return ''


def _form_block(module, flavor, form):
    """One of the two forms of an app, as its own column on the card (his ruling 2026-09-14: the access-only deb
    side by side with the actual install deb): the state + the one button."""
    ready = builder.pool_file_for(module, flavor, form)
    job = builder.generation_job(module, flavor, form)
    if ready:
        dl_est = builder.download_estimate_seconds(ready['bytes'])
        dl_text = (('download usually &lt;1 s' if dl_est < 1 else f'download usually ~{dl_est:g} s')
                   if dl_est is not None else 'no download timing data yet — the first one measures it')
        hold = builder.pool_entry(ready['file'])
        held = (f'held at least {hold["hold_remaining_seconds"] // 60} more min' if hold.get('hold_remaining_seconds') else 'past its hold — kept while there is room')
        state = (f'<span class="prov prov-prepped">READY — generated {ready["ageSeconds"] // 60} min ago, {held} '
                 f'(requested {hold.get("requests", 1)}×, downloaded {hold.get("downloads", 0)}×) · {human_size(ready["bytes"])} · {html.escape(dl_text)}</span>')
        button = f'<a class="dl" href="/downloads/apps/file/{html.escape(ready["file"])}" download>Download</a>'
    elif job and job['state'] == 'running':
        state = f'<span class="prov prov-demand">GENERATING NOW — {html.escape(job["step"])}</span>'
        button = f'<a class="dl" href="/downloads/apps/status/{html.escape(module)}?flavor={flavor}&amp;form={form}">View progress</a>'
    else:
        est = builder.estimate_seconds(module, flavor=flavor, form=form)
        state = on_demand_provenance(f'usually ~{est:g} s to generate' if est is not None else 'never generated yet — the first one measures it')
        button = f'<a class="dl" href="/downloads/apps/status/{html.escape(module)}?flavor={flavor}&amp;form={form}">Generate &amp; download</a>'
    if form == 'access':
        head = '<span class="form-head">Access only — the shell</span><span class="dl-meta">Opens the app hosted on your isle; installs nothing else. For any member, even Access only.'
        head += (' Offline: carries the shell runtime when the core staged it.' if flavor == 'offline' else '') + '</span>'
    else:
        head = '<span class="form-head">Install — runs here</span><span class="dl-meta">The app itself, for host / hardware members.</span>'
    return f'<div class="form form-{form}">{head}{state}{button}</div>'


def _module_card(module, entry, analysis, flavor='online', app=None, show_category=False):
    from appstore.custom.app_forms import manifest_app, HARDWARE_KINDS, EXPANSION_KINDS
    app = app or manifest_app(module, entry=entry)
    title = app.get('title') or module
    description = app.get('description') or entry.get('description', '')
    blurb = (f'<p class="blurb">{html.escape(description)}</p>' if description else '')
    kind = app.get('kind', 'polari-app')
    if show_category or app.get('subcategories'):
        from moduleService.app_taxonomy import CATEGORIES, SUBCATEGORIES
        crumbs = ([html.escape(CATEGORIES[app['category']]['title'])] if show_category and app.get('category') in CATEGORIES else []) \
            + [html.escape(SUBCATEGORIES[sc][1]) for sc in app.get('subcategories', []) if sc in SUBCATEGORIES]
        tags = ', '.join(html.escape(t) for t in app.get('tags', [])[:5])
        blurb += '<span class="dl-meta crumbs">' + ' · '.join(crumbs) + ((' — ' + tags) if tags else '') + '</span>'
    if kind in EXPANSION_KINDS:
        blurb += (f'<span class="prov prov-demand">Expansion of {html.escape(app.get("extends") or "?")} — its install refuses '
                  f'unless {html.escape(app.get("extends") or "the hardware app")} is installed first.</span>')
    elif kind in HARDWARE_KINDS:
        blurb += ('<span class="prov prov-demand">Hardware app — its install refuses before installing anything on a lightweight '
                  '(docker-swarm) isle or a member without the hardware tier, and says why.</span>')
    notice = _hardware_notice(module)
    if notice:
        blurb += f'<span class="prov prov-demand">{html.escape(notice)}</span>'
    refusal = analysis['refusals'].get(module)
    fetch_note = ''
    if not entry.get('downloaded') and not refusal and entry.get('repo'):
        fetch_note = ('<span class="prov prov-demand">Fetched first: this app\'s code is not on this instance yet; the install '
                      'form pulls it from its repository, then packages it (the access form needs no code).</span>')
    if (not entry.get('downloaded') and not entry.get('repo')) or refusal:
        reason = refusal or 'registered but its code is not downloaded on this instance and no repository is recorded'
        return f'''
<li class="dl-card dl-card-forms">
  <span class="dl-info">
    <span class="dl-name">{html.escape(title)} <code>{html.escape(module)}</code> <small>{html.escape(kind)}</small></span>
    {blurb}
    <span class="prov prov-demand">Not available here (the install form) — {html.escape(reason)}.</span>
    <div class="forms">{_form_block(module, flavor, 'access')}</div>
  </span>
</li>'''
    shared_links = ''
    shared_names = analysis['sharedByModule'].get(module, [])
    if shared_names:
        links = ', '.join(f'<a href="/downloads/apps/shared/{html.escape(name)}">{html.escape(name)}</a>' for name in shared_names)
        shared_links = f'<span class="dl-meta">Install first (shared payload): {links}</span>'
    payload_bytes = sum(size for _, _, size, _ in analysis['payloads'].get(module, []))
    req_lines, _ = _requirements_lines(module, payload_bytes)
    mode_note = ('<span class="dl-meta">the offline install form carries the pip libraries inside the deb</span>' if flavor == 'offline' else '')
    return f'''
<li class="dl-card dl-card-forms">
  <span class="dl-info">
    <span class="dl-name">{html.escape(title)} <code>{html.escape(module)}</code> <small>{html.escape(kind)}</small></span>
    {blurb}
    {req_lines}
    <span class="dl-meta">steps on download: {GENERATION_STEPS}</span>
    {shared_links}{mode_note}{fetch_note}
    <div class="forms">{_form_block(module, flavor, 'install')}{_form_block(module, flavor, 'access')}</div>
  </span>
</li>'''


def render_apps_section(flavor='online', root=None, heading='Add individual apps'):
    """The app cards for one flavour, without the page chrome — the main /downloads page embeds this under its
    top-level Online / Offline tab. His rulings 2026-09-14: every app in BOTH forms side by side (install / access
    only), grouped Software apps / Hardware apps, each hardware app's EXPANSIONS as a subsection under it."""
    from appstore.custom.app_forms import grouped
    flavor = flavor if flavor in ('online', 'offline') else 'online'
    modules = builder.registry_modules(root)
    if not modules:
        return ('<section class="step"><h2>' + html.escape(heading) + '</h2><p>No modules are registered on '
                'this instance yet, so there is nothing to generate.</p></section>')
    analysis = builder.analyze(root)
    g = grouped(modules, root)
    software = ''.join(_module_card(m, e, analysis, flavor, a) for m, e, a in g['software'])
    hardware = ''
    for m, e, a in g['hardware']:
        hardware += _module_card(m, e, analysis, flavor, a)
        exps = g['expansions'].get(m, [])
        if exps:
            hardware += (f'<li class="expansions"><details><summary>Expansions of {html.escape(a.get("title") or m)} ({len(exps)})</summary>'
                         '<ol class="dl-list">' + ''.join(_module_card(xm, xe, analysis, flavor, xa) for xm, xe, xa in exps) + '</ol></details></li>')
    orphans = ''.join(_module_card(m, e, analysis, flavor, a) for m, e, a in g['orphans'])
    note = ('Offline debs carry each app\'s pip libraries inside — bigger and slower to generate, for machines '
            'with no internet; at setup they install from what they carry, skipping anything already present. '
            'Engines such as the circuit simulator are already inside the Polari runtime; each card names any that are not.'
            if flavor == 'offline' else
            'Online debs are small — each app\'s libraries are fetched from the internet when it is set up, '
            'exactly as listed on its card.')
    forms_note = ('Every app comes in two forms, side by side: <strong>Install</strong> (the app itself, for a host or hardware '
                  'member) and <strong>Access only</strong> (its shell — a launcher that finds and opens the app your isle hosts; '
                  'for any member). Access-only apps exist online and offline, for software and hardware apps alike.')
    out = f'''
<section class="step">
<h2>{html.escape(heading)}</h2>
<p class="option-note">{note} {forms_note} Every official app is offered: one whose code is not on this instance yet is
   fetched from its repository when you click. Scripts and AIs use the same door: <code>/api/apps</code> (and <code>/api/access</code>).</p>
<h3>Software apps ({len(g['software'])})</h3>
<ol class="dl-list">{software}
</ol>'''
    if g['hardware'] or g['orphans']:
        out += (f'<h3>Hardware apps ({len(g["hardware"])})</h3><p class="option-note">A hardware app is a KVM guest that owns real '
                'devices; it needs a full isle and the hardware tier. Its expansions sit under it.</p>'
                f'<ol class="dl-list">{hardware}</ol>')
        if orphans:
            out += f'<h3>Expansions whose hardware app is not registered here ({len(g["orphans"])})</h3><ol class="dl-list">{orphans}</ol>'
    return out + '</section>'


def _pool_requests(module):
    n = 0
    for f in ('online', 'offline'):
        for fm in ('install', 'access'):
            pf = builder.pool_file_for(module, f, fm)
            if pf:
                n += builder.pool_entry(pf['file']).get('requests', 0)
    return n


def catalogue(root=None, q='', scope='category', category='', subcategory='', kind='', tier='', sort='name'):
    """The apps a page shows (his rulings 2026-09-14): one primary category per app, N sub-categories (cross-listed
    where a sub-category belongs to another category), search by name or properties either inside the category or
    across all, sort by name / size / most requested / recently generated, filters by kind and tier.
    Returns (rows, groups): rows = [(module, entry, app)] after search/filters; groups = {subcategory: [rows]}."""
    from moduleService.app_taxonomy import matches, SUBCATEGORIES
    from moduleService.tier_reach import tiers_for
    modules = builder.registry_modules(root)
    rows = []
    for m, e in sorted(modules.items()):
        a = manifest_app(m, root, e)
        in_cat = (not category) or a['category'] == category or category in a.get('secondary', [])
        if scope != 'all' and not in_cat:
            continue
        if subcategory and subcategory not in a['subcategories']:
            continue
        if kind and a['kind'] != kind:
            continue
        if tier and tier not in tiers_for(a['kind']):
            continue
        if not matches(q, m, a, a):
            continue
        rows.append((m, e, a))
    if sort == 'requests':
        rows.sort(key=lambda r: -_pool_requests(r[0]))
    elif sort == 'size':
        payloads = builder.analyze(root)['payloads']
        rows.sort(key=lambda r: -sum(size for _, _, size, _ in payloads.get(r[0], [])))
    elif sort == 'recent':
        rows.sort(key=lambda r: (builder.pool_file_for(r[0], 'online') or {'ageSeconds': 10 ** 9})['ageSeconds'])
    groups = {}
    for m, e, a in rows:
        subs = [sc for sc in a['subcategories'] if (not category) or SUBCATEGORIES[sc][0] == category] or ['other']
        for sc in subs:
            groups.setdefault(sc, []).append((m, e, a))
    return rows, groups


def _controls(flavor, q, scope, category, subcategory, kind, tier, sort, counts):
    from moduleService.app_taxonomy import CATEGORIES, SUBCATEGORIES
    from moduleService.tier_reach import TIERS
    esc = html.escape
    tabs = '<a class="tab%s" href="/downloads/apps?flavor=%s">All apps <small>%d</small></a>' % (' tab-on' if not category else '', flavor, sum(counts.values()))
    for c, v in CATEGORIES.items():
        tabs += '<a class="tab%s" href="/downloads/apps?flavor=%s&amp;category=%s">%s <small>%d</small></a>' % (' tab-on' if category == c else '', flavor, c, esc(v['title']), counts.get(c, 0))
    hidden = ''.join('<input type="hidden" name="%s" value="%s">' % (k, esc(v)) for k, v in (('flavor', flavor), ('category', category)) if v)
    scope_ui = ''
    if category:
        scope_ui = ('<label><input type="radio" name="scope" value="category"%s> in %s</label>' % (' checked' if scope != 'all' else '', esc(CATEGORIES[category]['title']))
                    + '<label><input type="radio" name="scope" value="all"%s> all apps</label>' % (' checked' if scope == 'all' else ''))
    sorts = ''.join('<option value="%s"%s>%s</option>' % (k, ' selected' if sort == k else '', v)
                    for k, v in (('name', 'name'), ('requests', 'most requested'), ('size', 'largest first'), ('recent', 'recently generated')))
    kinds = ''.join('<option value="%s"%s>%s</option>' % (k, ' selected' if kind == k else '', k or 'any kind')
                    for k in ('', 'polari-app', 'isle-app', 'hardware-app', 'hardware-extension-app', 'library', 'suite-app'))
    tiers = ''.join('<option value="%s"%s>%s</option>' % (t, ' selected' if tier == t else '', t or 'any member') for t in ('',) + tuple(TIERS))
    subs = ''
    if category:
        chips = ''.join('<a class="chip%s" href="/downloads/apps?flavor=%s&amp;category=%s&amp;subcategory=%s%s">%s</a>'
                        % (' chip-on' if subcategory == sc else '', flavor, category, sc, ('&amp;q=' + esc(q)) if q else '', esc(v[1]))
                        for sc, v in SUBCATEGORIES.items() if v[0] == category)
        if subcategory:
            chips += '<a class="chip" href="/downloads/apps?flavor=%s&amp;category=%s">clear</a>' % (flavor, category)
        subs = '<div class="chips">' + chips + '</div>'
    return ('<nav class="tabs tabs-cat" aria-label="Categories">' + tabs + '</nav>'
            '<form class="finder" method="get" action="/downloads/apps">' + hidden
            + '<input type="search" name="q" value="%s" placeholder="Search by name or property: gears, wifi, kvm, nutrition…" aria-label="Search apps">' % esc(q)
            + '<span class="scope">' + scope_ui + '</span>'
            + '<label>sort <select name="sort">' + sorts + '</select></label>'
            + '<label>kind <select name="kind">' + kinds + '</select></label>'
            + '<label>runs on <select name="tier">' + tiers + '</select></label>'
            + '<button type="submit">Find</button></form>' + subs)


def render_page(instance_title='Polari', root=None, flavor='online', q='', scope='category', category='', subcategory='', kind='', tier='', sort='name'):
    """/downloads/apps — the APPS catalogue (his rulings 2026-09-14): separate from installing Polari; category tabs,
    sub-category groups collapsed with counts, search all or inside the category, sort, filters; every app in both forms."""
    from moduleService.app_taxonomy import CATEGORIES, SUBCATEGORIES
    esc = html.escape
    flavor = flavor if flavor in ('online', 'offline') else 'online'
    title = esc(instance_title)
    modules = builder.registry_modules(root)
    if not modules:
        body = ('<header class="hero"><h1>Apps</h1></header><div class="card"><p>No modules are registered on this instance yet, so there is '
                'nothing to generate.</p><p class="note"><a href="/downloads">&larr; Back to Downloads</a></p></div>')
        return wrap_page(title, body, 'Apps')
    analysis = builder.analyze(root)
    counts = {}
    for m, e in modules.items():
        c = manifest_app(m, root, e)['category']
        counts[c] = counts.get(c, 0) + 1
    rows, groups = catalogue(root, q, scope, category, subcategory, kind, tier, sort)
    searching = bool(q or subcategory or kind or tier)
    cat_link = ('&amp;category=' + category) if category else ''
    flavor_tabs = ('<nav class="tabs" aria-label="Online or offline">'
                   + ''.join('<a class="tab%s" href="/downloads/apps?flavor=%s%s">%s</a>' % (' tab-on' if flavor == f else '', f, cat_link, lbl)
                             for f, lbl in (('online', '🌐 Online'), ('offline', '💾 Offline')))
                   + '</nav>')
    if searching:
        where = 'across all categories' if (scope == 'all' or not category) else 'in ' + esc(CATEGORIES[category]['title'])
        if rows:
            cards = ''.join(_module_card(m, e, analysis, flavor, a, show_category=True) for m, e, a in rows)
            listing = ('<p class="option-note">%d app(s) match%s %s.</p><ol class="dl-list">%s</ol>'
                       % (len(rows), (' “%s”' % esc(q)) if q else '', where, cards))
        else:
            listing = '<p class="option-note">Nothing matches %s. Try fewer words, or search all apps.</p>' % where
    else:
        listing = ''
        order = [sc for sc in SUBCATEGORIES if sc in groups] + (['other'] if 'other' in groups else [])
        for sc in order:
            items = groups[sc]
            sc_title, sc_blurb = (SUBCATEGORIES[sc][1], SUBCATEGORIES[sc][2]) if sc in SUBCATEGORIES else ('Other', '')
            cards = ''.join(_module_card(m, e, analysis, flavor, a, show_category=not category) for m, e, a in items)
            is_open = ' open' if (len(items) <= 4 or len(order) == 1) else ''
            listing += ('<details class="group"%s><summary>%s <small>%d</small><span class="blurb">%s</span></summary><ol class="dl-list">%s</ol></details>'
                        % (is_open, esc(sc_title), len(items), esc(sc_blurb), cards))
    head_title = 'Apps' if not category else CATEGORIES[category]['title']
    lede = (CATEGORIES[category]['blurb'] if category else
            'Every app comes in two forms: <strong>Install</strong> (the app itself, for a host or hardware member) and '
            '<strong>Access only</strong> (its shell, for any member). Pick a category, or search everything.')
    body = ('<header class="hero"><h1>%s</h1><p class="lede">%s</p></header>' % (head_title, lede)
            + '<section class="step">' + flavor_tabs + _controls(flavor, q, scope, category, subcategory, kind, tier, sort, counts) + listing + '</section>'
            + '<section class="step"><h2>Installing</h2><ol class="howto">'
              '<li>Click <strong>Generate &amp; download</strong> (or <strong>Download</strong> when it is already made) on the form you want; the card says how long it usually takes.</li>'
              '<li>If the card lists a shared-payload file, install that one first.</li>'
              '<li>Double-click the downloaded file and choose <strong>Install</strong>. An Install form stages the app for the isle to admit; an Access form is a launcher that finds and opens the app your isle hosts.</li>'
              '</ol></section>'
            + explainer_block([EXPLAIN_DEB, EXPLAIN_FLAVORS, EXPLAIN_WAIT, EXPLAIN_PREPPED_VS_DEMAND, EXPLAIN_SHARED, EXPLAIN_ADMIT, EXPLAIN_DISK])
            + '<p class="note"><a href="/downloads">&larr; Install Polari itself</a>: the platform installers, online and offline, and the USB stick.</p>')
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
        g = request.params.get
        response.text = render_page(flavor=g('flavor', 'online'), q=g('q', '') or '', scope=g('scope', 'category') or 'category', category=g('category', '') or '',
                                    subcategory=g('subcategory', '') or '', kind=g('kind', '') or '', tier=g('tier', '') or '', sort=g('sort', 'name') or 'name')

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
        form = request.params.get('form', 'install')
        form = form if form in ('install', 'access') else 'install'
        registry = builder.registry_modules()
        if module not in registry:
            _refuse(response,
                    f'"{module}" is not in the module registry')
            return
        if not registry[module].get('downloaded') and form == 'install':
            # fetch the code from its repository first (the API's ensure_code; needs the manager)
            try:
                from appstore.apps_api import ensure_code
                fetched = ensure_code(getattr(self.polServer, 'manager', None), module, registry[module])
            except Exception as exc:   # noqa: BLE001
                fetched = {'ok': False, 'refusal': f'fetch failed: {exc}'}
            if not fetched.get('ok'):
                _refuse(response, f'{module}: {fetched.get("refusal", "could not fetch its code")}', '409 Conflict')
                return
        job = builder.start_generation(module, flavor, form=form)
        title = html.escape(module) + (' (access only — the shell)' if form == 'access' else '')
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
        builder.inflight_begin(filename)   # never evicted while a download is in flight

    def read(self, n=-1):
        return self._fh.read(n)

    def close(self):
        if not self._closed:
            self._closed = True
            elapsed = time.time() - self._started
            builder.inflight_end(self._filename)
            builder.note_download(self._filename, max(0.001, elapsed), self._size)   # counts, refreshes the hold, measures
        self._fh.close()
