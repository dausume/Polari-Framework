"""
@module polariApiProfiler.schema_drift

Schema-drift detection + fuzzy field adaptation (Dustin 2026-07-16):
an external API that served a consistent data profile "long enough"
is SOLID; when the SAME endpoint then changes its formatting (field
renames etc.), that is DRIFT of a known API — never "a new API". The
adaptation analyzes the data formatting AND the word formatting of
the fields for near matches, proposes an old->new field migration as
an EVIDENCE-BEARING SUGGESTION (applied only when the caller says
so — knobs-and-suggestions), and continuity is then PROVEN: old ids
and locally stored values must match up after migration.

Reuses ProfileMatcher.analyze_structure for signatures. NOTE (flagged
upstream, not fixed here — file boundary): compare_to_profile's level
walk unions TYPE-signature levels only, so pure field levels (e.g.
level 2 of a list-of-dicts) never contribute and its fieldConfidence
reads 0 even for identical data. `profile_consistency` below computes
the corrected field comparison over the same signature dicts.

Determinism: no wall-clock, no randomness — scores are pure functions
of names + sample values.

@consumers
  - polariApiProfiler.api_discovery (drift-aware relocation matching)
  - polariApiProfiler.selftest_profiler_drift
"""

import re
from difflib import SequenceMatcher

#: Consecutive consistent samples before a profile is SOLID (knob).
DEFAULT_STABLE_AFTER = 5
#: Field-level consistency below this = the sample no longer matches.
DEFAULT_DRIFT_THRESHOLD = 0.75
#: Minimum similarity for a proposed field mapping.
DEFAULT_MIGRATION_THRESHOLD = 0.6
#: Two candidates within this of each other = surfaced as ambiguous.
AMBIGUITY_BAND = 0.1
#: Mapped fraction of old fields at/above which a drift is adaptable.
DEFAULT_ADAPTABLE_FRACTION = 0.5

_DATE_FORMATS = (
    (re.compile(r'^\d{4}-\d{2}-\d{2}$'), 'YYYY-MM-DD'),
    (re.compile(r'^\d{2}/\d{2}/\d{4}$'), 'MM/DD/YYYY'),
    (re.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}'), 'ISO datetime'),
)


# --- profile consistency (corrected field-level comparison) ---------

def profile_consistency(target_analysis, response_analysis):
    """Field+type consistency between two analyze_structure outputs,
    walking the union of FIELD levels (the upstream quirk skips
    them). 1.0 = same shape; disjoint field names -> ~0 fields."""
    target_fields = target_analysis.get('fieldSignatures', {}) or {}
    response_fields = response_analysis.get('fieldSignatures', {}) or {}
    field_levels = set(target_fields) | set(response_fields)
    field_scores = []
    for level in sorted(field_levels):
        a = set(target_fields.get(level, []))
        b = set(response_fields.get(level, []))
        union = a | b
        field_scores.append(len(a & b) / len(union) if union else 1.0)
    field_confidence = (sum(field_scores) / len(field_scores)
                        if field_scores else 1.0)
    target_types = target_analysis.get('typeSignatures', {}) or {}
    response_types = response_analysis.get('typeSignatures', {}) or {}
    type_levels = set(target_types) | set(response_types)
    type_hits = sum(
        1 for level in type_levels
        if sorted(target_types.get(level, []))
        == sorted(response_types.get(level, [])))
    type_confidence = (type_hits / len(type_levels)
                       if type_levels else 1.0)
    return {'fieldConfidence': field_confidence,
            'typeConfidence': type_confidence,
            'overall': 0.7 * field_confidence + 0.3 * type_confidence}


