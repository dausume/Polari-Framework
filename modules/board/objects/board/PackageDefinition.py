"""
@module board.objects.board.PackageDefinition

PackageDefinition — one class per file (design §7); fgm-2 (FIRMWARE_GENERATION_MODULE_PLAN.md §7.7 slice 1', his ruling §7.8.1).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PackageDefinition(treeObject):
    """What it is: ONE PHYSICAL PACKAGE a chip comes in — the same ATmega328P die is sold as a 28-pin SPDIP (what the UNO R3
    carries) and as a 32-pin TQFP (which adds the analog-only inputs ADC6 and ADC7). The package is its OWN axis: a physical
    board = one board design x one package x one USB interface (his ruling 2026-10-15); which package is on the bench is a
    PENDING identification, never assumed (`BoardInstance.package_variant`). Its pins are `PackageContact` rows.
    Related concepts: `SocDefinition` (the chip), `PackageContact` (one pin/pad of the package), `SocPin` (the chip's pin,
    which lists the contacts it appears on), `BoardDefinition.allowed_packages_json`, `BoardComponent`.
    """

    plain_words = ('A package is the physical case a chip comes in — how many legs it has and which signal sits on which leg. '
                   'The same chip can come in more than one package, and the bench board\'s package is confirmed by a person, not assumed.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', title: str = '', package_type: str = '', pin_count: int = 0,
                 code: str = '', footprint: str = '', adc_channels: int = 0, document: str = '', datasheet: str = '',
                 page_table: str = '', url: str = '', contacts_refs_json: str = '[]', used_by_json: str = '[]',
                 undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # '<soc>-<pins>-<type>' e.g. 'atmega328p-28-spdip'
        self.soc = soc  # the SocDefinition row
        self.title = title
        self.package_type = package_type  # SPDIP | TQFP | ...
        self.pin_count = pin_count
        self.code = code  # the vendor package code ('28P3'); '' when not cited
        self.footprint = footprint  # a KiCad library name when the repo cites one
        self.adc_channels = adc_channels  # ADC channels this package exposes (6 in SPDIP, 8 in TQFP)
        self.document = document
        self.datasheet = datasheet  # the Datasheet row (slug) this package is cited to
        self.page_table = page_table  # the figure/table + page
        self.url = url
        self.contacts_refs_json = contacts_refs_json  # ["PackageContact:<name>", ...] derived
        self.used_by_json = used_by_json  # [{board, component, how}] — which board designs model this package
        self.undetermined = undetermined
        self.notes = notes
