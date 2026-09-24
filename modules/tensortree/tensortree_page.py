"""
@module tensortree.tensortree_page
/display/tensortree — the trees and their validation, the nodes and unresolved spaces, the mappings (with two
statuses), the selections and the discovery policy. The nodes' VISUALIZATION is a sim-space binding rendered by
the existing sim space (tt-1); this page is the configured-table reading of the structure.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_TENSORTREE_PAGE_DISPLAYS = [
    _page('tensortree', 'tensortree',
          'Tensor trees — rooted, navigable views over tensor state: resolved nodes (every dimension bound to a visual '
          'channel), unresolved spaces (what is not yet understood, kept with what is), and the mappings between them',
          'TensorTreeDefinition', [
              _row(0, [_sapi('tensortree-trees', 0, 12, 'Trees and their validation (one root · one parent · acyclic · local validity)', '/api/tensortree', pick='trees')], min_height=220),
              _row(1, [_table('tensortree-nodes', 0, 6, 'Nodes — status is set by the validator', 'TensorNode', columns='tree,name,parent,title,tensor,dims_json,binding_ref,status'),
                       _table('tensortree-unresolved', 1, 6, 'Unresolved spaces — typed by the research task', 'UnresolvedTensorSpace',
                              columns='tree,name,parent,title,unresolved_kind,known_dims_json,candidate_mappings_json,open_questions_json')]),
              _row(2, [_table('tensortree-dims', 0, 12, 'Localized dimensions and their visual channel', 'LocalizedDimension', columns='node,name,dimension,range_json,channel,scale_json,coherent')]),
              _row(3, [_table('tensortree-mappings', 0, 12, 'Mappings — kind, the dims at both ends, validity, loss, two statuses, evidence', 'TensorMapping',
                              columns='name,kind,source_node,source_dims_json,target_node,target_dims_json,validity_json,loss_note,reconstruction_error,mapping_status,evidence_level,evidence_ref')]),
              _row(4, [_table('tensortree-selections', 0, 6, 'Selections — a click that is a mathematical object', 'TensorSelection', columns='name,node,ranges_json,created_from,created_at'),
                       _table('tensortree-policy', 1, 6, 'Discovery policy — the score is configuration', 'TensorDiscoveryPolicy',
                              columns='name,w_evidence,w_dims,w_validity,w_context,w_uncertainty,evidence_map_json,is_default')]),
          ]),
]
