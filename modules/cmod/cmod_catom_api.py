"""
@module cmod.cmod_catom_api

hsp-3a doors (HARDWARE_SYSTEM_PINS_PLAN.md §7): Catom assertions and what is derived from them. The rows are the stored CatomAssertion / StructObjectMap rows
(the seeds when the table is empty); every status is recomputed from the variant's cycle record on read.

GET /api/cmod/catom-assertions/{variant}[?view=assertions|bindings|gaps|draft|maps]
        assertions = the rows + status (verified | unverified | false) and why; bindings = one row per (pin, field) an assertion couples (the struct-pin
        bindings, derived); gaps = struct fields no catom asserts + the notebook draft's fields the struct lacks; draft = his draft field -> firmware field;
        maps = StructObjectMap field -> attribute. Without `view`: {ok, variant, assertions, bindings, gaps}. 404 no assertions for the variant; 422 unknown view.
GET /api/cmod/catom-variables/{variant}[?view=variables|assertions|pins|header|slots&variable=V]       hsp-3d: the generalized HAL
        variables = each with value + scope + verdict (accepted | warning | refused) and why; assertions = the defines-role assertions they make; pins = what the
        pin view draws (pin, role, variable, verdict); header = {text} the HAL lines the firmware is generated with; slots = the pins a role slot offers (needs
        `variable`). 404 no variables for the variant; 422 unknown view / variable.
POST /api/cmod/catom-variables/{variant}/check  body {variable, value}  -> {verdict, why[], pin, function}: the same check a value passes before it counts;
        NOTHING is written.
POST /api/cmod/catom-variables/{variant}/set    body {variable, value} (or {edits: {variable: value, ...}})   hsp-3c: THE slot-choice write. Checked by
        catom_variables.propose (pin functions, lifecycle, one pin one role against the proposed set, then the variant's own rules); a knob-backed variable
        (LED_PIN / BUTTON_PIN / SENSE_PIN) is written to its FirmwareVariant knob - the value `pol board gen` renders - the rest to the variable's bench
        value. 422 + every reason when refused (nothing written). -> {ok, results[], variant_rule, written[], not_written[]}
GET  /api/cmod/catom-variables/{variant}/solution   the variant's HAL drawn as a no-code solution (category 'hal'): {ok, solution, definition}
PUT  /api/cmod/catom-variables/{variant}/solution   body = the drawing; a card's new `value` goes through the same write; 422 naming the state when the
        drawing holds a non-HAL kind or an edit to a worked-out field, or the write is refused. -> {ok, why, results[], written[], solution, definition}
"""
import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import catom_assertions as CA
from cmod.custom import catom_variables as CV


class CatomAssertionAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/cmod/catom-assertions/{variant}', self)

    def _stored(self):
        table = (getattr(self.manager, 'objectTables', None) or {}).get('CatomAssertion') or {}
        return list(table.values()) or None

    def on_get(self, request, response, variant):
        rows = self._stored()
        if not CA.assertions(variant, rows, rec=None):
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no catom assertions for variant %r' % variant}
            return
        view = request.get_param('view') or ''
        if not view:
            response.media = {'ok': True, 'variant': variant, 'assertions': CA.assertions(variant, rows), 'bindings': CA.struct_pin_bindings(variant, rows),
                              'gaps': CA.gaps(variant, rows)}
            return
        if view not in CA.VIEWS:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'view must be one of %s' % ', '.join(CA.VIEWS)}
            return
        out = CA.VIEWS[view](variant, rows)
        response.media = {'ok': True, 'variant': variant, 'view': view, 'count': len(out), 'rows': out}


def _json(request):
    import json
    try:
        return json.loads(request.bounded_stream.read() or b'{}')
    except Exception:  # noqa: BLE001
        return {}


class CatomVariableAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/cmod/catom-variables/{variant}', self)
            polServer.falconServer.add_route('/api/cmod/catom-variables/{variant}/check', self, suffix='check')
            polServer.falconServer.add_route('/api/cmod/catom-variables/{variant}/set', self, suffix='set')
            polServer.falconServer.add_route('/api/cmod/catom-variables/{variant}/solution', self, suffix='solution')

    def _table(self, cls):
        return list(((getattr(self.manager, 'objectTables', None) or {}).get(cls) or {}).values())

    def _stored(self):
        return self._table('CatomVariable') or None

    def _variant_rows(self):
        return self._table('FirmwareVariant') or None

    def _save(self, row):
        db = getattr(self.manager, 'db', None) if self.manager is not None else None
        if db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(row)

    def _apply(self, variant, proposal):
        """Apply a passed proposal's writes to the stored rows, save them, keep the stored `hal-<variant>` drawing in step -> (written, not_written)."""
        touched, written, missing = CV.apply_writes(proposal['writes'], self._stored(), self._variant_rows())
        for row in touched:
            self._save(row)
        if touched:
            from cmod.custom import hal_nocode as HN
            live = next((r for r in self._table('SolutionDefinition') if getattr(r, 'name', '') == HN.solution_name(variant)), None)
            if live is not None:
                live.definition = HN.render(variant, self._stored(), self._variant_rows())['definition']
                self._save(live)
        return written, missing

    def _fail(self, response, status, text):
        response.status = status
        response.media = {'ok': False, 'error': text}

    def on_get(self, request, response, variant):
        rows, vrows = self._stored(), self._variant_rows()
        vs = CV.variables(variant, rows, vrows)
        if not vs:
            return self._fail(response, falcon.HTTP_404, 'no catom variables for variant %r' % variant)
        view = request.get_param('view') or 'variables'
        if view == 'variables':
            out = vs
        elif view == 'assertions':
            out = CV.role_assertions(variant, rows, vrows)
        elif view == 'pins':
            out = CV.pin_roles(variant, rows, vrows)
        elif view == 'header':
            response.media = {'ok': True, 'variant': variant, 'view': view, 'text': CV.render_header(variant, rows, vrows)}
            return
        elif view == 'slots':
            var = next((v for v in vs if v['variable'] == request.get_param('variable')), None)
            if var is None:
                return self._fail(response, falcon.HTTP_422, 'slots needs variable= one of %s' % ', '.join(v['variable'] for v in vs))
            response.media = dict(CV.slots(var, vs), ok=True, variant=variant, view=view)
            return
        else:
            return self._fail(response, falcon.HTTP_422, 'view must be variables, assertions, pins, header or slots')
        response.media = {'ok': True, 'variant': variant, 'view': view, 'count': len(out), 'rows': out}

    def on_post_check(self, request, response, variant):
        body = _json(request)
        vs = CV.variables(variant, self._stored(), self._variant_rows())
        var = next((v for v in vs if v['variable'] == body.get('variable')), None)
        if var is None:
            return self._fail(response, falcon.HTTP_422, 'variable must be one of %s' % ', '.join(v['variable'] for v in vs))
        response.media = dict(CV.check(var, body.get('value', ''), vs), ok=True, variant=variant, variable=var['variable'], written=False)

    def on_post_set(self, request, response, variant):
        body = _json(request)
        edits = body.get('edits') if isinstance(body.get('edits'), dict) else ({body['variable']: body.get('value', '')} if body.get('variable') else {})
        if not edits:
            return self._fail(response, falcon.HTTP_422, 'body needs {variable, value} or {edits: {variable: value}}')
        p = CV.propose(variant, edits, self._stored(), self._variant_rows())
        if p.get('error'):
            return self._fail(response, falcon.HTTP_422, p['error'])
        if not p['ok']:
            response.status = falcon.HTTP_422
            response.media = dict(p, ok=False, refused=True, written=[])
            return
        written, missing = self._apply(variant, p)
        response.media = dict(p, ok=True, variant=variant, written=written, not_written=missing)

    def on_get_solution(self, request, response, variant):
        from cmod.custom import hal_nocode as HN
        rows, vrows = self._stored(), self._variant_rows()
        if not CV.variables(variant, rows, vrows):
            return self._fail(response, falcon.HTTP_404, 'no catom variables for variant %r' % variant)
        response.media = {'ok': True, 'solution': HN.render(variant, rows, vrows), 'definition': HN.render_definition(variant, rows, vrows)}

    def on_put_solution(self, request, response, variant):
        from cmod.custom import hal_nocode as HN
        body = _json(request)
        definition = body.get('definition') if isinstance(body.get('definition'), dict) else body
        ok, why, p = HN.write_back(definition, variant, self._stored(), self._variant_rows())
        if not ok:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': True, 'error': why, 'results': p.get('results', []), 'variant_rule': p.get('variant_rule', '')}
            return
        written, missing = self._apply(variant, p)
        rows, vrows = self._stored(), self._variant_rows()
        response.media = {'ok': True, 'why': why, 'results': p['results'], 'written': written, 'not_written': missing,
                          'solution': HN.render(variant, rows, vrows), 'definition': HN.render_definition(variant, rows, vrows)}
