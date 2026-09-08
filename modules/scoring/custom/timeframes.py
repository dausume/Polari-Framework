"""
@cross-cutting
@module scoring.custom.timeframes
@tags @xc:bindings

Timeframe ALGEBRA for time-specific scoring (Dustin 2026-07-08:
"scores and their context [must] be very time specific … different
kinds of time frames and scales coexisting and overlapping and
interpolating between multiple metrics that use different scales").

Pure date math + combination rules — the engine orchestrates, this
module computes. Every derived value is LABELED with how it was
derived and which rows fed it; measured and derived are never
conflated.

How a metric may be resampled is metric semantics, declared on the
term (temporal_json): a 'stock' averages across time, a 'flow' sums,
an 'event' counts. Combining without a declaration is a refusal
naming the knob.

@consumers
  - scoring.custom.scoring_engine (time-aware value resolution)
@see /OVERLAP_MAP.md
"""

import json
from datetime import date, timedelta

#: temporal_json vocabulary: nature → allowed default resample.
TEMPORAL_NATURES = {
    'stock': 'mean',    # level at a point in time (LFPR, wage)
    'flow': 'sum',      # accumulates over the frame (spending, votes)
    'event': 'count',   # discrete occurrences
}
RESAMPLE_RULES = ('mean', 'sum', 'nearest', 'last', 'count')


def _parse_date(text):
    try:
        parts = [int(p) for p in str(text).split('-')[:3]]
        return date(*parts)
    except Exception:
        return None


def parse_frame(value_json_text):
    """A timeframe context's value_json → (start, end) dates or None."""
    try:
        payload = json.loads(value_json_text or '{}')
    except Exception:
        return None
    start = _parse_date(payload.get('start'))
    end = _parse_date(payload.get('end'))
    if start is None or end is None or end < start:
        return None
    return (start, end)


def frame_of_context(context_row):
    if getattr(context_row, 'context_type', '') != 'timeframe':
        return None
    return parse_frame(getattr(context_row, 'value_json', '{}'))


def duration_days(frame):
    return (frame[1] - frame[0]).days + 1


def overlap_days(a, b):
    start = max(a[0], b[0])
    end = min(a[1], b[1])
    return max(0, (end - start).days + 1)


def timeframe_specificity(frame):
    """Graded: shorter frames are MORE specific (a day beats a month
    beats a quarter beats a year beats an era)."""
    days = duration_days(frame)
    if days <= 1:
        return 9
    if days <= 31:
        return 8
    if days <= 92:
        return 7
    if days <= 366:
        return 6
    return 5


def frame_midpoint(frame):
    return frame[0] + timedelta(days=duration_days(frame) // 2)


def term_temporal(term_row):
    """(nature, resample_rule) from a term's temporal_json; (None,
    None) when undeclared."""
    try:
        payload = json.loads(
            getattr(term_row, 'temporal_json', '') or '{}')
    except Exception:
        payload = {}
    nature = payload.get('nature')
    if nature not in TEMPORAL_NATURES:
        return None, None
    rule = payload.get('resample', TEMPORAL_NATURES[nature])
    if rule not in RESAMPLE_RULES:
        rule = TEMPORAL_NATURES[nature]
    return nature, rule


def combine_over_frame(samples, target, rule):
    """Combine [(frame, raw, row_name)] overlapping `target` per the
    resample rule → (ok, value, meta). Meta always names the method
    and the rows; 'coverage' = covered share of the target frame."""
    inside = [(f, v, n) for f, v, n in samples
              if overlap_days(f, target) > 0]
    if not inside:
        return False, None, {'error': 'no samples overlap the frame'}
    covered = sum(overlap_days(f, target) for f, v, n in inside)
    coverage = min(1.0, covered / duration_days(target))
    rows = [n for _, _, n in inside]

    if rule == 'nearest':
        mid = frame_midpoint(target)
        _, value, name = min(
            inside, key=lambda s: abs(
                (frame_midpoint(s[0]) - mid).days))
        return True, value, {'derived': 'nearest-frame',
                             'fromRows': [name],
                             'coverage': round(coverage, 4)}
    if rule == 'last':
        _, value, name = max(inside, key=lambda s: s[0][1])
        return True, value, {'derived': 'last-frame',
                             'fromRows': [name],
                             'coverage': round(coverage, 4)}
    if rule in ('sum', 'count'):
        total = 0.0
        for frame, value, _ in inside:
            share = overlap_days(frame, target) / duration_days(frame)
            total += value * share
        return True, total, {'derived': f'{rule}-over-overlaps',
                             'fromRows': rows,
                             'coverage': round(coverage, 4)}
    # mean (stock): time-weighted by days of overlap
    weight_total = sum(overlap_days(f, target) for f, _, _ in inside)
    value = sum(v * overlap_days(f, target)
                for f, v, _ in inside) / weight_total
    return True, value, {'derived': 'time-weighted-mean',
                         'fromRows': rows,
                         'coverage': round(coverage, 4)}


def interpolate_at(samples, target):
    """Linear interpolation for a target frame sitting in a GAP
    between measured frames (stock metrics only) → (ok, value, meta).
    Refuses extrapolation beyond the measured range."""
    if not samples:
        return False, None, {'error': 'no samples to interpolate from'}
    mid = frame_midpoint(target)
    before = [s for s in samples if frame_midpoint(s[0]) <= mid]
    after = [s for s in samples if frame_midpoint(s[0]) > mid]
    if not before or not after:
        frontier = (max(samples, key=lambda s: s[0][1])[2]
                    if not after else
                    min(samples, key=lambda s: s[0][0])[2])
        return False, None, {
            'error': 'target frame is outside the measured range — '
                     'extrapolation refused',
            'frontierRow': frontier,
            'suggestion': {'knob': 'time_policy_json.'
                                   'allowExtrapolation',
                           'action': 'ingest a value covering the '
                                     'frame, or explicitly allow '
                                     'extrapolation'}}
    left = max(before, key=lambda s: frame_midpoint(s[0]))
    right = min(after, key=lambda s: frame_midpoint(s[0]))
    span = (frame_midpoint(right[0]) - frame_midpoint(left[0])).days
    if span <= 0:
        return True, left[1], {'derived': 'interpolated',
                               'fromRows': [left[2], right[2]],
                               'fraction': 0.0}
    fraction = (mid - frame_midpoint(left[0])).days / span
    value = left[1] + (right[1] - left[1]) * fraction
    return True, value, {'derived': 'interpolated',
                         'fromRows': [left[2], right[2]],
                         'fraction': round(fraction, 4)}
