"""
@module cicd.objects.cicd.TestVerdict

Row class TestVerdict of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TestVerdict(treeObject):
    """ONE SHA, ONE ANSWER (ci-12, his ruling 2026-09-19: "Based on the outcome on the test stage, we make a
    decision to push changes to main.").

    A decision needs a thing to decide ON. This row is that thing: for one superproject sha on the `test`
    branch, what the test pipeline built, what it scanned, what it ran and what it concluded. Everything
    downstream reads it and nothing downstream re-derives it — `pol jenkins promote main` refuses on it, and
    `routes/_lib.sh` refuses on it independently, so an untested build cannot be published even by hand.

    WHY A ROW OF ITS OWN, AND NOT FIELDS ON ReleaseRecord. It was the smaller change, though it is the extra
    file. A ReleaseRecord is per VERSION and is created by a release; a verdict is per SHA and exists BEFORE
    any version is minted, for shas that may never be released at all (most of them — you test far more than
    you ship). Carrying verdicts on ReleaseRecord would mean inventing a release row for every test run, so
    the table whose whole purpose is "what this version shipped" would fill with rows that shipped nothing,
    and `released_json`/`not_released_json` would be empty in most of it. The linkage goes the other way
    instead: `ReleaseRecord.tested_verdict` names the TestVerdict row a release was allowed by.

    (`ReleaseRecord.tested_against` is deliberately NOT reused for this. It already means something precise
    and different — the CORE RELEASE an app-mode build passed against — and the ingest door refuses an
    app-mode release that leaves it empty. Overloading it would make one column answer two questions and
    break that refusal.)

    THE VERDICTS, and why there are three:

        passed    every configured module selftest passed AND the isle stages recorded core_ok
                  (which, per ci-10, already requires a CLEAN hand-back from the product's own uninstall)
        failed    something that RAN said no
        partial   nothing said no, but something that should have answered did not

    `partial` is for a run where something that should have answered did not — no isle results at all, or a
    stage that could not be run because an earlier one leaked. It was the RESTING state until ci-3 (his ask
    2026-09-20): the install + selftest cycle inside the throwaway guest was a marked TODO, so every stage
    recorded `skipped` and `core_ok` could never become true. That cycle exists now, so a run that installs
    the deb, stands the isle up, runs the suites inside it and hands the machine back clean reaches
    `passed`, and one that cannot reaches `failed` with the first failing part named in `why`.

    `report_path` names the ONE PAGE rendered for this sha (`polari-jenkins/report.py` →
    `pool/test/<sha>/TEST_REPORT.md`): the verdict and why, the debs with their sha256, the image IDs that
    were installed, the advisory scan counts, the device selftests, and per isle stage the install
    time-to-online, the verify details, the suites that ran inside the product, the uninstall verdict with
    the product's own findings, and the leak diff. The release attaches that file as an asset, so the
    question "what was this release tested with?" is answerable from the release page alone.

    SCANS ARE CARRIED, NEVER COUNTED. `scans_json` holds the advisory counts by severity per tool so a
    person reading the verdict sees them without a log dive. No number in it can change `verdict` by one
    letter (his standing rule: security scans are advisory, never a gate).
    """

    #: the three answers, and nothing else
    VERDICTS = ('passed', 'failed', 'partial')
    #: who decided — the pipeline computes it; a person overriding one does it on a branch, loudly, not here
    DECIDERS = ('pipeline',)

    #: `git_branch`, NOT `branch`: `branch` is one of treeObject's own internal variables
    #: (objectTreeDecorators.TREE_OBJECT_INTERNAL_VARS), and a row field of that name silently
    #: breaks every construction of the class — "no branch was defined on the object" and then
    #: an INSERT that fails with no attribute `manager`. Found by the selftest, not by reading.
    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', sha: str = '', git_branch: str = 'test',
                 verdict: str = 'partial', why: str = '', built: bool = False,
                 scans_json: str = '{}', selftests_json: str = '{}', isle_json: str = '{}',
                 selftest_suites: int = 0, selftest_passed: int = 0, selftest_failed: int = 0,
                 core_ok: bool = False, run: str = '', decided_by: str = 'pipeline',
                 report_path: str = '', at: str = '', posted_by: str = ''):
        self.name = name                    # the row id — <device>:<sha>
        self.device = device                # PipelineDevice.name
        self.sha = sha                      # the SUPERPROJECT sha this verdict is about
        self.git_branch = git_branch        # the git branch it was tested on (test)
        self.verdict = verdict              # VERDICTS
        self.why = why                      # the one-line reason, in words — the column a person reads first
        self.built = built                  # did the build stage produce the artifacts the tests ran against
        # the three summaries, as JSON strings: they are opaque to the row and are rendered as configured
        # columns on the page (his rule: no raw JSON on a screen — a table cell is a configured column).
        self.scans_json = scans_json        # {tool: {severity: count}} + totals — ADVISORY
        self.selftests_json = selftests_json  # {module: pass|fail|skipped} + counts
        self.isle_json = isle_json          # core_ok, stages, passed/untested apps, uninstall verdicts
        self.selftest_suites = selftest_suites
        self.selftest_passed = selftest_passed
        self.selftest_failed = selftest_failed
        self.core_ok = core_ok              # what the isle stages recorded — the half that is still ci-3
        self.run = run                      # PipelineRun.name of the polari-test build that decided it
        self.decided_by = decided_by        # DECIDERS
        self.report_path = report_path      # ci-3: pool/test/<sha>/TEST_REPORT.md — the page, and a release asset
        self.at = at
        self.posted_by = posted_by          # the credential name that mirrored it in
