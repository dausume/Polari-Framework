"""
@module board.objects.board.FirmwareBuild

FirmwareBuild — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareBuild(treeObject):
    """What it is: One firmware build for one board definition (plan §2; filled from brd-1 on). Sizes are MEASURED
    (avr-size), never estimated; the repro block carries inputs by sha256, engine versions/digests and knobs.
    Related concepts: `BoardDefinition`, `BoardInstance` (flashed_to), the per-class packet headers (classes_json).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board_definition: str = '', classes_json: str = '[]', template: str = '',
                 source_sha: str = '', artifact_sha256: str = '', engines_json: str = '{}', size_text: int = 0,
                 size_data: int = 0, size_bss: int = 0, built_at: str = '', flashed_to: str = '',
                 flash_log: str = '', repro_json: str = '{}', notes: str = '', manager=None):
        self.name = name
        self.board_definition = board_definition
        self.classes_json = classes_json  # [{class, contract_hash}]
        self.template = template
        self.source_sha = source_sha
        self.artifact_sha256 = artifact_sha256
        self.engines_json = engines_json  # engine -> version/digest
        self.size_text = size_text
        self.size_data = size_data
        self.size_bss = size_bss
        self.built_at = built_at
        self.flashed_to = flashed_to
        self.flash_log = flash_log
        self.repro_json = repro_json
        self.notes = notes
