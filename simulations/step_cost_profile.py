"""
@cross-cutting
@module simulations.step_cost_profile
@tags @xc:bindings

StepCostProfile — MEASURED per-step cost of a simulation (one row per
SimulationDefinition, created lazily by the runner's tracker). This is
the measured counterpart of Dustin's static storage_predictor: real
wall-time and real persisted-bytes per step, learned while runs step.

Stat freezing (Dustin's rule — measurement consolidates itself away):
per-(Class.field) size stats carry {n, meanBytes, maxBytes, cv, frozen}.
Once a field has been sampled enough times that size change under the
LOCAL usage pattern is negligible (fixed-width numerics after 3
consistent samples; variable payloads at n >= 20 with cv < 0.05), it is
marked frozen: its mean/max become known constants and the per-step
serialization measuring for it STOPS. Volatile payloads (adaptive grids)
never stabilize and correctly keep being measured. `config_hash` pins
the stats to the local usage pattern — when the sim's parameters/field
policies change, the profile resets and re-learns; `reset_profile` is
the purposeful "re-measure" switch.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.step_cost_tracker (writes), resource projection (reads)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class StepCostProfile(treeObject):
    """Measured step-cost statistics for one SimulationDefinition.
    Identified by `name` = '<simulation_ref>-cost-profile'."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The SimulationDefinition these measurements belong to.
        simulation_ref: str = '',
        # Hash of the local usage pattern (parameters, field policies,
        # participating classes). Mismatch => stats reset + re-learn.
        config_hash: str = '',
        # How many live steps have been measured into this profile.
        step_count: int = 0,
        # Wall-time per step: cheap always-on EMA + observed max.
        avg_step_seconds: float = 0.0,
        max_step_seconds: float = 0.0,
        # Persisted bytes per step (sum over persisted rows/fields):
        # EMA + observed max.
        avg_step_bytes: float = 0.0,
        max_step_bytes: float = 0.0,
        # JSON dict keyed '<Class>.<field>' of per-field size stats:
        #   {"n": int, "meanBytes": float, "maxBytes": int,
        #    "cv": float, "frozen": bool}
        field_stats_json: str = '{}',
        # Step index at the last persist (throttled writes).
        updated_step: int = 0,
        manager=None,
    ):
        self.name = name
        self.simulation_ref = simulation_ref
        self.config_hash = config_hash
        self.step_count = step_count
        self.avg_step_seconds = avg_step_seconds
        self.max_step_seconds = max_step_seconds
        self.avg_step_bytes = avg_step_bytes
        self.max_step_bytes = max_step_bytes
        self.field_stats_json = field_stats_json
        self.updated_step = updated_step
