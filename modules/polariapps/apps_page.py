"""
@module polariapps.apps_page

/display/apps-security — SECURITY COVERAGE PER APP × VERSION (ct-8, design §6).

WHERE THIS TABLE WAS MEANT TO GO, AND WHERE IT ACTUALLY WENT. The design asks for the coverage totals "on the
security page and on each app's own page". The security page is owned by another slice; and an app's own page
(`/app/<name>`, `AppHomeComponent`) is NOT a configured Display at all — it is an Angular component that
renders `GET /api/apps/nav/{app}`, with no seedable row, item or table slot. So per the instruction for that
case: the coverage tables live on this polariapps MODULE page, `/display/apps-security`, and the app pages
reach them by name rather than by embedding them. Giving `AppHomeComponent` a seedable slot is frontend work
(FRONTEND_WORK_MAP), not something to fake with a new component here.

Everything is a CONFIGURED table or the generic structured panel (his rule: no raw JSON on screens, no new
reusable component). `confirmed_by` carries the `person` column format: the cell shows the shortened Keycloak
`sub` with the whole id in the tooltip and resolves names at RENDER time through the one gated door
`POST /api/security/people` — no name is ever stored in a decision row (D18-1).

CONVERGE, DO NOT INSERT (§54's gotcha, hit twice already): the core display seed only INSERTS a missing
`DisplayDefinition`, so an edit to a page that already exists on a live instance never lands. `seed_apps_pages`
runs the upsert path, which diffs the fields and leaves a row alone when `is_prior` is False — a page somebody
customized here stays theirs.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

#: D18-1: the confirming person is a Keycloak `sub` and nothing else; `person` resolves it on screen only.
CONFIRMER_FORMAT = 'confirmed_by:person'

DECISION_COLS = 'app,app_version,kind,subject,state,derived_from,confirmed_by,confirmed_at'

SEED_APPS_PAGE_DISPLAYS = [
    _page('apps-security', 'apps-security',
          'Security coverage per app and version — what each app version owes a ruling on, what a person has '
          'confirmed, and what a release would still be shipping open or stale',
          'SecurityDecision', [
              _row(0, [
                  _sapi('apps-security-coverage', 0, 12,
                        'Coverage per app × version — counts by kind and state, the live instance count under '
                        'each class, and none / partial / full (full = nothing open and nothing stale)',
                        '/api/apps/security/coverage', pick='apps'),
              ], min_height=300),
              _row(1, [
                  _sapi('apps-security-totals', 0, 5,
                        'Totals across every app version, and the vocabulary: eight kinds of decision, six states',
                        '/api/apps/security/coverage', hide='apps'),
                  # Filtered SERVER-side: `class-rows-table` renders a whole class, and "open" is a state, so
                  # the honest way to show only the gaps is the door that already filters by state.
                  _sapi('apps-security-open', 1, 7,
                        'Still OPEN — subjects enumerated from the app that nobody has ruled on (a real gap, '
                        'not silence)', '/api/apps/security/decisions?state=open', pick='decisions'),
              ], min_height=300),
              _row(2, [
                  _table('apps-security-decisions', 0, 12,
                         'Every decision row: app × version × kind × subject, its state, what proposed it and '
                         'which person confirmed it (by Keycloak sub — the name is resolved on screen, never '
                         'stored)', 'SecurityDecision', columns=DECISION_COLS,
                         column_formats=CONFIRMER_FORMAT),
              ]),
              _row(3, [
                  _table('apps-security-profiles', 0, 6,
                         'The permission profiles a confirmation concretes — a published profile is a PROPOSAL '
                         'until a person confirms it', 'AppPermissionProfile',
                         columns='name,app_name,kc_groups_json,verbs_json,published'),
                  _table('apps-security-apps', 1, 6, 'The apps these versions belong to',
                         'PolariAppDefinition', columns='name,title,use_case,modules_json'),
              ]),
          ]),
]


def seed_apps_pages(manager):
    """CONVERGE the polariapps pages rather than insert-by-name (§54; see the module docstring)."""
    from moduleService.seed_upsert import upsert_seed_pairs
    from polariApiServer.displayDefinition import DisplayDefinition
    return upsert_seed_pairs(manager, [
        ('DisplayDefinition', DisplayDefinition, SEED_APPS_PAGE_DISPLAYS),
    ], tag='AppsPagesSeed')


def start_page_converge(manager, polServer=None, wait_s=300, rows_wait_s=120, tick=2.0):
    """Run `seed_apps_pages` once, AFTER the tree's display rows are restored.

    Same reasoning as the security module's converge beside it: the endpoint constructor runs while falcon's
    routes are built, long before lazy boot's Phase B restores `DisplayDefinition`, so converging inline would
    walk an empty table and simply insert everything again next boot. Daemon thread; never raises into boot."""
    import threading
    import time

    def _rows():
        return len((getattr(manager, 'objectTables', None) or {}).get('DisplayDefinition', {}) or {})

    def _run():
        start = time.time()
        while time.time() - start < wait_s:
            registry = getattr(polServer, 'bootRegistry', None)
            try:
                pending = bool(registry.is_data_pending('polariapps')) if registry is not None else False
            except Exception:  # noqa: BLE001
                pending = False
            if not pending and (_rows() or time.time() - start >= rows_wait_s):
                break
            time.sleep(tick)
        try:
            for report in seed_apps_pages(manager) or []:
                if report.get('inserted') or report.get('updated'):
                    print('[AppsPagesSeed] %s: +%d ~%d' % (report.get('class', ''),
                                                           len(report.get('inserted', [])),
                                                           len(report.get('updated', []))), flush=True)
        except Exception as e:  # noqa: BLE001
            print(f'[AppsPagesSeed] failed: {e}', flush=True)

    thread = threading.Thread(target=_run, name='polariapps-page-converge', daemon=True)
    thread.start()
    return thread
