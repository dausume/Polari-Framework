"""
@module cicd.objects.cicd.PipelineRoute

Row class PipelineRoute of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PipelineRoute(treeObject):
    """ONE PUBLICATION ROUTE, and whether it may publish for real (ci-7 (C); `polari-jenkins/routes/_lib.sh`
    `arm()`).

    A route publishes for real only when BOTH are true: its secret is present on the device (`armed`) AND it
    is in the device's `CI_ROUTES` list (`enabled`). Everything else renders. `enabled` is the knob a person
    turns HERE — it is the half Polari owns. `armed` is REPORTED by the device, because only the device can
    see whether a secret file exists, and it is a boolean about PRESENCE: no value, no path, no fingerprint
    of a value ever reaches this row.

    `parked` marks the routes his rule shelved (dockerhub, npm, pypi, launchpad, snap — each needs an outside
    account); `why` carries the reason a route is dry or parked so the overview page can say it in words.

    Note that `enabled` + `armed` is still not permission to publish: THE RELEASE RULE (§70 addendum) sits
    above both — with no isle-test results for a version, every route is dry whatever these columns say.

    `target` is WHOSE route this is (his addendum 2026-09-19): the repo or registry OWNER a publish goes to.
    A developer maintaining their own Polari app publishes to their own GitHub releases and their own ghcr
    namespace — never to upstream Polari's. A fork republished under an upstream name would be a lie about
    provenance, so an `app`-mode device with a route whose target is the upstream owner is a validation
    FAIL, not a warning.
    """

    #: the upstream owner — an app-mode device may never publish under it
    UPSTREAM_OWNER = 'dausume'

    #: the routes ci-7 declared ACTIVE (secrets.sh SECRETS_ACTIVE_ROUTES)
    ACTIVE = ('github-release', 'ghcr', 'homebrew', 'apt-repo')
    #: parked by his rule — each needs an outside account (secrets.sh SECRETS_PARKED_ROUTES)
    PARKED = ('dockerhub', 'npm', 'pypi', 'launchpad', 'snap')

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', enabled: bool = False, armed: bool = False,
                 parked: bool = False, why: str = '', secrets_json: str = '[]', target: str = '',
                 last_published_at: str = '', last_published_url: str = '', posted_by: str = ''):
        self.name = name                # the row id — <device>:<route> (a device may enable a route another does not)
        self.device = device            # PipelineDevice.name
        self.enabled = enabled          # in CI_ROUTES — the knob a person turns here
        self.armed = armed              # the device reports its secret is PRESENT — never the value
        self.parked = parked            # shelved by his rule (needs an outside account)
        self.why = why                  # in words: why this route is dry, or why it is parked
        self.secrets_json = secrets_json    # the secret NAMES this route needs (area/name), never a value
        self.target = target            # the repo/registry OWNER a publish goes to — an app developer's own
        self.last_published_at = last_published_at
        self.last_published_url = last_published_url
        self.posted_by = posted_by
