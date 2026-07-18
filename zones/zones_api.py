"""
@module zones.zones_api

HTTP surface for AR zone capture (self-registering, authority_api
pattern). The headset flow is ONE write: POST /api/zones/capture with
the zone header + every placed point; everything after that is reads
and knob-bearing analysis calls.

@consumers polariServer (instantiated beside the other module APIs)
@see /AR_ZONE_CAPTURE_PLAN.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class ZonesAPI(treeObject):
    """Zone capture, estimation, packing, site summaries."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/zones'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/zones/capture', self, suffix='capture')
            polServer.falconServer.add_route(
                '/api/zones/{name}/estimate', self, suffix='estimate')
            polServer.falconServer.add_route(
                '/api/zones/{name}/distances', self,
                suffix='distances')
            polServer.falconServer.add_route(
                '/api/zones/{name}/pack', self, suffix='pack')
            polServer.falconServer.add_route(
                '/api/zones/{name}/calibrate', self,
                suffix='calibrate')
            polServer.falconServer.add_route(
                '/api/zones/{name}/constraints', self,
                suffix='constraints')
            polServer.falconServer.add_route(
                '/api/zones/{name}/to-simulation', self,
                suffix='to_simulation')
            polServer.falconServer.add_route(
                '/api/zones/{name}/room-summary', self,
                suffix='room_summary')
            polServer.falconServer.add_route(
                '/api/sites/{name}/summary', self,
                suffix='site_summary')

    def _payload(self, request, response):
        try:
            return json.load(request.bounded_stream)
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return None

    def on_post_capture(self, request, response):
        from scoring.worldview_elections import _by_name
        from zones.zone_basis import (CAPTURE_MODES, POINT_KINDS,
                                      SiteDefinition, ZONE_ROLES,
                                      ZoneDefinition, ZonePoint)
        payload = self._payload(request, response)
        if payload is None:
            return
        name = payload.get('name', '')
        points = payload.get('points') or []
        if not name or not isinstance(points, list) or not points:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False,
                              'error': "capture needs 'name' and a "
                                       "non-empty 'points' list"}
            return
        if _by_name(self.manager, 'ZoneDefinition').get(name) \
                is not None:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False,
                              'error': f"a ZoneDefinition named "
                                       f"'{name}' already exists"}
            return
        mode = payload.get('capture_mode', 'planar')
        if mode not in CAPTURE_MODES:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False,
                              'error': f'capture_mode must be one of '
                                       f'{CAPTURE_MODES}'}
            return
        role = payload.get('zone_role', 'selection')
        if role not in ZONE_ROLES:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False,
                              'error': f'zone_role must be one of '
                                       f'{ZONE_ROLES}'}
            return
        bad = [i for i, p in enumerate(points)
               if not isinstance(p, dict)
               or p.get('kind', 'ground') not in POINT_KINDS
               or any(not isinstance(p.get(a), (int, float))
                      for a in ('x', 'y', 'z'))]
        if bad:
            response.status = '422 Unprocessable Entity'
            response.media = {'ok': False,
                              'error': f'points {bad} need numeric '
                                       "x/y/z and a kind in "
                                       f'{POINT_KINDS}'}
            return
        site_name = payload.get('site_name', '')
        site_created = False
        if site_name and _by_name(self.manager,
                                  'SiteDefinition').get(site_name) \
                is None:
            site = SiteDefinition(
                name=site_name, display_name=site_name,
                notes='auto-created on first zone capture',
                manager=self.manager)
            self._save(site)
            site_created = True
        zone = ZoneDefinition(
            name=name,
            display_name=payload.get('display_name', name),
            site_name=site_name,
            room_label=payload.get('room_label', ''),
            zone_role=role,
            room_zone_name=payload.get('room_zone_name', ''),
            # Selections tie to a simulation; rooms are shared
            # reality and stay untied.
            simulation_ref=(payload.get('simulation_ref', '')
                            if role == 'selection' else ''),
            capture_mode=mode,
            capture_kind=payload.get('capture_kind', 'ar-headset'),
            reference_space=payload.get('reference_space', ''),
            origin_note=payload.get('origin_note', ''),
            status='committed',
            captured_by=payload.get('captured_by', ''),
            notes=payload.get('notes', ''),
            manager=self.manager)
        self._save(zone)
        for i, p in enumerate(points):
            row = ZonePoint(
                name=f'{name}-p{i}', zone_name=name, index=i,
                kind=p.get('kind', 'ground'),
                x=float(p['x']), y=float(p['y']), z=float(p['z']),
                confidence=p.get('confidence', 'tracked'),
                notes=p.get('notes', ''), manager=self.manager)
            self._save(row)
        from zones.zone_geometry import estimate_zone
        response.media = {'ok': True, 'zone': name,
                          'pointCount': len(points),
                          'siteCreated': site_created,
                          'estimate': estimate_zone(self.manager,
                                                    name)}

    def _save(self, row):
        # treeObjectInit already registered the instance (under its
        # own key) — the identity guard prevents a second entry per
        # row (the term_competition._insert idiom).
        table = self.manager.objectTables.setdefault(
            type(row).__name__, {})
        if not any(existing is row for existing in table.values()):
            table[row.name] = row
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass  # in-memory managers (selftests) have no db

    def on_get_estimate(self, request, response, name):
        from zones.zone_geometry import estimate_zone
        try:
            default_height = float(
                request.get_param('default_height_m') or 0)
        except ValueError:
            default_height = 0.0
        report = estimate_zone(self.manager, name,
                               default_height_m=default_height)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_distances(self, request, response, name):
        from zones.zone_geometry import point_distances
        report = point_distances(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_pack(self, request, response, name):
        from zones.zone_packing import DEFAULT_CUBE_M, pack_zone
        payload = self._payload(request, response)
        if payload is None:
            return
        result = pack_zone(
            self.manager, name,
            cube_size_m=float(payload.get('cube_size_m')
                              or DEFAULT_CUBE_M),
            fit_test=payload.get('fit_test', 'full-cell'),
            default_height_m=float(payload.get('default_height_m')
                                   or 0))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_calibrate(self, request, response, name):
        from zones.zone_geometry import calibrate_zone
        payload = self._payload(request, response)
        if payload is None:
            return
        result = calibrate_zone(self.manager, name,
                                payload.get('known_length_m'))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_constraints(self, request, response, name):
        from zones.zone_sim_bridge import zone_constraints
        report = zone_constraints(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_to_simulation(self, request, response, name):
        from zones.zone_sim_bridge import zone_to_simulation
        payload = self._payload(request, response)
        if payload is None:
            return
        result = zone_to_simulation(
            self.manager, name,
            target_simulation_ref=payload.get(
                'target_simulation_ref', ''),
            target_class_name=payload.get('target_class_name', ''))
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_get_room_summary(self, request, response, name):
        from zones.zone_packing import DEFAULT_CUBE_M, room_summary
        try:
            cube = float(request.get_param('cube_size_m')
                         or DEFAULT_CUBE_M)
        except ValueError:
            cube = DEFAULT_CUBE_M
        report = room_summary(self.manager, name, cube_size_m=cube)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_site_summary(self, request, response, name):
        from zones.zone_packing import DEFAULT_CUBE_M, site_summary
        try:
            cube = float(request.get_param('cube_size_m')
                         or DEFAULT_CUBE_M)
        except ValueError:
            cube = DEFAULT_CUBE_M
        report = site_summary(self.manager, name, cube_size_m=cube)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
