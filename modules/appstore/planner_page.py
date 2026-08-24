"""
@module appstore.planner_page

dl-6 (Dustin 2026-08-24): /downloads/plan — topology planning meets
the downloads surface. The page SPECULATES a topology: it asks how
many devices you have, whether each is normal or high-performance
(and in what way), and what you're trying to make app-wise — then
proposes a per-device role (core / hosting / member) and a
per-device DOWNLOAD BUNDLE with real links into /downloads and
/downloads/apps.

Knobs-and-suggestions ethos, applied to a wizard:
- The proposal is a SUGGESTION with its evidence shown (the
  measured pub-0 sizing points), never an action — nothing is
  created, assigned, or installed by this page.
- Honesty lines everywhere: module budgets are speculative
  extrapolations from two measured points; the suite install
  already CONTAINS every module (app debs are for adding modules
  to an instance that lacks them, e.g. exhibits later); multi-
  device module assignment happens inside the product (topology),
  not by which deb you download.
- Zero JS: three GET steps (device count + internet + goals →
  per-device performance → the plan). GET keeps every step
  bookmarkable and shareable; nothing server-side mutates.

Sizing evidence (why the budgets are what they are):
- pub-0 2026-08-16 measured: 9 modules + deps boot in 36.8 s at
  ~196 MiB backend peak on a 4-CPU/6 GB cap.
- focus-switch 2026-08-05: 22 modules ≈ 807 s, 8 modules ≈ 385 s
  on the older prf-a swarm (heavier stack).
Budgets below stay conservative multiples of the measured 9.

@consumers
  - polariServer (route registration via the appstore gate)
  - appstore.selftest_planner
"""

import html

from objectTreeDecorators import treeObject, treeObjectInit

from appstore import app_deb_builder as builder
from appstore.downloads_shared import explainer_block, wrap_page

#: Performance classes the wizard offers — 'in what way' matters
#: because the bottleneck decides the honest budget.
PERF_CLASSES = {
    'normal': ('Normal', 'a typical desktop or laptop '
               '(~4 cores, 8 GB)', 9),
    'highmem': ('High-performance — lots of RAM',
                '16 GB or more', 18),
    'highcpu': ('High-performance — many cores',
                '8+ cores', 14),
    'gpu': ('High-performance — discrete GPU',
            'a real graphics card (helps XR and future AI/scan '
            'work; module budget is RAM/CPU-bound)', 14),
    'small': ('Small / low-power',
              'mini PC, thin client, older machine — best as a '
              'member device that USES the isle rather than '
              'hosting it', 0),
}

#: What-you-want-to-make → registry modules. Filtered against the
#: LIVE registry at render time — the page never offers a module
#: this instance does not know.
GOALS = {
    'motors': ('Motors, electronics & hardware design',
               ['motors', 'magnetics', 'gears', 'electrodevice',
                'hwdigital', 'hwfpga', 'techtree']),
    'materials': ('Materials research & manufacturing',
                  ['materials_science', 'pspp', 'casting',
                   'waxprint', 'waxsupply', 'techtree']),
    'food': ('Growing food & nutrition',
             ['nutrition', 'aquaponics', 'plant_morphology',
              'tanks', 'microalgae', 'agro_forestry',
              'supplychain']),
    'climate': ('Climate & environment',
                ['climate', 'biomining', 'zones']),
    'simulation': ('Simulations & no-code modelling',
                   ['mathshapes', 'composition', 'resources',
                    'grpcbridge']),
    'business': ('Running a small business',
                 ['bizops', 'supplychain', 'odooconnect',
                  'scoring', 'dmvdata']),
    'collab': ('Meetings, media & XR',
               ['meshassets', 'xr']),
}

#: Every hosting instance carries these regardless of goals.
BASE_MODULES = ['appstore', 'polariapps', 'islemesh']

MAX_DEVICES = 6

EXPLAIN_SPECULATIVE = (
    'How solid is this proposal?',
    'It is a SPECULATION built from two measured points (9 modules '
    'boot in ~37 s using ~200 MiB on a 4-core/6 GB machine; 22 '
    'modules took ~13 minutes on older hardware) and conservative '
    'multiples of them. Your real machines will differ. Nothing '
    'here installs or configures anything — it is a shopping list '
    'with reasons, and every number you see says where it came '
    'from.')

EXPLAIN_ASSIGNMENT = (
    'Does the download decide which device runs which app?',
    'No. Every suite install contains every module — the downloads '
    'are the same for any hosting device. WHICH modules actually '
    'run where is decided inside the product (the topology pages) '
    'after your isle is up, and can be changed any time. This plan '
    'tells you what to enable where, not what to download '
    'differently.')

EXPLAIN_APP_DEBS = (
    'Why list per-app debs if the suite contains everything?',
    'For adding an app to an instance that lacks it — a trimmed '
    'install, a future exhibit variant, or a box that fell behind. '
    'On a fresh full install they are already present; the links '
    'are here so the plan works for both cases.')


