"""
@module hwmap.hwmap_api

POST /api/hwmap/ingest            a scanner snapshot (pol hwmap push) → rows replaced per device
GET  /api/hwmap                   snapshots (hardware-tier readiness per device)
GET  /api/hwmap/ports?device=     ports + slots of one device
GET  /api/hwmap/candidates?device=&app=   "what can be mapped to a potential KVM" — every port's
                                  verdict; with app=<hardware app> only the ports that satisfy
                                  that app's declared needs (and what is missing)
"""
import json
import time

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class HwmapAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/hwmap', self, suffix='list')
            add('/api/hwmap/ingest', self, suffix='ingest')
            add('/api/hwmap/ports', self, suffix='ports')
            add('/api/hwmap/candidates', self, suffix='candidates')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def _needs(self):
        out = {}
        for a in self._rows('HardwareAppDefinition'):
            try:
                n = json.loads(getattr(a, 'hardware_needs_json', '[]') or '[]')
            except ValueError:
                n = []
            if n:
                out[a.name] = n
        return out

    def _owners(self):
        owners = {}
        for d in self._rows('DeviceLink'):
            if getattr(d, 'owner', '') not in ('', 'host'):
                owners['%s:%s' % (d.usb_vendor_id, d.usb_product_id)] = d.owner
        return owners

    def _replace(self, class_name, cls, device, rows):
        table = (self.manager.objectTables or {}).get(class_name, {}) or {}
        for key, r in list(table.items()):
            if getattr(r, 'device_name', '') == device:
                try:
                    self.manager.db.deleteInstanceInDB(r) if hasattr(self.manager.db, 'deleteInstanceInDB') else None
                except Exception:  # noqa: BLE001
                    pass
                table.pop(key, None)
        n = 0
        for row in rows:
            obj = cls(manager=self.manager, **row)
            try:
                self.manager.db.saveInstanceInDB(obj); n += 1
            except Exception:  # noqa: BLE001
                pass
        return n

    def on_post_ingest(self, request, response):
        from hwmap.custom.mapping import build
        from hwmap.hwmap_basis import HardwareMapSnapshot, HardwarePort, HardwareSlot, PassthroughCandidate
        try:
            snap = json.loads(request.bounded_stream.read() or b'{}')
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return
        if not snap.get('device_name') or 'usb' not in snap:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'a scanner snapshot needs device_name + usb/pci/nics/serial (pol hwmap scan)'}
            return
        built = build(snap, self._owners(), self._needs())
        dev = snap['device_name']
        counts = {'snapshot': self._replace('HardwareMapSnapshot', HardwareMapSnapshot, dev, [built['snapshot']]),
                  'ports': self._replace('HardwarePort', HardwarePort, dev, built['ports']),
                  'slots': self._replace('HardwareSlot', HardwareSlot, dev, built['slots']),
                  'candidates': self._replace('PassthroughCandidate', PassthroughCandidate, dev, built['candidates'])}
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'device': dev, 'rows': counts, 'hardwareTierReady': built['snapshot']['hardware_tier_ready'],
                          'mappable': sum(1 for c in built['candidates'] if c['mappable'])}

    def on_get_list(self, request, response):
        response.media = {'ok': True, 'devices': [{'device': s.device_name, 'cpuVirt': s.cpu_virt, 'kvm': s.kvm_device, 'libvirt': s.libvirt,
                                                   'iommuGroups': s.iommu_groups, 'hardwareTierReady': s.hardware_tier_ready,
                                                   'usb': s.usb_ports, 'pci': s.pci_ports, 'nics': s.nics, 'serial': s.serial_ports,
                                                   'slots': s.slots, 'observedAt': s.observed_at} for s in self._rows('HardwareMapSnapshot')],
                          'note': 'a device with no snapshot has never run pol hwmap push; readiness = cpu virt + /dev/kvm + libvirt'}

    def on_get_ports(self, request, response):
        dev = request.get_param('device') or ''
        ports = [p for p in self._rows('HardwarePort') if not dev or p.device_name == dev]
        slots = [s for s in self._rows('HardwareSlot') if not dev or s.device_name == dev]
        response.media = {'ok': True, 'device': dev,
                          'ports': [{'port': p.name, 'kind': p.kind, 'role': p.role, 'id': p.port_id, 'description': p.description, 'driver': p.driver,
                                     'slot': p.slot, 'owner': p.owner, 'iommuGroup': p.iommu_group, 'byIdPath': p.by_id_path} for p in ports],
                          'slots': [{'slot': s.name, 'kind': s.kind, 'ports': '%d/%d used' % (s.ports_used, s.ports_total), 'speedMbps': s.speed_mbps, 'parent': s.parent} for s in slots]}

    def on_get_candidates(self, request, response):
        dev = request.get_param('device') or ''
        app = request.get_param('app') or ''
        cands = [c for c in self._rows('PassthroughCandidate') if not dev or c.device_name == dev]
        rows = []
        for c in cands:
            sat = json.loads(c.satisfies_json or '[]')
            if app and app not in sat:
                continue
            rows.append({'port': c.port, 'mapping': c.mapping, 'mappable': c.mappable, 'reasons': json.loads(c.reasons_json or '[]'),
                         'satisfies': sat, 'fragment': c.fragment, 'device': c.device_name})
        missing = []
        if app:
            needs = self._needs().get(app, [])
            if not needs:
                missing.append('%s declares no hardware needs (HardwareAppDefinition.hardware_needs_json)' % app)
            elif not any(r['mappable'] for r in rows):
                missing.append('no mappable port on %s satisfies %s: %s' % (dev or 'any scanned device', app, json.dumps(needs)))
        response.media = {'ok': True, 'device': dev, 'app': app, 'candidates': rows,
                          'mappable': sum(1 for r in rows if r['mappable']), 'missing': missing}
