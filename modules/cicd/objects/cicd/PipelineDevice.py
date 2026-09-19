"""
@module cicd.objects.cicd.PipelineDevice

Row class PipelineDevice of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PipelineDevice(treeObject):
    """ONE ROW PER PIPELINE DEVICE — and the SOURCE OF TRUTH for what `polari-jenkins/device.env` holds
    (ci-8, his ask 2026-09-19: *"We may want a CICD app as well that is always enabled with the pipeline
    that can allow us to read and modify the settings of the pipeline."*).

    THE DIRECTION OF TRUTH (the lead's ruling): Polari is the source, `device.env` is the FALLBACK. The
    device pulls (`cicd-sync.sh pull` → GET /api/cicd) at the top of every pipeline run and rewrites
    `device.env` from these columns; when the core does not answer it keeps the file it has and says so, so
    a pipeline never stalls because a Polari instance is down. `pol jenkins setup`/`doctor` push the other
    way after a change, so a knob turned on the device is not silently lost either.

    EDITING IS A CRUDE ACT ON THIS ROW'S OWN PAGE (his per-object display rule): there is no bespoke
    settings screen and no new frontend component. The write gate is the app-permission profile
    `cicd-settings` (cicd_seed) — admins only.

    ⚠ NO ADDRESS EVER. `isle_ssh_alias` is a `Host` entry from `~/.ssh/config`, never a hostname and never
    an IP; the same rule `device.env.example` carries. The validation refuses anything that parses as an
    address (`cicd.custom.cicd_validate.alias_findings`).

    ⚠ NO SECRET EVER. `ingest_token_hash` is the sha256 of the posting-only token, never the token. The
    token itself is shown ONCE, by `POST /api/cicd/device/token`, and is never stored, logged or echoed
    again. It may post the five mirror kinds and nothing else — it is not a build credential, it is not a
    Jenkins account, and it cannot read or change a setting.

    TWO MODES (his addendum 2026-09-19: *"some people will also be using this pipeline as a way to maintain
    their own Polari Apps and will only be testing the one app they are developing."*):

      `suite`  today's shape — the whole Polari suite is built, tested in a throwaway isle, and released.
      `app`    ONE Polari app, maintained by its developer. `app_name` is the module package,
               `app_repo` their `polari-module-<name>` git URL (the standalone loop `pol project` already
               builds). The CORE is not rebuilt: `core_source` = `release:<tag>` PULLS the official Polari
               release's core debs and images as artifacts (`release:latest` is allowed and is the default),
               so the app is tested against a core somebody else already proved. `core_source: build` is the
               escape hatch for a developer who also patches core from a suite checkout.

    In `app` mode the stages default to `core; <app_name>`, the isle test runs that app's selftests after the
    core verify and nothing else, and the release carries ONLY that app's deb — published to THEIR routes
    (`PipelineRoute.target` names the repo/registry owner), never to upstream Polari. A fork is never
    republished under an upstream name. The release rule is unchanged: the app deb ships only when its stage
    passed, and `ReleaseRecord.tested_against` records the core release it passed against.
    """

    #: the roles a device may hold — the pipeline controller, the throwaway-isle target, or both
    ROLES = ('pipeline', 'isle-target', 'both')
    #: what this device's pipeline is FOR (his addendum 2026-09-19)
    MODES = ('suite', 'app')
    #: where the throwaway isle goes (device.env CI_ISLE_TARGET)
    ISLE_TARGETS = ('local', 'ssh')
    #: device.env CI_ISLE_NESTED
    NESTED = ('auto', 'required', 'off')

    @treeObjectInit
    def __init__(self, name: str = '', role: str = 'pipeline', mode: str = 'suite',
                 app_name: str = '', app_repo: str = '', core_source: str = 'release:latest',
                 isle_target: str = 'local', isle_ssh_alias: str = '', isle_ssh_user: str = '',
                 vm_name: str = 'polari-ci-isle', vm_ram_gb: int = 4, vm_vcpus: int = 2, vm_disk_gb: int = 30,
                 nested: str = 'auto', isle_pool: str = '', image_url: str = '',
                 min_free_gb: int = 20, min_ram_headroom_gb: int = 1, executors: int = 1,
                 cache: str = 'on', cache_dir: str = '', cache_max_gb: int = 40,
                 cache_proxies: str = 'off', route_target: str = '',
                 routes_json: str = '[]', stages_summary: str = 'core',
                 setup_steps_done: int = 0, setup_steps_total: int = 8, setup_ready: bool = False,
                 setup_verdict: str = '', doctor_warnings: int = 0, preflight_verdict: str = '',
                 ingest_token_hash: str = '', token_issued_at: str = '', token_issued_by: str = '',
                 last_seen: str = '', last_pull: str = '', posted_by: str = '', notes: str = ''):
        self.name = name                        # the row id — the device's own name (never a hostname)
        self.role = role                        # ROLES
        self.mode = mode                        # MODES — CI_MODE: the whole suite, or ONE app
        self.app_name = app_name                # CI_APP_NAME — the module package this device maintains (app mode)
        self.app_repo = app_repo                # CI_APP_REPO — their polari-module-<name> git URL (app mode)
        self.core_source = core_source          # CI_CORE_SOURCE — release:<tag>|release:latest (PULL) | build
        self.isle_target = isle_target          # CI_ISLE_TARGET — local | ssh
        self.isle_ssh_alias = isle_ssh_alias    # CI_ISLE_SSH_HOST — an ssh ALIAS, never an address
        self.isle_ssh_user = isle_ssh_user      # CI_ISLE_SSH_USER — optional remote user
        self.vm_name = vm_name                  # CI_ISLE_VM_NAME
        self.vm_ram_gb = vm_ram_gb              # CI_ISLE_VM_RAM_GB
        self.vm_vcpus = vm_vcpus                # CI_ISLE_VM_VCPUS
        self.vm_disk_gb = vm_disk_gb            # CI_ISLE_VM_DISK_GB
        self.nested = nested                    # CI_ISLE_NESTED — NESTED
        self.isle_pool = isle_pool              # CI_ISLE_POOL — a path on the TARGET, empty = the default
        self.image_url = image_url              # CI_ISLE_IMAGE_URL — the cloud image the throwaway starts from
        self.min_free_gb = min_free_gb          # CI_MIN_FREE_GB — the retention floor
        self.min_ram_headroom_gb = min_ram_headroom_gb   # CI_MIN_RAM_HEADROOM_GB
        self.executors = executors              # CI_EXECUTORS — casc numExecutors follows it
        # ci-9 — THE OFFLINE-FIRST CACHE (his ask 2026-09-19: "the jenkins pipeline should try and use
        # offline artifacts for building where possible, that way we are taking less time when repeatedly
        # using the same data"). Tier one is a DIRECTORY the builders read first; tier two is four opt-in
        # caching proxies on 127.0.0.1. Every knob here is advisory: a misconfigured cache makes a build
        # slower, never refuses one.
        self.cache = cache                      # CI_CACHE — on | off
        self.cache_dir = cache_dir              # CI_CACHE_DIR — empty = <pool>/cache
        self.cache_max_gb = cache_max_gb        # CI_CACHE_MAX_GB — the doctor warns past it; it never deletes
        self.cache_proxies = cache_proxies      # CI_CACHE_PROXIES — off | on (tier two, opt-in)
        # ci-9 — WHERE THIS DEVICE'S OWN RELEASES GO. Unused in suite mode. In app mode it is required and
        # it may never be the upstream owner: a fork is never republished under an upstream name.
        self.route_target = route_target        # CI_ROUTE_TARGET
        self.routes_json = routes_json          # CI_ROUTES as a JSON list — the routes that MAY publish
        self.stages_summary = stages_summary    # CI_ISLE_STAGES rendered — the PipelineStage rows are the truth
        self.setup_steps_done = setup_steps_done        # SETUP_STATUS.md: steps N of M complete
        self.setup_steps_total = setup_steps_total
        self.setup_ready = setup_ready          # SETUP_STATUS.md verdict == READY
        self.setup_verdict = setup_verdict      # READY | NOT READY, verbatim
        self.doctor_warnings = doctor_warnings  # the doctor's warning count at the last push
        self.preflight_verdict = preflight_verdict      # PASS | FAIL from preflight --isle --json
        self.ingest_token_hash = ingest_token_hash      # sha256 of the posting-only token — NEVER the token
        self.token_issued_at = token_issued_at
        self.token_issued_by = token_issued_by  # the issuing admin's Keycloak `sub` alone (D18-1)
        self.last_seen = last_seen              # when the device last posted anything
        self.last_pull = last_pull              # when the device last pulled its settings
        self.posted_by = posted_by              # the `sub` or the credential name that last wrote this row
        self.notes = notes
