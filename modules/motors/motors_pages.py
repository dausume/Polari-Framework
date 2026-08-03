"""
@module motors.motors_pages

THE PER-OBJECT DISPLAY CONFIGURATION for the motor ladder — seeded as
DATA so M0/M1 render as configured tables, graphs and pages on a fresh
database instead of an alphabetical dump of every field (which, for
these classes, leads with the *_json blobs).

Polari expresses presentation PER OBJECT: a TableDefinition or
GraphDefinition names its `source_class`, and other displays reference
it for a specific context. So the rows below are not a page layout
bolted on — they are the motor classes' own display configuration,
carried with the module the way the class rows are.

Three kinds, and the pair that matters:
  TableDefinition   is_default_dataset_display  -> the MULTI-reference
                    view (which columns a list of these shows)
                    is_default_instance_display -> the SINGLE-reference
                    view (`detailDisplay.cards`, one object)
  GraphDefinition   {'graphConfig': {...}} over the same source_class
  DisplayDefinition the m0/m1 pages, which REFERENCE the above by id
                    and scope them with filterField/filterValue

⚠ COLUMN SHAPE. `tableConfiguration.columns` entries are
ColumnConfiguration: {name, displayName, dataType, order, visible,
...}. They are NOT {id, fieldName, index} — that shape parses to ZERO
columns and renders an EMPTY table with a correct row count, which is
a confusing way to fail. `detailDisplay.cards` DOES use
{id, fieldName, label, icon, format}; the two genuinely differ.

⚠ The display rows carry graph/table IDs, which are assigned at
insert. seed_motors_pages() re-points them AFTER the definitions are
upserted — see _repoint_display_refs. Seeding the pages with the
staging instance's ids would leave every embed blank on a fresh node.

@consumers polariServer (seed pass — seed_motors_pages)
"""

import json

