"""
@module cicd.objects.cicd.IsleTestResult

Row class IsleTestResult of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class IsleTestResult(treeObject):
    """ONE STAGE OF ONE isle-test RUN, mirrored from `pool/<version>/isle-test/results.json` (§70 addendum).

    His ask, 2026-09-19: *"the testing isle being what the pipeline is analyzing. The pipeline should only
    generate artifact for things that are tested."* This row IS that reading, brought where a person can see
    it: a stage stood a throwaway isle up, installed the core debs and its own app debs, ran each app's
    selftest inside the isle, recorded, and tore the isle down.

    `core_ok` is stage 1's core verdict (every stage installs the core, but the recorded one is the first).
    `results_json` maps app → `pass` | `fail` | `skipped`. `skipped` is the honest state today: the install
    cycle inside the guest is ci-3, still a marked TODO in `Jenkinsfile.isle-test`, so nothing passes yet and
    THE RELEASE RULE therefore publishes nothing. That is a real reading, not a gap in this module.
    """

    #: what a stage can record for an app
    OUTCOMES = ('pass', 'fail', 'skipped')

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', run: str = '', version: str = '',
                 stage_index: int = 1, apps_json: str = '[]', core_ok: bool = False,
                 results_json: str = '{}', started: str = '', finished: str = '', error: str = '',
                 posted_by: str = ''):
        self.name = name                # the row id — <run>:stage<index>
        self.device = device            # PipelineDevice.name
        self.run = run                  # PipelineRun.name
        self.version = version          # the pool version under test
        self.stage_index = stage_index  # 1-based, matching PipelineStage.index
        self.apps_json = apps_json      # the apps this stage tested; [] = core only
        self.core_ok = core_ok          # the core deb install + verify passed inside the throwaway isle
        self.results_json = results_json    # {app: pass|fail|skipped}
        self.started = started
        self.finished = finished
        self.error = error              # a stage that threw records it and the NEXT stage still runs
        self.posted_by = posted_by
