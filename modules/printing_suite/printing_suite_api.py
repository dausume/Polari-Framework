"""
@module printing_suite.printing_suite_api

GET  /api/printing-suite/summary          the pipeline as counts + the suite's placement
GET  /api/printing-suite/runs             every ProductionRun with its latest valid step records
POST /api/printing-suite/runs             {cadObject, targetMaterial, moldFeedstock?, printer?, profile?, requestedBy?} → a run (step design)
POST /api/printing-suite/runs/{name}/advance    run the current step (design → … → measure), cache the result
POST /api/printing-suite/runs/{name}/retry      {step} — re-run one step, invalidating the later cache
POST /api/printing-suite/runs/{name}/reprint    print the cached gcode again
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit


class PrintingSuiteAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/printing-suite/summary', self, suffix='summary')
            add('/api/printing-suite/runs', self, suffix='runs')
            add('/api/printing-suite/runs/{name}/advance', self, suffix='advance')
            add('/api/printing-suite/runs/{name}/retry', self, suffix='retry')
            add('/api/printing-suite/runs/{name}/reprint', self, suffix='reprint')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def on_get_summary(self, request, response):
        counts = {c: len(self._rows(c)) for c in ('ImportedCadObject', 'MathShapeDefinition', 'MoldDefinition', 'Material', 'MaterialLot',
                                                  'PrintProfile', 'SliceJob', 'GcodeArtifact', 'PrintJob', 'PrintOutcome', 'PrinterDefinition')}
        jobs = self._rows('PrintJob')
        response.media = {'ok': True, 'pipeline': counts,
                          'printing': [{'job': j.name, 'printer': j.printer, 'state': j.state, 'progressPct': j.progress_pct} for j in jobs if j.state in ('printing', 'paused')],
                          'placement': '/api/suiteapps/printing-production',
                          'note': 'shape → mold → profile → slice job → gcode artifact → print job → outcome; every arrow is a row'}

    # ---- production runs (the automation) ------------------------------
    def _ctx(self):
        from printing_suite.custom.adapters import build
        from printing_suite.custom.pipeline import latest_valid
        ctx = build(self.manager)
        ctx['step_result'] = lambda run, step: latest_valid(self._rows('RunStepRecord'), run['name'], step)
        return ctx

    def _run_dict(self, r):
        return {k: getattr(r, k) for k in ('name', 'cad_object', 'target_material', 'mold_feedstock', 'printer', 'profile', 'slicer', 'step', 'state', 'last_error')}

    def _apply(self, run_row, rec, upd):
        from printing_suite.printing_suite_basis import RunStepRecord
        row = RunStepRecord(manager=self.manager, **rec)
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001
            pass
        for k, v in upd.items():
            setattr(run_row, k, v)
        try:
            self.manager.db.saveInstanceInDB(run_row)
        except Exception:  # noqa: BLE001
            pass
        return {'ok': rec['ok'], 'run': run_row.name, 'step': rec['step'], 'attempt': rec['attempt'], 'result': {'class': rec['result_class'], 'ref': rec['result_ref']},
                'cached': rec['store_key'], 'sha256': rec['sha256'], 'error': rec['error'], 'next': upd.get('step'), 'state': upd.get('state')}

    def on_get_runs(self, request, response):
        from printing_suite.custom.pipeline import STEPS, latest_valid
        recs = self._rows('RunStepRecord')
        out = []
        for r in self._rows('ProductionRun'):
            out.append(dict(self._run_dict(r), steps={s: latest_valid(recs, r.name, s) for s in STEPS}))
        response.media = {'ok': True, 'runs': out, 'steps': list(STEPS)}

    def on_post_runs(self, request, response):
        from printing_suite.printing_suite_basis import ProductionRun
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_400; response.media = {'ok': False, 'error': 'bad JSON: %s' % e}; return
        if not body.get('cadObject') or not body.get('targetMaterial'):
            response.status = falcon.HTTP_400; response.media = {'ok': False, 'error': 'cadObject (an ImportedCadObject name) and targetMaterial are required'}; return
        import time
        name = body.get('name') or 'run-%s-%s' % (body['cadObject'], time.strftime('%Y%m%d-%H%M%S'))
        row = ProductionRun(manager=self.manager, name=name, cad_object=body['cadObject'], target_material=body['targetMaterial'],
                            mold_feedstock=body.get('moldFeedstock', 'pla'), printer=body.get('printer', 'voron-2.4-350'), profile=body.get('profile', ''),
                            slicer=body.get('slicer', 'kirimoto'), requested_by=body.get('requestedBy', ''), requested_at=time.strftime('%Y-%m-%dT%H:%M:%S'))
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001
            pass
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'run': self._run_dict(row), 'next': 'POST /api/printing-suite/runs/%s/advance' % name}

    def _find_run(self, name, response):
        r = next((x for x in self._rows('ProductionRun') if x.name == name), None)
        if r is None:
            response.status = falcon.HTTP_404; response.media = {'ok': False, 'error': 'no ProductionRun %r' % name}
        return r

    def on_post_advance(self, request, response, name):
        from printing_suite.custom.pipeline import advance
        r = self._find_run(name, response)
        if r is None:
            return
        if r.state == 'done':
            response.media = {'ok': True, 'run': name, 'state': 'done', 'note': 'nothing left to run; reprint reuses the cached gcode'}; return
        rec, upd = advance(self._run_dict(r), self._ctx())
        response.media = self._apply(r, rec, upd)

    def on_post_retry(self, request, response, name):
        from printing_suite.custom.pipeline import retry
        r = self._find_run(name, response)
        if r is None:
            return
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:  # noqa: BLE001
            body = {}
        rec, upd = retry(self._run_dict(r), body.get('step', r.step), self._ctx())
        if rec is None:
            response.status = falcon.HTTP_400; response.media = {'ok': False, 'error': upd.get('last_error')}; return
        response.media = self._apply(r, rec, upd)

    def on_post_reprint(self, request, response, name):
        from printing_suite.custom.pipeline import reprint
        r = self._find_run(name, response)
        if r is None:
            return
        rec, upd = reprint(self._run_dict(r), self._ctx())
        response.media = self._apply(r, rec, upd)
