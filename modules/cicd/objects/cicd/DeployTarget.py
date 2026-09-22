"""
@module cicd.objects.cicd.DeployTarget

Row class DeployTarget of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DeployTarget(treeObject):
    """ONE PLACE POLARI RUNS, AND THE CONDITIONS UNDER WHICH THE PIPELINE MAY TOUCH IT (dep-0, plan §11.2).

    A SETTINGS row: Polari is its source of truth and `polari-jenkins/deploy/targets.env` is the device's
    fallback, exactly as `PipelineDevice` is to `device.env`. His ruling 2026-09-22 bounds what "touch"
    means: the pipeline's key on the target is RESTRICTED to the deploy agent (`pol prod agent`) — it can
    stash the stack's volumes, replace images with `docker service update`, verify, and nothing else. It
    never runs `pol prod apply`, never reads the vault. The FIRST deploy of a box is a person's.

    `ssh_alias` is an alias in the PIPELINE user's ssh config, never an address — the ingest door refuses an
    address the same way it does for the isle target. `name` is chosen (it is rendered here), never a
    hostname. `hold` true means nothing deploys by itself: only `pol jenkins deploy <name> --now`, a person.
    """

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', ssh_alias: str = '', route: str = 'swarm',
                 profile: str = 'lean', channel: str = 'release', window: str = 'any', health_urls: str = '',
                 min_free_gb: int = 4, needs_routes: str = 'github-release,ghcr', settle_s: int = 60,
                 hold: bool = True, notes: str = ''):
        self.name = name                    # chosen — rendered on a page, never a hostname
        self.device = device                # the PipelineDevice that deploys to it
        self.ssh_alias = ssh_alias          # an alias in the pipeline user's ssh config — never an address
        self.route = route                  # swarm (pol prod stack: the agent swaps images) | isle (the deb route, later)
        self.profile = profile              # the pol prod stack size there: lean | full
        self.channel = channel              # release (a published release with a passed verdict) | test (a staging box)
        self.window = window                # a 5-field cron window, or any
        self.health_urls = health_urls      # space-separated URLs that must answer 2xx before AND after
        self.min_free_gb = min_free_gb      # disk floor on the target
        self.needs_routes = needs_routes    # the publish routes this target CONSUMES; they must have published for real
        self.settle_s = settle_s            # seconds between the update and the health-after reading
        self.hold = hold                    # true = never automatic; a person's --now only
        self.notes = notes
