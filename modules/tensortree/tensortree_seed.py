"""
@module tensortree.tensortree_seed

The ONE seeded row: the default TensorDiscoveryPolicy (plan §F3) — the ranking's weights and evidence map as
data. No tree is seeded: a TensorTree is made over a real tensor (tt-1: the waxprint thermal field).
"""
from tensortree.tensortree_basis import (TensorTreeDefinition, TensorNode, UnresolvedTensorSpace, LocalizedDimension,
                                         TensorMapping, TensorSelection, TensorDiscoveryPolicy)

SEED_DISCOVERY_POLICIES = [{
    'name': 'default', 'description': 'Score = 0.30·E + 0.25·D + 0.25·V + 0.10·C + 0.10·(1−U) after the hard filters (plan §F3)',
    'w_evidence': 0.30, 'w_dims': 0.25, 'w_validity': 0.25, 'w_context': 0.10, 'w_uncertainty': 0.10,
    'evidence_map_json': '{"measured": 1.0, "validated": 0.85, "implemented": 0.65, "analytical": 0.4, "proposed": 0.2, "none": 0.1}',
    'is_default': True, 'notes': 'weights are configuration, not scientific constants'}]

TENSORTREE_SEED_PAIRS = [
    ('TensorTreeDefinition', TensorTreeDefinition, []), ('TensorNode', TensorNode, []),
    ('UnresolvedTensorSpace', UnresolvedTensorSpace, []), ('LocalizedDimension', LocalizedDimension, []),
    ('TensorMapping', TensorMapping, []), ('TensorSelection', TensorSelection, []),
    ('TensorDiscoveryPolicy', TensorDiscoveryPolicy, SEED_DISCOVERY_POLICIES),
]
