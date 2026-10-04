"""
@module pcb.pcb_page

Four pages, every one a CONFIGURED table over rows — no raw JSON, no new component (plan §4; his rule
`no-raw-json-on-screens`). Per-layer SVGs and the STEP/Gerber/drill files are links through
GET /api/pcb/artifacts/{board}/{path} (pcb_api.py) on the FabricationExport table's `artifact_url` column
(`column_formats` kind `link`, the mathproofs module's own pattern for a URL column) — an EXISTING display kind,
never a new image-viewer component.

/display/board-schematic   Schematic + SchematicSheet + the embedded Symbols + the ERC findings (DrcResult kind=erc)
/display/board-layout      PcbBoard + Placement + Route (ingested, never authored) + the per-layer SVG exports
/display/board-bom         Part — the BOM: value, manufacturer/MPN where cited, package, mount, symbol/footprint, qty
/display/board-fab         FabRuleSet + FabRule (DKRed, cited) + DrcResult (kind=drc/fab-rule) + every FabricationExport
                            file with the fab's naming verdict (accepted | no | discrepancy)
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_PAGES = [
    _page('board-schematic', 'board-schematic',
          'Board schematics — one row per `.kicad_sch` (rendered by Polari from rows, D-pcb-1, or ingested from an open '
          'board), its sheets, the symbols it embeds, and the ERC findings kicad-cli reported (a clean run is one row, '
          'never hidden)',
          'Schematic', [
              _row(0, [_table('pcb-schematics', 0, 12, 'Schematics — file, format, origin (rendered | ingested), counts', 'Schematic',
                              columns='name,board,file,sha256,format_version,generator,title,sheets,symbols,power_symbols,wires,'
                                      'labels,junctions,no_connects,origin,licence_notes',
                              column_formats='name:ref:Schematic')]),
              _row(1, [_table('pcb-sheets', 0, 6, 'Sheets', 'SchematicSheet', columns='name,schematic,path,page,file,symbols',
                              column_formats='schematic:ref:Schematic'),
                       _table('pcb-symbols', 1, 6, 'Symbols used — KiCad library reference, source, licence', 'Symbol',
                              columns='name,lib,symbol,source,lib_version,licence,pin_count,description')]),
              _row(2, [_table('pcb-erc', 0, 12, 'Check findings — kicad-cli ERC/DRC/parity + Polari\'s DKRed checks (severity none = a clean run; '
                              'sort/filter by kind for erc)', 'DrcResult',
                              columns='board,kind,severity,rule,description,report_sha256,engine_version,source_date')]),
          ]),
    _page('board-layout', 'board-layout',
          'Board layout — the physical board as KiCad holds it: layer stack, outline, footprint placements and the '
          'copper of each net SUMMARISED (never authored by Polari — a person places and routes in KiCad, D-pcb-2), plus '
          'one per-layer SVG per export (kicad-cli pcb export svg, /api/pcb/artifacts/<board>/layers/<file>.svg)',
          'PcbBoard', [
              _row(0, [_table('pcb-boards', 0, 12, 'Boards — layer count, outline, stackup, the fab rule set it is checked against', 'PcbBoard',
                              columns='name,board_definition,file,sha256,copper_layers,thickness_mm,width_mm,height_mm,'
                                      'fab_rule_set,footprints,nets,segments,vias,zones,licence,provenance',
                              column_formats='name:ref:PcbBoard,fab_rule_set:ref:FabRuleSet')]),
              _row(1, [_table('pcb-placements', 0, 7, 'Placements — ref, footprint, position, side (ingested)', 'Placement',
                              columns='board,ref,value,footprint,part,x_mm,y_mm,rotation,side,attr',
                              column_formats='board:ref:PcbBoard,part:ref:Part'),
                       _table('pcb-routes', 1, 5, 'Routes — one row per net, summarised (segments, vias, length, widths)', 'Route',
                              columns='board,net,segments,vias,length_mm,min_width_mm,widths_json,layers_json,pads',
                              column_formats='board:ref:PcbBoard')]),
              _row(2, [_table('pcb-layer-svgs', 0, 12, 'Every export (sort/filter export_set=layers for the per-layer SVGs — kicad-cli pcb export svg) '
                              '— click artifact_url to open the file',
                              'FabricationExport', columns='board,export_set,layer,filename,sha256,bytes,artifact_url,engine_version,source_date',
                              column_formats='board:ref:PcbBoard,artifact_url:link')]),
          ]),
    _page('board-bom', 'board-bom',
          'Bill of materials — one row per Part: value, manufacturer/MPN where a source names them, package, mount, the '
          'KiCad symbol and footprint it uses, reference designators, licence notes, and what is still undetermined',
          'Part', [
              _row(0, [_table('pcb-bom', 0, 12, 'BOM', 'Part',
                              columns='name,board,value,manufacturer,mpn,package,mount,symbol,footprint,refs_json,qty,'
                                      'lifecycle,datasheet,provenance,licence_notes,undetermined,notes',
                              column_formats='symbol:ref:Symbol,footprint:ref:Footprint')]),
              _row(1, [_table('pcb-footprints', 0, 6, 'Footprints — KiCad library reference, source, licence, land pattern', 'Footprint',
                              columns='name,lib,footprint,source,lib_version,licence,pad_count,mount,description'),
                       _table('pcb-landpatterns', 1, 6, 'Land patterns — dimensions as drawn (pcb-0) or IPC-7351-derived (pcb-3)', 'LandPattern',
                              columns='name,package,density,pitch_mm,pad_w_mm,pad_h_mm,drill_mm,pads,derivation,undetermined')]),
          ]),
    _page('board-fab', 'board-fab',
          'Fabrication — DKRed\'s constraints as cited rows, the DRC/fab-rule findings checked against them, and every '
          'exported file with the fab\'s verdict on its name (accepted | no | discrepancy — settled at the first upload, '
          'pcb-2)',
          'FabRuleSet', [
              _row(0, [_table('pcb-fabruleset', 0, 12, 'Fab profile', 'FabRuleSet',
                              columns='name,fab,title,url,retrieved,discrepancies', column_formats='name:ref:FabRuleSet,url:link')]),
              _row(1, [_table('pcb-fabrules', 0, 12, 'Rules — each cited: operator, value, the KiCad rule or Polari check it becomes', 'FabRule',
                              columns='name,rule_set,key,op,value,unit,value_mm,source_text,kicad_rule,polari_check,url',
                              column_formats='rule_set:ref:FabRuleSet,url:link')]),
              _row(2, [_table('pcb-drc', 0, 12, 'Check findings — kicad-cli\'s own DRC/ERC/parity and Polari\'s DKRed checks (severity none = clean; '
                              'sort/filter by kind for drc / fab-rule / parity / unconnected)',
                              'DrcResult', columns='board,kind,severity,rule,description,report_sha256,engine_version,source_date')]),
              _row(3, [_table('pcb-exports', 0, 12, 'Every exported file — kind, layer, sha256, the fab\'s naming verdict, the artifact', 'FabricationExport',
                              columns='board,export_set,kind,layer,filename,extension,sha256,bytes,fab_rule_set,accepted,fab_name,'
                                      'naming_note,artifact_url,engine_version,source_date',
                              column_formats='board:ref:PcbBoard,fab_rule_set:ref:FabRuleSet,artifact_url:link')]),
          ]),
]

#: the module's page export (manifest `pages`): /display/board-schematic, board-layout, board-bom, board-fab
SEED_PCB_PAGE_DISPLAYS = _PAGES
