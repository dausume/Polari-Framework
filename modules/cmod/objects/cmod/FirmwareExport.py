"""
@module cmod.objects.cmod.FirmwareExport

FirmwareExport — one class per file (design §7); ucd-0f pulled forward (UNO_CORE_DEMO_PLAN.md §5b, his ask 2026-10-08:
"the key thing we need is a link that shows just the UI for firmware no code and an export").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareExport(treeObject):
    """What it is: ONE EXPORT OF ONE FIRMWARE SOLUTION — a directory a person can take away, read and build WITHOUT
    Polari: the rendered plain-C project (the same files cmod-glue committed), a `CMakeLists.txt` + an avr-gcc toolchain
    file (`cmake -B build && cmake --build build` → `firmware.hex`; targets `board`, `twin`, `size`, `flash`), a README
    that explains itself (what the firmware does, its tasks, schedule, register map, the board, the sizes, the shas) and
    `polari-export.json` (the manifest: solution, graph, board, usb ids / programmer / baud as DATA, every file's sha256).
    Packed as a `.tar.gz` served by GET /api/firmware/exports/<name>/download. `makefile_sha256` is the sha of the
    `firmware.hex` the committed Makefile build produced (cmod-glue's record); `cmake_sha256` the sha the exported
    CMake build produced when `verify` ran it on the engines image; `parity` says whether they are the same bytes —
    identical | differs | not-run — never assumed. The export is a TRANSIENT rendering of rows that already exist
    (D-exp-1: `module_home('exp')`, regenerated on request); this row is its durable record.
    Related concepts: `FirmwareSolution`, `CGlueBuild`, board's `FirmwareBuild`, FIRMWARE_EXPORT_PLAN.md (exp-0).
    """

    plain_words = ('A firmware export is a folder you can download that holds the firmware\'s C code, a CMake build '
                   'file, and a README explaining what it does — so you can read it and build it on your own machine, '
                   'with no Polari needed.')

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', graph: str = '', board: str = '', form: str = 'source-dir',
                 target: str = 'both', mode: str = 'online', path: str = '', tar_path: str = '', tar_sha256: str = '',
                 files_json: str = '[]', makefile_sha256: str = '', cmake_sha256: str = '', parity: str = 'not-run',
                 verify_log: str = '', download_url: str = '', created_at: str = '', status: str = 'created',
                 why: str = '', notes: str = '', manager=None):
        self.name = name                    # '<solution>@<timestamp>' (uno-sim-rig@2026-10-08T09-12-03)
        self.solution = solution            # the FirmwareSolution row
        self.graph = graph                  # its CGraph
        self.board = board                  # the board the solution resolved to
        self.form = form                    # source-dir (tar.gz of it) — tar | deb | jpackage are later forms
        self.target = target                # both | board | twin — which CMake target the README leads with
        self.mode = mode                    # online (apt pointers for the toolchain) | offline (later: the engines image tar)
        self.path = path                    # the export directory on the host that made it
        self.tar_path = tar_path            # the .tar.gz beside it
        self.tar_sha256 = tar_sha256
        self.files_json = files_json        # [{file, sha256, bytes}, …]
        self.makefile_sha256 = makefile_sha256  # firmware.hex sha from the committed Makefile build (cmod-glue record)
        self.cmake_sha256 = cmake_sha256    # firmware.hex sha from the exported CMake build, when verified
        self.parity = parity                # identical | differs | not-run
        self.verify_log = verify_log        # the tail of the cmake run, when verified
        self.download_url = download_url    # /api/firmware/exports/<name>/download
        self.created_at = created_at
        self.status = status                # created | verified | refused
        self.why = why                      # the refusal, when refused
        self.notes = notes
