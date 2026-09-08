"""
@cross-cutting
@module scoring.agreement_policy_basis
@tags @xc:bindings

AgreementPolicy — the SETTINGS for group-agreement classification
(Dustin 2026-07-08: "allowing for settings to be made for what is
considered Consensus, what is considered majority definition, what is
considered split, etc."). Bands are rows, not code: edit the policy,
the classifications change.

Three band sets, each an ordered JSON list of {'label', 'max'} (a
value classifies into the FIRST band whose max it does not exceed):

  direction_bands_json — over the dominant-stance fraction (0.5-1.0):
      is the group split on a term being good or bad?
      Default (Dustin's): ≤0.5 divisive · ≤0.65 slight-majority ·
      ≤0.85 large-majority · ≤0.99 near-consensus · else consensus.
  weight_bands_json    — over the SPREAD of members' weight shares
      for a term (relative mean absolute deviation, 0 = identical
      weighting): do members agree how much the term MATTERS?
  similarity_bands_json — over cosine similarity (−1..1) between two
      groups' aggregate definitions ('min' bands: first band whose
      min the value meets): do groups agree on what good
      performance is?

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.group_aggregation
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class AgreementPolicy(treeObject):
    """One configurable set of agreement-classification bands."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        direction_bands_json: str = '[]',
        weight_bands_json: str = '[]',
        similarity_bands_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.direction_bands_json = direction_bands_json
        self.weight_bands_json = weight_bands_json
        self.similarity_bands_json = similarity_bands_json
        self.notes = notes


def classify_max(value, bands, fallback='unclassified'):
    """First band whose 'max' the value does not exceed."""
    for band in bands:
        if value <= band.get('max', 1.0) + 1e-9:
            return band.get('label', fallback)
    return bands[-1].get('label', fallback) if bands else fallback


def classify_min(value, bands, fallback='unclassified'):
    """First band whose 'min' the value meets (bands ordered
    strongest-first)."""
    for band in bands:
        if value >= band.get('min', 0.0) - 1e-9:
            return band.get('label', fallback)
    return bands[-1].get('label', fallback) if bands else fallback


def policy_bands(policy_row):
    """The three parsed band sets off a policy row."""
    def loads(attr):
        try:
            return json.loads(getattr(policy_row, attr, '') or '[]')
        except Exception:
            return []
    return {
        'direction': loads('direction_bands_json'),
        'weight': loads('weight_bands_json'),
        'similarity': loads('similarity_bands_json'),
    }


#: Dustin's bands (2026-07-08), seeded editable.
SEED_AGREEMENT_POLICIES = [{
    'name': 'default-agreement',
    'display_name': 'Default agreement bands',
    'description': 'Dustin 2026-07-08: 50/50 divisive; 50-65 slight '
                   'majority; 65-85 large majority; 85-99 '
                   'near-consensus; above = genuine consensus. Weight '
                   'and similarity bands are first-cut defaults — '
                   'edit this row to recalibrate every aggregate.',
    'direction_bands_json': json.dumps([
        {'label': 'divisive', 'max': 0.5},
        {'label': 'slight-majority', 'max': 0.65},
        {'label': 'large-majority', 'max': 0.85},
        {'label': 'near-consensus', 'max': 0.99},
        {'label': 'consensus', 'max': 1.0},
    ]),
    'weight_bands_json': json.dumps([
        {'label': 'aligned-weighting', 'max': 0.15},
        {'label': 'varied-weighting', 'max': 0.4},
        {'label': 'contested-weighting', 'max': 10.0},
    ]),
    'similarity_bands_json': json.dumps([
        {'label': 'shared-definition', 'min': 0.9},
        {'label': 'broadly-aligned', 'min': 0.7},
        {'label': 'partially-aligned', 'min': 0.4},
        {'label': 'divergent', 'min': -1.0},
    ]),
}]
