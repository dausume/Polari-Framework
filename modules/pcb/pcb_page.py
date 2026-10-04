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
from polariApiServer.module_pages_seed import _page, _row, _table, _svg_panel

_PAGES = [
    _page('board-schematic', 'board-schematic',
          'Board schematics — one row per `.kicad_sch` (rendered by Polari from rows, D-pcb-1, or ingested from an open '
          'board), its sheets, the symbols it embeds, and the ERC findings kicad-cli reported (a clean run is one row, '
          'never hidden). Data comes from `pol pcb render` (Polari-authored) or `pol pcb ingest` (an open board\'s own '
          '.kicad_sch read in verbatim). Goes with /display/board-layout (the physical board for the same board name), '
          '/display/board-bom (the parts the symbols reference) and /display/board-fab (the fab checks).',
          'Schematic', [
              _row(0, [_svg_panel('pcb-schematic-svg', 0, 12, 'The schematic, drawn — every schematic SVG Polari has (rendered or ingested)',
                                  '/api/pcb/svgs?kind=svg-schematic',
                                  description='What this is for: the schematic ITSELF, not a row about it — kicad-cli\'s `sch export svg` '
                                              'on whichever schematic is selected (one per Schematic row below: the uno-shield render, or an '
                                              'ingested board like ecc83-pp). ERC findings with a reported position overlay as circles when '
                                              'the drawing\'s own viewBox is known.',
                                  markers_path='/api/pcb/drc-positions?kind=erc')], min_height=420),
              _row(1, [_table('pcb-schematics', 0, 12, 'Schematics — file, format, origin (rendered | ingested), counts', 'Schematic',
                              description='What this is for: one row per schematic FILE Polari knows about. One row = one Schematic. '
                                          'Columns: file/sha256 (the .kicad_sch and its fingerprint), format_version/generator (KiCad\'s own '
                                          'header fields), origin (rendered = Polari wrote it from rows; ingested = read from an open board '
                                          'verbatim), sheets/symbols/power_symbols/wires/labels/junctions/no_connects (counts from parsing it).',
                              columns='name,board,file,sha256,format_version,generator,title,sheets,symbols,power_symbols,wires,'
                                      'labels,junctions,no_connects,origin,licence_notes',
                              column_formats='name:ref:Schematic')]),
              _row(2, [_table('pcb-sheets', 0, 6, 'Sheets', 'SchematicSheet',
                              description='What this is for: a schematic may be split into multiple SHEETS (pages). One row = one sheet. '
                                          'Columns: path/page (where it sits in the sheet hierarchy), file (its own .kicad_sch if split out), '
                                          'symbols (how many it holds).',
                              columns='name,schematic,path,page,file,symbols',
                              column_formats='schematic:ref:Schematic'),
                       _table('pcb-symbols', 1, 6, 'Symbols used — KiCad library reference, source, licence', 'Symbol',
                              description='What this is for: every distinct KiCad symbol a schematic uses, with its licence traced. One row '
                                          '= one Symbol. Columns: lib/symbol (the KiCad library reference), source/lib_version (where that '
                                          'library came from), licence, pin_count.',
                              columns='name,lib,symbol,source,lib_version,licence,pin_count,description')]),
              _row(3, [_table('pcb-erc', 0, 12, 'Check findings — kicad-cli ERC/DRC/parity + Polari\'s DKRed checks (severity none = a clean run; '
                              'sort/filter by kind for erc)', 'DrcResult',
                              description='What this is for: every check kicad-cli (or Polari\'s own DKRed rules) has run against a schematic '
                                          'or board, PASS included (a clean run is one row with severity=none, never hidden). One row = one '
                                          'finding. Columns: kind (erc | drc | fab-rule | parity | unconnected — filter to erc for this page), '
                                          'severity, rule/description (what failed and why), report_sha256 (the raw report this came from).',
                              columns='board,kind,severity,rule,description,report_sha256,engine_version,source_date')]),
          ]),
    _page('board-layout', 'board-layout',
          'Board layout — the physical board as KiCad holds it: layer stack, outline, footprint placements and the '
          'copper of each net SUMMARISED (never authored by Polari — a person places and routes in KiCad, D-pcb-2), plus '
          'one per-layer SVG per export (kicad-cli pcb export svg, /api/pcb/artifacts/<board>/layers/<file>.svg — click '
          'artifact_url below to open a layer; Polari does not yet render these inline, D-pcb follow-up). Goes with '
          '/display/board-schematic (the circuit this board was routed from), /display/board-bom (the Placements\' '
          'parts) and /display/board-fab (the DRC findings against this same PcbBoard).',
          'PcbBoard', [
              _row(0, [_svg_panel('pcb-layout-svg', 0, 12, 'The board, drawn — per-layer SVGs (F.Cu, B.Cu, F.Silkscreen, Edge.Cuts, …)',
                                  '/api/pcb/svgs?kind=svg-layer',
                                  description='What this is for: the board ITSELF, layer by layer — kicad-cli\'s `pcb export svg` for '
                                              'whichever layer is selected (one per FabricationExport row of "Every export" below). DRC '
                                              'findings with a reported position overlay as circles when the drawing\'s own viewBox is known.',
                                  markers_path='/api/pcb/drc-positions?kind=drc,unconnected,parity,fab-rule')], min_height=420),
              _row(1, [_table('pcb-boards', 0, 12, 'Boards — layer count, outline, stackup, the fab rule set it is checked against', 'PcbBoard',
                              description='What this is for: the physical board file itself — ingested from KiCad, never authored by Polari. '
                                          'One row = one PcbBoard (.kicad_pcb). Columns: copper_layers/thickness_mm/width_mm/height_mm (the '
                                          'stackup and outline), fab_rule_set (which FabRuleSet it is checked against), footprints/nets/'
                                          'segments/vias/zones (counts), provenance (ingested | …).',
                              columns='name,board_definition,file,sha256,copper_layers,thickness_mm,width_mm,height_mm,'
                                      'fab_rule_set,footprints,nets,segments,vias,zones,licence,provenance',
                              column_formats='name:ref:PcbBoard,fab_rule_set:ref:FabRuleSet')]),
              _row(2, [_table('pcb-placements', 0, 7, 'Placements — ref, footprint, position, side (ingested)', 'Placement',
                              description='What this is for: where each part SITS on the board, as KiCad placed it. One row = one placed '
                                          'footprint. Columns: ref (the schematic designator, e.g. R3), x_mm/y_mm/rotation/side (its position), '
                                          'footprint/part (what it is).',
                              columns='board,ref,value,footprint,part,x_mm,y_mm,rotation,side,attr',
                              column_formats='board:ref:PcbBoard,part:ref:Part'),
                       _table('pcb-routes', 1, 5, 'Routes — one row per net, summarised (segments, vias, length, widths)', 'Route',
                              description='What this is for: the copper of one NET, summarised (never the raw track geometry — a person '
                                          'routes in KiCad). One row = one net. Columns: segments/vias (how it is built), length_mm/'
                                          'min_width_mm (the longest/thinnest point, relevant to the fab rules), layers_json (which copper '
                                          'layers it rides on).',
                              columns='board,net,segments,vias,length_mm,min_width_mm,widths_json,layers_json,pads',
                              column_formats='board:ref:PcbBoard')]),
              _row(3, [_table('pcb-layer-svgs', 0, 12, 'Every export (sort/filter export_set=layers for the per-layer SVGs — kicad-cli pcb export svg) '
                              '— click artifact_url to open the file',
                              'FabricationExport',
                              description='What this is for: every file kicad-cli has exported from this board — layer SVGs among them. One '
                                          'row = one exported file. Columns: export_set (filter to "layers" for the per-layer SVGs), layer '
                                          '(F.Cu, B.Cu, F.SilkS, Edge.Cuts, …), artifact_url (GET /api/pcb/artifacts/<board>/<path> — opens the '
                                          'file; not yet rendered inline on this page), sha256/bytes (the exact file fingerprinted).',
                              columns='board,export_set,layer,filename,sha256,bytes,artifact_url,engine_version,source_date',
                              column_formats='board:ref:PcbBoard,artifact_url:link')]),
          ]),
    _page('board-bom', 'board-bom',
          'Bill of materials — one row per Part: value, manufacturer/MPN where a source names them, package, mount, the '
          'KiCad symbol and footprint it uses, reference designators, licence notes, and what is still undetermined. '
          'Parts are referenced by /display/board-schematic\'s symbols and /display/board-layout\'s placements.',
          'Part', [
              _row(0, [_table('pcb-bom', 0, 12, 'BOM', 'Part',
                              description='What this is for: the bill of materials — one row per distinct part needed to build a board. One '
                                          'row = one Part. Columns: value/manufacturer/mpn (what to actually buy, where cited), package/mount '
                                          '(how it is built), symbol/footprint (the KiCad library references it uses), refs_json (which '
                                          'reference designators use it, e.g. R1,R3,R7), qty, undetermined (named gaps, never guessed).',
                              columns='name,board,value,manufacturer,mpn,package,mount,symbol,footprint,refs_json,qty,'
                                      'lifecycle,datasheet,provenance,licence_notes,undetermined,notes',
                              column_formats='symbol:ref:Symbol,footprint:ref:Footprint')]),
              _row(1, [_table('pcb-footprints', 0, 6, 'Footprints — KiCad library reference, source, licence, land pattern', 'Footprint',
                              description='What this is for: every distinct KiCad footprint a BOM part uses, with its licence traced. One row '
                                          '= one Footprint. Columns: lib/footprint (the KiCad library reference), source/lib_version, licence, '
                                          'pad_count, mount.',
                              columns='name,lib,footprint,source,lib_version,licence,pad_count,mount,description'),
                       _table('pcb-landpatterns', 1, 6, 'Land patterns — dimensions as drawn (pcb-0) or IPC-7351-derived (pcb-3)', 'LandPattern',
                              description='What this is for: the actual pad geometry a footprint draws, with where the numbers came from. One '
                                          'row = one LandPattern. Columns: pitch_mm/pad_w_mm/pad_h_mm/drill_mm/pads (the dimensions), '
                                          'derivation (as-drawn from the source file, or IPC-7351-derived), undetermined.',
                              columns='name,package,density,pitch_mm,pad_w_mm,pad_h_mm,drill_mm,pads,derivation,undetermined')]),
          ]),
    _page('board-fab', 'board-fab',
          'Fabrication — DKRed\'s constraints as cited rows, the DRC/fab-rule findings checked against them, and every '
          'exported file with the fab\'s verdict on its name (accepted | no | discrepancy — settled at the first upload, '
          'pcb-2). Checks the same PcbBoard shown at /display/board-layout; its exported files overlap with the '
          '"every export" table there (this page adds the fab-naming verdict).',
          'FabRuleSet', [
              _row(0, [_table('pcb-fabruleset', 0, 12, 'Fab profile', 'FabRuleSet',
                              description='What this is for: which fab (manufacturer) a board is being checked against. One row = one '
                                          'FabRuleSet. Columns: fab/title (who), url/retrieved (the cited source and when), discrepancies '
                                          '(count of rules that disagree with KiCad\'s own defaults).',
                              columns='name,fab,title,url,retrieved,discrepancies', column_formats='name:ref:FabRuleSet,url:link')]),
              _row(1, [_table('pcb-fabrules', 0, 12, 'Rules — each cited: operator, value, the KiCad rule or Polari check it becomes', 'FabRule',
                              description='What this is for: DKRed\'s own constraints (min trace width, drill size, …), each CITED, never '
                                          'guessed. One row = one rule. Columns: key/op/value/unit (the constraint, e.g. min_trace_width >= '
                                          '0.15mm), source_text (the cited wording), kicad_rule/polari_check (what it becomes as an actual '
                                          'check), url (the source).',
                              columns='name,rule_set,key,op,value,unit,value_mm,source_text,kicad_rule,polari_check,url',
                              column_formats='rule_set:ref:FabRuleSet,url:link')]),
              _row(2, [_table('pcb-drc', 0, 12, 'Check findings — kicad-cli\'s own DRC/ERC/parity and Polari\'s DKRed checks (severity none = clean; '
                              'sort/filter by kind for drc / fab-rule / parity / unconnected)',
                              'DrcResult',
                              description='What this is for: the same DrcResult table as /display/board-schematic\'s ERC panel, filtered here '
                                          'to the fabrication kinds (drc | fab-rule | parity | unconnected). One row = one finding, PASS '
                                          'included.',
                              columns='board,kind,severity,rule,description,report_sha256,engine_version,source_date')]),
              _row(3, [_table('pcb-exports', 0, 12, 'Every exported file — kind, layer, sha256, the fab\'s naming verdict, the artifact', 'FabricationExport',
                              description='What this is for: every exported file (Gerbers, drill, STEP, layer SVGs) with the FAB\'S OWN '
                                          'verdict on whether its name matches what that fab expects. One row = one file. Columns: accepted/'
                                          'fab_name/naming_note (the verdict: accepted | no | discrepancy, settled at the first upload), '
                                          'artifact_url (GET /api/pcb/artifacts/<board>/<path>).',
                              columns='board,export_set,kind,layer,filename,extension,sha256,bytes,fab_rule_set,accepted,fab_name,'
                                      'naming_note,artifact_url,engine_version,source_date',
                              column_formats='board:ref:PcbBoard,fab_rule_set:ref:FabRuleSet,artifact_url:link')]),
          ]),
]

#: the module's page export (manifest `pages`): /display/board-schematic, board-layout, board-bom, board-fab
SEED_PCB_PAGE_DISPLAYS = _PAGES
