"""
@module firmwarefaults.objects.evidence.FormalCheck

FormalCheck — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FormalCheck(treeObject):
    """What it is: The FORMAL TIER, narrow (FIRMWARE_SCENARIO_PLAN.md §5 tier 2, sc-2b): one C function of one firmware variant,
    one property, one bound, checked by CBMC (BSD-4-clause style — run as a separate-process engine in prf-formal-engines,
    never linked). The harness models the interrupt as CBMC nondeterminism over the variant's own unedited hal.c. Outcome in
    his vocabulary: `decided` (bounded — every property holds up to bound k; never `proved`), `refuted` (a counterexample
    trace, its sha kept), `inapplicable` (the source does not compile — e.g. hal.c's static guard refuses the variant),
    `undetermined` (the bound was too small to decide, or the budget ran out), `error`. The limits of the model are on the
    row: CBMC has no AVR architecture; widths, endianness and the byte-wise read model are stated.
    sc-2c: a second engine, Frama-C's Mthread (LGPL-2.1, opam-built into prf-formal-engines) — `engine` frama-c-mthread, `bound` "unbounded":
    an interference fixed point over the whole program (no unwind, no k) → `decided (unbounded)` or `refuted` with the two racing
    source lines; its rule (protected / byte-atomic single writer / race) per shared variable in properties_json.
    Related concepts: the Scenario and its claim (the claim gains the `formal` evidence tier), `FirmwareVariant`.
    """

    plain_words = ('A formal check asks a model checker to try every way an interrupt could interleave with one small firmware '
                   'function, up to a stated limit, and either finds the exact sequence that breaks it or reports that none '
                   'exists within that limit.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', scenario: str = '', variant: str = '', build_name: str = '', function: str = '',
                 property_text: str = '', harness: str = '', harness_files_json: str = '[]', model: str = '', bound_k: int = 0, unwind: int = 0,
                 width: str = '16', defines_json: str = '[]', volatile_models_json: str = '[]', isr: str = '', budget_s: float = 300.0,
                 expected: str = '', engine: str = 'cbmc', engine_version: str = '', engine_where: str = '', outcome: str = 'not-run',
                 claim_status: str = '', verdict_raw: str = '', outcome_words: str = '', properties_json: str = '[]', failed_property: str = '',
                 counterexample_json: str = '{}', trace_sha256: str = '', trace_steps: int = 0, source_sha256: str = '', harness_sha256: str = '',
                 wall_s: float = 0.0, cpu_s: float = 0.0, peak_rss_mb: float = 0.0, limits: str = '', claim: str = '', repro_json: str = '{}',
                 ran_at: str = '', notes: str = '', bound: str = '', manager=None):
        self.name = name
        self.title = title
        self.scenario = scenario  # the Scenario whose claim this check speaks to
        self.variant = variant  # the FirmwareVariant (its board_config.h carries the knob)
        self.build_name = build_name  # the generated build (variant + source sha) — the claim's FirmwareBuild
        self.function = function  # the C function under check
        self.property_text = property_text
        self.harness = harness  # the harness file (custom/cbmc_model/…)
        self.harness_files_json = harness_files_json
        self.model = model  # the interrupt model in words
        self.bound_k = bound_k  # the bound in the property's own unit (ticks per gap, steps)
        self.unwind = unwind  # CBMC --unwind (with --unwinding-assertions)
        self.width = width  # 16 (LP32, int as avr-gcc) | 32
        self.defines_json = defines_json
        self.volatile_models_json = volatile_models_json
        self.isr = isr
        self.budget_s = budget_s
        self.expected = expected  # decided | refuted | inapplicable — what the plan expects
        self.engine = engine
        self.engine_version = engine_version
        self.engine_where = engine_where  # the ladder rung (knob / local binary / local image / topology)
        self.outcome = outcome  # not-run | decided | refuted | inapplicable | undetermined | error
        self.claim_status = claim_status  # e.g. "decided (bounded, k=2)" — never "proved"
        self.verdict_raw = verdict_raw  # polari-cbmc-check's verdict
        self.outcome_words = outcome_words
        self.properties_json = properties_json  # [{property, status, description, where}]
        self.failed_property = failed_property
        self.counterexample_json = counterexample_json  # the values that break it (refuted)
        self.trace_sha256 = trace_sha256
        self.trace_steps = trace_steps
        self.source_sha256 = source_sha256  # the variant's hal.c
        self.harness_sha256 = harness_sha256
        self.wall_s = wall_s
        self.cpu_s = cpu_s
        self.peak_rss_mb = peak_rss_mb
        self.limits = limits  # what the model does NOT capture
        self.claim = claim  # the MathClaim name it added the formal tier to
        self.repro_json = repro_json
        self.ran_at = ran_at
        self.notes = notes
        self.bound = bound  # sc-2c: "k=2 (bounded)" (CBMC) | "unbounded" (Mthread) — what the decision covers
