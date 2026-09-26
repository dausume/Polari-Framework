"""
@module tensortree.tensortree_page
/display/tensortree — ONE tree at a time (bp-2a, his ask 2026-09-25): the tree panel's chip is the page's SCOPE.
Picking a tree dispatches the frontend display event `setScope` {key: 'tree', value, facets: {nodes, sim_space}};
the display page re-substitutes every `{scope:…}` placeholder in the configured panels' inputs — so the tables
below filter to that tree's rows (its nodes' names as the set the dims / mappings / selections belong to) and the
ONE sim-space viewer shows the space that tree's bindings render in. Configuration and events; no page code.
The pages' text for non-experts comes from the classes' `plain_words` through GET /api/plain (bp-2d).
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

_CLASSES = 'TensorTreeDefinition,TensorNode,UnresolvedTensorSpace,LocalizedDimension,TensorMapping,TensorSelection,TensorDiscoveryPolicy'


def _component(item_id, name, title, inputs, segments=12):
    return {'id': item_id, 'index': 0, 'type': 'component', 'rowSegmentsUsed': segments, 'gridColumnStart': None, 'title': title,
            'visible': True, 'collapsed': False, 'cssClass': '', 'componentProps': {'componentName': name, 'inputs': inputs}, 'item': None, 'nestedRows': []}


def _scoped(item_id, index, segments, title, class_name, columns, filter_field, filter_value, column_formats=''):
    t = _table(item_id, index, segments, title, class_name, columns=columns, column_formats=column_formats)
    t['componentProps']['inputs'].update({'filterField': filter_field, 'filterValue': filter_value})
    return t


SEED_TENSORTREE_PAGE_DISPLAYS = [
    _page('tensortree', 'tensortree',
          'Tensor trees — rooted, navigable views over tensor state: resolved nodes (every dimension bound to a visual '
          'channel), unresolved spaces (what is not yet understood, kept with what is), and the mappings between them. '
          'Pick a tree in the panel: every table and the viewer follow it.',
          'TensorTreeDefinition', [
              # bp-2d: for anyone — the object kinds of this page in plain words (the classes' plain_words, one door)
              _row(0, [_sapi('tensortree-plain', 0, 12, 'In plain words — what these objects are, for a non-expert', '/api/plain?classes=' + _CLASSES, hide='ok')], min_height=160),
              _row(1, [_sapi('tensortree-trees', 0, 12, 'All trees and their validation (one root · one parent · acyclic · local validity)', '/api/tensortree', pick='trees')], min_height=220),
              # tt-5: the tree itself, drawn for intuition; bp-2a: its chip is the page scope (scopeKey → setScope events)
              _row(2, [_component('tensortree-panel', 'tensor-tree-panel',
                                  'The tree — pick one (the page follows); click a node; solid = resolved, dashed = an unresolved space; arcs = mappings coloured by evidence',
                                  {'treeName': '{scope:tree}', 'scopeKey': 'tree'})], min_height=480),
              # tt-1 / tt-6: a resolved node's visualization is a SIM-SPACE BINDING rendered by the existing viewer — ONE viewer, the
              # space the selected tree's bindings render in (wind-spatial → newtonian-pendulum-viz; plate-mechanics → plate-mechanics-2d)
              _row(3, [_component('tensortree-scene', 'sim-space-viewer',
                                  '{scope:tree} — as its bindings render it (the wind grid: x/y/z → position, w → vector; the plate: σ_vm per element → colour, u per node → a line, exaggeration a stated knob)',
                                  {'simSpaceName': '{scope:tree.sim_space}'})], min_height=420),
              _row(4, [_scoped('tensortree-nodes', 0, 6, 'Nodes of {scope:tree} — status is set by the validator', 'TensorNode',
                               'name,parent,title,tensor,dims_json,binding_ref,status', 'tree', '{scope:tree}', column_formats='name:ref:TensorNode,parent:ref:TensorNode,tensor:ref:Tensor'),
                       _scoped('tensortree-unresolved', 1, 6, 'Unresolved spaces of {scope:tree} — typed by the research task', 'UnresolvedTensorSpace',
                               'name,parent,title,unresolved_kind,known_dims_json,candidate_mappings_json,open_questions_json', 'tree', '{scope:tree}',
                               column_formats='name:ref:UnresolvedTensorSpace,parent:ref:TensorNode')]),
              _row(5, [_scoped('tensortree-dims', 0, 12, 'Localized dimensions of {scope:tree} and their visual channel', 'LocalizedDimension',
                               'node,name,dimension,range_json,channel,scale_json,coherent', 'node', '{scope:tree.nodes}', column_formats='node:ref:TensorNode,dimension:ref:TensorDimension')]),
              _row(6, [_scoped('tensortree-mappings', 0, 12, 'Mappings from {scope:tree} — kind, the dims at both ends, validity, loss, two statuses, evidence', 'TensorMapping',
                               'name,kind,source_node,source_dims_json,target_node,target_dims_json,validity_json,loss_note,reconstruction_error,mapping_status,evidence_level,evidence_ref',
                               'source_node', '{scope:tree.nodes}', column_formats='name:ref:TensorMapping,source_node:ref:TensorNode,target_node:ref:TensorNode')]),
              _row(7, [_scoped('tensortree-selections', 0, 6, 'Selections on {scope:tree} — a click that is a mathematical object', 'TensorSelection',
                               'name,node,ranges_json,created_from,created_at', 'node', '{scope:tree.nodes}', column_formats='node:ref:TensorNode'),
                       _table('tensortree-policy', 1, 6, 'Discovery policy (all trees) — the score is configuration', 'TensorDiscoveryPolicy',
                              columns='name,w_evidence,w_dims,w_validity,w_context,w_uncertainty,evidence_map_json,is_default')]),
              # tt-7: the coupling rows a kind=coupling mapping names or CREATED (POST /api/tensortree/mappings/{name}/couple) — the runner's rows, all trees
              _row(8, [_table('tensortree-couplings', 0, 12, 'Simulation couplings (all trees) — what a kind=coupling mapping executes as (the runner\'s row; created from the tree or seeded)', 'SimulationCouplingDefinition',
                              columns='name,source_simulation_ref,source_class_name,target_simulation_ref,target_class_name,sampler_equation_ref,enabled,description')]),
          ]),
]
