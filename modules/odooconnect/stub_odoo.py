"""
@module odooconnect.stub_odoo

TEST-ONLY in-process stub of Odoo's /jsonrpc endpoint (stdlib
http.server, ephemeral port) — the CI stand-in the od-3/od-4 selftests
run against; no live Odoo anywhere near CI.

Behavior implemented (just enough, honestly refusing the rest):
  common.version / common.authenticate ('stub'/'stub-pass' -> uid 7)
  res.partner:      search_read (paging + write_date)
  product.template: search_read (incl. [x_polari_ref,=,v] domain),
                    create, write, fields_get — x_polari_ref does NOT
                    exist until created via ir.model.fields (so the
                    ensure-field path is exercised for real)
  ir.model:         search [['model','=',m]]
  ir.model.fields:  create (adds the field to product.template)

@consumers odooconnect.selftest_odoo, odooconnect.selftest_odoo_sync
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class StubState:
    """Mutable server state — one per test run; reset() re-arms it."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.partners = [
            {'id': i, 'name': f'partner-{i:02d}',
             'write_date': f'2026-07-28 00:00:{i:02d}'}
            for i in range(1, 26)]
        self.products = []
        self.product_fields = {'name', 'list_price'}
        self.next_id = 1000
        self.created_payloads = []


STATE = StubState()


def _filter(records, domain):
    if not domain:
        return list(records)
    clause = domain[0]
    if isinstance(clause, (list, tuple)) and len(clause) == 3 \
            and clause[1] == '=':
        field, _, value = clause
        return [r for r in records if r.get(field) == value]
    return list(records)


def _page(records, kwargs):
    offset = int(kwargs.get('offset', 0))
    limit = int(kwargs.get('limit', 0)) or len(records)
    fields = kwargs.get('fields')
    page = records[offset:offset + limit]
    if fields:
        keep = set(fields) | {'id'}
        page = [{k: v for k, v in r.items() if k in keep}
                for r in page]
    return page


class StubOdooHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _reply(self, result=None, error=None):
        body = {'jsonrpc': '2.0', 'id': 1}
        if error is not None:
            body['error'] = error
        else:
            body['result'] = result
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _err(self, message):
        self._reply(error={'message': message})

    def do_POST(self):
        if self.path != '/jsonrpc':
            self.send_error(404)
            return
        req = json.loads(self.rfile.read(
            int(self.headers.get('Content-Length', 0))))
        params = req.get('params', {})
        service, method = params.get('service'), params.get('method')
        args = params.get('args', [])
        if service == 'common' and method == 'version':
            self._reply({'server_version': '18.0-stub'})
            return
        if service == 'common' and method == 'authenticate':
            db, login, password = args[0], args[1], args[2]
            ok = (db.startswith('odoo_') and login == 'stub'
                  and password == 'stub-pass')
            self._reply(7 if ok else False)
            return
        if service != 'object' or method != 'execute_kw':
            self._err('stub: unknown service')
            return
        _db, uid, password, model, obj_method = args[:5]
        if uid != 7 or password != 'stub-pass':
            self._err('Access Denied')
            return
        m_args = args[5] if len(args) > 5 else []
        m_kwargs = args[6] if len(args) > 6 else {}
        self._object_call(model, obj_method, m_args, m_kwargs)

    def _object_call(self, model, obj_method, m_args, m_kwargs):
        s = STATE
        if model == 'res.partner' and obj_method == 'search_read':
            domain = m_args[0] if m_args else []
            self._reply(_page(_filter(s.partners, domain), m_kwargs))
        elif model == 'res.partner' and obj_method == 'create':
            s.next_id += 1
            s.partners.append({'id': s.next_id,
                               'write_date': '2026-07-28 01:00:00',
                               **dict(m_args[0])})
            self._reply(s.next_id)
        elif model == 'product.template':
            if obj_method == 'search_read':
                domain = m_args[0] if m_args else []
                self._reply(_page(_filter(s.products, domain),
                                  m_kwargs))
            elif obj_method == 'fields_get':
                asked = m_args[0] if m_args else []
                self._reply({f: {'type': 'char'} for f in asked
                             if f in s.product_fields})
            elif obj_method == 'create':
                vals = dict(m_args[0])
                bad = [k for k in vals
                       if k not in s.product_fields]
                if bad:
                    self._err(f'Invalid field {bad[0]} on '
                              'product.template')
                    return
                s.next_id += 1
                rec = {'id': s.next_id,
                       'write_date': '2026-07-28 01:00:00', **vals}
                s.products.append(rec)
                s.created_payloads.append(vals)
                self._reply(s.next_id)
            elif obj_method == 'write':
                ids, vals = m_args[0], dict(m_args[1])
                bad = [k for k in vals if k not in s.product_fields]
                if bad:
                    self._err(f'Invalid field {bad[0]} on '
                              'product.template')
                    return
                for rec in s.products:
                    if rec['id'] in ids:
                        rec.update(vals)
                self._reply(True)
            else:
                self._err(f'stub: no product.template.{obj_method}')
        elif model == 'ir.model' and obj_method == 'search':
            domain = m_args[0] if m_args else []
            wanted = domain[0][2] if domain else ''
            self._reply([55] if wanted == 'product.template' else [])
        elif model == 'ir.model.fields' and obj_method == 'create':
            vals = dict(m_args[0])
            s.product_fields.add(vals.get('name', ''))
            self._reply(900)
        else:
            self._err(f'stub: no {model}.{obj_method}')


def start_stub():
    """Start the stub on an ephemeral port; returns (server, url)."""
    server = ThreadingHTTPServer(('127.0.0.1', 0), StubOdooHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_address[1]}'
