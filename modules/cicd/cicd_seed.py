"""
@module cicd.cicd_seed

WHAT THIS MODULE SEEDS: almost nothing, and that is the point.

A pipeline device is ADOPTED (its first `cicd-sync.sh push`), not seeded — a seeded device would be a
machine nobody owns, with settings nobody set, that a real device would then silently inherit. Runs, isle
results and releases are things that HAPPENED; seeding one would be a claim. So every row table starts
empty.

The one thing that IS seeded is the WRITE GATE: two `AppPermissionProfile` rows, so that when
`POLARI_APP_PERMISSIONS=enforce` is in force the settings rows are an administrator's to change and
everybody else's to read. The import is guarded because the profile class belongs to `polariapps`, and a
core that did not admit polariapps still admits this module perfectly well — it simply has no app-permission
gate to seed for, which is the same state every other module is in there.
"""
from cicd.cicd_basis import (IsleTestResult, PipelineDevice, PipelineRoute, PipelineRun,
                             PipelineSecretPresence, PipelineStage, ReleaseRecord)

#: the settings classes a person may change, and the mirrored ones they may only read
_SETTINGS = ['PipelineDevice', 'PipelineStage', 'PipelineRoute']
_MIRRORED = ['PipelineSecretPresence', 'PipelineRun', 'IsleTestResult', 'ReleaseRecord']

SEED_CICD_PERMISSION_PROFILES = [
    {
        'name': 'cicd-settings',
        'title': 'CI/CD — pipeline settings (administrators)',
        'description': 'Read and CHANGE the pipeline\'s configuration: the device, its testing stages and '
                       'which publication routes may publish. Polari is the source of truth for all of it; '
                       'the device\'s device.env is rewritten from these rows at the top of every run.',
        'app_name': '',
        'kc_groups_json': '["polari-admin"]',
        'verbs_json': '["read", "create", "update", "delete"]',
        'extra_classes_json': '["PipelineDevice", "PipelineStage", "PipelineRoute"]',
        'published': True,
        'is_prior': True,
        'notes': 'ci-8. ADMIN_ROLES already bypass the gate; this row states the intent explicitly so the '
                 'grant survives a change to that bypass, and so the profiles page shows who may turn a '
                 'pipeline knob. The mirrored tables (runs, isle results, releases, secret presence) are '
                 'deliberately absent: they are written by the pipeline through POST /api/cicd/ingest with '
                 'a posting-only token, and a person hand-editing a run that happened is not a thing to grant.',
    },
    {
        'name': 'cicd-observer',
        'title': 'CI/CD — read the pipeline (template)',
        'description': 'Read the pipeline: its settings, its runs, what each isle stage tested and what each '
                       'version was allowed to ship. Changes nothing.',
        'app_name': '',
        'kc_groups_json': '[]',
        'verbs_json': '["read"]',
        'extra_classes_json': '["PipelineDevice", "PipelineStage", "PipelineRoute", '
                              '"PipelineSecretPresence", "PipelineRun", "IsleTestResult", "ReleaseRecord", '
                              '"TestVerdict"]',
        'published': False,
        'is_prior': True,
        'notes': 'TEMPLATE, the shipped convention: it grants nothing until a real Keycloak group is bound '
                 'in kc_groups_json (see /api/groups) and published is set true. Reading is safe by '
                 'construction — no table in this module holds a secret value.',
    },
]

CICD_SEED_PAIRS = [
    # A device is ADOPTED by its first push, never seeded — see the module docstring.
    ('PipelineDevice', PipelineDevice, []),
    ('PipelineStage', PipelineStage, []),
    ('PipelineRoute', PipelineRoute, []),
    # PRESENCE, reported by the device. Never seeded: Polari cannot know what is on another machine's disk.
    ('PipelineSecretPresence', PipelineSecretPresence, []),
    # Things that HAPPENED. A seeded run would be a claim about a build nobody ran.
    ('PipelineRun', PipelineRun, []),
    ('IsleTestResult', IsleTestResult, []),
    ('ReleaseRecord', ReleaseRecord, []),
]

try:                                        # the write gate, when polariapps is admitted here
    from polariapps.apps_permissions_basis import AppPermissionProfile as _APP
    CICD_SEED_PAIRS.append(('AppPermissionProfile', _APP, SEED_CICD_PERMISSION_PROFILES))
except Exception:                           # no polariapps on this instance → no app-permission gate to seed
    _APP = None
