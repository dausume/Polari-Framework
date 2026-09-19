"""
@module cicd.cicd_page

/display/cicd            the pipeline: which device, is it ready, which routes may publish, and the rule
                         that decides what may ever ship
/display/cicd-stages     the isle testing stages — the ordered list that IS what can be released
/display/cicd-runs       the mirrored Jenkins builds and what each isle stage recorded
/display/cicd-releases   per version: what shipped, and what did not, with the reason

CONFIGURED PAGES ONLY. Every item here is one of the two generic registered components — `class-rows-table`
and `api-structured-panel` — so ci-8 added no Angular at all (his rule: "there should not be any json
showing on the screens, everything should be configured tables, graphs, or visualizations"; and the
per-object display rule: a setting is edited on its OWN row's page, through CRUDE, not on a bespoke
settings screen).

That is also WHY the settings tables are on these pages: the `class-rows-table` over `PipelineDevice`,
`PipelineStage` and `PipelineRoute` IS the editing surface, gated by the `cicd-settings` permission profile
(cicd_seed) — admins change a knob, everybody else reads it.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

#: the rule, short enough for a panel title
RULE = ('the pipeline only ships what it TESTED in a throwaway isle — no results for a version means '
        'nothing is published and the tag is not pushed')

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
                         columns='version,stage_index,apps_json,core_ok,results_json,started,finished,error'),
              ]),
          ]),

    _page('cicd-runs', 'cicd-runs',
          'CI/CD — the builds, mirrored in from the pipeline (nothing here drives Jenkins; the mirror flows '
          'one way, inward)',
          'PipelineRun', [
              _row(0, [
                  _sapi('cicd-runs-list', 0, 12,
                        'Recent runs — job, number, version, status and what the run said about itself',
                        '/api/cicd/runs', pick='runs'),
              ], min_height=300),
              _row(1, [
                  _table('cicd-run-rows', 0, 12, 'Run rows', 'PipelineRun',
                         columns='job,number,version,status,started,finished,duration_seconds,commit,summary'),
              ]),
              _row(2, [
                  _table('cicd-result-rows', 0, 12,
                         'Isle test results — per run × stage: did the core install and verify, and what did '
                         'each app\'s selftest say inside the throwaway isle', 'IsleTestResult',
                         columns='run,version,stage_index,apps_json,core_ok,results_json,error'),
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
                                 'tested_against,published_routes_json,dry_routes_json,released_json,'
                                 'not_released_json,why_not,released_at'),
              ]),
          ]),
]
