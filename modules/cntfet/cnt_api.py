"""
@module cntfet.cnt_api

Knob surface for the S1 aligned-CNT FET. Explicit acts only:
derive | iv (engine vs|tob) | calibrate | validate | equivalence;
GET capability (the D14 honest report), GET verilog-a (the
generated twin source).

@consumers
  - polariServer (route registration, gated on feature presence)
  - cntfet.selftest_cntfet (function level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_calibration import (
    calibrate_device, seed_anchor_rows,
)
from cntfet.cnt_capability import capability
from cntfet.cnt_derive import derive_device, get_row, run_iv
from cntfet.cnt_validate import validate
from cntfet.cnt_verilog_a import generate_va


class CNTFETAPI(treeObject):
    """Catalogue + the S1 acts."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/cntfet'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/cntfet/capability', self, suffix='capability')
            add('/api/cntfet/citations', self, suffix='citations')
            add('/api/cntfet/devices', self, suffix='devices')
            add('/api/cntfet/devices/{name}', self, suffix='device')
            add('/api/cntfet/devices/{name}/verilog-a', self,
                suffix='verilog_a')
            # fet-viz: per-device curve feeds + characterization
            # (per-object surfaces — any display row points here).
            add('/api/cntfet/device/{name}/points', self,
                suffix='device_points')
            add('/api/cntfet/device/{name}/characterization',
                self, suffix='device_characterization')
            # fi-0: operating states + the criteria that qualify a
            # bias point (FET_INTUITION_PLAN).
            add('/api/cntfet/device/{name}/states', self,
                suffix='device_states')
            add('/api/cntfet/figures', self, suffix='figures')
            add('/api/cntfet/figures/{figure_id}', self,
                suffix='figure')
            add('/api/cntfet/figures/{figure_id}/points', self,
                suffix='figure_points')
            add('/api/cntfet/cell-library', self,
                suffix='cell_library')

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def on_get_capability(self, request, response):
        response.media = capability()

    def on_get_cell_library(self, request, response):
        from cntfet.cnt_cell_library import library_report
        response.media = library_report()

    def on_get_figures(self, request, response):
        from cntfet.cnt_figures import figures_index
        response.media = figures_index()

    def on_get_figure(self, request, response, figure_id):
        from cntfet.cnt_figures import build_figure
        report = build_figure(figure_id, manager=self.manager)
        if not report.get('ok'):
            response.status = ('404 Not Found'
                               if 'error' in report
                               else '503 Service Unavailable')
        response.media = report

    def on_get_figure_points(self, request, response, figure_id):
        from cntfet.cnt_figures import figure_points
        report = figure_points(figure_id, manager=self.manager)
        if not report.get('ok'):
            response.status = ('404 Not Found'
                               if 'error' in report
                               else '503 Service Unavailable')
        response.media = report

    def on_get_citations(self, request, response):
        from cntfet.cnt_citations import citations_report
        response.media = citations_report(self.manager)

    def on_get_devices(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        devices = []
        for row in (tables.get('AlignedCNTFETDevice')
                    or {}).values():
            devices.append({
                'name': getattr(row, 'name', ''),
                'polarity': getattr(row, 'polarity', ''),
                'material': getattr(row, 'material', ''),
                'geometry': getattr(row, 'geometry', ''),
                'gateStack': getattr(row, 'gate_stack', ''),
                'contact': getattr(row, 'contact', ''),
                'temperatureK': getattr(row, 'temperature_k', 0.0),
                'manufacturingRegime': getattr(
                    row, 'manufacturing_regime', ''),
                'derivedAt': getattr(row, 'derived_at', ''),
            })
        devices.sort(key=lambda d: d['name'])
        results = [{
            'name': getattr(r, 'name', ''),
            'device': getattr(r, 'device', ''),
            'kind': getattr(r, 'kind', ''),
            'verdict': getattr(r, 'verdict', ''),
            'ranAt': getattr(r, 'ran_at', ''),
        } for r in (tables.get('CNTFETSimResult') or {}).values()]
        results.sort(key=lambda r: r['ranAt'], reverse=True)
        response.media = {'ok': True, 'devices': devices,
                          'recentResults': results[:10],
                          'capability': capability()}

    def on_get_device_points(self, request, response, name):
        from cntfet.cnt_device_viz import device_curve_points
        try:
            vd = float(request.get_param('vd') or 0.6)
        except ValueError:
            self._refuse(response, 'vd must be numeric')
            return
        report = device_curve_points(
            self.manager, name,
            curve=request.get_param('curve') or 'transfer', vd=vd)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_device_characterization(self, request, response,
                                       name):
        from cntfet.cnt_device_viz import device_characterization
        report = device_characterization(self.manager, name)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_device_states(self, request, response, name):
        """?vd= (default 0.6) ?vg= (optional point) ?direction=
        rising|falling ?vov_decades= ?vdsat_criterion=model|textbook
        — knobs echoed in the payload."""
        from cntfet.cnt_device_viz import device_model
        from cntfet.cnt_states import device_states_report
        id_fn, p, device, refusal = device_model(self.manager, name)
        if refusal is not None:
            response.status = '422 Unprocessable Entity'
            response.media = refusal
            return
        knobs = {}
        try:
            vd = float(request.get_param('vd') or 0.6)
            vg_raw = request.get_param('vg')
            vg = float(vg_raw) if vg_raw not in (None, '') else None
            if request.get_param('vov_decades'):
                knobs['vov_decades'] = float(
                    request.get_param('vov_decades'))
        except ValueError as exc:
            self._refuse(response, f'bad numeric parameter: {exc}')
            return
        crit = request.get_param('vdsat_criterion')
        if crit:
            if crit not in ('model', 'textbook'):
                self._refuse(response, 'vdsat_criterion must be '
                                       'model | textbook')
                return
            knobs['vdsat_criterion'] = crit
        direction = request.get_param('direction') or 'rising'
        if direction not in ('rising', 'falling'):
            self._refuse(response, 'direction must be rising | falling')
            return
        response.media = device_states_report(
            p, device, vds_v=vd, vgs_v=vg, direction=direction,
            knobs=knobs, manager=self.manager)

    def on_get_verilog_a(self, request, response, name):
        device = get_row(self.manager, 'AlignedCNTFETDevice', name)
        if device is None:
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        response.content_type = 'text/plain; charset=utf-8'
        response.text = generate_va()

    def on_post_device(self, request, response, name):
        """{action: derive | iv | calibrate | validate |
        equivalence, engine?, vg?, vd?, transmissionMode?}."""
        try:
            raw = request.bounded_stream.read()
            payload = json.loads(raw) if raw else {}
        except Exception as e:
            return self._refuse(response, f'bad JSON payload: {e}')
        device = get_row(self.manager, 'AlignedCNTFETDevice', name)
        if device is None:
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        action = payload.get('action', '')
        if action == 'derive':
            response.media = derive_device(self.manager, device)
            return
        if action == 'iv':
            report = run_iv(
                self.manager, device,
                engine=payload.get('engine', 'vs'),
                vg_list=payload.get('vg'),
                vd_list=payload.get('vd'),
                transmission_mode=payload.get('transmissionMode',
                                              'acoustic-mfp'),
                profile=payload.get('profile', 'VS_MINIMAL'))
            if not report.get('ok'):
                response.status = '422 Unprocessable Entity'
            response.media = report
            return
        if action == 'calibrate':
            from cntfet.cnt_basis import CNTCalibrationAnchor
            seed_anchor_rows(self.manager, CNTCalibrationAnchor)
            report = calibrate_device(self.manager, device)
            if not report.get('ok'):
                response.status = '422 Unprocessable Entity'
            response.media = report
            return
        if action == 'validate':
            response.media = validate(self.manager, device)
            return
        if action == 'f3-oracle':
            from cntfet.cnt_kwant import f3_oracle
            report = f3_oracle(
                self.manager, device,
                bias_points=payload.get('biasPoints'),
                energy_points=int(payload.get('energyPoints',
                                              60)),
                scf=payload.get('scf'))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'characterize-cells':
            from cntfet.cnt_cell_library import characterize_cells
            report = characterize_cells(
                self.manager, device,
                cells=payload.get('cells'),
                drives=tuple(payload.get('drives', [1])),
                vdd=float(payload.get('vdd', 0.6)))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'characterize-sequential':
            from cntfet.cnt_sequential import characterize_sequential
            report = characterize_sequential(
                self.manager, device,
                vdd=float(payload.get('vdd', 0.6)),
                executor=payload.get('executor', 'polari-own-loop'),
                iters=int(payload.get('iters', 6)))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'd11-crosscheck':
            from cntfet.cnt_cell_library import d11_crosscheck
            report = d11_crosscheck(
                self.manager, device,
                vdd=float(payload.get('vdd', 0.6)))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'characterize':
            from cntfet.cnt_characterization import (
                characterize_inverter,
            )
            report = characterize_inverter(
                self.manager, device,
                vdd=float(payload.get('vdd', 0.6)))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'cells':
            from cntfet.cnt_cells import run_cell_battery
            report = run_cell_battery(
                self.manager, device,
                vdd=float(payload.get('vdd', 0.6)))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'ring-oscillator':
            from cntfet.cnt_ring_oscillator import (
                run_ring_oscillator,
            )
            report = run_ring_oscillator(
                self.manager, device,
                vdd=float(payload.get('vdd', 0.6)),
                stages=int(payload.get('stages', 5)))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'inverter':
            from cntfet.cnt_inverter import run_inverter_vtc
            report = run_inverter_vtc(
                self.manager, device,
                vdd=float(payload.get('vdd', 0.6)))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'montecarlo':
            from cntfet.cnt_montecarlo import monte_carlo
            report = monte_carlo(
                self.manager, device,
                sample_count=int(payload.get('samples', 200)),
                seed=int(payload.get('seed', 1)),
                criteria=payload.get('criteria'))
            if not report.get('ok'):
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'triangle':
            from cntfet.cnt_triangle import validation_triangle
            report = validation_triangle(
                self.manager, device,
                vg_list=payload.get('vg'),
                vd_list=payload.get('vd'),
                transmission_mode=payload.get('transmissionMode',
                                              'acoustic-mfp'))
            if not report.get('ok'):
                response.status = '422 Unprocessable Entity'
            response.media = report
            return
        if action == 'equivalence':
            report = self._equivalence(device)
            if not report.get('ok'):
                response.status = ('422 Unprocessable Entity'
                                   if 'refusal' not in report
                                   else '503 Service Unavailable')
            response.media = report
            return
        return self._refuse(
            response,
            f'unknown action "{action}" (derive | iv | calibrate '
            '| validate | triangle | montecarlo | equivalence)')

    def _equivalence(self, device):
        """Build the {Lg, d, T, Rc} variant spread around the
        device and run the D3 regression; persist the verdict."""
        from cntfet.cnt_derive import resolve_components
        from cntfet.cnt_osdi import equivalence_regression
        from cntfet.cnt_vs_model import build_vs_params
        if not getattr(device, 'derived_at', ''):
            return {'ok': False, 'error': 'device never derived — '
                    'POST {"action": "derive"} first'}
        rows, missing = resolve_components(self.manager, device)
        if missing:
            return {'ok': False,
                    'error': f'missing components: {missing}'}
        mat, geo = rows['material'], rows['geometry']
        gate, contact = rows['gate_stack'], rows['contact']
        transport = rows['transport']

        def params(lg_nm=None, d_nm=None, t_k=None, rc=None):
            from cntfet.cnt_bandstructure import eg_ev
            d_use = d_nm if d_nm is not None else mat.diameter_nm
            return build_vs_params(
                {'diameter_nm': d_use, 'eg_ev': eg_ev(d_use)},
                {'lg_nm': lg_nm if lg_nm is not None
                 else geo.lg_nm},
                {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
                {'rc_ohm': rc if rc is not None
                 else contact.rc_ohm},
                {'vt0_v': transport.vt0_v,
                 'efsd_ev': transport.efsd_ev},
                t_k if t_k is not None else device.temperature_k)
        variants = {
            'base': params(),
            'lg-300nm': params(lg_nm=300.0),
            'd-1.0nm': params(d_nm=1.018),  # (13,0)
            't-350k': params(t_k=350.0),
            'rc-20k': params(rc=20000.0),
        }
        report = equivalence_regression(variants)
        if 'refusal' in report:
            return report
        # Persist the verdict as a result row.
        from datetime import datetime, timezone
        from cntfet.cnt_basis import CNTFETSimResult
        stamp = datetime.now(timezone.utc).isoformat()
        row = CNTFETSimResult(
            name=f'{device.name}-equivalence-'
                 f'{stamp[11:19].replace(":", "")}',
            device=device.name, kind='equivalence',
            engine='python-reference vs openvaf-osdi-ngspice',
            physics_fidelity='VS_MINIMAL',
            inputs_json=json.dumps(
                {'variants': list(variants)}),
            series_json='[]',
            metrics_json=json.dumps({
                'pointsChecked': report['pointsChecked'],
                'worst': report['worst'],
                'toleranceRel': report['toleranceRel'],
                'toleranceAbs': report['toleranceAbs']}),
            verdict=report['verdict'], ran_at=stamp,
            notes=f"bundle: {report.get('bundleDir', '')}",
            manager=self.manager)
        try:
            db = getattr(self.manager, 'db', None)
            if db is not None:
                db.saveInstanceInDB(row)
        except Exception:
            pass
        report['resultRow'] = row.name
        return report
