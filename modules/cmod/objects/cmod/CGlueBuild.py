"""
@module cmod.objects.cmod.CGlueBuild

CGlueBuild — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CGlueBuild(treeObject):
    """What it is: One GENERATED PROJECT of a `CGraph` and what was proven about it (C_MODULARIZATION_PLAN.md §5, §10 cmod-1):
    the files rendered (each with its sha256) and the graph's sha, the build by `make` alone (the .hex sha, avr-size
    .text / .data / .bss), the cost estimated BEFORE the build (the atoms as nodes + the glue reference) against the bytes
    measured after, and the BEHAVIOUR-EQUIVALENCE proof: the hand-written app it replaces and the rendered glue run in the
    simavr twin with the same stimulus, their decoded frames compared field by field. Committed as
    cmod/custom/glue_builds/<graph>.json and projected into this row.
    Related concepts: `CGraph`, `CProject` (the rendered project conforms back as a plain project), board's `FirmwareBuild`.
    """

    plain_words = 'A glue build is the C project Polari wrote from a firmware drawing, with its size and the proof it behaves like the hand-written one.'

    @treeObjectInit
    def __init__(self, name: str = '', graph: str = '', graph_sha256: str = '', generated_project: str = '', generator: str = '',
                     files: str = '', files_sha256: str = '', rendered_at: str = '', build_ok: bool = False, built_by: str = '',
                     hex_sha256: str = '', size_text: int = 0, size_data: int = 0, size_bss: int = 0, reference: str = '',
                     ref_hex_sha256: str = '', ref_size_text: int = 0, ref_size_data: int = 0, ref_size_bss: int = 0,
                     cost_estimate_bytes: int = 0, cost_measured_bytes: int = 0, cost_why: str = '', equivalent: bool = False,
                     proof: str = '', frames_compared: int = 0, fields_compared: str = '', differences: str = '',
                     stimulus: str = '', cycles: str = '', engines: str = '', conformed: str = '', proven_at: str = '',
                     notes: str = '', manager=None):
        self.name = name                    # <graph>@<files sha 12>
        self.graph = graph
        self.graph_sha256 = graph_sha256
        self.generated_project = generated_project
        self.generator = generator          # cmod.custom.glue + its version
        self.files = files                  # 'file sha12, …'
        self.files_sha256 = files_sha256    # one sha over every rendered file
        self.rendered_at = rendered_at
        self.build_ok = build_ok
        self.built_by = built_by            # make alone, where it ran
        self.hex_sha256 = hex_sha256
        self.size_text = size_text
        self.size_data = size_data
        self.size_bss = size_bss
        self.reference = reference          # the hand-written build it is compared with
        self.ref_hex_sha256 = ref_hex_sha256
        self.ref_size_text = ref_size_text
        self.ref_size_data = ref_size_data
        self.ref_size_bss = ref_size_bss
        self.cost_estimate_bytes = cost_estimate_bytes
        self.cost_measured_bytes = cost_measured_bytes
        self.cost_why = cost_why
        self.equivalent = equivalent
        self.proof = proof                  # the verdict in words
        self.frames_compared = frames_compared
        self.fields_compared = fields_compared
        self.differences = differences
        self.stimulus = stimulus
        self.cycles = cycles
        self.engines = engines
        self.conformed = conformed          # the rendered project read back by `pol cmod conform` (atoms, manifest sha)
        self.proven_at = proven_at
        self.notes = notes
