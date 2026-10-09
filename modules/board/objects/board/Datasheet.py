"""
@module board.objects.board.Datasheet

Datasheet — one class per file (design §7); ucd-doc.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Datasheet(treeObject):
    """What it is: ONE DOCUMENT a cited fact (DatasheetFact) or register field (RegisterField) points to, tracked as
    its own first-class row — his ask (2026-10-09, verbatim): "We should also be tracking data sheets as both
    documents and believe we already do as data, but I believe there are 3 different kinds of data sheets usually for
    a board ... Let's trace these." The three kinds + the fourth (all-in-one) + the overflow bucket:

      soc          the CHIP's datasheet: registers, pins, electrical limits (the ATmega328P DS40002061B).
      board        the BOARD's reference: pinout, schematic, connectors, parts (Arduino's UNO R3 docs / pinout PDF).
      programming  bootloader, flash protocol, toolchain settings (boards.txt, the Optiboot README).
      combined     one document that carries all three (none cited yet in this codebase — `covers_json` would name
                   which of soc/board/programming it stands in for).
      other        everything that is none of the three on purpose: a kit book, a language reference, a sensor
                   datasheet for a KIT PART rather than the board/chip itself, a Wikipedia page, an ingested repo file
                   (Zephyr's dtsi) — `notes` says why.
      undetermined a document a DatasheetFact/RegisterField cites that this table does not yet know — never dropped,
                   never guessed; a name + a note recording exactly what was cited.

    One row per distinct (document, revision) a seed fact/field cites (board.custom.datasheets scans them at seed
    time); `facts_refs_json`/`fields_refs_json` are the reverse links (every DatasheetFact/RegisterField naming this
    row), derived, never hand-maintained. `for_soc`/`for_board` name the SocDefinition/BoardDefinition this document
    is OF (not every document is of one — a kit book or Wikipedia page is of neither); a BoardDefinition's own
    `datasheets_json` ({kind: slug}) is derived from these two columns (board.custom.datasheets.board_coverage) so a
    board's readiness page can say "programming reference: missing" by name.
    Related concepts: `DatasheetFact`, `RegisterField`, `SocDefinition`, `BoardDefinition`.
    """

    plain_words = ('A datasheet is the document a cited fact came from, tracked as its own row: what it is, what '
                   'kind of reference it is (the chip\'s own book, the board\'s own reference, how to flash it, or '
                   'something else), who publishes it, which revision, and every fact or register field that cites '
                   'it — so clicking a fact\'s document opens the document itself, not just a string.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = 'undetermined', for_soc: str = '', for_board: str = '',
                 publisher: str = '', revision: str = '', url: str = '', sha256: str = '', fetched_at: str = '',
                 pages: int = 0, format: str = 'text', licence_note: str = '', facts_refs_json: str = '[]',
                 fields_refs_json: str = '[]', covers_json: str = '[]', origin: str = '', undetermined: str = '',
                 notes: str = '', manager=None):
        self.name = name  # a stable slug ('atmega328p-ds40002061b', 'arduino-uno-r3-docs', 'arduino-boards-txt', …)
        self.title = title
        self.kind = kind  # soc | board | programming | combined | other | undetermined
        self.for_soc = for_soc  # the SocDefinition row this document is OF ('' = not a chip datasheet)
        self.for_board = for_board  # the BoardDefinition row this document is OF ('' = not a board reference)
        self.publisher = publisher
        self.revision = revision  # verbatim, as the citing fact's own `revision` column carries it
        self.url = url
        self.sha256 = sha256  # when the file was fetched and hashed this session ('' = not fetched/not applicable)
        self.fetched_at = fetched_at  # 'YYYY-MM-DD' when known, '' otherwise (said why in notes)
        self.pages = pages  # 0 = unknown
        self.format = format  # pdf | web | text | repo-file
        self.licence_note = licence_note
        self.facts_refs_json = facts_refs_json  # ["DatasheetFact:<name>", …] — derived (board.custom.datasheets)
        self.fields_refs_json = fields_refs_json  # ["RegisterField:<name>", …] — derived
        self.covers_json = covers_json  # for kind='combined': which of ["soc","board","programming"] it carries
        self.origin = origin  # cited | derived:<how> | polari:<why synthesized>
        self.undetermined = undetermined  # named gaps (e.g. an unmatched citation's kind), never guessed
        self.notes = notes
