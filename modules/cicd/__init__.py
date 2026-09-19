"""
@module cicd

CI/CD — the build + publish pipeline's SETTINGS as Polari rows, and its runs mirrored in (ci-8; his ask
2026-09-19: *"We may want a CICD app as well that is always enabled with the pipeline that can allow us to
read and modify the settings of the pipeline."*).

Polari is the SOURCE OF TRUTH for the pipeline's configuration; `polari-jenkins/device.env` is the fallback
and is rewritten from these rows by `cicd-sync.sh pull` at the top of every Jenkinsfile. Runs, isle-test
stage results, release records and secret PRESENCE come the other way, through one posting-only credential
that can reach `POST /api/cicd/ingest` and nothing else.

Requires nothing from other feature modules (the app-permission profiles it seeds are guarded).
"""
from cicd.cicd_basis import CICD_CLASSES, IsleTestResult, PipelineDevice, PipelineRoute, PipelineRun, PipelineSecretPresence, PipelineSetupStep, PipelineStage, ReleaseRecord  # noqa: F401
from cicd.cicd_seed import CICD_SEED_PAIRS  # noqa: F401
from cicd.cicd_page import SEED_CICD_PAGE_DISPLAYS  # noqa: F401
