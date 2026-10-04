"""
@module pcb.pcb_api

GET  /api/pcb                      summary: boards ingested, parts, symbols, footprints, DRC/ERC severity counts, the
                                    engines ladder's current rung (nothing run)
GET  /api/pcb/engines               where kicad-cli WOULD run (pcb.custom.pcb_engines.placement — the ladder, nothing run)
POST /api/pcb/ingest                body {path} (a KiCad project directory on THIS server's host, e.g. the stored
                                    upstream board under modules/pcb/custom/upstream/…) or {board, files: {name: text}}
                                    (the project's own files, inline) + optional {source_date}: runs pcb.custom.ingest
                                    (rows, no engine, then every check/export through the ladder) and UPSERTS every row
                                    class by name (Part, Symbol, Footprint, LandPattern, Schematic, SchematicSheet,
                                    PcbBoard, Placement, Route, DrcResult, FabricationExport, FabRuleSet, FabRule, and
                                    board.BoardNet — brd-bo's net class, the one pcb reuses rather than duplicate).
                                    `refused` names the knob when the engine is unreachable; the rows are still stored.
POST /api/pcb/render/uno-shield     THE UNO SHIELD skeleton (pcb.custom.uno_shield + schematic_writer): writes
                                    `uno-shield.kicad_sch` from brd-bo's rows, runs `sch erc` through the ladder, and
                                    stores the Schematic/SchematicSheet/Symbol/Part/DrcResult rows. No PCB yet (pcb-2).
GET  /api/pcb/artifacts/{board}/{path}
                                    one exported file's bytes (a Gerber, drill, SVG, STEP, BOM, netlist …), for the
                                    FabricationExport table's artifact_url column and the per-layer SVG links on
                                    /display/board-layout.
"""
import inspect
import json
import os

import falcon

from objectTreeDecorators import treeObject, treeObjectInit

#: the artifact dirs ingest.py has already written this server's exports under (POLARI_PCB_HOME/<board>/artifacts/<board>)
from pcb.custom.ingest import home as _pcb_home


class PcbAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/pcb', self, suffix='summary')
            add('/api/pcb/engines', self, suffix='engines')
            add('/api/pcb/ingest', self, suffix='ingest')
            add('/api/pcb/render/uno-shield', self, suffix='render_uno_shield')
            add('/api/pcb/artifacts/{board}/{path:path}', self, suffix='artifact')

    # ---------------------------------------------------------------- rows
    def _table(self, class_name):
        return ((self.manager.objectTables or {}).get(class_name, {}) or {}) if self.manager is not None else {}

    def _rows(self, class_name):
        return list(self._table(class_name).values())

    def _class(self, class_name):
        from pcb.pcb_basis import PCB_CLASSES
        by_name = {c.__name__: c for c in PCB_CLASSES}
        if class_name in by_name:
            return by_name[class_name]
        if class_name == 'BoardNet':   # brd-bo's class — pcb reuses it rather than a second net model (plan §2b)
            from board.objects.board.BoardNet import BoardNet
            return BoardNet
        return None

    def _upsert(self, class_name, rows):
        cls = self._class(class_name)
        if cls is None or self.manager is None:
            return 0
        allowed = set(inspect.signature(cls.__init__).parameters) - {'self', 'manager'}
        by_name = {getattr(r, 'name', ''): r for r in self._rows(class_name)}
        n = 0
        for r in rows:
            fields = {k: v for k, v in r.items() if k in allowed}
            if not fields.get('name'):
                continue
            row = by_name.get(fields['name'])
            if row is None:
                row = cls(manager=self.manager, **fields)
            else:
                for k, v in fields.items():
                    setattr(row, k, v)
            try:
                self.manager.db.saveInstanceInDB(row)
                n += 1
            except Exception:  # noqa: BLE001
                pass
        return n

    # ---------------------------------------------------------------- summary / engines
    def on_get_summary(self, request, response):
        boards = self._rows('PcbBoard')
        drc = self._rows('DrcResult')
        by_sev = {}
        for d in drc:
            by_sev[d.severity] = by_sev.get(d.severity, 0) + 1
        from pcb.custom.pcb_engines import resolve
        response.media = {'ok': True, 'boards': len(boards), 'parts': len(self._rows('Part')), 'symbols': len(self._rows('Symbol')),
                          'footprints': len(self._rows('Footprint')), 'schematics': len(self._rows('Schematic')),
                          'exports': len(self._rows('FabricationExport')), 'drcBySeverity': by_sev, 'engine': resolve()}

    def on_get_engines(self, request, response):
        from pcb.custom.pcb_engines import placement
        response.media = dict(placement(), ok=True)

    # ---------------------------------------------------------------- ingest
    @staticmethod
    def _body(request, response):
        try:
            raw = request.bounded_stream.read() or b''
            return json.loads(raw) if raw.strip() else {}
        except ValueError as e:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return None

    def on_post_ingest(self, request, response):
        from pcb.custom import ingest as I
        body = self._body(request, response)
        if body is None:
            return
        path = body.get('path')
        files = body.get('files')
        if not path and not files:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'ingest needs {path: <a KiCad project dir on this host>} or {board, files: {name: text}}'}
            return
        source_date = body.get('source_date') or I.E.SOURCE_DATE
        try:
            if path:
                res = I.ingest(path, board=body.get('board'), source_date=source_date)
            else:
                import tempfile
                with tempfile.TemporaryDirectory(prefix='pcb-ingest-') as d:
                    for name, text in files.items():
                        fp = os.path.join(d, name)
                        os.makedirs(os.path.dirname(fp) or d, exist_ok=True)
                        open(fp, 'w', encoding='utf-8').write(text)
                    res = I.ingest(d, board=body.get('board'), source_date=source_date)
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': str(e)}
            return
        rows = res['rows']
        stored = {k: self._upsert(k, v) for k, v in rows.items() if k != 'problems' and isinstance(v, list)}
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'board': rows.get('board', body.get('board', '')), 'stored': stored,
                          'problems': rows.get('problems', []), 'refused': res.get('refused', ''),
                          'netlistVsBoard': (res.get('record') or {}).get('netlist_vs_board', {})}

    def on_post_render_uno_shield(self, request, response):
        from pcb.custom import uno_shield as U
        from pcb.custom import schematic_writer as W
        from pcb.custom import pcb_engines as E
        d = U.design()
        need = {c['lib_id'] for c in d['components']} | {W.POWER_LIB[n] for n in d['nets'] if n in W.POWER_LIB} | {'power:PWR_FLAG'}
        try:
            libs = {}
            for lib_id in need:
                lib, name = lib_id.split(':', 1)
                libs[lib_id] = E.library('symbol', lib, name)['text']
            text, report = W.write(d, libs, title='UNO Shield (pcb-0 schematic skeleton)')
        except (E.EngineRefused, W.WriterRefused) as e:
            response.status = falcon.HTTP_503
            response.media = {'ok': False, 'error': str(e)}
            return
        erc = {}
        try:
            res = E.run(['sch', 'erc', '--format', 'json', '--severity-all', '-o', 'erc.json', 'uno-shield.kicad_sch'],
                       {'uno-shield.kicad_sch': text}, source_date=E.SOURCE_DATE)
            erc = json.loads(res['files'].get('erc.json', b'{}') or b'{}')
        except E.EngineRefused as e:
            erc = {'refused': str(e)}
        violations = sum(len(s.get('violations', [])) for s in (erc.get('sheets') or []))
        sch_row = {'name': d['board'], 'board': d['board'], 'file': 'uno-shield.kicad_sch', 'sha256': __import__('hashlib').sha256(text.encode()).hexdigest(),
                  'format_version': W.FORMAT_VERSION, 'generator': 'polari_pcb', 'title': 'UNO Shield', 'sheets': 1,
                  'symbols': len(d['components']), 'power_symbols': report['power_symbols'], 'wires': 0, 'labels': report['labels'],
                  'junctions': 0, 'no_connects': 0, 'origin': 'rendered', 'licence_notes':
                  'our design (GPL-3.0 with the project); the KiCad library symbols it embeds are CC-BY-SA-4.0 with the design exception',
                  'notes': 'host %s sha %s' % (d['host'], d['host_sha'][:12])}
        self._upsert('Schematic', [sch_row])
        from pcb.custom.uno_shield import part_rows
        self._upsert('Part', part_rows(d))
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'board': d['board'], 'host': d['host'], 'components': len(d['components']),
                          'connections': len(report['connections']), 'unconnectedPins': len(report['unconnected_pins']),
                          'powerSymbols': report['power_symbols'], 'labels': report['labels'], 'ercViolations': violations,
                          'erc': erc, 'schematicText': text}

    # ---------------------------------------------------------------- artifacts
    def on_get_artifact(self, request, response, board, path):
        safe = os.path.normpath(path)
        if safe.startswith('..') or os.path.isabs(safe):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad artifact path'}
            return
        fp = os.path.join(_pcb_home(), board, 'artifacts', board, safe)
        if not os.path.isfile(fp):
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no artifact %s/%s (ingest the board first)' % (board, path)}
            return
        data = open(fp, 'rb').read()
        ext = fp.rsplit('.', 1)[-1].lower()
        response.content_type = {'svg': 'image/svg+xml', 'step': 'model/step', 'csv': 'text/csv', 'json': 'application/json',
                                 'net': 'text/plain'}.get(ext, 'application/octet-stream')
        response.data = data