def goal_modules(goals, registry):
    """Ordered, de-duplicated module list for the chosen goals,
    filtered to modules the live registry actually knows."""
    seen, out = set(), []
    for goal in goals:
        for module in GOALS.get(goal, (None, []))[1]:
            if module in registry and module not in seen:
                seen.add(module)
                out.append(module)
    return out


def plan_topology(perfs, goals, registry):
    """The speculation. perfs = ['normal', 'small', ...] in device
    order. Returns {'devices': [{'index', 'perf', 'role',
    'modules', 'budget'}], 'modules': [...], 'overflow': [...]}.
    Core = the strongest hosting device (budget, then order);
    goal modules distribute core-first, budget-capped; leftovers
    are reported honestly, never silently dropped."""
    modules = goal_modules(goals, registry)
    devices = []
    for index, perf in enumerate(perfs, start=1):
        budget = PERF_CLASSES[perf][2]
        devices.append({'index': index, 'perf': perf,
                        'budget': budget,
                        'role': 'member' if budget == 0
                                else 'hosting',
                        'modules': []})
    hosting = [d for d in devices if d['role'] == 'hosting']
    if hosting:
        core = max(hosting, key=lambda d: d['budget'])
        core['role'] = 'core'
        remaining = list(modules)
        for device in sorted(hosting,
                             key=lambda d: (d['role'] != 'core',
                                            -d['budget'])):
            take = device['budget'] - len(BASE_MODULES)
            device['modules'] = remaining[:max(0, take)]
            remaining = remaining[max(0, take):]
        overflow = remaining
    else:
        overflow = modules
    return {'devices': devices, 'modules': modules,
            'overflow': overflow}


# --- rendering ------------------------------------------------------

def _step1(title):
    goal_boxes = ''.join(
        f'<label class="pick"><input type="checkbox" name="g" '
        f'value="{key}"> {html.escape(label)}</label>'
        for key, (label, _) in GOALS.items())
    count_options = ''.join(
        f'<option value="{n}">{n}</option>'
        for n in range(1, MAX_DEVICES + 1))
    return f'''
<header class="hero">
<h1>Plan your {title} setup</h1>
<p class="lede">Three quick questions, then a per-device proposal:
   which machine should host, what to enable where, and exactly
   what to download for each. Nothing is installed or decided for
   you — it's a shopping list with reasons.</p>
</header>
<form method="get" action="/downloads/plan" class="step">
<h2><span class="step-no">1</span>Your devices and goals</h2>
<p><label>How many computers will be part of this?
   <select name="d">{count_options}</select></label></p>
<p><label>Will they have internet during install?
   <select name="net"><option value="yes">yes</option>
   <option value="no">no / limited</option></select></label></p>
<p>What are you trying to make or do? (pick any)</p>
{goal_boxes}
<p><button class="dl" type="submit">Next: describe each
   device</button></p>
</form>'''


def _step2(count, net, goals):
    hidden = (f'<input type="hidden" name="d" value="{count}">'
              f'<input type="hidden" name="net" '
              f'value="{html.escape(net)}">'
              + ''.join(f'<input type="hidden" name="g" '
                        f'value="{html.escape(g)}">'
                        for g in goals))
    rows = ''
    for i in range(1, count + 1):
        options = ''.join(
            f'<option value="{key}">{html.escape(label)} — '
            f'{html.escape(blurb)}</option>'
            for key, (label, blurb, _) in PERF_CLASSES.items())
        rows += (f'<p><label>Device {i}: '
                 f'<select name="p{i}">{options}</select>'
                 f'</label></p>')
    return f'''
<header class="hero"><h1>Describe each device</h1>
<p class="lede">"High-performance" matters differently depending
   on HOW it's strong — RAM decides how many apps fit, cores
   decide how fast they think.</p></header>
<form method="get" action="/downloads/plan" class="step">
<h2><span class="step-no">2</span>What kind of machine is each
    one?</h2>
{hidden}{rows}
<p><button class="dl" type="submit">Propose my setup</button></p>
</form>'''


_ROLE_BLURB = {
    'core': ('runs the isle: the router, the app store, and the '
             'first polari instance'),
    'hosting': ('runs its own polari instance and takes a share '
                'of the apps'),
    'member': ('joins the isle and uses the apps the other '
               'machines host — nothing heavy runs here'),
}


