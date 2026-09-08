"""@module pspp.objects.evidence_methods._shared — what the evidence_methods row classes share (constants, seeds, helpers); split from evidence_methods_basis.py (sap-2c)."""
from materialsScience.materials_basis import DERIVATION_METHODS

EVIDENCE_METHOD_VOCAB = {
    'measured': {
        'category': 'empirical',
        'description': 'Directly measured on this material/state.',
        'required_provenance': 'instrument + conditions (+ standard if '
                               'one was followed)',
        'default_validation_class': 'measurement',
    },
    'literature': {
        'category': 'empirical',
        'description': 'Reported by an external source for a comparable '
                       'material; not measured here.',
        'required_provenance': 'citation (source, table/figure, edition)',
        'default_validation_class': 'unvalidated',
    },
    'estimated': {
        'category': 'judgment',
        'description': 'Human judgment / worksheet prior — honest '
                       'placeholder awaiting data.',
        'required_provenance': 'who estimated + the basis note',
        'default_validation_class': 'unvalidated',
    },
    'interpolated': {
        'category': 'derived',
        'description': 'Read between points of a digitized source '
                       'dataset (never past its validity domain — '
                       'extrapolation is UNSUPPORTED, invariant I6).',
        'required_provenance': 'DigitizedDataset name + bracketing points',
        'default_validation_class': 'unvalidated',
    },
    'rules-of-mixtures': {
        'category': 'derived-model',
        'description': 'Constituent blend via a named mixing rule '
                       '(linear/Voigt/Reuss/Hill) — bounds or idealized '
                       'estimates, not measurements.',
        'required_provenance': 'constituent values + the mixing rule used',
        'default_validation_class': 'unvalidated',
    },
    'homogenized': {
        'category': 'derived-model',
        'description': 'Effective property from a finer-scale solve '
                       '(FEM homogenization).',
        'required_provenance': 'engine + model definition + input lineage',
        'default_validation_class': 'unvalidated',
    },
    'coarse-grained': {
        'category': 'derived-model',
        'description': 'Mapped up from an atomistic representation '
                       '(bead mapping / CG force field).',
        'required_provenance': 'mapping + source atomistic definition',
        'default_validation_class': 'unvalidated',
    },
    'dft-parameterized': {
        'category': 'derived-model',
        'description': 'Derived from a quantum (DFT) computation.',
        'required_provenance': 'functional/basis + structure + engine run',
        'default_validation_class': 'unvalidated',
    },
    'ml-prediction': {
        'category': 'derived-model',
        'description': 'Predicted by a trained model — only as good as '
                       'its training distribution.',
        'required_provenance': 'model identity + training-set scope',
        'default_validation_class': 'unvalidated',
    },
    'unknown': {
        'category': 'unknown',
        'description': 'Origin not recorded — a flagged debt, never a '
                       'silent default.',
        'required_provenance': '',
        'default_validation_class': 'unvalidated',
        'supports_uncertainty': False,
    },
}
SEED_EVIDENCE_METHODS = [
    {
        'name': key,
        'category': entry['category'],
        'description': entry['description'],
        'required_provenance': entry.get('required_provenance', ''),
        'default_validation_class': entry.get(
            'default_validation_class', 'unvalidated'),
        'supports_uncertainty': entry.get('supports_uncertainty', True),
        'provenance_id': 'pspp-1 evidence vocabulary '
                         '(PSPP_MATERIALS_PLAN.md §2)',
    }
    for key, entry in EVIDENCE_METHOD_VOCAB.items()
]
def evidence_identifiers():
    """All valid identifiers (vocabulary keys)."""
    return sorted(EVIDENCE_METHOD_VOCAB)
def validate_evidence_method(identifier):
    """Evidence-bearing verdict for one identifier — refusal names the
    vocabulary (the knob), never a bare False."""
    if identifier in EVIDENCE_METHOD_VOCAB:
        return {'ok': True, 'identifier': identifier,
                'category': EVIDENCE_METHOD_VOCAB[identifier]['category']}
    return {
        'ok': False,
        'refusal': f'unknown evidence method {identifier!r}',
        'suggestion': 'use one of the EvidenceMethod vocabulary '
                      f'identifiers: {evidence_identifiers()} — or add '
                      'a new EvidenceMethod row if this is a genuinely '
                      'new way of knowing',
    }
def legacy_methods_covered():
    """True when every legacy DERIVATION_METHODS identifier exists in
    the vocabulary (the unification contract with materialsScience)."""
    return all(m in EVIDENCE_METHOD_VOCAB for m in DERIVATION_METHODS)
