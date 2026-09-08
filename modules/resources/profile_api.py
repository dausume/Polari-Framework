"""
@cross-cutting
@module resources.profile_api

ResourceProfilesAPI (res-2): the resource-profile surface. Reads
serve the admission advisor (res-4) and the Topology tab; writes are
declare/classify/import-from-capability — knobs and cached evidence,
never auto-applied placement.

@consumers
  - polariServer (instantiated next to NodeResourcesAPI)
  - resources.profiles_selftest (handler-level, fake manager)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from resources.custom.profile_analysis import (
    classify_module, declared_profile, find_profile,
    import_engine_profile, profile_dict, recommend_backend,
)


class ResourceProfilesAPI(treeObject):
    """Module/engine resource-profile endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/resources/profiles'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/resources/profiles', self, suffix='catalogue')
            add('/api/modules/{module_name}/resource-profile', self,
                suffix='profile')
            add('/api/modules/{module_name}/classify', self,
                suffix='classify')
            add('/api/resources/engine-profile', self,
                suffix='engine_profile')
            add('/api/resources/measure', self, suffix='measure')

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    # ---- reads ------------------------------------------------------

    def on_get_catalogue(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        rows = (tables.get('ModuleResourceProfile') or {}).values()
        response.media = {'ok': True, 'profiles': sorted(
            (profile_dict(p) for p in rows),
            key=lambda d: d['subjectName'])}

    def on_get_profile(self, request, response, module_name):
        """The subject's profile — creates a declared one on first
        ask (a knob row the admin can then edit)."""
        existing = find_profile(self.manager, module_name)
        if existing is not None:
            response.media = {'ok': True, 'created': False,
                              'profile': profile_dict(existing)}
            return
        report = declared_profile(self.manager, module_name)
        if not report.get('ok'):
            return self._refuse(response, report.get('error'))
        media = {'ok': True, 'created': report['created'],
                 'profile': profile_dict(report['profile'])}
        if 'classification' in report:
            media['classification'] = report['classification']
        response.media = media

    # ---- classification + import --------------------------------------

    def on_post_classify(self, request, response, module_name):
        verdict = classify_module(self.manager, module_name)
        existing = find_profile(self.manager, module_name)
        if existing is not None and getattr(
                existing, 'fidelity', '') != 'measured':
            existing.character = verdict['character']
            if verdict['character'] == 'data' and not getattr(
                    existing, 'recommended_backend', ''):
                existing.recommended_backend = recommend_backend(
                    existing)['backend']
            try:
                self.manager.db.saveInstanceInDB(existing)
            except Exception:
                pass
            verdict['profileUpdated'] = True
        response.media = verdict

    def on_post_engine_profile(self, request, response):
        """Cache a live worker's /capability resources block:
        {service_kind, url?}."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        kind = (payload or {}).get('service_kind', '')
        if not kind:
            return self._refuse(response,
                                'payload needs {service_kind}')
        report = import_engine_profile(
            self.manager, kind, url=(payload or {}).get('url', ''))
        if not report.get('ok'):
            response.status = '409 Conflict'
            response.media = report
            return
        report['profile'] = profile_dict(report['profile'])
        response.media = report

    def on_post_measure(self, request, response):
        """res-3: measure what CAN be measured for a subject —
        {subject, url?} — measured overrides declared, honest
        absence for the rest."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        subject = (payload or {}).get('subject', '')
        if not subject:
            return self._refuse(response, 'payload needs {subject}')
        from resources.custom.profile_measure import measure_subject
        report = measure_subject(
            self.manager, subject, url=(payload or {}).get('url', ''))
        if not report.get('ok'):
            response.status = '409 Conflict'
        response.media = report