class ProfileStabilityTracker:
    """Tracks one endpoint's profile over repeated samples.

    Plain class (not a treeObject row): the tracker is analysis state
    owned by whatever loop polls the endpoint; persisting it as a row
    would need polariServer registration, which stays a follow-up —
    `snapshot()` returns a dict ready to store on such a row later.

    Status walk: observing -> solid -> drifted. Identity is the
    ENDPOINT URL: a mismatch after solidity is always 'the same API
    changed its formatting', never 'unknown API'.
    """

    def __init__(self, endpoint_url,
                 stable_after=DEFAULT_STABLE_AFTER,
                 drift_threshold=DEFAULT_DRIFT_THRESHOLD,
                 matcher=None):
        if matcher is None:
            from polariApiProfiler.profileMatcher import ProfileMatcher
            matcher = ProfileMatcher(manager=None)
        self.matcher = matcher
        self.endpoint_url = endpoint_url
        self.stable_after = int(stable_after)
        self.drift_threshold = float(drift_threshold)
        self.status = 'observing'
        self.consecutive = 0
        self.samples_seen = 0
        self.profile = None            # analyze_structure output
        self.drifted_analysis = None   # the post-drift shape
        self.last_consistency = None

    def observe(self, response_data):
        """Feed one sample -> {'status', 'consecutive', 'evidence'}."""
        analysis = self.matcher.analyze_structure(response_data)
        self.samples_seen += 1
        if self.profile is None:
            self.profile = analysis
            self.consecutive = 1
            return self._result('first sample profiled')
        consistency = profile_consistency(self.profile, analysis)
        self.last_consistency = consistency
        consistent = (consistency['fieldConfidence']
                      >= self.drift_threshold)
        if consistent:
            self.consecutive += 1
            if (self.status == 'observing'
                    and self.consecutive >= self.stable_after):
                self.status = 'solid'
                return self._result(
                    f'{self.consecutive} consecutive consistent '
                    f'samples (>= stable_after={self.stable_after}) '
                    f'— profile is SOLID')
            return self._result(
                f'consistent (fieldConfidence='
                f"{consistency['fieldConfidence']:.2f})")
        if self.status == 'solid' or self.status == 'drifted':
            self.status = 'drifted'
            self.drifted_analysis = analysis
            return self._result(
                f'the SAME api ({self.endpoint_url}) changed its '
                f'formatting: fieldConfidence dropped to '
                f"{consistency['fieldConfidence']:.2f} against the "
                f'solid profile (threshold '
                f'{self.drift_threshold}) — drift, not a new API')
        # Not yet solid: the shape flapped — restart observation on
        # the new shape (honest: it was never solid to begin with).
        self.profile = analysis
        self.consecutive = 1
        return self._result(
            'shape changed BEFORE solidity — observation restarted '
            'on the new shape')

    def _result(self, evidence):
        return {'status': self.status,
                'consecutive': self.consecutive,
                'samplesSeen': self.samples_seen,
                'evidence': evidence}

    def snapshot(self):
        """Row-ready state (for a future ApiProfileStability row)."""
        return {'endpointUrl': self.endpoint_url,
                'status': self.status,
                'consecutive': self.consecutive,
                'samplesSeen': self.samples_seen,
                'stableAfter': self.stable_after,
                'driftThreshold': self.drift_threshold}


# --- word-formatting + data-formatting similarity --------------------

def _tokens(name):
    """snake/kebab/camel/Pascal -> lowercase token list."""
    spaced = re.sub(r'[-_\s]+', ' ', str(name))
    spaced = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', spaced)
    spaced = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', spaced)
    return [t for t in spaced.lower().split(' ') if t]


def _token_pair_score(a, b):
    if a == b:
        return 1.0
    shorter, longer = sorted((a, b), key=len)
    if len(shorter) >= 2 and longer.startswith(shorter):
        return 0.7  # abbreviation: 'hh'~'household', 'id'~'identifier'
    if len(shorter) >= 3 and shorter in longer:
        return 0.6
    return 0.0


def _name_similarity(old_name, new_name):
    old_tokens, new_tokens = _tokens(old_name), _tokens(new_name)
    evidence = []
    remaining = list(new_tokens)
    total = 0.0
    for token in old_tokens:
        best, best_score = None, 0.0
        for candidate in remaining:
            score = _token_pair_score(token, candidate)
            if score > best_score:
                best, best_score = candidate, score
        if best is not None and best_score > 0:
            remaining.remove(best)
            total += best_score
            kind = 'exact' if best_score == 1.0 else 'partial'
            evidence.append(f"name token '{token}' ~ '{best}' "
                            f'({kind})')
    denominator = max(len(old_tokens), len(new_tokens)) or 1
    token_score = total / denominator
    seq_score = SequenceMatcher(
        None, ''.join(old_tokens), ''.join(new_tokens)).ratio()
    score = max(token_score, seq_score)
    if token_score >= seq_score and evidence:
        evidence.insert(0, f'name tokens {old_tokens} ~ '
                           f'{new_tokens}: score {token_score:.2f}')
    else:
        evidence.insert(0, f'name string similarity '
                           f'{seq_score:.2f} '
                           f"('{old_name}' vs '{new_name}')")
    return score, evidence


