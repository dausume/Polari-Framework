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

    ci-10 (his ask + addendum 2026-09-19) adds the TEARDOWN, which is two different readings and must be
    read as two:

    * `uninstall_verdict` — **a test result about the PRODUCT.** Before the VM is destroyed, the stage runs
      the isle's own `isle uninstall --everything`, its own zero-footprint verify, and the hand-back proof
      (a default route, public DNS, apt, a network owner). `clean` | `dirty` | `failed` | `skipped`, with
      `uninstall_json` carrying the product's own words. It is COUPLED to `core_ok`: an isle that cannot
      hand the machine back is not releasable, whatever its selftests said. `skipped` is not a pass — it
      means the hand-back was never exercised, which is every stage's state until ci-3 lands.
    * `leak_verdict`, `leaks_json`, `ram_delta_mb`, `disk_delta_mb` — **a resource guard about the
      PIPELINE.** After the wipe, the target is diffed against a baseline taken before stage 1: anything new
      that survived is a leak, and so is RAM or disk that did not come back (`ram_delta_mb` negative past
      the tolerance is exactly the "memory issues" the ask names). A leak never blocks a release — it is
      our mess, not the product's — but it stops the NEXT stage, which would otherwise start dirtier.
    """

    #: what a stage can record for an app
    OUTCOMES = ('pass', 'fail', 'skipped')
    #: what the PRODUCT's own uninstall can record (a test result — it gates the release)
    UNINSTALL_VERDICTS = ('clean', 'dirty', 'failed', 'skipped')
    #: what OUR wipe + diff can record (a resource guard — it gates the next stage, never a release)
    LEAK_VERDICTS = ('clean', 'leaked', 'leaked-after-rewipe', 'leak-check-unreadable')

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', run: str = '', version: str = '',
                 stage_index: int = 1, apps_json: str = '[]', core_ok: bool = False,
                 results_json: str = '{}', started: str = '', finished: str = '', error: str = '',
                 uninstall_verdict: str = 'skipped', uninstall_json: str = '{}',
                 leak_verdict: str = 'clean', leaks_json: str = '[]',
                 ram_delta_mb: int = 0, disk_delta_mb: int = 0,
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
        # ---- ci-10: the product's own hand-back (a TEST — it gates the release)
        self.uninstall_verdict = uninstall_verdict   # clean|dirty|failed|skipped
        self.uninstall_json = uninstall_json         # the product's own findings, verbatim
        # ---- ci-10: our own leak diff (a RESOURCE GUARD — it gates the next stage)
        self.leak_verdict = leak_verdict             # clean|leaked|leaked-after-rewipe|leak-check-unreadable
        self.leaks_json = leaks_json                 # what survived the wipe, one string per thing
        self.ram_delta_mb = ram_delta_mb             # now − baseline; NEGATIVE = memory that did not come back
        self.disk_delta_mb = disk_delta_mb           # now − baseline on the libvirt images dir
        self.posted_by = posted_by
