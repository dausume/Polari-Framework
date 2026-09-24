"""
@module computelod.computelod_api

  GET /api/computelod                         the ladder: eleven rungs with kinds, owner, design_level_ref, status
  GET /api/computelod/rungs/{name}            one rung + its kinds + its concept node's prerequisites
  GET /api/computelod/walk/{rung}/{ref}?direction=down|up   one step through the mappings from a row
  GET /api/computelod/path?rung=&ref=&direction=            the chain end to end (a ref may hold '/', so query params)
  GET /api/computelod/lod1                                  the teaching path's committed report
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit

from computelod.custom.computelod_walk import ladder, walk, path


class ComputeLodAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/computelod'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/computelod', self)
            add('/api/computelod/rungs/{name}', self, suffix='rung')
            add('/api/computelod/walk/{rung}/{ref}', self, suffix='walk')
            add('/api/computelod/path', self, suffix='path')                 # lod-1: the chain, end to end (query params: a ref may hold '/')
            add('/api/computelod/lod1', self, suffix='lod1')                 # the teaching path's committed report
            add('/api/computelod/lod2', self, suffix='lod2')                 # open silicon: SKY130 mapping + OpenSTA timing
            add('/api/computelod/lod2/cnt', self, suffix='lod2_cnt')         # the second Liberty: our own CNT cell library
            add('/api/computelod/lod3', self, suffix='lod3')                 # cells → transistors → layout, read from the artefacts
            add('/api/computelod/lod4', self, suffix='lod4')                 # fabrication → materials, by reference

    def _rows(self, cls):
        return list((getattr(self.manager, 'objectTables', {}) or {}).get(cls, {}).values())

    def on_get(self, request, response):
        response.media = {'ok': True, 'ladder': ladder(self.manager),
                          'rule': 'ONE conceptual ladder; a KIND specializes within a rung and never creates one; die/package hang off microarchitecture through the microchip ladder (design_level_ref)'}

    def on_get_rung(self, request, response, name):
        r = next((x for x in ladder(self.manager) if x['name'] == name), None)
        if r is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no rung %r' % name}; return
        node = next((n for n in self._rows('TechNode') if str(n.name) == r['concept_node']), None)
        prereq = json.loads(getattr(node, 'depends_on_json', '[]') or '[]') if node is not None else []
        response.media = {'ok': True, 'rung': r, 'learn': {'concept_node': r['concept_node'], 'recommended_prerequisites': prereq,
                                                            'note': 'learning order ≠ implementation order (plan §7): these are tech-tree edges, the ladder is the other'}}

    def on_get_path(self, request, response):
        rung = (request.params.get('rung') or '').strip(); ref = (request.params.get('ref') or '').strip()
        if not rung or not ref:
            response.status = '400 Bad Request'; response.media = {'ok': False, 'error': 'path needs ?rung=<ComputeLOD.name>&ref=<the row at that rung>'}; return
        d = (request.params.get('direction') or 'down').strip()
        response.media = {'ok': True, 'path': path(self.manager, rung, ref, 'up' if d == 'up' else 'down')}

    def on_get_lod4(self, request, response):
        from computelod.custom.lod4_process import report
        rep = report()
        node = next((n for n in self._rows('SiliconProcessNode') if str(getattr(n, 'name', '')) == 'sky130'), None)
        response.media = {'ok': bool(rep), 'report': rep or {}, 'process_node_row': None if node is None else {'name': 'sky130', 'node_nm': getattr(node, 'node_nm', 0), 'vdd_v': getattr(node, 'vdd_v', 0),
                          'rights_class': getattr(node, 'rights_class', ''), 'fabrication_evidence': getattr(node, 'fabrication_evidence', ''), 'manufacturable': getattr(node, 'manufacturable', None),
                          'manufacturable_reason': getattr(node, 'manufacturable_reason', '')}, 'how_to_rerun': 'python3 -m computelod.custom.lod4_process run (a reading; nothing fetched)'}

    def on_get_lod3(self, request, response):
        from computelod.custom.lod3_cells import report
        rep = report()
        slim = None
        if rep:   # the per-device lists are large; the summary is the reading
            slim = {'adder': rep['adder'], 'sky130': {'source': rep['sky130']['source'], 'files': rep['sky130']['files'],
                                                     'cells': {k: {kk: vv for kk, vv in v.items() if kk != 'devices'} for k, v in rep['sky130']['cells'].items()}},
                    'cnt': {'cells': {k: {kk: vv for kk, vv in v.items() if kk != 'devices'} for k, v in rep['cnt']['cells'].items()}}, 'not_done': rep['not_done']}
        response.media = {'ok': bool(rep), 'report': slim or {}, 'how_to_rerun': 'python3 -m computelod.custom.lod3_cells run (fetches per-cell .spice/.lef from the pinned SKY130 cell repo into ~/.cache/polari-lod, never committed)'}

    def on_get_lod2_cnt(self, request, response):
        from computelod.custom.lod2_cnt import report
        rep = report()
        response.media = {'ok': bool(rep), 'report': rep or {}, 'how_to_rerun': 'python3 -m computelod.custom.lod2_cnt run (boots the server in-process from a throwaway cwd; ngspice + OpenVAF through the cntfet ladder, yosys via the tools image, OpenSTA via openroad/opensta; the Liberty is OURS and committed under initialData/lod2/cnt)'}

    def on_get_lod2(self, request, response):
        from computelod.custom.lod2_silicon import report
        rep = report()
        response.media = {'ok': bool(rep), 'report': rep or {}, 'how_to_rerun': 'python3 -m computelod.custom.lod2_silicon run (yosys via the tools image; OpenSTA via docker pull openroad/opensta; the SKY130 Liberty is fetched into ~/.cache/polari-lod at a pinned commit, never committed)'}

    def on_get_lod1(self, request, response):
        from computelod.custom.lod1_chain import report
        rep = report()
        response.media = {'ok': bool(rep), 'report': rep or {}, 'how_to_rerun': 'python3 -m computelod.custom.lod1_chain run (tools on the PATH, or docker build -t polari-computelod-tools:noble modules/computelod/custom/tools)',
                          'teaching_path': 'C c=a+b → GCC → add a0,a0,a1 = 0x00b50533 → PicoRV32 decode (picorv32.v:1068) + alu_add_sub (:1231) → rv32_add.v → yosys netlist → iverilog: RTL and gates agree'}

    def on_get_walk(self, request, response, rung, ref):
        d = (request.params.get('direction') or 'down').strip()
        response.media = {'ok': True, 'walk': walk(self.manager, rung, ref, 'up' if d == 'up' else 'down')}
