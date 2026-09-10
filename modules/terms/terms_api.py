"""
@module terms.terms_api

The terms API — what the frontends' terms gate talks to:

  GET  /api/terms/active?app=<app>&session=<id>
        the active documents that apply (global + this app), each with its
        version, body (Markdown), body_sha256, and whether THIS subject
        (the logged-in user, else the anonymous terms session) has already
        accepted that version — so the client knows what to show
  POST /api/terms/accept   {terms_name, terms_version, body_sha256, session, app}
        records ONE TermsAcceptance (append-only). Refuses when the named
        document/version is not active or the hash does not match the text
        currently served — an acceptance must be of the text that was shown
  GET  /api/terms/status?app=&session=   accepted / pending per document
  GET  /terms/{name}       the document as a server-rendered page (no JS)

Subject: `req.context.user_info['sub']` when a Bearer token is present
(AuthContextMiddleware), else the client's anonymous session id. The
client fingerprint is hashed (sha256 of remote address + user agent);
raw values are never stored.
"""
import hashlib
import html
import json
import re
import uuid
from datetime import datetime, timezone

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from terms.terms_basis import TermsAcceptance, TermsDocument


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def body_hash(text):
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


def _md_to_html(md):
    """The small Markdown the seeded terms use: ## headings, paragraphs, - lists."""
    out, para, in_list = [], [], False

    def flush():
        if para:
            out.append('<p>%s</p>' % html.escape(' '.join(para)))
            para.clear()
    for line in (md or '').split('\n'):
        s = line.strip()
        if s.startswith('- '):
            flush()
            if not in_list:
                out.append('<ul>'); in_list = True
            out.append('<li>%s</li>' % html.escape(s[2:]))
            continue
        if in_list:
            out.append('</ul>'); in_list = False
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            flush(); out.append('<h%d>%s</h%d>' % (len(m.group(1)) + 1, html.escape(m.group(2)), len(m.group(1)) + 1))
        elif not s:
            flush()
        else:
            para.append(s)
    flush()
    if in_list:
        out.append('</ul>')
    return '\n'.join(out)


class TermsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/terms/active', self, suffix='active')
            add('/api/terms/status', self, suffix='status')
            add('/api/terms/accept', self, suffix='accept')
            add('/terms/{name}', self, suffix='page')

    # -- rows ----------------------------------------------------------
    def _table(self, class_name):
        return (getattr(self.manager, 'objectTables', None) or {}).get(class_name, {})

    def _documents(self, app=''):
        docs = []
        for row in self._table('TermsDocument').values():
            if not getattr(row, 'active', False):
                continue
            scope = getattr(row, 'scope', 'global')
            if scope == 'app' and getattr(row, 'app_name', '') != (app or ''):
                continue
            docs.append(row)
        docs.sort(key=lambda r: (0 if getattr(r, 'kind', '') == 'demo' else 1, getattr(r, 'name', '')))
        return docs

    def _document(self, name):
        for row in self._table('TermsDocument').values():
            if getattr(row, 'name', '') == name:
                return row
        return None

    def _subject(self, request, session):
        info = getattr(request.context, 'user_info', None) or {}
        sub = info.get('sub') if isinstance(info, dict) else None
        if sub:
            return str(sub), 'user'
        return (session or ''), 'anonymous'

    def _accepted(self, doc, subject):
        if not subject:
            return False
        for row in self._table('TermsAcceptance').values():
            if (getattr(row, 'terms_name', '') == doc.name and getattr(row, 'terms_version', '') == doc.version
                    and getattr(row, 'subject', '') == subject):
                return True
        return False

    def _doc_payload(self, doc, subject):
        return {'name': doc.name, 'title': doc.title, 'kind': doc.kind, 'scope': doc.scope,
                'app_name': doc.app_name, 'version': doc.version,
                'requires_acceptance': bool(doc.requires_acceptance), 'show_bar': bool(doc.show_bar),
                'bar_text': doc.bar_text, 'summary': doc.summary, 'body_md': doc.body_md,
                'body_sha256': body_hash(doc.body_md), 'effective_at': doc.effective_at,
                'contact': doc.contact, 'page': '/terms/%s' % doc.name,
                'accepted': (not doc.requires_acceptance) or self._accepted(doc, subject)}

    # -- handlers ------------------------------------------------------
    def on_get_active(self, request, response):
        app = request.get_param('app') or ''
        session = request.get_param('session') or ''
        subject, kind = self._subject(request, session)
        docs = [self._doc_payload(d, subject) for d in self._documents(app)]
        response.media = {'ok': True, 'app': app, 'subject_kind': kind,
                          'documents': docs,
                          'pending': [d['name'] for d in docs if d['requires_acceptance'] and not d['accepted']],
                          'show_bar': any(d['show_bar'] for d in docs),
                          'bar_text': next((d['bar_text'] for d in docs if d['show_bar'] and d['bar_text']), '')}

    def on_get_status(self, request, response):
        app = request.get_param('app') or ''
        session = request.get_param('session') or ''
        subject, kind = self._subject(request, session)
        docs = self._documents(app)
        response.media = {'ok': True, 'subject_kind': kind,
                          'documents': [{'name': d.name, 'version': d.version,
                                         'accepted': (not d.requires_acceptance) or self._accepted(d, subject)} for d in docs]}

    def on_post_accept(self, request, response):
        body = request.get_media() or {}
        name = str(body.get('terms_name', ''))
        version = str(body.get('terms_version', ''))
        sha = str(body.get('body_sha256', ''))
        session = str(body.get('session', '')) or ''
        app = str(body.get('app', '')) or ''
        doc = self._document(name)
        if doc is None or not doc.active:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no active terms document named %r' % name}
            return
        if version != doc.version or sha != body_hash(doc.body_md):
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'error': 'the version/text accepted is not the one this instance serves — reload and read the current terms',
                              'current_version': doc.version, 'current_sha256': body_hash(doc.body_md)}
            return
        subject, kind = self._subject(request, session)
        if not subject:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'an acceptance needs a subject: a logged-in user or an anonymous terms session id'}
            return
        fingerprint = hashlib.sha256(('%s|%s' % (request.remote_addr or '', request.user_agent or '')).encode('utf-8')).hexdigest()
        row = TermsAcceptance(name='%s@%s@%s' % (name, subject[:24], uuid.uuid4().hex[:8]),
                              terms_name=name, terms_version=version, body_sha256=sha,
                              subject=subject, subject_kind=kind, client_session=session, app_name=app,
                              accepted_at=_now(), method='clickwrap', client_hash=fingerprint,
                              manager=self.manager)
        db = getattr(self.manager, 'db', None)
        if db is not None:
            try:
                db.saveInstanceInDB(row)
            except Exception:  # noqa: BLE001
                pass
        response.media = {'ok': True, 'accepted': {'terms_name': name, 'terms_version': version,
                                                   'subject_kind': kind, 'accepted_at': row.accepted_at,
                                                   'record': row.name}}

    def on_get_page(self, request, response, name):
        doc = self._document(name)
        if doc is None:
            response.status = falcon.HTTP_404
            response.content_type = 'text/plain; charset=utf-8'
            response.text = 'no terms document named %s' % name
            return
        response.content_type = 'text/html; charset=utf-8'
        response.text = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>%s</title>'
                         '<meta name="viewport" content="width=device-width, initial-scale=1">'
                         '<style>body{font-family:system-ui,sans-serif;max-width:72ch;margin:2rem auto;padding:0 1rem;line-height:1.55;color:#212529;background:#fff}'
                         'h1{font-size:1.8rem}h2{font-size:1.2rem;margin-top:1.6rem}.meta{color:#555b62;font-size:.9rem}</style></head><body>'
                         '<h1>%s</h1><p class="meta">Version %s%s · %s%s</p>%s'
                         '<p class="meta">Text sha256 %s</p></body></html>') % (
            html.escape(doc.title), html.escape(doc.title), html.escape(doc.version),
            (' · effective %s' % html.escape(doc.effective_at)) if doc.effective_at else '',
            'active' if doc.active else 'not active',
            (' · contact: %s' % html.escape(doc.contact)) if doc.contact else '',
            _md_to_html(doc.body_md), body_hash(doc.body_md))
