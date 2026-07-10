"""
@cross-cutting
@module polariDataTyping.schema_stability_basis
@tags @xc:bindings

Schema stabilization state as DATA (object-coherence): one profile
row per class saying whether its schema has stabilized (enough clean
traffic ran through it with no new type deviations), and one event
row per OOPS (a stabilized schema rejected real data) — the offending
payload is CAPTURED in the event, never lost.

Follows the StepCostProfile stat-freezing idiom: observation
consolidates itself away (a stabilized class skips per-instance
typing analysis — the first concrete step of functionality moving
OUT of the object tree), but reality wins: a mismatch destabilizes
the schema, adapts it to the new data, and records what happened.

@consumers
  - polariDataTyping.schema_stability (the engine)
  - polariDBmanagement.managedDB.saveInstanceInDB (clean/mismatch hooks)
  - polariServer.defClassList (auto-CRUDE + persistence)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SchemaStabilityProfile(treeObject):
    """Stabilization state of one class's schema."""

    @treeObjectInit
    def __init__(
        self,
        # '<className>-schema-stability' (unique key).
        name: str = '',
        subject_class: str = '',
        # 'unstable' (still learning) | 'stabilized' (typed schema
        # trusted, per-instance analysis skipped) | 'destabilized'
        # (was stabilized, an OOPS knocked it back — relearning).
        status: str = 'unstable',
        # KNOB: clean saves with no new deviation before the schema
        # counts as stabilized.
        stabilize_threshold: int = 50,
        # Clean saves since the last new type deviation.
        clean_saves: int = 0,
        # Lifetime counters (honest history, never reset).
        total_saves: int = 0,
        deviation_count: int = 0,
        destabilize_count: int = 0,
        # Per-field getDeviationSummary snapshot taken at
        # stabilization time (what the schema was trusted AS).
        field_summary_json: str = '{}',
        stabilized_at: str = '',
        destabilized_at: str = '',
        # Analysis passes skipped since stabilization (the measurable
        # win of moving typing work out of the object tree).
        skipped_analyses: int = 0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_class = subject_class
        self.status = status
        self.stabilize_threshold = stabilize_threshold
        self.clean_saves = clean_saves
        self.total_saves = total_saves
        self.deviation_count = deviation_count
        self.destabilize_count = destabilize_count
        self.field_summary_json = field_summary_json
        self.stabilized_at = stabilized_at
        self.destabilized_at = destabilized_at
        self.skipped_analyses = skipped_analyses
        self.notes = notes


class SchemaDeviationEvent(treeObject):
    """One recorded OOPS: data arrived that the (stabilized) schema
    could not hold. The attempted payload is preserved here, so a
    failed write is never silent data loss."""

    @treeObjectInit
    def __init__(
        self,
        # '<className>@<ts>' (unique key).
        name: str = '',
        subject_class: str = '',
        # Column the DB named in its error ('' = not parseable).
        field: str = '',
        # What the schema expected vs what arrived.
        expected_type: str = '',
        actual_type: str = '',
        # The data that was being submitted (JSON, truncated) — the
        # CAPTURE Dustin asked for.
        attempted_payload_json: str = '{}',
        # The raw DB error text.
        db_error: str = '',
        # What the smooth handler did:
        # 'adapted-widened+saved' (column widened, write landed) |
        # 'adapted-coerced+saved' (values coerced, write landed) |
        # 'quarantined' (write still failed — payload preserved HERE).
        action: str = '',
        # True when the write eventually landed.
        resolved: bool = False,
        occurred_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.subject_class = subject_class
        self.field = field
        self.expected_type = expected_type
        self.actual_type = actual_type
        self.attempted_payload_json = attempted_payload_json
        self.db_error = db_error
        self.action = action
        self.resolved = resolved
        self.occurred_at = occurred_at
        self.notes = notes