#: Per-object table + instance-display configuration.
SEED_MOTOR_TABLES = [{'definition': '{"tableConfiguration": {"id": "motor-design-table", '
                '"className": "MotorDesignDefinition", "displayName": '
                '"Motor designs", "columns": [{"name": "name", '
                '"displayName": "Design", "dataType": "str", '
                '"available": true, "visible": true, "order": 0, '
                '"sortable": true, "filterable": true, "resizable": '
                'true, "width": 220, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}, {"name": "ladder_rung", '
                '"displayName": "Rung", "dataType": "str", '
                '"available": true, "visible": true, "order": 1, '
                '"sortable": true, "filterable": true, "resizable": '
                'true, "width": 90, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}, {"name": "topology", '
                '"displayName": "Topology", "dataType": "str", '
                '"available": true, "visible": true, "order": 2, '
                '"sortable": true, "filterable": true, "resizable": '
                'true, "width": 200, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}, {"name": "tolerance_tier", '
                '"displayName": "Tier", "dataType": "str", '
                '"available": true, "visible": true, "order": 3, '
                '"sortable": true, "filterable": true, "resizable": '
                'true, "width": 90, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}, {"name": "display_name", '
                '"displayName": "Full name", "dataType": "str", '
                '"available": true, "visible": true, "order": 4, '
                '"sortable": true, "filterable": true, "resizable": '
                'true, "width": 320, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}], "removedColumns": [], '
                '"sortOrder": [], "sortDirection": "asc", '
                '"sortColumn": "name", "pagination": {"enabled": true, '
                '"pageSize": 25, "pageSizeOptions": [10, 25, 50]}, '
                '"filter": {"globalFilterEnabled": true, '
                '"columnFiltersEnabled": true, "activeFilters": {}, '
                '"caseSensitive": false}, "sections": {"enabled": '
                'false, "sections": []}, "density": "comfortable", '
                '"selectionMode": "none", "showRowNumbers": false, '
                '"showHeaders": true, "stripedRows": true, '
                '"showGridLines": true, "hoverHighlight": true, '
                '"reorderableColumns": true, "fixedHeight": 0, '
                '"cssClass": "", "lastModified": '
                '"2026-08-03T00:00:00.000Z", "version": 1}, '
                '"rowWrapping": {"enabled": false, "fieldsPerRow": 4, '
                '"separatorStyle": "thin"}, "crudPermissions": '
                '{"allowCreate": true, "allowEdit": true, '
                '"allowDelete": false}, "instanceActions": [], '
                '"datasetActions": [], "detailDisplay": {"cards": '
                '[{"id": "c-name", "fieldName": "name", "label": '
                '"Design", "icon": "settings", "format": "text"}, '
                '{"id": "c-rung", "fieldName": "ladder_rung", "label": '
                '"Ladder rung", "icon": "stairs", "format": "text"}, '
                '{"id": "c-topology", "fieldName": "topology", '
                '"label": "Topology", "icon": "account_tree", '
                '"format": "text"}, {"id": "c-tier", "fieldName": '
                '"tolerance_tier", "label": "Tolerance tier", "icon": '
                '"straighten", "format": "text"}, {"id": "c-display", '
                '"fieldName": "display_name", "label": "Full name", '
                '"icon": "label", "format": "text"}, {"id": "c-prior", '
                '"fieldName": "is_prior", "label": "Prior (not '
                'measured)", "icon": "science", "format": "text"}]}}',
  'description': 'Standard table + instance display for a motor '
                 'design.',
  'is_default_dataset_display': True,
  'is_default_instance_display': True,
  'is_default_table': True,
  'name': 'motor-design-standard',
  'source_class': 'MotorDesignDefinition'},
 {'definition': '{"tableConfiguration": {"id": '
                '"motorpartdefinition-table", "className": '
                '"MotorPartDefinition", "displayName": "Motor parts", '
                '"columns": [{"name": "display_name", "displayName": '
                '"Part", "dataType": "str", "available": true, '
                '"visible": true, "order": 0, "sortable": true, '
                '"filterable": true, "resizable": true, "width": 240, '
                '"minWidth": 60, "alignment": "left", "format": '
                '"default", "pinned": false, "showTypeIcon": true, '
                '"userCanHide": true, "userCanReorder": true}, '
                '{"name": "function", "displayName": "Function", '
                '"dataType": "str", "available": true, "visible": '
                'true, "order": 1, "sortable": true, "filterable": '
                'true, "resizable": true, "width": 200, "minWidth": '
                '60, "alignment": "left", "format": "default", '
                '"pinned": false, "showTypeIcon": true, "userCanHide": '
                'true, "userCanReorder": true}, {"name": '
                '"material_ref", "displayName": "Material", '
                '"dataType": "str", "available": true, "visible": '
                'true, "order": 2, "sortable": true, "filterable": '
                'true, "resizable": true, "width": 240, "minWidth": '
                '60, "alignment": "left", "format": "default", '
                '"pinned": false, "showTypeIcon": true, "userCanHide": '
                'true, "userCanReorder": true}, {"name": "quantity", '
                '"displayName": "Qty", "dataType": "int", "available": '
                'true, "visible": true, "order": 3, "sortable": true, '
                '"filterable": true, "resizable": true, "width": 80, '
                '"minWidth": 60, "alignment": "left", "format": '
                '"default", "pinned": false, "showTypeIcon": true, '
                '"userCanHide": true, "userCanReorder": true}, '
                '{"name": "purpose", "displayName": "Purpose", '
                '"dataType": "str", "available": true, "visible": '
                'true, "order": 4, "sortable": true, "filterable": '
                'true, "resizable": true, "width": 360, "minWidth": '
                '60, "alignment": "left", "format": "default", '
                '"pinned": false, "showTypeIcon": true, "userCanHide": '
                'true, "userCanReorder": true}], "removedColumns": [], '
                '"sortOrder": [], "sortDirection": "asc", '
                '"sortColumn": "display_name", "pagination": '
                '{"enabled": true, "pageSize": 25, "pageSizeOptions": '
                '[10, 25, 50]}, "filter": {"globalFilterEnabled": '
                'true, "columnFiltersEnabled": true, "activeFilters": '
                '{}, "caseSensitive": false}, "sections": {"enabled": '
                'false, "sections": []}, "density": "comfortable", '
                '"selectionMode": "none", "showRowNumbers": false, '
                '"showHeaders": true, "stripedRows": true, '
                '"showGridLines": true, "hoverHighlight": true, '
                '"reorderableColumns": true, "fixedHeight": 0, '
                '"cssClass": "", "lastModified": '
                '"2026-08-03T00:00:00.000Z", "version": 1}, '
                '"rowWrapping": {"enabled": false, "fieldsPerRow": 4, '
                '"separatorStyle": "thin"}, "crudPermissions": '
                '{"allowCreate": true, "allowEdit": true, '
                '"allowDelete": false}, "instanceActions": [], '
                '"datasetActions": [], "detailDisplay": {"cards": '
                '[{"id": "pc-name", "fieldName": "display_name", '
                '"label": "Part", "icon": "build", "format": "text"}, '
                '{"id": "pc-fn", "fieldName": "function", "label": '
                '"Function", "icon": "settings", "format": "text"}, '
                '{"id": "pc-mat", "fieldName": "material_ref", '
                '"label": "Material", "icon": "science", "format": '
                '"text"}, {"id": "pc-qty", "fieldName": "quantity", '
                '"label": "Quantity", "icon": "tag", "format": '
                '"number"}, {"id": "pc-why", "fieldName": '
                '"why_this_material", "label": "Why this material", '
                '"icon": "help", "format": "text"}, {"id": "pc-buf", '
                '"fieldName": "field_buffer_mm", "label": "Field '
                'buffer (mm)", "icon": "straighten", "format": '
                '"number"}]}}',
  'description': 'Parts of a motor design — the bill, readable.',
  'is_default_dataset_display': True,
  'is_default_instance_display': True,
  'is_default_table': True,
  'name': 'motor-part-standard',
  'source_class': 'MotorPartDefinition'},
 {'definition': '{"tableConfiguration": {"id": '
                '"motorverificationrun-table", "className": '
                '"MotorVerificationRun", "displayName": "Verification '
                'runs", "columns": [{"name": "name", "displayName": '
                '"Run", "dataType": "str", "available": true, '
                '"visible": true, "order": 0, "sortable": true, '
                '"filterable": true, "resizable": true, "width": 220, '
                '"minWidth": 60, "alignment": "left", "format": '
                '"default", "pinned": false, "showTypeIcon": true, '
                '"userCanHide": true, "userCanReorder": true}, '
                '{"name": "kind", "displayName": "Kind", "dataType": '
                '"str", "available": true, "visible": true, "order": '
                '1, "sortable": true, "filterable": true, "resizable": '
                'true, "width": 160, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}, {"name": "steps_commanded", '
                '"displayName": "Commanded", "dataType": "int", '
                '"available": true, "visible": true, "order": 2, '
                '"sortable": true, "filterable": true, "resizable": '
                'true, "width": 120, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}, {"name": "steps_taken", '
                '"displayName": "Taken", "dataType": "int", '
                '"available": true, "visible": true, "order": 3, '
                '"sortable": true, "filterable": true, "resizable": '
                'true, "width": 110, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}, {"name": "clock_error_s", '
                '"displayName": "Clock error (s)", "dataType": '
                '"float", "available": true, "visible": true, "order": '
                '4, "sortable": true, "filterable": true, "resizable": '
                'true, "width": 140, "minWidth": 60, "alignment": '
                '"left", "format": "default", "pinned": false, '
                '"showTypeIcon": true, "userCanHide": true, '
                '"userCanReorder": true}], "removedColumns": [], '
                '"sortOrder": [], "sortDirection": "asc", '
                '"sortColumn": "name", "pagination": {"enabled": true, '
                '"pageSize": 25, "pageSizeOptions": [10, 25, 50]}, '
                '"filter": {"globalFilterEnabled": true, '
                '"columnFiltersEnabled": true, "activeFilters": {}, '
                '"caseSensitive": false}, "sections": {"enabled": '
                'false, "sections": []}, "density": "comfortable", '
                '"selectionMode": "none", "showRowNumbers": false, '
                '"showHeaders": true, "stripedRows": true, '
                '"showGridLines": true, "hoverHighlight": true, '
                '"reorderableColumns": true, "fixedHeight": 0, '
                '"cssClass": "", "lastModified": '
                '"2026-08-03T00:00:00.000Z", "version": 1}, '
                '"rowWrapping": {"enabled": false, "fieldsPerRow": 4, '
                '"separatorStyle": "thin"}, "crudPermissions": '
                '{"allowCreate": true, "allowEdit": true, '
                '"allowDelete": false}, "instanceActions": [], '
                '"datasetActions": [], "detailDisplay": {"cards": '
                '[{"id": "vc-name", "fieldName": "name", "label": '
                '"Run", "icon": "play_arrow", "format": "text"}, '
                '{"id": "vc-kind", "fieldName": "kind", "label": '
                '"Kind", "icon": "category", "format": "text"}, {"id": '
                '"vc-cmd", "fieldName": "steps_commanded", "label": '
                '"Steps commanded", "icon": "tag", "format": '
                '"number"}, {"id": "vc-took", "fieldName": '
                '"steps_taken", "label": "Steps taken", "icon": '
                '"check", "format": "number"}, {"id": "vc-err", '
                '"fieldName": "clock_error_s", "label": "Clock error '
                '(s)", "icon": "schedule", "format": "number"}, {"id": '
                '"vc-dur", "fieldName": "duration_s", "label": '
                '"Duration (s)", "icon": "timer", "format": '
                '"number"}]}}',
  'description': 'Verification runs — sim vs MEASURED, and the clock '
                 'error.',
  'is_default_dataset_display': True,
  'is_default_instance_display': True,
  'is_default_table': True,
  'name': 'motor-verification-standard',
  'source_class': 'MotorVerificationRun'}]

