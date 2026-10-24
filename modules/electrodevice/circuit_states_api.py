"""
@module electrodevice.circuit_states_api

cst-0/1 (PROTOTYPING_VIEWS_PLAN.md §2, §8): the doors of THE CIRCUIT STATES — thin falcon handlers over electrodevice.custom.cst_verdict (derived on each
read from the circuit rows, the HAL init source, the parsed atoms, the press record and the cited limits; the .op runs cached a minute).

GET  /api/circuit-states/configs                    the configs a bench circuit exists for (the picker)
GET  /api/circuit-states/{config}                   the document (+ `rows` = the states) — no SPICE run (fast; the stored verdicts ride on the rows)
GET  /api/circuit-states/{config}/states            the CircuitState rows (with the last .op verdicts when run)
GET  /api/circuit-states/{config}/transitions       the CircuitStateTransition rows
GET  /api/circuit-states/{config}/spice             the per-state .op results (one row per state × pull-up end); 424 when no ngspice is on this node
GET  /api/circuit-states/{config}/findings          what SPICE and the structural rule flagged
POST /api/circuit-states/{config}/run               run the .op per state now and STORE the rows (CircuitState / CircuitStateTransition / CircuitRunResult)

A refusal is {ok: false, error: <plain words>} with 404 (no config / no circuit) or 424 (no engine on this node — the words name the knob).
"""
import time

from objectTreeDecorators import treeObject, treeObjectInit

CACHE_S = 60.0
_CACHE = {}


class CircuitStatesAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/circuit-states/configs', self, suffix='configs')
            add('/api/circuit-states/{config}', self, suffix='doc')
            add('/api/circuit-states/{config}/states', self, suffix='states')
            add('/api/circuit-states/{config}/transitions', self, suffix='transitions')
            add('/api/circuit-states/{config}/spice', self, suffix='spice')
            add('/api/circuit-states/{config}/findings', self, suffix='findings')
            add('/api/circuit-states/{config}/run', self, suffix='run')

    def _tables(self):
        from board.custom import electrical_check as EC
        t = EC.tables_for(self.manager)
        from board.custom import electrical_atmega328p as E
        t.setdefault('ElectricalCharacteristic', E.characteristics())
        t.setdefault('PinGroupBudget', E.budgets())
        return t

    def _doc(self, response, config, spice=False, fresh=False):
        from electrodevice.custom import cst_verdict as V
        from electrodevice.custom.cst_sources import SourceRefused
        from board.custom.firmware_state import StateRefused
        if not config or config == 'undefined':
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': 'name the config: /api/circuit-states/<config> (GET /api/circuit-states/configs lists them; the page takes ?config=)'}
            return None
        key = (config, spice)
        hit = _CACHE.get(key)
        if hit and not fresh and time.time() - hit[0] < CACHE_S:
            return hit[1]
        try:
            doc = V.document(config, self._tables(), spice=spice, manager=self.manager)
        except (SourceRefused, StateRefused) as e:
            response.status = '404 Not Found'
            response.media = {'ok': False, 'error': str(e)}
            return None
        except Exception as e:   # noqa: BLE001 — words, never a 500 wall
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False, 'error': 'the circuit states of %s could not be derived: %s' % (config, str(e)[:400])}
            return None
        _CACHE[key] = (time.time(), doc)
        return doc

    def on_get_configs(self, request, response):
        from board.custom import variants as V
        from board.custom.installer import _rows
        rows = _rows(self.manager, 'FirmwareVariant') or V.SEED_FIRMWARE_VARIANTS
        g = lambda r, k: r.get(k, '') if isinstance(r, dict) else getattr(r, k, '')   # noqa: E731
        out = [{'name': g(r, 'name'), 'title': g(r, 'title'), 'app': g(r, 'app')} for r in rows if g(r, 'board_definition') in ('arduino-uno-r3', '', None)]
        response.media = {'ok': True, 'rows': out, 'count': len(out)}

    def on_get_doc(self, request, response, config):
        from electrodevice.custom import cst_verdict as V
        doc = self._doc(response, config)
        if doc is not None:
            response.media = dict(doc, rows=V.state_rows(doc))

    def _rows(self, response, config, fn, spice=False):
        from electrodevice.custom import cst_verdict as V
        doc = self._doc(response, config, spice=spice)
        if doc is None:
            return
        rows = getattr(V, fn)(doc)
        response.media = {'ok': True, 'config': config, 'rows': rows, 'count': len(rows), 'counts': doc['counts'], 'engine': doc['engine'], 'derived_at': doc['derived_at']}

    def on_get_states(self, request, response, config):
        self._rows(response, config, 'state_rows', spice=self._has_engine())

    def on_get_transitions(self, request, response, config):
        self._rows(response, config, 'transition_rows')

    def on_get_findings(self, request, response, config):
        self._rows(response, config, 'finding_rows', spice=self._has_engine())

    def _has_engine(self):
        from electrodevice.custom.spice_run import capability
        return bool(capability()['available'])

    def on_get_spice(self, request, response, config):
        from electrodevice.custom.spice_run import capability
        cap = capability()
        if not cap['available']:
            response.status = '424 Failed Dependency'
            response.media = {'ok': False, 'error': 'no ngspice on this node: the circuit states still enumerate, but no .op can run here — %s' % (cap.get('suggestion') or {}).get('how', ''), 'capability': cap}
            return
        self._rows(response, config, 'spice_rows', spice=True)

    def on_post_run(self, request, response, config):
        from electrodevice.custom import cst_verdict as V
        from electrodevice.custom.spice_run import capability
        cap = capability()
        if not cap['available']:
            response.status = '424 Failed Dependency'
            response.media = {'ok': False, 'error': 'no ngspice on this node: nothing was run — %s' % (cap.get('suggestion') or {}).get('how', ''), 'capability': cap}
            return
        doc = self._doc(response, config, spice=True, fresh=True)
        if doc is None:
            return
        stored = ''
        if self.manager is not None and getattr(self.manager, 'objectTables', None) is not None:
            try:
                V.persist(self.manager, doc)
                stored = 'CircuitState %d, CircuitStateTransition %d, CircuitRunResult %d rows stored' % (doc['counts']['states'], doc['counts']['transitions'], doc['counts']['simulated'])
            except Exception as e:   # noqa: BLE001
                stored = 'rows not stored: %s' % e
        response.media = {'ok': True, 'config': config, 'counts': doc['counts'], 'stored': stored, 'rows': V.state_rows(doc), 'spice': V.spice_rows(doc), 'findings': V.finding_rows(doc)}
