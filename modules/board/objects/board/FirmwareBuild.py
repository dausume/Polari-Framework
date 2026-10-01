"""
@module board.objects.board.FirmwareBuild

FirmwareBuild — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareBuild(treeObject):
    """What it is: One firmware build for one board definition (plan §2; filled from brd-1 on). Sizes are MEASURED
    (avr-size), never estimated; the repro block carries inputs by sha256, engine versions/digests and knobs.
    Related concepts: `BoardDefinition`, `BoardInstance` (flashed_to), the per-class packet headers (classes_json),
    `FirmwareVariant` (variant), the installer's compat check (header_sha256 + tag_order_json).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board_definition: str = '', state: str = '', classes_json: str = '[]', template: str = '',
                 source_sha: str = '', artifact_sha256: str = '', engines_json: str = '{}', size_text: int = 0,
                 size_data: int = 0, size_bss: int = 0, built_at: str = '', flashed_to: str = '',
                 flash_log: str = '', repro_json: str = '{}', notes: str = '', variant: str = '',
                 header_sha256: str = '', tag_order_json: str = '{}', hex_path: str = '', manager=None):
        self.name = name
        self.board_definition = board_definition
        self.state = state  # generated | built | refused (past the board's cited limits) | flashed — brd-1
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
        # brd-fi — compatibility is judged on what the board will actually speak, never on contract_hash alone
        # (brd-1's finding: contract_hash covers field→type only, so v1/v2 share a hash yet differ in wire order)
        self.variant = variant  # the FirmwareVariant it was generated from
        self.header_sha256 = header_sha256  # sha256 of the generated header (one class) / of 'class:sha' lines (several)
        self.tag_order_json = tag_order_json  # {class: [field, …] in TAG (= wire) order} at gen time
        self.hex_path = hex_path  # where the built .hex lives on the host that built it (the build store)
