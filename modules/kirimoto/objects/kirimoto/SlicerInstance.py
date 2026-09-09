"""
@module kirimoto.objects.kirimoto.SlicerInstance

SlicerInstance — one deployed Kiri:Moto behind the isle agent.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SlicerInstance(treeObject):
    """What it is: one running Kiri:Moto container: its isle domain, the
    upstream commit it was built from, the Moonraker targets it can send
    gcode to (the voron guests), and whether it answered its last probe.
    Related concepts: `IsleCatalogEntry` (the store row that deploys it),
    `SlicerProfile`, the printing suite's `SliceJob`/`GcodeArtifact`.
    How it is measured: the isle's app registry + a probe of /kiri; the
    commit is the build's, never a guess.
    """

    @treeObjectInit
    def __init__(self, name: str = 'kirimoto', domain: str = 'kirimoto.isle', upstream_commit: str = '',
                 version: str = '', moonraker_targets_json: str = '[]', probe_ok: bool = False,
                 observed_at: str = '', is_mock: bool = False, notes: str = ''):
        self.name = name
        self.domain = domain
        self.upstream_commit = upstream_commit
        self.version = version
        self.moonraker_targets_json = moonraker_targets_json
        self.probe_ok = probe_ok
        self.observed_at = observed_at
        self.is_mock = is_mock
        self.notes = notes
