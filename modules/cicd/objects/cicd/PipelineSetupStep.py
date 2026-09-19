"""
@module cicd.objects.cicd.PipelineSetupStep

Row class PipelineSetupStep of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PipelineSetupStep(treeObject):
    """ONE STEP of `pol jenkins setup`, as the device last reported it (ci-11a).

    His ask 2026-09-19: the pipeline should be usable as a desktop application, "guiding people through
    use like a normal app" with no terminal. That wizard is driven by `pol jenkins setup --json`, which
    runs ON THE DEVICE — a Polari core cannot run `pol`, and must not be able to. So the device pushes
    the document it produced (`cicd-sync.sh push-setup`, after every `push`) and these rows are the only
    copy a browser can see. `GET /api/cicd/setup` reassembles the protocol document from them.

    WHY THE SUB-STRUCTURES ARE STRINGS. `checks_json`, `questions_json`, `actions_json` and `where_json`
    hold the step's own lists verbatim. Two reasons, both deliberate:

    * the mirror door refuses any key named like a value, and a question's key is literally `key` — a
      nested post would be refused by the very guard that keeps secrets out of these rows;
    * a check or an action is not a Polari row and should not pretend to be one. It is a rendering the
      device computed; Polari stores it, shows it, and never re-derives it.

    NO SECRET VALUE EXISTS HERE, and the protocol is what guarantees it: a question of kind `secret`
    carries `present` or nothing as its `answered`, never a value, and a secret is stored by the
    `secrets-put` verb whose value travels on stdin. The selftest asserts the class carries no
    value-shaped field and that the ingest door refuses a payload that smuggles one.

    THE ROW IS A REPORT, NOT A KNOB. Nothing a person edits here reaches the device: the settings live
    on PipelineDevice / PipelineStage / PipelineRoute, and this row is overwritten by the next push.
    """

    #: the state vocabulary of `polari-pipeline-setup/1` — declared, not left to a string anybody invents
    STATES = ('done', 'todo', 'blocked', 'skipped')

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', step: str = '', index: int = 0,
                 total: int = 0, title: str = '', state: str = 'todo', explain: str = '',
                 checks_json: str = '[]', questions_json: str = '[]', actions_json: str = '[]',
                 where_json: str = '[]', at: str = '', posted_by: str = ''):
        self.name = name                    # the row id — <device>:<step>
        self.device = device                # PipelineDevice.name
        self.step = step                    # role | checkout | network | secrets | isle | stages | controller | summary
        self.index = index                  # 1..total, the order a person walks them in
        self.total = total
        self.title = title
        self.state = state                  # STATES
        self.explain = explain              # the plain-words paragraphs the step shows
        self.checks_json = checks_json      # [{name, value, verdict, fix}]
        self.questions_json = questions_json  # [{key, label, kind, default, answered, options?}]
        self.actions_json = actions_json    # [{id, label, privileged, verb, done, why, params?}]
        self.where_json = where_json        # [{what, url, scopes}]
        self.at = at                        # when the device produced it
        self.posted_by = posted_by
