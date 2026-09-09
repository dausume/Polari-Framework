"""
@module hardwareapps.hardwareapps_api

/api/hardwareapps                   the definitions with their render verdicts
/api/hardwareapps/render/{name}     the domain XML + UCI script for one app (what `isle vm define --from-polari` fetches)
/api/hardwareapps/state             the twins
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class HardwareAppsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/hardwareapps', self, suffix='list')
            add('/api/hardwareapps/render/{name}', self, suffix='render')
            add('/api/hardwareapps/state', self, suffix='state')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def _passthrough(self, defn):
        """Resolve passthrough_json names against DeviceLink rows (USB) or
        treat them as host NIC names — never invent vendor ids."""
        try:
            names = json.loads(getattr(defn, 'passthrough_json', '[]') or '[]')
        except ValueError:
            names = []
        links = {getattr(r, 'name', ''): r for r in self._rows('DeviceLink')}
        out, missing = [], []
        for n in names:
            r = links.get(n)
            if r is not None and getattr(r, 'usb_vendor_id', ''):
                out.append({'kind': 'usb', 'vendor_id': r.usb_vendor_id, 'product_id': r.usb_product_id, 'description': n, 'owner': getattr(r, 'owner', '')})
            elif r is None and n.startswith(('eth', 'enp', 'wl')):
                out.append({'kind': 'nic', 'interface': n})
            else:
                missing.append(n)
        return out, missing

    def _provision(self, defn):
        """Non-OpenWrt guests render a shell provisioner through the dotted
        'module.path:function' the row names; the function receives the
        row as a dict plus whatever the owning module adds (the voron
        module passes its printer + boards). Absent = no script."""
        dotted = getattr(defn, 'provisioner', '') or ''
        if not dotted:
            return '', []
        try:
            import importlib
            mod, fn = dotted.split(':')
            render = getattr(importlib.import_module(mod), fn)
        except Exception as e:  # noqa: BLE001
            return '', ['provisioner %r not importable: %s' % (dotted, str(e)[:80])]
        payload = {k: getattr(defn, k) for k in vars(defn) if not k.startswith('_') and k != 'manager'}
        # the provisioner's module may add context from rows (the voron module
        # adds its printer + boards): `provision_context(manager, payload)`
        ctx = getattr(importlib.import_module(mod), 'provision_context', None)
        if callable(ctx):
            try:
                payload.update(ctx(self.manager, payload) or {})
            except Exception as e:  # noqa: BLE001
                return '', ['provision_context raised: %s' % str(e)[:120]]
        try:
            return render(payload)
        except Exception as e:  # noqa: BLE001
            return '', ['provisioner raised: %s' % str(e)[:120]]

    def _render(self, defn):
        from hardwareapps.custom.domain_xml import render_domain
        from hardwareapps.custom.uci_profiles import render_uci
        pt, missing = self._passthrough(defn)
        xml, refusals = render_domain(defn, pt)
        uci, uci_refusals = render_uci(defn) if getattr(defn, 'uci_profile', '') else ('', [])
        prov, prov_refusals = self._provision(defn)
        owned = [p['description'] for p in pt if p.get('owner') and p['owner'] not in ('', 'host', defn.name)]
        if owned:
            refusals.append('passthrough device(s) owned by another VM: %s (passthrough is exclusive)' % ', '.join(owned))
        if missing:
            refusals.append('passthrough name(s) not a DeviceLink row nor a host NIC: %s' % ', '.join(missing))
        return {'name': defn.name, 'kind': defn.kind, 'role': defn.role, 'extends': defn.extends,
                'domainXml': xml, 'uciScript': uci, 'provisionScript': prov, 'passthrough': pt,
                'needs': json.loads(getattr(defn, 'hardware_needs_json', '[]') or '[]'),
                'refusals': refusals + uci_refusals + prov_refusals, 'ok': not (refusals or uci_refusals or prov_refusals),
                'requiresTier': defn.requires_tier, 'image': {'ref': defn.vm_image_ref, 'sha256Raw': defn.image_sha256_raw}}

    def on_get_list(self, request, response):
        apps = []
        for d in self._rows('HardwareAppDefinition'):
            r = self._render(d)
            apps.append({k: r[k] for k in ('name', 'kind', 'role', 'extends', 'ok', 'refusals', 'requiresTier', 'image')})
        response.media = {'ok': True, 'apps': apps,
                          'note': 'the router is a hardware app woven into the isle and is not listed; isle vm applies what /render returns'}

    def on_get_render(self, request, response, name):
        for d in self._rows('HardwareAppDefinition'):
            if getattr(d, 'name', '') == name:
                response.media = self._render(d)
                return
        response.status = falcon.HTTP_404
        response.media = {'ok': False, 'error': 'no HardwareAppDefinition %r' % name}

    def on_get_state(self, request, response):
        response.media = {'ok': True, 'states': [{'app': s.app, 'device': s.device_name, 'vmState': s.vm_state, 'ip': s.ip,
                                                  'uptimeS': s.uptime_s, 'probeOk': s.probe_ok, 'observedAt': s.observed_at, 'isMock': s.is_mock}
                                                 for s in self._rows('HardwareAppState')]}