#: Graphs over the motor classes.
SEED_MOTOR_GRAPHS = [{'definition': '{"graphConfig": {"renderStyle": "barY", "xDimension": '
                '"display_name", "yDimensions": ["field_buffer_mm"], '
                '"seriesColors": [], "options": {"width": 800, '
                '"height": 360, "marginTop": 20, "marginRight": 30, '
                '"marginBottom": 90, "marginLeft": 60, "showLegend": '
                'false, "showGrid": true, "xLabel": "part", "yLabel": '
                '"field buffer (mm)"}, "aggregation": {"enabled": '
                'false, "strategy": "average"}}}',
  'description': 'Field buffer per part (mm).',
  'name': 'motor-part-field-buffer',
  'source_class': 'MotorPartDefinition'},
 {'definition': '{"graphConfig": {"renderStyle": "barY", "xDimension": '
                '"display_name", "yDimensions": ["quantity"], '
                '"seriesColors": [], "options": {"width": 800, '
                '"height": 360, "marginTop": 20, "marginRight": 30, '
                '"marginBottom": 90, "marginLeft": 60, "showLegend": '
                'false, "showGrid": true, "xLabel": "part", "yLabel": '
                '"quantity"}, "aggregation": {"enabled": false, '
                '"strategy": "average"}}}',
  'description': 'Part count per part of a design.',
  'name': 'motor-part-quantity',
  'source_class': 'MotorPartDefinition'},
 {'definition': '{"graphConfig": {"renderStyle": "barY", "xDimension": '
                '"name", "yDimensions": ["clock_error_s"], '
                '"seriesColors": [], "options": {"width": 800, '
                '"height": 320, "marginTop": 20, "marginRight": 30, '
                '"marginBottom": 70, "marginLeft": 70, "showLegend": '
                'false, "showGrid": true, "xLabel": "run", "yLabel": '
                '"clock error (s)"}, "aggregation": {"enabled": false, '
                '"strategy": "average"}}}',
  'description': 'Clock error by run — THE M0 metric.',
  'name': 'motor-verification-error',
  'source_class': 'MotorVerificationRun'}]

