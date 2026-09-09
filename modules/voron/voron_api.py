"""
@module voron.voron_api

/api/voron/summary             printers + boards + mode + guest readiness (guest row exists; every real-mode USB board measured)
/api/voron/render/{printer}    printer.cfg + the provisioner verdict for one printer (what the guest's provisioner is rendered from)
"""
import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class VoronAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/voron/summary', self, suffix='summary')
            add('/api/voron/render/{printer}', self, suffix='render')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def _boards(self, printer_name):
        return [b for b in self._rows('PrinterBoard') if getattr(b, 'printer', '') == printer_name]

    def _guest(self, printer):
        """The HardwareAppDefinition row the printer names, or the module's own
        seed dict when the row is not (yet) in the tables — the render says which."""
        from voron.voron_basis import SEED_VORON_HARDWARE_APPS
        for a in self._rows('HardwareAppDefinition'):
            if getattr(a, 'name', '') == printer.hardware_app:
                return {k: getattr(a, k, '') for k in SEED_VORON_HARDWARE_APPS[0]}, 'row'
        for a in SEED_VORON_HARDWARE_APPS:
            if a['name'] == printer.hardware_app:
                return dict(a), 'seed'
        return None, 'missing'

    @staticmethod
    def _board_view(b):
        return {'name': b.name, 'role': b.role, 'model': b.model, 'mcu': b.mcu_name, 'connection': b.connection,
                'serialById': b.serial_by_id, 'canbusUuid': b.canbus_uuid, 'firmwareFlashed': b.firmware_flashed,
                'measured': (b.connection != 'usb' or bool(b.serial_by_id)) and (b.connection != 'canbus' or bool(b.canbus_uuid))}

    def on_get_summary(self, request, response):
        out = []
        for p in self._rows('PrinterDefinition'):
            boards = self._boards(p.name)
            guest, source = self._guest(p)
            unmeasured = [b.name for b in boards if p.mode == 'real' and b.connection == 'usb' and not b.serial_by_id]
            out.append({'printer': p.name, 'model': p.model, 'mode': p.mode, 'bedMm': '%sx%sx%s' % (p.bed_x_mm, p.bed_y_mm, p.bed_z_mm),
                        'probe': p.probe, 'guest': p.hardware_app, 'guestDefined': source == 'row', 'guestSource': source,
                        'imagePinned': bool(guest and guest.get('image_sha256_raw')), 'boards': len(boards),
                        'usbBoardsMeasured': not unmeasured, 'unmeasured': unmeasured,
                        'ready': source == 'row' and not unmeasured and bool(guest.get('image_sha256_raw'))})
        response.media = {'ok': True, 'printers': out, 'boards': [self._board_view(b) for b in self._rows('PrinterBoard')],
                          'states': len(self._rows('PrinterState')),
                          'note': 'printer.cfg + provisioner verdicts: /api/voron/render/<printer>; the guest domain XML: '
                                  '/api/hardwareapps/render/voron-printer; the isle applies both with isle vm'}

    def on_get_render(self, request, response, printer):
        from voron.custom.printer_cfg import render_printer_cfg
        from voron.custom.provision import render_provision
        p = next((r for r in self._rows('PrinterDefinition') if getattr(r, 'name', '') == printer), None)
        if p is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no PrinterDefinition %r' % printer}
            return
        boards = self._boards(p.name)
        cfg, refusals = render_printer_cfg(p, boards)
        guest, source = self._guest(p)
        if guest is None:
            prov_refusals = ['no HardwareAppDefinition %r (seed SEED_VORON_HARDWARE_APPS or define the guest)' % p.hardware_app]
        else:
            _, prov_refusals = render_provision(dict(guest, printer=p, boards=boards,
                                                     allow_unpinned=request.get_param_as_bool('allow_unpinned') or False))
        response.media = {'ok': not (refusals or prov_refusals), 'printer': p.name, 'mode': p.mode, 'model': p.model,
                          'printerCfg': cfg, 'refusals': refusals, 'provisionRefusals': prov_refusals,
                          'guest': p.hardware_app, 'guestSource': source, 'boards': [self._board_view(b) for b in boards]}
