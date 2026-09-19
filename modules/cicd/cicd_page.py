"""
@module cicd.cicd_page

/display/cicd            the pipeline: which device, is it ready, which routes may publish, and the rule
                         that decides what may ever ship
/display/cicd-setup      THE WIZARD (ci-11a) — the setup walkthrough, step by step, with its buttons
/display/cicd-stages     the isle testing stages — the ordered list that IS what can be released
/display/cicd-runs       the mirrored Jenkins builds and what each isle stage recorded
/display/cicd-releases   per version: what shipped, and what did not, with the reason

CONFIGURED PAGES ONLY. Every item here is one of the two generic registered components — `class-rows-table`
and `api-structured-panel` — so ci-8 added no Angular at all (his rule: "there should not be any json
showing on the screens, everything should be configured tables, graphs, or visualizations"; and the
per-object display rule: a setting is edited on its OWN row's page, through CRUDE, not on a bespoke
settings screen).

ci-11a adds exactly ONE component, `pipeline-setup-panel`, and only because his ask needs a thing no
configured table can be: a button that runs a command on the machine the browser is sitting on. The
store's own surface could not be extended with a mode — `app-isle-store` is a routed page with no
`@Input()` at all, hard-wired to catalogue fetching and installs — so the panel follows the
`security-threat-sim` shape instead (a registered panel with typed inputs). Everything ELSE on the page
below is still a configured table or the structured panel.

THE LAYER BOUNDARY (his rule 2026-09-19 — "keep different pieces logically separate, like CLI vs JavaFX").
The page talks to the bridge contract and to `/api/cicd/setup`. It never composes a command: an action
carries a VERB id from `polari-jenkins/shell-verbs.json` and the shell resolves it. And when no shell is
present the panel shows the same state read-only, with the exact command beside each step.

That is also WHY the settings tables are on these pages: the `class-rows-table` over `PipelineDevice`,
`PipelineStage` and `PipelineRoute` IS the editing surface, gated by the `cicd-settings` permission profile
(cicd_seed) — admins change a knob, everybody else reads it.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

#: the rule, short enough for a panel title
RULE = ('the pipeline only ships what it TESTED in a throwaway isle — no results for a version means '
        'nothing is published and the tag is not pushed')


def _setup_panel(item_id, index, segments, title, step='', path='/api/cicd/setup'):
    """The ONE new component of ci-11a — `pipeline-setup-panel`.

    `step` empty renders the whole walkthrough; naming a step renders that one. The panel reads `path`
    for the mirrored state (so a plain browser sees something), and asks the desktop shell whether it can
    drive the device live. It never builds a command: an action names a verb id from the tracked
    allowlist and the shell resolves it.
    """
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'pipeline-setup-panel',
            'inputs': {'path': path, 'step': step, 'device': ''},
        },
        'item': None, 'nestedRows': [],
    }


SEED_CICD_PAGE_DISPLAYS = [
    _page('cicd', 'cicd',
          'CI/CD — the pipeline device, its settings (Polari is the source of truth; device.env follows), '
          'which routes may publish, and the release rule that decides what can ship at all',
          'PipelineDevice', [
              _row(0, [
                  _sapi('cicd-mode', 0, 12,
                        'What this pipeline is FOR — the whole Polari suite, or ONE Polari app somebody '
                        'maintains (in app mode the core is pulled from a stated Polari release, never '
                        'rebuilt, and only that app\'s deb is released, to that developer\'s own routes)',
                        '/api/cicd', pick='mode_reading'),
              ], min_height=160),
              _row(1, [
                  _sapi('cicd-readiness', 0, 6,
                        'This pipeline device — is it ready? (setup steps complete, doctor warnings, the '
                        'preflight verdict, when it last reported in)',
                        '/api/cicd', pick='readiness'),
                  _sapi('cicd-settings-now', 1, 6,
                        'The settings in force — what the device writes into device.env at the top of every run',
                        '/api/cicd', pick='settings'),
              ], min_height=260),
              _row(2, [
                  _sapi('cicd-validation', 0, 7,
                        'Validation — the SAME rules polari-jenkins/device.sh applies, so a knob that is wrong '
                        'here is wrong there (FAIL refuses a change; WARN says what it will cost)',
                        '/api/cicd', pick='validation'),
                  _sapi('cicd-rule', 1, 5, 'The release rule, in his words', '/api/cicd', pick='release_rule'),
              ], min_height=260),
              _row(3, [
                  _table('cicd-devices', 0, 12,
                         'Pipeline devices — EDIT HERE: this table is the settings surface (admins only, the '
                         'cicd-settings permission profile). The device picks a change up at its next sync.',
                         'PipelineDevice',
                         columns='name,role,mode,app_name,app_repo,core_source,isle_target,isle_ssh_alias,'
                                 'vm_ram_gb,vm_vcpus,vm_disk_gb,nested,min_free_gb,min_ram_headroom_gb,'
                                 'executors,setup_steps_done,setup_ready,doctor_warnings,preflight_verdict,'
                                 'last_seen'),
              ]),
              _row(4, [
                  _sapi('cicd-routes-now', 0, 5,
                        'Publication routes — enabled (Polari\'s knob) beside armed (the device sees its '
                        'secret). Both, and the release rule, before anything publishes for real.',
                        '/api/cicd', pick='routes'),
                  _table('cicd-routes', 1, 7,
                         'Route rows — set `enabled` here; `armed` is the device\'s reading and is reported, '
                         'never set from Polari', 'PipelineRoute',
                         columns='name,device,enabled,armed,parked,target,why,last_published_at'),
              ], min_height=300),
              _row(5, [
                  _table('cicd-secrets', 0, 12,
                         'Secret PRESENCE — names, whether the device has each one, which routes go dry '
                         'without it, and where to get it. No value exists in this table.',
                         'PipelineSecretPresence',
                         columns='area,secret_name,present,kind,needed_by_json,where_to_get,how_to_make,blocked_why'),
              ]),
          ]),

    # ---------------------------------------------------------------- ci-11a: THE WIZARD
    # His ask 2026-09-19: turn the pipeline into a desktop app "similar to how the isle mesh is
    # working", guiding people through use like a normal app, eliminating the terminal.
    _page('cicd-setup', 'cicd-setup',
          'CI/CD — SET UP THE PIPELINE, step by step. Each step says what it is in plain words, shows what '
          'is true on the device right now, asks what it needs, and offers the button that does it. In the '
          'desktop application the buttons run on your machine (unprivileged ones directly, privileged ones '
          'through the system\'s own elevation prompt); in a plain browser the same steps are read-only and '
          'each shows the exact command instead.',
          'PipelineSetupStep', [
              _row(0, [
                  _setup_panel('cicd-setup-wizard', 0, 12,
                               'The walkthrough — `pol jenkins setup`, one step at a time'),
              ], min_height=640),
              _row(1, [
                  _sapi('cicd-setup-readiness', 0, 6,
                        'Is this device ready? (steps complete, doctor warnings, the preflight verdict, and '
                        'when the device last reported in)',
                        '/api/cicd', pick='readiness'),
                  _sapi('cicd-setup-rule', 1, 6,
                        'What the setup is FOR: the rule that decides what may ever ship',
                        '/api/cicd', pick='release_rule'),
              ], min_height=260),
              _row(2, [
                  _table('cicd-setup-steps', 0, 12,
                         'The steps as the device last reported them — its own reading, mirrored in and '
                         'never re-derived here (a Polari core cannot run `pol`, and should not be able to). '
                         '`state` is done / todo / blocked / skipped.',
                         'PipelineSetupStep',
                         columns='index,step,title,state,total,at'),
              ]),
              _row(3, [
                  _table('cicd-setup-secrets', 0, 12,
                         'What each step still needs from you, and WHERE to get it. Presence only — no value '
                         'exists in this table, on this page, or in any answer behind it.',
                         'PipelineSecretPresence',
                         columns='area,secret_name,present,kind,needed_by_json,where_to_get,how_to_make,blocked_why'),
              ]),
          ]),

    _page('cicd-stages', 'cicd-stages',
          'CI/CD — isle testing stages: each stage runs in its OWN throwaway isle, one at a time, and only '
          'what a stage TESTED may ever be released',
          'PipelineStage', [
              _row(0, [
                  _sapi('cicd-stages-now', 0, 7,
                        'The stages in force, in order — stage 1 is core, each later stage adds its apps',
                        '/api/cicd', pick='stages'),
                  _sapi('cicd-stages-rule', 1, 5,
                        'Why the order matters: this list is also the list of what can ever ship',
                        '/api/cicd', pick='release_rule'),
              ], min_height=240),
              _row(1, [
                  _table('cicd-stage-rows', 0, 12,
                         'Stage rows — EDIT HERE (admins only): `index` is the order, `apps` the modules that '
                         'stage installs and selftests inside the isle. An empty app list is core only.',
                         'PipelineStage', columns='name,device,index,apps_json,note'),
              ]),
              _row(2, [
                  _table('cicd-stage-results', 0, 12,
                         'What each stage actually recorded, most recent versions first',
                         'IsleTestResult',
                         columns='version,stage_index,apps_json,core_ok,results_json,uninstall_verdict,'
                                 'leak_verdict,ram_delta_mb,disk_delta_mb,started,finished,error'),
              ]),
          ]),

    _page('cicd-runs', 'cicd-runs',
          'CI/CD — the builds, mirrored in from the pipeline (nothing here drives Jenkins; the mirror flows '
          'one way, inward). dev iterate · test decide · main release.',
          'PipelineRun', [
              # ci-12: THE VERDICT COLUMN, first on the page, because it is the one thing a person comes
              # here to read — "may this sha go to main?". Everything below it is the evidence.
              _row(0, [
                  _sapi('cicd-verdicts-list', 0, 12,
                        'Test verdicts — ONE answer per superproject sha on the test branch. `passed` is '
                        'the only one that may be promoted to main; `partial` means nothing said no but '
                        'something that should have answered did not (today: the isle stages, still ci-3). '
                        'The scan counts are carried here and never change a verdict.',
                        '/api/cicd/verdicts', pick='verdicts'),
              ], min_height=260),
              _row(1, [
                  _table('cicd-verdict-rows', 0, 12,
                         'Verdict rows — sha, branch, verdict and the reason in words; the selftest '
                         'arithmetic; core_ok (the half the release rule turns on, and the half that stays '
                         'false until the ci-3 install cycle lands); and the advisory scan counts.',
                         'TestVerdict',
                         columns='sha,git_branch,verdict,why,built,selftest_suites,selftest_passed,'
                                 'selftest_failed,core_ok,scans_json,selftests_json,isle_json,run,at'),
              ]),
              _row(2, [
                  _sapi('cicd-runs-list', 0, 12,
                        'Recent runs — job, number, version, status and what the run said about itself',
                        '/api/cicd/runs', pick='runs'),
              ], min_height=300),
              _row(3, [
                  _table('cicd-run-rows', 0, 12, 'Run rows', 'PipelineRun',
                         columns='job,number,version,status,started,finished,duration_seconds,commit,summary'),
              ]),
              _row(4, [
                  _table('cicd-result-rows', 0, 12,
                         'Isle test results — per run × stage: did the core install and verify, and what did '
                         'each app\'s selftest say inside the throwaway isle; then the TEARDOWN in its two '
                         'readings — the PRODUCT\'s own uninstall (did the isle hand the machine back? it '
                         'gates the release) and OUR leak diff (did the pipeline leave anything behind? it '
                         'gates the next stage). A negative ram_delta_mb is memory that did not come back.',
                         'IsleTestResult',
                         columns='run,version,stage_index,apps_json,core_ok,results_json,uninstall_verdict,'
                                 'uninstall_json,leak_verdict,leaks_json,ram_delta_mb,disk_delta_mb,error'),
              ]),
          ]),

    _page('cicd-releases', 'cicd-releases',
          'CI/CD — what each version shipped, and what it did NOT, with the reason (' + RULE + ')',
          'ReleaseRecord', [
              _row(0, [
                  _sapi('cicd-releases-list', 0, 12,
                        'Per version: the tag, whether it was pushed, which routes published for real, the '
                        'assets that shipped — and the assets held back, named, with why',
                        '/api/cicd/releases', pick='releases'),
              ], min_height=320),
              _row(1, [
                  _table('cicd-release-rows', 0, 12, 'Release rows', 'ReleaseRecord',
                         columns='version,mode,app_name,tag,tag_pushed,results_present,core_ok,'
                                 'tested_verdict,tested_sha,tested_against,published_routes_json,'
                                 'dry_routes_json,released_json,not_released_json,why_not,released_at'),
              ]),
          ]),
]