#: The M0/M1 pages that reference the above.
SEED_MOTOR_PAGE_DISPLAYS = [{'definition': '{"rows": [{"index": 0, "rowSegments": 12, '
                '"minRowHeight": 220, "maxRowHeight": 0, "autoHeight": '
                'true, "cssClass": "", "items": [{"id": "d-detail", '
                '"index": 0, "type": "component", "rowSegmentsUsed": '
                '12, "gridColumnStart": null, "title": "The design '
                '\\u2014 configured instance display", "visible": '
                'true, "collapsed": false, "cssClass": "", "item": '
                'null, "nestedRows": [], "componentProps": '
                '{"componentName": "instance-detail-panel", "inputs": '
                '{"className": "MotorDesignDefinition", "filterField": '
                '"name", "filterValue": "clock-lavet-m0"}}}]}, '
                '{"index": 1, "rowSegments": 12, "minRowHeight": 320, '
                '"maxRowHeight": 0, "autoHeight": true, "cssClass": '
                '"", "items": [{"id": "d-parts", "index": 0, "type": '
                '"component", "rowSegmentsUsed": 12, '
                '"gridColumnStart": null, "title": "Parts of this '
                'design (multi-reference, filtered by design_ref)", '
                '"visible": true, "collapsed": false, "cssClass": "", '
                '"item": null, "nestedRows": [], "componentProps": '
                '{"componentName": "class-rows-table", "inputs": '
                '{"className": "MotorPartDefinition", "filterField": '
                '"design_ref", "filterValue": "clock-lavet-m0", '
                '"columns": '
                '"display_name,function,material_ref,quantity"}}}]}, '
                '{"index": 2, "rowSegments": 12, "minRowHeight": 420, '
                '"maxRowHeight": 0, "autoHeight": true, "cssClass": '
                '"", "items": [{"id": "d-graph", "index": 0, "type": '
                '"component", "rowSegmentsUsed": 6, "gridColumnStart": '
                'null, "title": "Part quantities \\u2014 configured '
                'GraphDefinition", "visible": true, "collapsed": '
                'false, "cssClass": "", "item": null, "nestedRows": '
                '[], "componentProps": {"componentName": '
                '"embeddedGraph", "inputs": {"graphConfigId": '
                '"INBE101Edv", "className": "MotorPartDefinition", '
                '"filterField": "design_ref", "filterValue": '
                '"clock-lavet-m0"}}}, {"id": "d-graph2", "index": 1, '
                '"type": "component", "rowSegmentsUsed": 6, '
                '"gridColumnStart": null, "title": "Field buffer per '
                'part", "visible": true, "collapsed": false, '
                '"cssClass": "", "item": null, "nestedRows": [], '
                '"componentProps": {"componentName": "embeddedGraph", '
                '"inputs": {"graphConfigId": "Y6vkNBG3N", "className": '
                '"MotorPartDefinition", "filterField": "design_ref", '
                '"filterValue": "clock-lavet-m0"}}}]}, {"index": 3, '
                '"rowSegments": 12, "minRowHeight": 300, '
                '"maxRowHeight": 0, "autoHeight": true, "cssClass": '
                '"", "items": [{"id": "d-runs", "index": 0, "type": '
                '"component", "rowSegmentsUsed": 12, '
                '"gridColumnStart": null, "title": "Verification runs '
                '\\u2014 configured TableDefinition", "visible": true, '
                '"collapsed": false, "cssClass": "", "item": null, '
                '"nestedRows": [], "componentProps": {"componentName": '
                '"embeddedTable", "inputs": {"tableConfigId": '
                '"rWGrdGQ4b", "className": "MotorVerificationRun", '
                '"filterField": "design_ref", "filterValue": '
                '"clock-lavet-m0"}}}]}, {"index": 4, "rowSegments": '
                '12, "minRowHeight": 520, "maxRowHeight": 0, '
                '"autoHeight": true, "cssClass": "", "items": [{"id": '
                '"d-sim", "index": 0, "type": "component", '
                '"rowSegmentsUsed": 12, "gridColumnStart": null, '
                '"title": "The simulation \\u2014 embedded sim space", '
                '"visible": true, "collapsed": false, "cssClass": "", '
                '"item": null, "nestedRows": [], "componentProps": '
                '{"componentName": "sim-space-viewer", "inputs": '
                '{"simSpaceName": "motor-m0-viz", "hideRunPanel": '
                'false, "clickNavigates": false}}}]}]}',
  'description': 'M0 — the Lavet clock stepper, configured end to end.',
  'isPage': True,
  'linkedSolutions': '[]',
  'name': 'm0-detail',
  'pageRoute': 'm0-detail',
  'source_class': 'MotorDesignDefinition'},
 {'definition': '{"rows": [{"index": 0, "rowSegments": 12, '
                '"minRowHeight": 220, "maxRowHeight": 0, "autoHeight": '
                'true, "cssClass": "", "items": [{"id": "d-detail", '
                '"index": 0, "type": "component", "rowSegmentsUsed": '
                '12, "gridColumnStart": null, "title": "The design '
                '\\u2014 configured instance display", "visible": '
                'true, "collapsed": false, "cssClass": "", "item": '
                'null, "nestedRows": [], "componentProps": '
                '{"componentName": "instance-detail-panel", "inputs": '
                '{"className": "MotorDesignDefinition", "filterField": '
                '"name", "filterValue": "reluctance-6s4p-m1"}}}]}, '
                '{"index": 1, "rowSegments": 12, "minRowHeight": 320, '
                '"maxRowHeight": 0, "autoHeight": true, "cssClass": '
                '"", "items": [{"id": "d-parts", "index": 0, "type": '
                '"component", "rowSegmentsUsed": 12, '
                '"gridColumnStart": null, "title": "Parts of this '
                'design (multi-reference, filtered by design_ref)", '
                '"visible": true, "collapsed": false, "cssClass": "", '
                '"item": null, "nestedRows": [], "componentProps": '
                '{"componentName": "class-rows-table", "inputs": '
                '{"className": "MotorPartDefinition", "filterField": '
                '"design_ref", "filterValue": "reluctance-6s4p-m1", '
                '"columns": '
                '"display_name,function,material_ref,quantity"}}}]}, '
                '{"index": 2, "rowSegments": 12, "minRowHeight": 420, '
                '"maxRowHeight": 0, "autoHeight": true, "cssClass": '
                '"", "items": [{"id": "d-graph", "index": 0, "type": '
                '"component", "rowSegmentsUsed": 6, "gridColumnStart": '
                'null, "title": "Part quantities \\u2014 configured '
                'GraphDefinition", "visible": true, "collapsed": '
                'false, "cssClass": "", "item": null, "nestedRows": '
                '[], "componentProps": {"componentName": '
                '"embeddedGraph", "inputs": {"graphConfigId": '
                '"INBE101Edv", "className": "MotorPartDefinition", '
                '"filterField": "design_ref", "filterValue": '
                '"reluctance-6s4p-m1"}}}, {"id": "d-graph2", "index": '
                '1, "type": "component", "rowSegmentsUsed": 6, '
                '"gridColumnStart": null, "title": "Field buffer per '
                'part", "visible": true, "collapsed": false, '
                '"cssClass": "", "item": null, "nestedRows": [], '
                '"componentProps": {"componentName": "embeddedGraph", '
                '"inputs": {"graphConfigId": "Y6vkNBG3N", "className": '
                '"MotorPartDefinition", "filterField": "design_ref", '
                '"filterValue": "reluctance-6s4p-m1"}}}]}, {"index": '
                '3, "rowSegments": 12, "minRowHeight": 300, '
                '"maxRowHeight": 0, "autoHeight": true, "cssClass": '
                '"", "items": [{"id": "d-runs", "index": 0, "type": '
                '"component", "rowSegmentsUsed": 12, '
                '"gridColumnStart": null, "title": "Verification runs '
                '\\u2014 configured TableDefinition", "visible": true, '
                '"collapsed": false, "cssClass": "", "item": null, '
                '"nestedRows": [], "componentProps": {"componentName": '
                '"embeddedTable", "inputs": {"tableConfigId": '
                '"rWGrdGQ4b", "className": "MotorVerificationRun", '
                '"filterField": "design_ref", "filterValue": '
                '"reluctance-6s4p-m1"}}}]}, {"index": 4, '
                '"rowSegments": 12, "minRowHeight": 520, '
                '"maxRowHeight": 0, "autoHeight": true, "cssClass": '
                '"", "items": [{"id": "d-sim", "index": 0, "type": '
                '"component", "rowSegmentsUsed": 12, '
                '"gridColumnStart": null, "title": "The simulation '
                '\\u2014 embedded sim space", "visible": true, '
                '"collapsed": false, "cssClass": "", "item": null, '
                '"nestedRows": [], "componentProps": {"componentName": '
                '"sim-space-viewer", "inputs": {"simSpaceName": '
                '"motor-m1-viz", "hideRunPanel": false, '
                '"clickNavigates": false}}}]}]}',
  'description': 'M1 — the 6-slot/4-pole reluctance motor, configured '
                 'end to end.',
  'isPage': True,
  'linkedSolutions': '[]',
  'name': 'm1-detail',
  'pageRoute': 'm1-detail',
  'source_class': 'MotorDesignDefinition'}]

