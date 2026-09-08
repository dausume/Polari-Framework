"""
@module electrodevice.device_api

Knob surface for material-derived electronic devices. All acts are
explicit: derive (run the material sim, stamp parameters), card
(version + download the SPICE abstraction), circuit-test (ngspice run
— pixels default to the LIVE LedMatrix4x4State row, so the test
evaluates what the FPGA is actually commanding right now).

@consumers
  - electrodevice.electrodevice_selftest (function level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.custom.device_derive import (
    derive_device, get_device, make_card_row,
)
from electrodevice.device_validator_basis import validate
from electrodevice.semiconductor_basis import (
    derive_semiconductor, get_profile,
)
from electrodevice.custom.spice_run import (
    capability, run_led_grid, run_led_switch,
)


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
            add('/api/electrodevice/semiconductors', self,
                suffix='semiconductors')
            add('/api/electrodevice/semiconductors/{name}', self,
                suffix='semiconductor')
            add('/api/electrodevice/photo/{name}', self,
                suffix='photo')
            add('/api/electrodevice/solar/{name}', self,
                suffix='solar')

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
        if action == 'validate':
            report = validate(self.manager, device, 'transistor'
                              if device.device_type in ('nfet',
                                                        'pfet')
                              else 'device')
            response.media = report
            return
        if action == 'switch-test':
            # The proof-of-concept micro-circuit: inverter + switch.
            names = {
                'pfet': payload.get('pfet', 'cnt-pfet-inverter'),
                'nfet': payload.get('nfet', 'cnt-nfet-led-switch'),
                'resistor': payload.get('resistor',
                                        'cnt-solgel-led-resistor'),
            }
            parts = {k: get_device(self.manager, v)
                     for k, v in names.items()}
            missing = [v for k, v in names.items()
                       if parts[k] is None]
            if missing:
                return self._refuse(response,
                                    f'missing devices: {missing}')
            report = run_led_switch(
                self.manager, device, parts['pfet'], parts['nfet'],
                parts['resistor'],
                vdd=float(payload.get('vdd', 3.3)))
            if not report.get('ok'):
                response.status = '422 Unprocessable Entity'
            response.media = report
            return
        if action == 'switching-analysis':
            from electrodevice.custom.switching import run_switching_analysis
            report = run_switching_analysis(
                self.manager, device,
                rdrv_ohm=float(payload.get('rdrvOhm', 33.0)),
                cload_f=float(payload.get('cloadF', 1e-11)),
                vdd=float(payload.get('vdd', 3.3)))
            if not report.get('ok'):
                response.status = '422 Unprocessable Entity'
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
            'circuit-test | switch-test | validate | '
            'switching-analysis)')

    def on_get_semiconductors(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        profiles = [{
            'name': getattr(r, 'name', ''),
            'material': getattr(r, 'material', ''),
            'variant': getattr(r, 'variant', ''),
            'gapEv': getattr(r, 'gap_ev', 0.0),
            'carrierType': getattr(r, 'carrier_type', ''),
            'levelShiftEv': getattr(r, 'level_shift_ev', 0.0),
            'derivedAt': getattr(r, 'derived_at', ''),
        } for r in (tables.get('SemiconductorProfile')
                    or {}).values()]
        profiles.sort(key=lambda x: x['name'])
        response.media = {'ok': True, 'profiles': profiles}

    def on_post_semiconductor(self, request, response, name):
        """{action: derive | validate}."""
        try:
            raw = request.bounded_stream.read()
            payload = json.loads(raw) if raw else {}
        except Exception as e:
            return self._refuse(response, f'bad JSON payload: {e}')
        profile = get_profile(self.manager, name)
        if profile is None:
            return self._refuse(response, f'no profile "{name}"',
                                '404 Not Found')
        action = payload.get('action', '')
        if action == 'derive':
            response.media = derive_semiconductor(self.manager,
                                                  profile)
            return
        if action == 'validate':
            response.media = validate(self.manager, profile,
                                      'semiconductor')
            return
        return self._refuse(response,
                            f'unknown action "{action}" (derive | '
                            'validate)')

    def on_post_photo(self, request, response, name):
        """{action: tune} — run the candidate ladder, pick the
        best absorption-edge match for the target wavelength."""
        try:
            raw = request.bounded_stream.read()
            payload = json.loads(raw) if raw else {}
        except Exception as e:
            return self._refuse(response, f'bad JSON payload: {e}')
        from electrodevice.custom.photo_derive import (get_absorber,
                                                tune_absorber)
        absorber = get_absorber(self.manager, name)
        if absorber is None:
            return self._refuse(response, f'no absorber "{name}"',
                                '404 Not Found')
        if payload.get('action') != 'tune':
            return self._refuse(response, 'action must be "tune"')
        if payload.get('targetWavelengthNm'):
            absorber.target_wavelength_nm = float(
                payload['targetWavelengthNm'])
        report = tune_absorber(self.manager, absorber)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_post_solar(self, request, response, name):
        """{action: optimize} — rank absorbers by blackbody
        ultimate efficiency, stamp the stack."""
        try:
            raw = request.bounded_stream.read()
            payload = json.loads(raw) if raw else {}
        except Exception as e:
            return self._refuse(response, f'bad JSON payload: {e}')
        from electrodevice.custom.photo_derive import (get_stack,
                                                optimize_stack)
        stack = get_stack(self.manager, name)
        if stack is None:
            return self._refuse(response, f'no stack "{name}"',
                                '404 Not Found')
        if payload.get('action') != 'optimize':
            return self._refuse(response, 'action must be '
                                          '"optimize"')
        report = optimize_stack(self.manager, stack)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_card(self, request, response, name):
        device = get_device(self.manager, name)
        if device is None:
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        from electrodevice.custom.device_derive import render_card
        text = render_card(device)
        if text is None:
            return self._refuse(
                response,
                f'device "{name}" has never been derived — POST '
                '{"action": "derive"} first', '404 Not Found')
        response.content_type = 'text/plain; charset=utf-8'
        response.text = text
