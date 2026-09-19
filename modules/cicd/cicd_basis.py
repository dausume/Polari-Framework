"""
@module cicd.cicd_basis

The INDEX of the cicd rows: classes live one-per-file under objects/; this file re-exports them
and holds the list admission registers.
"""
from cicd.objects.cicd.PipelineDevice import PipelineDevice  # noqa: F401
from cicd.objects.cicd.PipelineStage import PipelineStage  # noqa: F401
from cicd.objects.cicd.PipelineRoute import PipelineRoute  # noqa: F401
from cicd.objects.cicd.PipelineSecretPresence import PipelineSecretPresence  # noqa: F401
from cicd.objects.cicd.PipelineRun import PipelineRun  # noqa: F401
from cicd.objects.cicd.IsleTestResult import IsleTestResult  # noqa: F401
from cicd.objects.cicd.ReleaseRecord import ReleaseRecord  # noqa: F401

#: THE SETTINGS rows — Polari is their source of truth and `device.env` is derived from them.
#: A write here is a CRUDE act on the row's own page, gated by the `cicd-settings` permission profile.
CICD_SETTINGS_CLASSES = [PipelineDevice, PipelineStage, PipelineRoute]

#: THE MIRRORED rows — written only by the pipeline, through POST /api/cicd/ingest, with the
#: posting-only credential. A person reads them; nobody hand-edits a run that happened.
CICD_MIRROR_CLASSES = [PipelineSecretPresence, PipelineRun, IsleTestResult, ReleaseRecord]

CICD_CLASSES = CICD_SETTINGS_CLASSES + CICD_MIRROR_CLASSES
