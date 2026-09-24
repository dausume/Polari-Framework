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
              # tt-5: the tree itself, drawn for intuition — structure as a d3 tree (resolved solid, unresolved dashed
              # with its kind), mappings as evidence-coloured arcs that may cross branches, dims → channels, and the
              # cycle select → discover → map (a selection is a row). One registered panel; d3 is the existing home.
              _row(1, [{'id': 'tensortree-panel', 'index': 0, 'type': 'component', 'rowSegmentsUsed': 12, 'gridColumnStart': None,
                        'title': 'The tree — click a node; solid = resolved, dashed = an unresolved space; arcs = mappings coloured by evidence',
                        'visible': True, 'collapsed': False, 'cssClass': '',
                        'componentProps': {'componentName': 'tensor-tree-panel', 'inputs': {'treeName': 'wind-spatial'}},
                        'item': None, 'nestedRows': []}], min_height=480),
              # tt-1: a resolved node's visualization is a SIM-SPACE BINDING rendered by the existing viewer — the
              # wind-grid node binds to WindFieldGridState-3d in the newtonian-pendulum-viz space (no new renderer)
              _row(2, [{'id': 'tensortree-wind-scene', 'index': 0, 'type': 'component', 'rowSegmentsUsed': 12, 'gridColumnStart': None,
                        'title': 'wind-grid — the resolved root node of the wind-spatial tree, as its binding renders it (x/y/z → position, w → vector)',
                        'visible': True, 'collapsed': False, 'cssClass': '',
                        'componentProps': {'componentName': 'sim-space-viewer', 'inputs': {'simSpaceName': 'newtonian-pendulum-viz'}},
                        'item': None, 'nestedRows': []}], min_height=420),
              _row(3, [_table('tensortree-nodes', 0, 6, 'Nodes — status is set by the validator', 'TensorNode', columns='tree,name,parent,title,tensor,dims_json,binding_ref,status'),
                       _table('tensortree-unresolved', 1, 6, 'Unresolved spaces — typed by the research task', 'UnresolvedTensorSpace',
                              columns='tree,name,parent,title,unresolved_kind,known_dims_json,candidate_mappings_json,open_questions_json')]),
              _row(4, [_table('tensortree-dims', 0, 12, 'Localized dimensions and their visual channel', 'LocalizedDimension', columns='node,name,dimension,range_json,channel,scale_json,coherent')]),
              _row(5, [_table('tensortree-mappings', 0, 12, 'Mappings — kind, the dims at both ends, validity, loss, two statuses, evidence', 'TensorMapping',
                              columns='name,kind,source_node,source_dims_json,target_node,target_dims_json,validity_json,loss_note,reconstruction_error,mapping_status,evidence_level,evidence_ref')]),
              _row(6, [_table('tensortree-selections', 0, 6, 'Selections — a click that is a mathematical object', 'TensorSelection', columns='name,node,ranges_json,created_from,created_at'),
                       _table('tensortree-policy', 1, 6, 'Discovery policy — the score is configuration', 'TensorDiscoveryPolicy',
                              columns='name,w_evidence,w_dims,w_validity,w_context,w_uncertainty,evidence_map_json,is_default')]),
          ]),
]
