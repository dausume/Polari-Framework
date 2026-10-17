"""
@module board.register_profile_api

rp-0 (MISSION_PROFILE_SOLVER_PLAN.md §2.4): the register profile's two doors, DERIVED on every read from this server's rows
(Register, RegisterField, RegisterAddressMapping, MemoryRegion; the seed tables when a server holds none):

GET  /api/board/socs/{soc}/register-profile[?class=pin|peripheral|memory|cpu][&list=fields|classes]
        per register: its class (pin-configuration | peripheral-operation | memory-nvm | cpu-system, or `mixed`), the classes it
        touches, the fields_note (`fields not modelled` when no RegisterField rows), a reason and a citation; `rows` is the
        register table (or, with list=fields, one row per field with its own class, source, reason and citation); `totals`
        counts per class; `registers` carries the fields of every register.
GET  /api/board/socs/{soc}/memory-map[?board=B][&build=NAME][&text=&data=&bss=][&list=registers]
        per region (register file, I/O, extended I/O, SRAM, flash with its application and boot loader sections, EEPROM): start,
        end, size, address space, what lives there, citation, which registers live in it / control it and, with a build (a
        FirmwareBuild name, or text/data/bss) used vs available with the bootloader subtracted; `unmeasured` without one.
        With ?list=registers `rows` is one row per register with its region.

The routes sit under /api/board/socs/... - a literal `socs` segment beside the existing `/api/board/{board}/...` routes; the
selftest adds them on a real falcon.App next to every other board route (a clash raises UnacceptableRouteError at boot).
"""
import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class RegisterProfileAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/socs/{soc}/register-profile', self, suffix='register_profile')
            add('/api/board/socs/{soc}/memory-map', self, suffix='memory_map')

    def _tables(self):
        from board.custom import register_profile as RP
        t = RP.tables_from_manager(self.manager) if self.manager is not None else {}
        if not t.get('Register'):
            return RP.seed_tables()
        for cls in ('MemoryRegion', 'RegisterAddressMapping'):   # a server that has not converged the new rows yet: the code-owned seed
            if not t.get(cls):
                t[cls] = RP.seed_tables()[cls]
        return t

    def on_get_register_profile(self, request, response, soc):
        from board.custom import register_profile as RP
        cls = request.params.get('class')
        if cls:
            cls = RP.SHORT.get(cls, cls)
            if cls not in RP.CLASSES:
                response.status = falcon.HTTP_400
                response.media = {'ok': False, 'error': 'class is one of %s' % ', '.join(RP.SHORT)}
                return
        try:
            prof = RP.profile(self._tables(), RP._resolve_soc(soc))
        except KeyError as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': e.args[0]}
            return
        lst = request.params.get('list')
        rows = RP.field_rows(prof, cls) if lst == 'fields' else RP.class_rows(prof) if lst == 'classes' else RP.register_rows(prof, cls)
        response.media = {'ok': True, 'soc': prof['soc'], 'class': cls or '', 'list': lst or 'registers', 'count': len(rows), 'rows': rows,
                          'totals': prof['totals'], 'registers': prof['registers'], 'rules': prof['rules']}

    def on_get_memory_map(self, request, response, soc):
        from board.custom import memory_map_view as MV
        from board.custom import register_profile as RP
        p = request.params
        t = self._tables()
        build = None
        if p.get('build'):
            build = next((b for b in t.get('FirmwareBuild', []) if b.get('name') == p['build']), None)
            if build is None:
                response.status = falcon.HTTP_404
                response.media = {'ok': False, 'error': 'no FirmwareBuild named %s' % p['build']}
                return
        elif any(p.get(k) for k in ('text', 'data', 'bss')):
            try:
                build = {'name': 'sizes given in the request', 'size_text': int(p.get('text') or 0), 'size_data': int(p.get('data') or 0), 'size_bss': int(p.get('bss') or 0)}
            except ValueError:
                response.status = falcon.HTTP_400
                response.media = {'ok': False, 'error': 'text, data and bss are byte counts (integers)'}
                return
        try:
            mm = MV.memory_map(t, RP._resolve_soc(soc), board=p.get('board') or None, build=build)
        except KeyError as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': e.args[0]}
            return
        rows = MV.register_rows(mm) if p.get('list') == 'registers' else mm['regions']
        response.media = {'ok': True, 'soc': mm['soc'], 'board': mm['board'], 'list': p.get('list') or 'regions', 'count': len(rows), 'rows': rows, 'basis': mm['basis'],
                          'data_space': mm['data_space'], 'overlaps': mm['overlaps'], 'firmware_use': mm['firmware_use'], 'boot': mm['boot'], 'controls': mm['controls']}