#: The ids stored inside the display definitions above are whatever
#: the authoring instance handed out. They are ADVISORY ONLY —
#: _repoint_display_refs replaces them with this node's ids at seed
#: time, which was verified by seeding deliberately wrong ids and
#: watching all six embeds get corrected on boot.
#:
#: Which seeded definition each embed should point at, by the name it
#: was authored against. The stored `definition` carries whatever ids
#: the authoring instance handed out; on any other node those ids
#: refer to nothing, so the embed renders blank. Keyed by display item
#: id so the mapping is explicit rather than positional.
EMBED_TARGETS = {
    'd-graph': ('GraphDefinition', 'motor-part-quantity'),
    'd-graph2': ('GraphDefinition', 'motor-part-field-buffer'),
    'd-runs': ('TableDefinition', 'motor-verification-standard'),
}


def _by_name(manager, class_name, name):
    """The live row of `class_name` called `name`, or None."""
    table = (getattr(manager, 'objectTables', {}) or {}).get(class_name, {})
    for inst in (table or {}).values():
        if getattr(inst, 'name', '') == name:
            return inst
    return None


def _repoint_display_refs(manager):
    """Re-point every embed at THIS node's definition ids.

    graphConfigId / tableConfigId are ids, not names, and ids are
    assigned at insert. A seeded page therefore cannot carry a working
    reference — it has to be resolved after the definitions exist.
    Returns how many items were repointed, so the seed pass can report
    it rather than fail silently.
    """
    wanted = {d['name'] for d in SEED_MOTOR_PAGE_DISPLAYS}
    repointed = 0
    for row in list((getattr(manager, 'objectTables', {}) or {})
                    .get('DisplayDefinition', {}).values()):
        if getattr(row, 'name', '') not in wanted:
            continue
        try:
            definition = json.loads(getattr(row, 'definition', '') or '{}')
        except ValueError:
            continue
        changed = False
        for display_row in (definition.get('rows') or []):
            for item in (display_row.get('items') or []):
                target = EMBED_TARGETS.get(item.get('id', ''))
                if not target:
                    continue
                class_name, def_name = target
                found = _by_name(manager, class_name, def_name)
                if found is None:
                    print(f'[MotorsPagesSeed] {def_name} not found — '
                          f'"{row.name}" keeps its stored id and that '
                          f'panel will render empty', flush=True)
                    continue
                key = ('graphConfigId' if class_name == 'GraphDefinition'
                       else 'tableConfigId')
                inputs = (item.get('componentProps') or {}).get('inputs')
                if inputs is None:
                    continue
                if inputs.get(key) != found.id:
                    inputs[key] = found.id
                    changed = True
                    repointed += 1
        if changed:
            row.definition = json.dumps(definition)
            try:
                manager.db.saveInstanceInDB(row)
            except Exception as save_error:
                print(f'[MotorsPagesSeed] could not persist repointed '
                      f'"{row.name}": {save_error}', flush=True)
    return repointed


def seed_motors_pages(manager):
    """Upsert the motor classes' display configuration.

    Upserted, not inserted, so an edited config converges instead of
    duplicating — the same contract every other module's page seed
    uses.
    """
    from composition.seed_upsert import upsert_seed_pairs
    from polariApiServer.tableDefinition import TableDefinition
    from polariApiServer.graphDefinition import GraphDefinition
    from polariApiServer.displayDefinition import DisplayDefinition

    reports = upsert_seed_pairs(manager, [
        ('TableDefinition', TableDefinition, SEED_MOTOR_TABLES),
        ('GraphDefinition', GraphDefinition, SEED_MOTOR_GRAPHS),
        ('DisplayDefinition', DisplayDefinition,
         SEED_MOTOR_PAGE_DISPLAYS),
    ], tag='MotorsPagesSeed')

    repointed = _repoint_display_refs(manager)
    if repointed:
        print(f'[MotorsPagesSeed] repointed {repointed} embed '
              f'reference(s) at this node\'s definition ids', flush=True)
    return reports