def _dominant_type(samples):
    counts = {}
    for value in samples:
        counts[type(value).__name__] = counts.get(
            type(value).__name__, 0) + 1
    return max(sorted(counts), key=counts.get) if counts else 'none'


def _date_format(value):
    for pattern, label in _DATE_FORMATS:
        if isinstance(value, str) and pattern.match(value):
            return label
    return None


def _value_similarity(old_samples, new_samples):
    """Data-formatting analysis. Identical values under a renamed
    field are the strongest evidence — exact-set overlap dominates;
    numeric fallback is INTERVAL overlap (never mean-closeness, which
    would confuse rents with years); date-like strings compare their
    format class."""
    evidence = []
    if not old_samples or not new_samples:
        return 0.0, ['no samples to compare']
    old_set = {repr(v) for v in old_samples}
    new_set = {repr(v) for v in new_samples}
    union = old_set | new_set
    jaccard = len(old_set & new_set) / len(union) if union else 0.0
    if jaccard > 0:
        evidence.append(
            f'values: {len(old_set & new_set)}/{len(union)} exact '
            f'overlap (Jaccard {jaccard:.2f})')
        return jaccard, evidence
    old_numbers = [v for v in old_samples
                   if isinstance(v, (int, float))
                   and not isinstance(v, bool)]
    new_numbers = [v for v in new_samples
                   if isinstance(v, (int, float))
                   and not isinstance(v, bool)]
    if old_numbers and new_numbers:
        low = max(min(old_numbers), min(new_numbers))
        high = min(max(old_numbers), max(new_numbers))
        full_low = min(min(old_numbers), min(new_numbers))
        full_high = max(max(old_numbers), max(new_numbers))
        span = full_high - full_low
        overlap = max(0.0, high - low)
        interval = (overlap / span) if span else 1.0
        score = min(0.5, interval * 0.5)
        evidence.append(f'numeric interval overlap {interval:.2f} '
                        f'(capped fallback, no exact overlap)')
        return score, evidence
    old_formats = {_date_format(v) for v in old_samples} - {None}
    new_formats = {_date_format(v) for v in new_samples} - {None}
    if old_formats and old_formats == new_formats:
        evidence.append(f'same date format '
                        f'{sorted(old_formats)} (no value overlap)')
        return 0.5, evidence
    evidence.append('no value overlap and no shared format')
    return 0.0, evidence


def field_similarity(old_name, new_name, old_samples, new_samples):
    """{'score': 0..1, 'evidence': [...]} — word formatting of the
    field names + data formatting of the sample values; identical
    values weigh highest."""
    name_score, name_evidence = _name_similarity(old_name, new_name)
    old_type = _dominant_type(old_samples)
    new_type = _dominant_type(new_samples)
    type_score = 1.0 if old_type == new_type else 0.0
    type_evidence = (f'types match ({old_type})' if type_score
                     else f'type mismatch ({old_type} vs {new_type})')
    value_score, value_evidence = _value_similarity(old_samples,
                                                    new_samples)
    score = (0.40 * name_score + 0.15 * type_score
             + 0.45 * value_score)
    return {'score': round(score, 4),
            'components': {'name': round(name_score, 4),
                           'type': type_score,
                           'value': round(value_score, 4)},
            'evidence': name_evidence + [type_evidence]
            + value_evidence}


def fields_with_samples(rows):
    """[{field: value}...] -> {field: [values]} (shared helper)."""
    out = {}
    for row in rows or []:
        if isinstance(row, dict):
            for field, value in row.items():
                out.setdefault(field, []).append(value)
    return out


