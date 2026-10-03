"""
@module board.objects.board.InstallPlan

InstallPlan — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class InstallPlan(treeObject):
    """What it is: The DRY-RUN of one install (brd-fi, plan §7a): which build goes onto which BoardInstance (or the
    simavr twin), the EXACT argv the flasher will run, which engine and where it resolves, which adapter (if any),
    the compatibility verdict at planning time, and what will be stamped on the instance. Nothing is opened to make
    a plan; `run` needs this row AND an explicit confirm, and re-checks compatibility first.
    Related concepts: `FirmwareBuild`, `BoardInstance`, `ProgrammerKind`, `InstallRecord` (the run).
    """

    @treeObjectInit
    def __init__(self, name: str = '', build: str = '', variant: str = '', instance: str = '', target_kind: str = '',
                 host: str = '', port: str = '', programmer: str = '', engine: str = '', engine_how: str = '',
                 engine_where: str = '', adapter: str = '', argv_json: str = '[]', argv_text: str = '',
                 wrapper_text: str = '', compat: str = '', compat_why: str = '', will_stamp: str = '',
                 artifact_sha256: str = '', state: str = 'planned', planned_at: str = '', notes: str = '', manager=None):
        self.name = name  # 'plan-<build>-<n>'
        self.build = build
        self.variant = variant
        self.instance = instance  # BoardInstance name, or 'twin:<board>'
        self.target_kind = target_kind  # board | twin
        self.host = host  # the host that holds the port (the server's own host — a plan elsewhere is refused at run)
        self.port = port
        self.programmer = programmer
        self.engine = engine
        self.engine_how = engine_how
        self.engine_where = engine_where
        self.adapter = adapter
        self.argv_json = argv_json
        self.argv_text = argv_text  # shown VERBATIM on the page
        self.wrapper_text = wrapper_text  # the docker wrapper when the image rung runs it
        self.compat = compat  # compatible | stale-header | unknown-class
        self.compat_why = compat_why
        self.will_stamp = will_stamp
        self.artifact_sha256 = artifact_sha256
        self.state = state  # planned | refused | ran
        self.planned_at = planned_at
        self.notes = notes
