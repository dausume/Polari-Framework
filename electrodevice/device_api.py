"""
@module electrodevice.device_api

Knob surface for material-derived electronic devices. All acts are
explicit: derive (run the material sim, stamp parameters), card
(version + download the SPICE abstraction), circuit-test (ngspice run
— pixels default to the LIVE LedMatrix4x4State row, so the test
evaluates what the FPGA is actually commanding right now).

@consumers
  - electrodevice.selftest_electrodevice (function level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.device_derive import (
    derive_device, get_device, make_card_row,
)
from electrodevice.spice_run import capability, run_led_grid


class ElectroDeviceAPI(treeObject):
    """Catalogue + derive/card/circuit-test acts."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/electrodevice'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/electrodevice/devices', self, suffix='devices')
            add('/api/electrodevice/devices/{name}', self,
                suffix='device')
            add('/api/electrodevice/devices/{name}/card', self,
                suffix='card')
            add('/api/electrodevice/capability', self,
                suffix='capability')

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def on_get_capability(self, request, response):
        response.media = capability()

    def on_get_devices(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        devices = []
        for row in (tables.get('ElectronicDeviceDefinition')
                    or {}).values():
            devices.append({
                'name': getattr(row, 'name', ''),
                'deviceType': getattr(row, 'device_type', ''),
                'simModel': getattr(row, 'sim_model', ''),
                'length_m': getattr(row, 'length_m', 0.0),
                'crossSection_m2': getattr(row, 'cross_section_m2',
                                           0.0),
                'sigma_S_per_m': getattr(row, 'sigma_s_per_m', 0.0),
                'resistance_ohm': getattr(row, 'resistance_ohm', 0.0),
                'derivedAt': getattr(row, 'derived_at', ''),
            })
        devices.sort(key=lambda d: d['name'])
        runs = [{
            'name': getattr(r, 'name', ''),
            'device': getattr(r, 'device_name', ''),
            'verdict': getattr(r, 'verdict', ''),
            'ranAt': getattr(r, 'ran_at', ''),
        } for r in (tables.get('CircuitRunResult') or {}).values()]
        runs.sort(key=lambda r: r['ranAt'], reverse=True)
        response.media = {'ok': True, 'devices': devices,
                          'recentRuns': runs[:10],
                          'capability': capability()}

    def on_post_device(self, request, response, name):
        """{action: derive | card | circuit-test, pixels?, vdd?,
        fromGrid?}."""
        try:
            raw = request.bounded_stream.read()
            payload = json.loads(raw) if raw else {}
        except Exception as e:
            return self._refuse(response, f'bad JSON payload: {e}')
        device = get_device(self.manager, name)
        if device is None:
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        action = payload.get('action', '')
        if action == 'derive':
            response.media = derive_device(self.manager, device)
            return
        if action == 'card':
            report = make_card_row(self.manager, device)
            report.pop('row', None)
            if not report.get('ok'):
                response.status = '400 Bad Request'
            response.media = report
            return
        if action == 'circuit-test':
            pixels = payload.get('pixels')
            if pixels is None:
                # Default: the LIVE grid state — the circuit test
                # evaluates what the FPGA is commanded to right now.
                grid_name = payload.get('fromGrid', 'renode-led-grid')
                tables = (getattr(self.manager, 'objectTables', None)
                          or {})
                grid = next(
                    (g for g in (tables.get('LedMatrix4x4State')
                                 or {}).values()
                     if getattr(g, 'name', '') == grid_name), None)
                if grid is None:
                    return self._refuse(
                        response,
                        f'no pixels given and no LED grid '
                        f'"{grid_name}" found')
                pixels = int(getattr(grid, 'pixels', 0))
            report = run_led_grid(self.manager, device, int(pixels),
                                  vdd=float(payload.get('vdd', 3.3)))
            if not report.get('ok'):
                response.status = '422 Unprocessable Entity'
            response.media = report
            return
        return self._refuse(
            response,
            f'unknown action "{action}" (derive | card | '
            'circuit-test)')

    def on_get_card(self, request, response, name):
        device = get_device(self.manager, name)
        if device is None:
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        from electrodevice.device_derive import render_card
        text = render_card(device)
        if text is None:
            return self._refuse(
                response,
                f'device "{name}" has never been derived — POST '
                '{"action": "derive"} first', '404 Not Found')
        response.content_type = 'text/plain; charset=utf-8'
        response.text = text
