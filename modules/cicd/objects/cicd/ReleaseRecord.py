"""
@module cicd.objects.cicd.ReleaseRecord

Row class ReleaseRecord of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ReleaseRecord(treeObject):
    """ONE VERSION, AND WHAT IT WAS ALLOWED TO SHIP (§70 addendum, THE RELEASE RULE).

    The rule, hard: no `isle-test/results.json` for a version → every route dry and the tag NOT pushed;
    `core_ok` false → the same; an app whose stage result is not `pass` → its deb left out of the assets and
    NAMED, with the reason, under "not released". `DRY_RUN=false` does not override it.

    So this row carries BOTH halves. `released_json` is what actually shipped. `not_released_json` is the
    other half — `{asset: why}` — and it is the column that makes the rule legible to somebody who did not
    read `routes/_lib.sh`: an app is missing from a release because nobody tested it, and the record says so
    by name rather than by absence.

    `tested_against` is what makes an APP-mode release honest (his addendum 2026-09-19). A developer
    maintaining one Polari app does not rebuild the core: they PULL an official Polari release's core debs
    and images (`PipelineDevice.core_source = release:<tag>`) and test their app against that. So the record
    must say WHICH core it passed against — "polari-app-household 2026.09.20 passed against core
    polari-v2026.09.19" is a claim somebody can check; "it passed" is not. In `suite` mode it holds the
    version's own tag, because the core it was tested against is the one this run built.
    """

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', version: str = '', tag: str = '',
                 tag_pushed: bool = False, results_present: bool = False, core_ok: bool = False,
                 mode: str = 'suite', app_name: str = '', tested_against: str = '',
                 published_routes_json: str = '[]', dry_routes_json: str = '{}',
                 released_json: str = '[]', not_released_json: str = '{}',
                 run: str = '', released_at: str = '', why_not: str = '', posted_by: str = ''):
        self.name = name                        # the row id — <device>:<version>
        self.device = device                    # PipelineDevice.name
        self.version = version                  # the minted calendar version (mint-tag.sh: YYYY.MM.DD[.N])
        self.tag = tag                          # polari-vYYYY.MM.DD[.N] — minted, whether or not it was pushed
        self.tag_pushed = tag_pushed            # only with a github credential AND the release rule satisfied
        self.results_present = results_present   # was there an isle-test/results.json for this version at all
        self.core_ok = core_ok                  # what that file said about the core
        self.mode = mode                        # suite | app — what this device's pipeline is for
        self.app_name = app_name                # the one app this release is of (app mode)
        self.tested_against = tested_against    # the CORE release this passed against (app mode: release:<tag>)
        self.published_routes_json = published_routes_json   # routes that published FOR REAL
        self.dry_routes_json = dry_routes_json  # {route: why it stayed dry} — the honest other half
        self.released_json = released_json      # the assets that shipped
        self.not_released_json = not_released_json   # {asset: why} — untested or failed, named
        self.run = run                          # PipelineRun.name of the release build
        self.released_at = released_at
        self.why_not = why_not                  # the one-line reason nothing shipped, when nothing did
        self.posted_by = posted_by
