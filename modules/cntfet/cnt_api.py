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
            # fi-2/fi-3: scoring by characteristic equations (+ MC
            # best/worst case) and the cell-library scores.
            add('/api/cntfet/device/{name}/score', self,
                suffix='device_score')
            add('/api/cntfet/device/{name}/cell-scores', self,
                suffix='device_cell_scores')
            # fi-4: competitive ranking against every other FET.
            add('/api/cntfet/device/{name}/compare', self,
                suffix='device_compare')
            # fv arc: regimes (fv-1), transport (fv-2), the
            # characteristic registry (fv-3), device fields (fv-4).
            add('/api/cntfet/device/{name}/regimes', self,
                suffix='device_regimes')
            add('/api/cntfet/device/{name}/transport', self,
                suffix='device_transport')
            add('/api/cntfet/device/{name}/characteristics', self,
                suffix='device_characteristics')
            add('/api/cntfet/device/{name}/characteristic/{key}',
                self, suffix='device_characteristic')
            add('/api/cntfet/device/{name}/fields', self,
                suffix='device_fields')
            # fp-6: the weave — every page / partner / cell this FET
            # is connected to, as data the nav rows render.
            add('/api/cntfet/device/{name}/links', self,
                suffix='device_links')
            # fp arc: power (fp-1), taxonomy + signal score (fp-3),
            # cell logic / circuit diagrams (fp-5).
            add('/api/cntfet/device/{name}/power', self,
                suffix='device_power')
            add('/api/cntfet/device/{name}/cell-power', self,
                suffix='device_cell_power')
            add('/api/cntfet/device/{name}/taxonomy', self,
                suffix='device_taxonomy')
            add('/api/cntfet/device/{name}/signal-score', self,
                suffix='device_signal_score')
            add('/api/cntfet/cell/{cell}/logic', self,
                suffix='cell_logic')
            add('/api/cntfet/cells/logic', self, suffix='cells_logic')
            # cells wrap-up: which FET runs give which cells their data
            add('/api/cntfet/cells/coverage', self,
                suffix='cells_coverage')
            # open library: proven-free cells on proven-free devices.
            add('/api/cntfet/open-library', self, suffix='open_libraries')
            add('/api/cntfet/open-library/{lib}', self,
                suffix='open_library')
            add('/api/cntfet/open-library/{lib}/liberty', self,
                suffix='open_library_liberty')
            # functional blocks (ladder rank 3) composed from cells.
            add('/api/cntfet/blocks', self, suffix='blocks')
            add('/api/cntfet/block/{key}', self, suffix='block')
            add('/api/cntfet/block/{key}/proof', self,
                suffix='block_proof')
            add('/api/cntfet/block/{key}/logic', self,
                suffix='block_logic')
            add('/api/cntfet/block/{key}/power', self,
                suffix='block_power')
            add('/api/cntfet/device/{name}/cell-coverage', self,
                suffix='device_cell_coverage')
            # ip: licensing / freedom-to-operate records per technology
            # (tracked like everything else; engineering record, not
            # legal advice — every payload says so).
            add('/api/cntfet/device/{name}/ip', self, suffix='device_ip')
            add('/api/cntfet/ip', self, suffix='library_ip')
            # evidence: first-class patents / publications / licences and
            # the proof-of-freedom chain per FET / cell / route (US).
            add('/api/cntfet/device/{name}/proof', self,
                suffix='device_proof')
            add('/api/cntfet/cell/{cell}/proof', self, suffix='cell_proof')
            add('/api/cntfet/proof', self, suffix='library_proof')
            add('/api/cntfet/evidence', self, suffix='evidence_index')
            add('/api/cntfet/evidence/{item}', self,
                suffix='evidence_detail')
            # fp-2 / fp-4: silicon FETs on sol-gel + silicon refinement
            # (the sifet module rides this API class — same server).
            add('/api/sifet/capability', self, suffix='si_capability')
            add('/api/sifet/devices', self, suffix='si_devices')
            add('/api/sifet/devices/{name}', self, suffix='si_device')
            add('/api/sifet/refinement', self, suffix='si_refinement')
            add('/api/sifet/refinement/{route}', self,
                suffix='si_refinement_route')
            add('/api/sifet/refinement/{route}/points', self,
                suffix='si_refinement_points')
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
        """?curve= ?vd= ?samples= (fi-3 MC count behind score-terms /
        transfer-envelope; 0 = nominal only) ?seed="""
        from cntfet.cnt_device_viz import (
            DEFAULT_MC_SAMPLES, device_curve_points,
        )
        try:
            vd = float(request.get_param('vd') or 0.6)
            samples = int(request.get_param('samples')
                          or DEFAULT_MC_SAMPLES)
            seed = int(request.get_param('seed') or 1)
        except ValueError:
            self._refuse(response, 'vd/samples/seed must be numeric')
            return
        report = device_curve_points(
            self.manager, name,
            curve=request.get_param('curve') or 'transfer', vd=vd,
            samples=max(0, min(samples, 2000)), seed=seed)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_device_score(self, request, response, name):
        """fi-2: the device scored by its characteristic equations.
        ?samples= (default 0) adds the fi-3 Monte Carlo best/worst
        case + score quantiles; ?vt_definition=model|constant-current
        ?off_decades= ?vov_decades= ?g_on_target_over_g0= are the
        scoring knobs (echoed)."""
        from cntfet.cnt_scoring import score_device
        knobs = {}
        try:
            for key in ('off_decades', 'vov_decades',
                        'g_on_target_over_g0'):
                if request.get_param(key):
                    knobs[key] = float(request.get_param(key))
            samples = int(request.get_param('samples') or 0)
            seed = int(request.get_param('seed') or 1)
        except ValueError as exc:
            self._refuse(response, f'bad numeric parameter: {exc}')
            return
        vt_def = request.get_param('vt_definition')
        if vt_def:
            if vt_def not in ('model', 'constant-current'):
                self._refuse(response, 'vt_definition must be model '
                                       '| constant-current')
                return
            knobs['vt_definition'] = vt_def
        report = score_device(self.manager, name, knobs)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
            response.media = report
            return
        if samples > 0:
            from cntfet.cnt_device_viz import _montecarlo
            device = get_row(self.manager, 'AlignedCNTFETDevice', name)
            mc = _montecarlo(self.manager, device,
                             max(1, min(samples, 2000)), seed)
            report['monteCarlo'] = (
                {'sampleCount': mc['sampleCount'], 'seed': seed,
                 'yield': mc['yield'], **mc['score']}
                if mc.get('ok') else
                {'refusal': mc.get('refusal') or mc.get('error')})
        response.media = report

    def on_get_device_compare(self, request, response, name):
        from cntfet.cnt_compare import compare_devices
        report = compare_devices(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def _floats(self, request, response, keys):
        """Optional float params → dict; refuses on a bad number."""
        out = {}
        for key in keys:
            raw = request.get_param(key)
            if raw in (None, ''):
                continue
            try:
                out[key] = float(raw)
            except ValueError:
                self._refuse(response, f'{key} must be numeric')
                return None
        return out

    def _modelled(self, response, name):
        from cntfet.cnt_device_viz import device_model
        id_fn, p, device, refusal = device_model(self.manager, name)
        if refusal is not None:
            response.status = '422 Unprocessable Entity'
            response.media = refusal
            return None
        return id_fn, p, device

    def on_get_device_regimes(self, request, response, name):
        """fv-1: ?vg= ?vd= (point) + the map summary + exponent."""
        from cntfet.cnt_regimes import device_regimes_report
        m = self._modelled(response, name)
        if m is None:
            return
        q = self._floats(request, response, ('vg', 'vd'))
        if q is None:
            return
        response.media = device_regimes_report(
            m[1], m[2], vgs=q.get('vg'), vds=q.get('vd'),
            manager=self.manager)

    def on_get_device_transport(self, request, response, name):
        """fv-2: ?vg= ?vd= ?t= (hours) ?horizon= (hours)."""
        from cntfet.cnt_transport import transport_report
        m = self._modelled(response, name)
        if m is None:
            return
        q = self._floats(request, response, ('vg', 'vd', 't', 'horizon'))
        if q is None:
            return
        kwargs = {'vgs': q.get('vg', 0.6), 'vds': q.get('vd', 0.6),
                  't_hours': q.get('t', 0.0)}
        if 'horizon' in q:
            kwargs['horizon_hours'] = q['horizon']
        report = transport_report(self.manager, m[2], m[1], **kwargs)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def _scene_names(self):
        tables = getattr(self.manager, 'objectTables', None) or {}
        return {getattr(r, 'name', '')
                for r in (tables.get('SimSpaceDefinition') or {}).values()}

    def on_get_device_characteristics(self, request, response, name):
        from cntfet.cnt_characteristics import characteristics_index
        if (get_row(self.manager, 'AlignedCNTFETDevice', name) is None
                and get_row(self.manager, 'SiliconMOSFET', name) is None):
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        response.media = characteristics_index(self.manager, name)

    def on_get_device_characteristic(self, request, response, name,
                                     key):
        from cntfet.cnt_characteristics import characteristic_detail
        if (get_row(self.manager, 'AlignedCNTFETDevice', name) is None
                and get_row(self.manager, 'SiliconMOSFET', name) is None):
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        report = characteristic_detail(self.manager, name, key,
                                       self._scene_names())
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_device_fields(self, request, response, name):
        """fv-4: ?field=material|potential|electron-density|n-doping|
        p-doping ?vg= ?vd= — the 1-D profile (F1 sketch, labelled)."""
        from cntfet.cnt_fields import field_profile
        device = get_row(self.manager, 'AlignedCNTFETDevice', name)
        if device is None:
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        q = self._floats(request, response, ('vg', 'vd'))
        if q is None:
            return
        report = field_profile(self.manager, device,
                               request.get_param('field') or 'potential',
                               q.get('vg', 0.6), q.get('vd', 0.6))
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_device_links(self, request, response, name):
        """fp-6 weave: pages + partners + cells for one FET."""
        from cntfet.cnt_links import device_links
        device = (get_row(self.manager, 'AlignedCNTFETDevice', name)
                  or get_row(self.manager, 'SiliconMOSFET', name))
        if device is None:
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        response.media = device_links(self.manager, device)

    def on_get_device_power(self, request, response, name):
        """fp-1: static / leakage / dynamic power + budget checks.
        ?vdd= ?activity= ?f="""
        from cntfet.cnt_power import budget_report
        m = self._modelled(response, name)
        if m is None:
            return
        q = self._floats(request, response, ('vdd', 'activity', 'f'))
        if q is None:
            return
        knobs = {k2: v for k, v in q.items()
                 for k2 in ({'vdd': 'vdd_v', 'f': 'f_hz'}.get(k, k),)}
        report = budget_report(self.manager, name, knobs=knobs or None)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_device_cell_power(self, request, response, name):
        """fp-1: every characterized cell's leakage states + dynamic."""
        from cntfet.cnt_power import library_power
        m = self._modelled(response, name)
        if m is None:
            return
        report = library_power(self.manager, name)
        if not report.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_device_taxonomy(self, request, response, name):
        """fp-3: shape, optimization class (switching vs signal),
        complementary partner + conditions, regions summary."""
        from cntfet.cnt_taxonomy import device_taxonomy_report
        if (get_row(self.manager, 'AlignedCNTFETDevice', name) is None
                and get_row(self.manager, 'SiliconMOSFET', name) is None):
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        report = device_taxonomy_report(self.manager, name)
        if not report.get('ok', True):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_device_signal_score(self, request, response, name):
        """fp-3: the analog / signal-optimized score concept."""
        from cntfet.cnt_taxonomy import score_signal
        if (get_row(self.manager, 'AlignedCNTFETDevice', name) is None
                and get_row(self.manager, 'SiliconMOSFET', name) is None):
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        report = score_signal(self.manager, name)
        if not report.get('ok', True):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_cell_logic(self, request, response, cell):
        """fp-5: boolean AST, gate DAG, truth table, transistor
        netlist with placement, switch-level proof, state space."""
        from cntfet.cnt_logic import cell_logic_report
        try:
            drive = int(request.get_param('drive') or 1)
        except ValueError:
            return self._refuse(response, 'drive must be an integer')
        report = cell_logic_report(cell, drive=drive)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_device_ip(self, request, response, name):
        from cntfet.cnt_ip import device_ip_report
        if (get_row(self.manager, 'AlignedCNTFETDevice', name) is None
                and get_row(self.manager, 'SiliconMOSFET', name) is None):
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        response.media = device_ip_report(self.manager, name)

    def on_get_device_proof(self, request, response, name):
        from cntfet.cnt_evidence import freedom_proof
        if (get_row(self.manager, 'AlignedCNTFETDevice', name) is None
                and get_row(self.manager, 'SiliconMOSFET', name) is None):
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        response.media = freedom_proof(self.manager, 'device', name)

    def on_get_cell_proof(self, request, response, cell):
        from cntfet.cnt_evidence import freedom_proof
        report = freedom_proof(self.manager, 'cell', cell)
        if not report.get('ok', True):
            response.status = '404 Not Found'
        response.media = report

    def on_get_library_proof(self, request, response):
        from cntfet.cnt_evidence import library_proof
        response.media = library_proof(self.manager)

    def on_get_evidence_index(self, request, response):
        from cntfet.cnt_evidence import evidence_index
        response.media = evidence_index(
            self.manager, kind=request.get_param('kind'),
            subject=request.get_param('subject'))

    def on_get_evidence_detail(self, request, response, item):
        from cntfet.cnt_evidence import evidence_detail
        report = evidence_detail(self.manager, item)
        if not report.get('ok', True):
            response.status = '404 Not Found'
        response.media = report

    def on_get_library_ip(self, request, response):
        from cntfet.cnt_ip import library_ip_report
        response.media = library_ip_report(self.manager)

    def on_get_blocks(self, request, response):
        """?device= (default cnt-aligned-s1) — every block's proof /
        timing / power / provenance on that device."""
        from cntfet.cnt_blocks import library_blocks_report
        response.media = library_blocks_report(
            self.manager, request.get_param('device') or 'cnt-aligned-s1')

    def on_get_block(self, request, response, key):
        """?device= ?timing=1 — OpenSTA runs only when asked (a GET
        must not launch a docker run by default)."""
        from cntfet.cnt_blocks import block_report
        report = block_report(self.manager,
                              request.get_param('device') or 'cnt-aligned-s1',
                              key,
                              with_timing=request.get_param('timing') == '1')
        if not report.get('ok', True):
            response.status = '404 Not Found'
        response.media = report

    def on_get_block_logic(self, request, response, key):
        """the cell-logic-diagram payload for a block (state space,
        gate DAG over cell instances)."""
        from cntfet.cnt_blocks import block_logic
        report = block_logic(key)
        if not report.get('ok', True):
            response.status = '404 Not Found'
        response.media = report

    def on_get_block_power(self, request, response, key):
        from cntfet.cnt_blocks import block_power
        q = self._floats(request, response, ('activity', 'f'))
        if q is None:
            return
        report = block_power(self.manager,
                             request.get_param('device') or 'cnt-aligned-s1',
                             key, activity=q.get('activity', 0.1),
                             f_hz=q.get('f', 1e9))
        if not report.get('ok', True):
            response.status = '422 Unprocessable Entity'
        response.media = report

    def on_get_block_proof(self, request, response, key):
        from cntfet.cnt_blocks import block_proof
        report = block_proof(self.manager,
                             request.get_param('device') or 'cnt-aligned-s1',
                             key)
        if not report.get('ok', True):
            response.status = '404 Not Found'
        response.media = report

    def on_get_open_libraries(self, request, response):
        from cntfet.cnt_open_library import open_library_index
        response.media = open_library_index(self.manager)

    def on_get_open_library(self, request, response, lib):
        from cntfet.cnt_open_library import open_library_report
        report = open_library_report(self.manager, lib)
        if not report.get('ok', True):
            response.status = '404 Not Found'
        response.media = report

    def on_get_open_library_liberty(self, request, response, lib):
        from cntfet.cnt_open_library import open_liberty_text
        report = open_liberty_text(self.manager, lib)
        if not report.get('ok', True) or not report.get('text'):
            response.status = '422 Unprocessable Entity'
            response.media = report
            return
        response.content_type = 'text/plain; charset=utf-8'
        response.text = report['text']

    def on_post_open_library(self, request, response, lib):
        """{action: refresh | characterize {drives, cells, force} |
        export {outdir, force} | ladder-update {apply}}"""
        from cntfet.cnt_open_library import (
            characterize_open_library, export_open_library,
            ladder_cell_rung_update, refresh_open_library,
        )
        try:
            raw = request.bounded_stream.read()
            payload = json.loads(raw) if raw else {}
        except ValueError:
            return self._refuse(response, 'body must be JSON')
        action = payload.get('action', 'refresh')
        if action == 'refresh':
            response.media = refresh_open_library(self.manager, lib)
        elif action == 'characterize':
            report = characterize_open_library(
                self.manager, lib,
                drives=tuple(payload.get('drives', [1])),
                cells=payload.get('cells'),
                force=bool(payload.get('force', False)))
            if not report.get('ok'):
                response.status = '422 Unprocessable Entity'
            response.media = report
        elif action == 'export':
            report = export_open_library(
                self.manager, lib,
                payload.get('outdir') or f'/tmp/open-library/{lib}',
                force=bool(payload.get('force', False)))
            if not report.get('ok', True):
                response.status = '422 Unprocessable Entity'
            response.media = report
        elif action == 'ladder-update':
            response.media = ladder_cell_rung_update(
                self.manager, apply=bool(payload.get('apply', False)))
        else:
            self._refuse(response, 'actions: refresh | characterize | '
                                   'export | ladder-update')

    def on_get_cells_coverage(self, request, response):
        from cntfet.cnt_cell_coverage import cells_coverage
        response.media = cells_coverage(self.manager)

    def on_get_device_cell_coverage(self, request, response, name):
        from cntfet.cnt_cell_coverage import device_cell_coverage
        if (get_row(self.manager, 'AlignedCNTFETDevice', name) is None
                and get_row(self.manager, 'SiliconMOSFET', name) is None):
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        response.media = device_cell_coverage(self.manager, name)

    def on_get_cells_logic(self, request, response):
        from cntfet.cnt_logic import library_logic_report
        response.media = library_logic_report()

    # ── sifet (fp-2 / fp-4) ────────────────────────────────────────

    def on_get_si_capability(self, request, response):
        from sifet.si_device import capability as si_capability
        response.media = si_capability()

    def on_get_si_devices(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        rows = [{'name': getattr(r, 'name', ''),
                 'polarity': getattr(r, 'polarity', ''),
                 'shape': getattr(r, 'shape', ''),
                 'dielectric': getattr(r, 'dielectric', ''),
                 'lg_nm': getattr(r, 'lg_nm', None),
                 'derivedAt': getattr(r, 'derived_at', '')}
                for r in (tables.get('SiliconMOSFET') or {}).values()]
        rows.sort(key=lambda r: r['name'])
        response.media = {'ok': True, 'devices': rows,
                          'note': 'every /api/cntfet/device/{name}/* '
                                  'surface (states, regimes, score, '
                                  'transport, fields, characteristics, '
                                  'compare) accepts these names too — '
                                  'the VS parameterisation is shared'}

    def on_post_si_device(self, request, response, name):
        """{action: derive}"""
        from sifet.si_device import derive_si_device, get_row as si_row
        device = si_row(self.manager, 'SiliconMOSFET', name)
        if device is None:
            return self._refuse(response, f'no SiliconMOSFET "{name}"',
                                '404 Not Found')
        try:
            raw = request.bounded_stream.read()
            payload = json.loads(raw) if raw else {}
        except ValueError:
            return self._refuse(response, 'body must be JSON')
        if payload.get('action', 'derive') != 'derive':
            return self._refuse(response, 'actions: derive')
        response.media = derive_si_device(self.manager, device)

    def on_get_si_refinement(self, request, response):
        from sifet.si_refinement import refinement_report
        response.media = refinement_report(self.manager)

    def on_get_si_refinement_route(self, request, response, route):
        """?feed=<json ppm map> ?passes= ?fs_cut="""
        from sifet.si_refinement import route_simulation
        q = self._floats(request, response, ('passes', 'fs_cut'))
        if q is None:
            return
        knobs = {k: (int(v) if k == 'passes' else v) for k, v in q.items()}
        report = route_simulation(self.manager, route,
                                  feed_ppm_json=request.get_param('feed'),
                                  knobs=knobs or None)
        if not report.get('ok', True):
            response.status = '404 Not Found'
        response.media = report

    def on_get_si_refinement_points(self, request, response, route):
        """?curve=impurity-ladder|scheil — the named-graph-panel feed."""
        from sifet.si_pages_seed import refinement_points
        report = refinement_points(
            self.manager, route,
            curve=request.get_param('curve') or 'impurity-ladder',
            feed_ppm_json=request.get_param('feed'))
        if not report.get('ok', True):
            response.status = '404 Not Found'
        response.media = report

    def on_get_device_cell_scores(self, request, response, name):
        from cntfet.cnt_cell_scoring import score_cells
        report = score_cells(self.manager, name)
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
        # a SiliconMOSFET row takes the cell / power actions too (the
        # VS card is shared; derive is the sifet route's job)
        device = (get_row(self.manager, 'AlignedCNTFETDevice', name)
                  or get_row(self.manager, 'SiliconMOSFET', name))
        if device is None:
            return self._refuse(response, f'no device "{name}"',
                                '404 Not Found')
        action = payload.get('action', '')
        if action == 'derive':
            response.media = derive_device(self.manager, device)
            return
        if action == 'sample-fields':
            # fv-4: generate the FETFieldSample rows the 3-D scene
            # binds (one band-coloured cell per x per Vg per field).
            from cntfet.cnt_fields import sample_fields
            try:
                vd = float(payload.get('vd', 0.6))
                n_cells = int(payload.get('nCells', 40))
            except (TypeError, ValueError):
                return self._refuse(response, 'vd/nCells must be numeric')
            report = sample_fields(self.manager, device, vd=vd,
                                   n_cells=max(8, min(n_cells, 200)))
            if not report.get('ok'):
                response.status = '422 Unprocessable Entity'
            response.media = report
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
        if action == 'characterize-latch':
            # cells-2: the transparent D latch (setup/hold on the
            # closing edge, D→Q) via the own-loop bisection.
            from cntfet.cnt_sequential import characterize_latch
            report = characterize_latch(
                self.manager, device,
                vdd=float(payload.get('vdd', getattr(device, 'vdd_v', None) or 0.6)),
                iters=int(payload.get('iters', 6)))
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
                vdd=float(payload.get('vdd', getattr(device, 'vdd_v', None) or 0.6)),
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
                vdd=float(payload.get('vdd', getattr(device, 'vdd_v', None) or 0.6)),
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
