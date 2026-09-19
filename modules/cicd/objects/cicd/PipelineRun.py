"""
@module cicd.objects.cicd.PipelineRun

Row class PipelineRun of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PipelineRun(treeObject):
    """ONE JENKINS BUILD, MIRRORED IN (ci-8). The pipeline posts a row at the START of a run and again when
    it FINISHES, through `POST /api/cicd/ingest` with the posting-only credential.

    MIRRORED, NOT DRIVEN. Nothing in Polari starts, stops or reads a Jenkins build: the credential the
    device holds can post these five kinds and nothing else. It is not a Jenkins account, it has no build
    permission, and there is no door here that asks Jenkins for anything. The pipeline is the only thing
    that talks to Jenkins, and it talks outward.

    `url` is the controller's own UI URL, which is a LOOPBACK url by construction (`docker-compose.yml`
    binds `127.0.0.1:${JENKINS_PORT}` only, and the doctor warns if that ever changes). It is stored so a
    person sitting at the device — or on an `ssh -L` tunnel — can click through to the console; it names no
    address because there is no address to name. The ingest door refuses a `url` that is not loopback,
    rather than storing a LAN address into a row that a page could render.
    """

    #: the jobs seeded by polari-jenkins/jobs/seed.groovy. ci-12 added `test` — the TESTING pipeline that
    #: the `test` branch drives (wipe → build → scan → test → one verdict) — and `release-manual`, the
    #: hand-driven twin of `release` that exists so the POLLED release job can stay unparameterised and
    #: therefore coalesce its queued items.
    JOBS = ('dev-build', 'test', 'release', 'release-manual', 'publish', 'isle-test')
    #: a run's state — `running` is what a start post writes
    STATUSES = ('running', 'success', 'unstable', 'failure', 'aborted')

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', job: str = '', number: int = 0, version: str = '',
                 status: str = 'running', started: str = '', finished: str = '', duration_seconds: int = 0,
                 url: str = '', summary: str = '', commit: str = '', posted_by: str = ''):
        self.name = name                # the row id — <device>:<job>#<number>
        self.device = device            # PipelineDevice.name
        self.job = job                  # JOBS
        self.number = number            # the Jenkins build number
        self.version = version          # the pool version this run is about ('' for a bare dev build)
        self.status = status            # STATUSES
        self.started = started
        self.finished = finished
        self.duration_seconds = duration_seconds
        self.url = url                  # the controller's loopback console URL — never a LAN address
        self.summary = summary          # one line: what the run did, or why it stopped
        self.commit = commit            # the superproject sha the run built
        self.posted_by = posted_by      # the credential name that mirrored it in
