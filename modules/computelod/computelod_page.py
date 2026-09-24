"""
@module computelod.computelod_page
/display/computelod — the ladder as configured tables and one structured reading (no raw JSON): the eleven rungs,
their kinds, the downward and upward mappings with their two statuses. The microchip ladder keeps its own page.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_COMPUTELOD_PAGE_DISPLAYS = [
    _page('computelod', 'computelod',
          'Compute levels of detail — ONE ladder from C to materials: every rung points at the module that owns it, '
          'a KIND specializes within a rung, and every mapping between rungs carries its evidence',
          'ComputeLOD', [
              _row(0, [_sapi('computelod-ladder', 0, 12, 'The ladder: rank, group, owner, the microchip rung it references, its kinds, status', '/api/computelod', pick='ladder')], min_height=300),
              _row(1, [_table('computelod-rungs', 0, 12, 'Rungs', 'ComputeLOD',
                              columns='rank,name,group,title,design_level_ref,owner_module,languages_json,tools_json,concept_node,status')]),
              _row(2, [_table('computelod-kinds', 0, 12, 'Kinds — a specialization within a rung, never a new rung', 'ComputeKind',
                              columns='rung,name,title,design_kind_ref,notes')]),
              _row(3, [_table('computelod-mappings', 0, 6, 'Downward: how is this implemented (ComputeMapping)', 'ComputeMapping',
                              columns='source_rung,source_ref,kind,target_rung,target_ref,mapping_status,evidence_level,evidence_ref,loss_note'),
                       _table('computelod-characterizations', 1, 6, 'Upward: what does it produce (CharacterizationMapping) — conditions are load-bearing', 'CharacterizationMapping',
                              columns='source_rung,source_ref,characteristic,method,conditions_json,result,units,target_rung,mapping_status,evidence_level,evidence_ref')]),
          ]),
]
