"""
@module cicd.objects.cicd.DeployRecord

Row class DeployRecord of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DeployRecord(treeObject):
    """ONE DEPLOY OF ONE RELEASE TO ONE TARGET, AND HOW IT WENT (dep-1, plan §11.4).

    Mirrored, never judged: `polari-jenkins/deploy/apply.sh` wrote applied.json or failed.json on the
    device and posted it here as kind `deploy`. The row answers "what runs where, since when, from which
    release" — and on a failure, where it rolled back to (a re-pin of the previous release; the volume stash
    the agent made before anything moved stays on the target for a person's `pol prod restore`).

    A skipped deploy is NOT a record: a condition that was false is written to the device's pool
    (skipped.json) and read with `pol jenkins deploy status`; only something that touched the target is
    mirrored, because this table is the history of the target, not of the pipeline's ticks.
    """

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', target: str = '', release: str = '',
                 from_release: str = '', result: str = '', failed_at: str = '', rollback: str = '',
                 stash: str = '', apply_seconds: int = 0, at: str = '', posted_by: str = ''):
        self.name = name                    # the row id — <device>:<target>:<release>
        self.device = device                # PipelineDevice.name
        self.target = target                # DeployTarget.name
        self.release = release              # polari-vYYYY.MM.DD[.N] deployed (or attempted)
        self.from_release = from_release    # what the target ran before — the rollback point
        self.result = result                # applied | failed
        self.failed_at = failed_at          # stash | update | verify | health — the step that failed, if any
        self.rollback = rollback            # in words: rolled back to <release> | ROLLBACK FAILED … | nothing moved
        self.stash = stash                  # the volume stash the agent made on the target before the update
        self.apply_seconds = apply_seconds  # stash + update, wall clock
        self.at = at
        self.posted_by = posted_by
