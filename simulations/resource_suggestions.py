"""
@cross-cutting
@module simulations.resource_suggestions
@tags @xc:bindings

Data-saving suggestions — turn a StepCostProfile's MEASURED per-field
sizes into ranked, concrete, one-click-appliable proposals. Every
proposal is a ready-to-apply fragment for the EXISTING per-run
`field_save_overrides_json` channel (or the run's recording interval),
so applying one never needs new machinery — and never mutates the saved
SimulationDefinition.

Suggestion kinds:
  * fieldInterval — persist a bulky field every N steps instead of every
    step (biggest lever for constant-size payloads like a field grid).
  * fieldPolicy  — demote a heavy field to 'derivable' (not persisted;
    recomputed each live step). Worded carefully: the user decides
    whether history of that field matters to them.
  * recordingInterval — persist rows every N steps overall.

@consumers
  - simulations.simulation_api (/resource-suggestions + critical refusals)
@see /OVERLAP_MAP.md
"""

from typing import Any, Dict, List

from simulations.storage_predictor import _human_bytes
from simulations.step_cost_tracker import get_profile, _parse_stats

# Only fields at least this share of the measured step cost are worth
# suggesting about — below it the savings read as noise.
MIN_SHARE = 0.10
SUGGESTED_INTERVAL = 10


def suggestions_for(manager, sim_ref: str) -> List[Dict[str, Any]]:
    """Ranked data-saving proposals for a simulation, from its measured
    profile. Empty when nothing has been measured yet (the static
    predictor has no per-field reality to rank against)."""
    profile = get_profile(manager, sim_ref)
    if profile is None or int(getattr(profile, 'step_count', 0) or 0) <= 0:
        return []
    avg_step = float(getattr(profile, 'avg_step_bytes', 0.0) or 0.0)
    if avg_step <= 0:
        return []
    stats = _parse_stats(profile)
    ranked = sorted(stats.items(),
                    key=lambda kv: float(kv[1].get('meanBytes', 0.0)),
                    reverse=True)

    out: List[Dict[str, Any]] = []
    for key, st in ranked:
        mean = float(st.get('meanBytes', 0.0))
        share = mean / avg_step if avg_step else 0.0
        if share < MIN_SHARE:
            break  # ranked — everything after is smaller
        pretty = _human_bytes(int(mean))
        pct = f'{share * 100:.0f}%'
        # Lever 1: sparser persistence of just this field.
        interval_savings = mean * (1 - 1 / SUGGESTED_INTERVAL)
        out.append({
            'kind': 'fieldInterval',
            'target': key,
            'proposal': {key: {'policy': 'core',
                               'interval': SUGGESTED_INTERVAL}},
            'savingsBytesPerStep': int(interval_savings),
            'message': (f'{key} is about {pct} of each step\'s data '
                        f'(~{pretty}/step). Keeping it every '
                        f'{SUGGESTED_INTERVAL} steps instead of every step '
                        f'saves ~{_human_bytes(int(interval_savings))} per '
                        f'step; the timeline for this field just gets '
                        f'sparser.'),
        })
        # Lever 2: don't persist it at all (recomputed live each step).
        out.append({
            'kind': 'fieldPolicy',
            'target': key,
            'proposal': {key: {'policy': 'derivable'}},
            'savingsBytesPerStep': int(mean),
            'message': (f'If you don\'t need {key}\'s history after the '
                        f'run, marking it "derivable" stops persisting it '
                        f'entirely (~{pretty}/step saved). The live '
                        f'simulation still computes it every step — only '
                        f'the stored record goes. Your call: keep history, '
                        f'or run leaner.'),
        })

    # Lever 3: overall sparser rows — always available, ranked last
    # since it thins EVERY field's timeline.
    overall = avg_step * (1 - 1 / SUGGESTED_INTERVAL)
    out.append({
        'kind': 'recordingInterval',
        'target': '*',
        'proposal': {'recordingIntervalSteps': SUGGESTED_INTERVAL},
        'savingsBytesPerStep': int(overall),
        'message': (f'Recording every {SUGGESTED_INTERVAL}th step overall '
                    f'saves ~{_human_bytes(int(overall))} per step — the '
                    f'whole timeline gets sparser, but the simulation '
                    f'itself stays exact.'),
    })
    out.sort(key=lambda s: s['savingsBytesPerStep'], reverse=True)
    return out