def propose_field_migration(old_fields_with_samples,
                            new_fields_with_samples,
                            threshold=DEFAULT_MIGRATION_THRESHOLD):
    """One-to-one old->new field mapping SUGGESTION. Greedy by
    confidence; near-ties are SURFACED in 'ambiguous', never silently
    picked; below-threshold pairs stay unmatched."""
    scores = {}
    for old_name, old_samples in old_fields_with_samples.items():
        for new_name, new_samples in new_fields_with_samples.items():
            scores[(old_name, new_name)] = field_similarity(
                old_name, new_name, old_samples, new_samples)
    ambiguous = []
    ambiguous_old = set()
    for old_name in old_fields_with_samples:
        ranked = sorted(
            ((scores[(old_name, new_name)]['score'], new_name)
             for new_name in new_fields_with_samples),
            reverse=True)
        if (len(ranked) >= 2 and ranked[0][0] >= threshold
                and ranked[1][0] >= threshold
                and ranked[0][0] - ranked[1][0] < AMBIGUITY_BAND):
            ambiguous.append({
                'oldField': old_name,
                'candidates': [
                    {'newField': name, 'confidence': score}
                    for score, name in ranked[:2]],
                'evidence': 'near-tie within '
                            f'{AMBIGUITY_BAND} — surfaced for a '
                            'human/vote, not silently picked'})
            ambiguous_old.add(old_name)
    mapping = {}
    used_new = set()
    for (old_name, new_name), result in sorted(
            scores.items(), key=lambda kv: -kv[1]['score']):
        if (result['score'] < threshold or old_name in mapping
                or old_name in ambiguous_old
                or new_name in used_new):
            continue
        mapping[old_name] = {'newField': new_name,
                             'confidence': result['score'],
                             'evidence': result['evidence']}
        used_new.add(new_name)
    unmatched_old = [f for f in old_fields_with_samples
                     if f not in mapping and f not in ambiguous_old]
    unmatched_new = [f for f in new_fields_with_samples
                     if f not in used_new]
    return {'mapping': mapping, 'unmatchedOld': unmatched_old,
            'unmatchedNew': sorted(unmatched_new),
            'ambiguous': ambiguous}


def drift_verdict(migration, old_field_count,
                  adaptable_fraction=DEFAULT_ADAPTABLE_FRACTION):
    """Explicit adaptability verdict for a drift: 'adaptable' when
    enough of the old schema maps across, else 'incompatible'."""
    mapped = len(migration.get('mapping', {}))
    fraction = mapped / old_field_count if old_field_count else 0.0
    verdict = ('adaptable' if fraction >= adaptable_fraction
               else 'incompatible')
    return {'verdict': verdict,
            'mappedFraction': round(fraction, 4),
            'mappedFields': mapped,
            'oldFieldCount': old_field_count,
            'evidence': f'{mapped}/{old_field_count} old fields '
                        f'mapped (adaptable at '
                        f'>= {adaptable_fraction})'}


def apply_migration(rows, mapping):
    """Rename new-format rows BACK to the old canonical field names
    (local objects keep their schema). Unmapped new fields ride along
    under their new names — extra data is kept, never dropped."""
    new_to_old = {entry['newField']: old_name
                  for old_name, entry in mapping.items()}
    migrated = []
    for row in rows or []:
        migrated.append({new_to_old.get(field, field): value
                         for field, value in row.items()})
    return migrated


def verify_continuity(old_rows, migrated_rows, key_field):
    """PROOF that old ids and locally stored values match up after a
    migration: per shared id, every field present in both rows must
    agree."""
    old_by_id = {row.get(key_field): row for row in old_rows or []}
    new_by_id = {row.get(key_field): row
                 for row in migrated_rows or []}
    matched, mismatches = [], []
    for row_id in sorted(set(old_by_id) & set(new_by_id), key=repr):
        matched.append(row_id)
        old_row, new_row = old_by_id[row_id], new_by_id[row_id]
        for field in sorted(set(old_row) & set(new_row)):
            if old_row[field] != new_row[field]:
                mismatches.append({'id': row_id, 'field': field,
                                   'oldValue': old_row[field],
                                   'newValue': new_row[field]})
    missing = sorted(set(old_by_id) - set(new_by_id), key=repr)
    new_ids = sorted(set(new_by_id) - set(old_by_id), key=repr)
    return {'ok': not mismatches and not missing,
            'matchedIds': matched,
            'valueMismatches': mismatches,
            'missingIds': missing,
            'newIds': new_ids}