def _device_bundle(device, net):
    """The per-device download list, as real links."""
    if device['role'] == 'member':
        items = ('<li>From <a href="/downloads">Downloads</a>, '
                 'Option B pieces 1–3: <strong>Isle Mesh</strong>, '
                 '<strong>Polari Shell</strong>, <strong>Isle App '
                 'Store</strong> (a member device skips the '
                 'finisher).</li>')
    else:
        items = ('<li><a href="/downloads">Downloads</a> Option A: '
                 '<strong>Polari Complete</strong> — one file, the '
                 'whole suite (every module included).</li>')
        if device['modules']:
            links = ', '.join(
                f'<a href="/downloads/apps/get/{m}">{m}</a>'
                for m in device['modules'])
            items += (f'<li>Enable here (topology): '
                      f'{links} <span class="dl-meta">— app-deb '
                      'links included for instances that lack a '
                      'module; a fresh full install already has '
                      'them all.</span></li>')
    if net == 'no':
        items += ('<li><a href="/downloads/offline">Offline '
                  'media</a> — this device has no internet during '
                  'install; the offline page says honestly what '
                  'is ready.</li>')
    return items


def _plan_page(perfs, net, goals, registry):
    plan = plan_topology(perfs, goals, registry)
    cards = ''
    for device in plan['devices']:
        label, blurb, budget = PERF_CLASSES[device['perf']]
        modules_line = ''
        if device['role'] != 'member':
            shown = ', '.join(BASE_MODULES + device['modules'])
            modules_line = (
                f'<p class="dl-meta">Suggested modules '
                f'({len(BASE_MODULES) + len(device["modules"])} '
                f'of a ~{budget} budget): {html.escape(shown)}</p>')
        cards += f'''
<section class="step">
<h2><span class="step-no">{device['index']}</span>Device
    {device['index']} — {html.escape(label)}:
    <em>{device['role']}</em></h2>
<p class="option-note">This machine {_ROLE_BLURB[device['role']]}.
</p>{modules_line}
<ol class="howto">{_device_bundle(device, net)}</ol>
</section>'''
    goal_names = ', '.join(GOALS[g][0] for g in goals
                           if g in GOALS) or 'nothing selected'
    overflow = ''
    if plan['overflow']:
        overflow = (
            '<p class="note">⚠ More apps than your devices '
            'comfortably host by the measured budgets: '
            f'{html.escape(", ".join(plan["overflow"]))} — they '
            'still install; expect slower boots, or add a hosting '
            'device.</p>')
    no_host = ''
    if all(d['role'] == 'member' for d in plan['devices']):
        no_host = ('<p class="note">⚠ Every device you described '
                   'is small/low-power — an isle needs at least '
                   'one hosting machine. The plan below treats '
                   'them as members of an isle hosted elsewhere.'
                   '</p>')
    body = f'''
<header class="hero"><h1>Your proposed setup</h1>
<p class="version">{len(plan['devices'])} device(s) &middot;
   goals: {html.escape(goal_names)}</p>
<p class="lede">A speculation with its reasons shown — change any
   answer by going <a href="/downloads/plan">back to the start</a>.
   Nothing was installed or configured.</p></header>
{no_host}{cards}{overflow}
{explainer_block([EXPLAIN_SPECULATIVE, EXPLAIN_ASSIGNMENT,
                  EXPLAIN_APP_DEBS])}
<p class="note"><a href="/downloads">&larr; Back to Downloads</a>
</p>'''
    return body


def render_page(params, instance_title='Polari'):
    """params: dict-like with d/net/g(list)/p1..pN. Renders
    whichever wizard step the params have reached."""
    title = html.escape(instance_title)
    try:
        count = int(params.get('d', ''))
    except (TypeError, ValueError):
        count = 0
    if count < 1:
        return wrap_page(title, _step1(title), 'Plan')
    count = min(count, MAX_DEVICES)
    net = params.get('net', 'yes')
    net = net if net in ('yes', 'no') else 'yes'
    goals = [g for g in (params.get_list('g') or [])
             if g in GOALS]
    perfs = []
    for i in range(1, count + 1):
        perf = params.get(f'p{i}', '')
        if perf not in PERF_CLASSES:
            perfs = None
            break
        perfs.append(perf)
    if perfs is None:
        return wrap_page(title, _step2(count, net, goals), 'Plan')
    registry = builder.registry_modules()
    return wrap_page(title, _plan_page(perfs, net, goals,
                                       registry), 'Plan')


class _Params:
    """Tiny adapter so render_page takes falcon's req.params or a
    plain dict (selftests): get() + get_list()."""

    def __init__(self, raw):
        self.raw = raw or {}

    def get(self, key, default=None):
        value = self.raw.get(key, default)
        if isinstance(value, list):
            return value[0] if value else default
        return value

    def get_list(self, key):
        value = self.raw.get(key)
        if value is None:
            return []
        return value if isinstance(value, list) else [value]


class PlannerPage(treeObject):
    """GET /downloads/plan — the three-step wizard (query-param
    driven, zero JS, nothing mutates)."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/downloads/plan'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/downloads/plan', self, suffix='page')

    def on_get_page(self, request, response):
        response.content_type = 'text/html; charset=utf-8'
        response.text = render_page(_Params(request.params))
