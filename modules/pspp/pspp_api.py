"""
@module pspp.pspp_api

HTTP surface for the PSPP views (PeersAPI pattern — self-registering
falcon routes). Thin over pspp_views/progress_engine; every payload
carries its evidence and refusals render as refusals.

  GET  /api/pspp/datasets                    dataset catalog
  GET  /api/pspp/datasets/{name}/curve       chart-ready curve + bands
  GET  /api/pspp/network                     reaction-network graph
  GET  /api/pspp/states/{material}           MaterialState DAG
  GET  /api/pspp/progress?mr=&t=&hours=      cure-progress v1
  POST /api/pspp/grade                       composition → windows
  GET  /api/pspp/pathways?cation=&mr=&site=  kinetics-free reachability
  POST /api/pspp/guide                       experiment guidance
  POST /api/pspp/checkpoint                  cure checkpoint plan/apply
  GET  /api/pspp/benchmarks                  benchmark-case catalog
  GET  /api/pspp/benchmarks/{name}/overlay   measured vs predicted
  GET  /api/pspp/wax-states                  pspp-11 wax state routes
  GET  /api/pspp/structure/groups            most-likely motifs (gsp-1/4)
  POST /api/pspp/structure/sample            ensemble sample (gsp-2)
  POST /api/pspp/structure/scene             sample -> SimSpace (gsp-3)
  POST /api/pspp/structure/stepped-groups    stepped Q dist (gsp-4b)
  POST /api/pspp/structure/xrd               Debye halo (gsp-5)
  GET  /api/pspp/solgel/routes               acid/base fork demos (sg-5)
  POST /api/pspp/solgel/stepped              sol-gel stepped Q dist
  GET  /api/pspp/solgel/sources              precursor sourcing + subs
  GET  /api/pspp/solgel/community-routes     accessible-route rollups
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.cure_checkpoints import (
    apply_cure_checkpoint, plan_cure_checkpoint,
)
from pspp.experiment_guidance import experiment_guide
from pspp.network_stepping import (
    reachable_frameworks, solution_inventory,
)
from pspp.pspp_views import (
    dataset_catalog, dataset_curve, grade_payload, network_graph,
    state_dag,
)
from pspp.progress_engine import cure_progress
from pspp.structure_groups import most_likely_groups, stepped_groups
from pspp.structure_sampling import build_geopolymer_sample
from pspp.structure_scene import (
    geopolymer_materials, scene_definition, scene_name,
)
from pspp.structure_validation import simulated_halo
from pspp.solgel_structure import (
    solgel_route_demo, solgel_stepped_groups,
)
from pspp.solgel_sourcing import (
    COMMUNITY_ROUTES, SEED_PRECURSOR_SOURCES, route_accessibility,
    route_report, substitution_map,
)


class PsppAPI(treeObject):
    """PSPP dataset/network/grading/progress endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/pspp'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/pspp/datasets', self, suffix='datasets')
            add('/api/pspp/datasets/{name}/curve', self,
                suffix='curve')
            add('/api/pspp/network', self, suffix='network')
            add('/api/pspp/states/{material}', self, suffix='states')
            add('/api/pspp/progress', self, suffix='progress')
            add('/api/pspp/grade', self, suffix='grade')
            add('/api/pspp/pathways', self, suffix='pathways')
            add('/api/pspp/guide', self, suffix='guide')
            add('/api/pspp/checkpoint', self, suffix='checkpoint')
            add('/api/pspp/benchmarks', self, suffix='benchmarks')
            add('/api/pspp/benchmarks/{name}/overlay', self,
                suffix='overlay')
            add('/api/pspp/wax-states', self, suffix='wax_states')
            add('/api/pspp/structure/groups', self,
                suffix='structure_groups')
            add('/api/pspp/structure/sample', self,
                suffix='structure_sample')
            add('/api/pspp/structure/scene', self,
                suffix='structure_scene')
            add('/api/pspp/structure/stepped-groups', self,
                suffix='structure_stepped')
            add('/api/pspp/structure/xrd', self,
                suffix='structure_xrd')
            add('/api/pspp/solgel/routes', self,
                suffix='solgel_routes')
            add('/api/pspp/solgel/stepped', self,
                suffix='solgel_stepped')
            add('/api/pspp/solgel/sources', self,
                suffix='solgel_sources')
            add('/api/pspp/solgel/community-routes', self,
                suffix='solgel_community')

    # -- community sourcing surface (MTT2 sg-community) --

    def on_get_solgel_sources(self, request, response):
        """Precursor sourcing catalog + the substitution map ('what
        common material replaces this lab input?'). Reads live
        PrecursorSource rows when present, else the seeds."""
        sources = self._live('PrecursorSource', SEED_PRECURSOR_SOURCES)
        response.media = {
            'ok': True,
            'sources': [
                {'name': self._g(s, 'name'),
                 'displayName': self._g(s, 'display_name'),
                 'speciesRef': self._g(s, 'species_ref'),
                 'tier': self._g(s, 'accessibility_tier'),
                 'claimStatus': self._g(s, 'claim_status'),
                 'derivation': self._g(s, 'derivation'),
                 'source': self._g(s, 'source_reference')}
                for s in sources],
            'substitutionMap': substitution_map(sources),
        }

    def on_get_solgel_community(self, request, response):
        """Accessible-route rollups. ?route=<name> returns the full
        report (sourcing + accessibility + chemistry); no route lists
        every route's accessibility rollup."""
        sources = self._live('PrecursorSource', SEED_PRECURSOR_SOURCES)
        route = request.get_param('route')
        if route:
            payload = route_report(route, sources=sources)
            if not payload.get('ok'):
                response.status = '404 Not Found'
            response.media = payload
            return
        response.media = {
            'ok': True,
            'routes': {name: route_accessibility(name, sources=sources)
                       for name in COMMUNITY_ROUTES},
        }

    @staticmethod
    def _g(row, key, default=''):
        return (row.get(key, default) if isinstance(row, dict)
                else getattr(row, key, default))

    # -- sol-gel library surface (MTT2_SOLGEL_SINTERING_PLAN sg-5) --

    def on_get_solgel_routes(self, request, response):
        """The acid/base catalysis-fork demos: ?route=acid|base (omit
        for both), &nTetrahedra=&seed=&sample=false to skip the
        cluster/halo."""
        want_sample = (request.get_param('sample') or '') != 'false'
        n = request.get_param_as_int('nTetrahedra') or 80
        seed = request.get_param_as_int('seed') or 1
        route = request.get_param('route')
        if route:
            response.media = solgel_route_demo(
                route, n_tetrahedra=n, seed=seed, sample=want_sample)
            return
        response.media = {
            'ok': True,
            'routes': {r: solgel_route_demo(
                r, n_tetrahedra=n, seed=seed, sample=want_sample)
                for r in ('acid', 'base')},
        }

    def on_post_solgel_stepped(self, request, response):
        """{r, ph, steps:[{rule,times}], alkoxide?, amount?} ->
        sol-gel Q-motif fractions after scientist-driven steps."""
        body = request.media if request.content_length else {}
        payload = solgel_stepped_groups(
            body.get('r'), body.get('ph', 7.0),
            steps=body.get('steps') or [],
            alkoxide=body.get('alkoxide') or 'teos',
            amount=float(body.get('amount', 100.0)))
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def on_get_datasets(self, request, response):
        response.media = dataset_catalog(self.manager)

    def on_get_curve(self, request, response, name):
        samples = request.get_param_as_int('samples') or 60
        payload = dataset_curve(self.manager, name,
                                samples=max(8, min(samples, 400)))
        if not payload.get('ok'):
            response.status = '404 Not Found'
        response.media = payload

    def on_get_network(self, request, response):
        response.media = network_graph(self.manager)

    def on_get_states(self, request, response, material):
        response.media = state_dag(self.manager, material)

    def on_get_progress(self, request, response):
        try:
            mr = float(request.get_param('mr') or '')
        except ValueError:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'mr must be a number'}
            return
        temperature = request.get_param('t')
        hours = request.get_param('hours')
        payload = cure_progress(
            self.manager, mr,
            cure_temperature_c=float(temperature) if temperature
            else 80.0,
            hours=float(hours) if hours else 6.0)
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def on_get_benchmarks(self, request, response):
        from pspp.benchmark_cases import benchmark_catalog
        response.media = benchmark_catalog(self.manager)

    def on_get_overlay(self, request, response, name):
        from pspp.benchmark_cases import benchmark_overlay_by_name
        payload = benchmark_overlay_by_name(self.manager, name)
        if not payload.get('ok'):
            response.status = '404 Not Found'
        response.media = payload

    def on_get_wax_states(self, request, response):
        from pspp.wax_states import wax_state_map
        payload = wax_state_map(self.manager)
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def _live(self, table, seeds):
        from pspp.pspp_views import _seed_or_rows
        return _seed_or_rows(self.manager, table, seeds)

    def on_get_pathways(self, request, response):
        from pspp.reaction_network import SEED_REACTION_RULES
        from pspp.threshold_windows import SEED_THRESHOLD_WINDOWS
        cation = request.get_param('cation') or ''
        try:
            mr = float(request.get_param('mr') or '')
        except ValueError:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'mr must be a number',
                              'suggestion': '?cation=Na&mr=1.0'}
            return
        from pspp.pspp_views import _datasets
        inventory = solution_inventory(cation, mr,
                                       datasets=_datasets(self.manager))
        if not inventory.get('ok'):
            response.status = '422 Unprocessable Entity'
            response.media = inventory
            return
        payload = reachable_frameworks(
            inventory['inventory'],
            rules=self._live('ReactionRule', SEED_REACTION_RULES),
            site=request.get_param('site'),
            conditions={'MR': mr},
            windows=self._live('ThresholdReactionWindow',
                               SEED_THRESHOLD_WINDOWS),
            cation=cation)
        payload['inventory'] = inventory['inventory']
        payload['inventoryAssumptions'] = inventory['assumptions']
        response.media = payload

    def on_post_guide(self, request, response):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'body must be JSON'}
            return
        mr = body.get('mr')
        response.media = experiment_guide(
            self.manager,
            composition=body.get('composition'),
            basis=body.get('basis', 'mass'),
            family=body.get('family', ''),
            cation=body.get('cation', ''),
            mr=float(mr) if mr is not None else None,
            cure_temperature_c=float(body.get('t', 80.0)),
            site=body.get('site'))

    def on_post_checkpoint(self, request, response):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'body must be JSON'}
            return
        material = body.get('material', '')
        mr = body.get('mr')
        if not material or mr is None:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'material and mr are '
                                         'required',
                              'suggestion': '{"material": "...", '
                                            '"mr": 1.83, "apply": '
                                            'false}'}
            return
        run = (apply_cure_checkpoint if body.get('apply')
               else plan_cure_checkpoint)
        payload = run(self.manager, material, float(mr),
                      cure_temperature_c=float(body.get('t', 80.0)),
                      state_name=body.get('state_name', ''),
                      parent_state=body.get('parent_state'))
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def on_post_grade(self, request, response):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'body must be JSON'}
            return
        payload = grade_payload(
            self.manager, body.get('composition'),
            basis=body.get('basis', 'mass'),
            family=body.get('family', ''))
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    # -- gsp structure surface (GEOPOLYMER_STRUCTURE_SAMPLING_PLAN) --

    def on_get_structure_groups(self, request, response):
        mr = request.get_param_as_float('mr')
        payload = most_likely_groups(
            manager=self.manager,
            material=request.get_param('material'),
            state=request.get_param('state'),
            cation=request.get_param('cation'),
            mr=mr,
            physical_state=request.get_param('physicalState')
            or 'glass')
        response.media = payload

    def _fractions_from_body(self, body):
        """(fractions, source) from an explicit qFractions dict or a
        groups query (material/state | cation+mr) | refusal dict."""
        explicit = body.get('qFractions')
        if explicit:
            return ({k: float(v) for k, v in explicit.items()},
                    {'mode': 'explicit'})
        groups = most_likely_groups(
            manager=self.manager,
            material=body.get('material'),
            state=body.get('state'),
            cation=body.get('cation'),
            mr=body.get('mr'),
            physical_state=body.get('physicalState') or 'glass')
        if not groups.get('ok'):
            return None, groups
        fractions = {g['motif']: g['fraction']
                     for g in groups['groups']}
        source = {'mode': groups['mode'],
                  'caveats': groups.get('caveats') or [],
                  'evidence': groups.get('evidence')}
        if groups['mode'] == 'state':
            source['stateKey'] = groups['stateKey']
        else:
            source.update({'cation': groups['cation'],
                           'MR': groups['MR'],
                           'physicalState': groups['physicalState']})
        return fractions, source

    def _build_sample(self, body):
        fractions, source = self._fractions_from_body(body)
        if fractions is None:
            return None, source
        sample = build_geopolymer_sample(
            fractions,
            n_tetrahedra=int(body.get('nTetrahedra', 60)),
            seed=int(body.get('seed', 1)),
            cation=body.get('cation') or 'Na',
            si_al_ratio=body.get('siAlRatio'),
            target_density_g_cm3=body.get('targetDensity', 2.0))
        if sample.get('ok'):
            sample['groupsSource'] = source
        return sample, None

    def on_post_structure_sample(self, request, response):
        body = request.media if request.content_length else {}
        sample, refusal = self._build_sample(body)
        if sample is None:
            response.status = '422 Unprocessable Entity'
            response.media = refusal
            return
        if not sample.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = sample

    def on_post_structure_scene(self, request, response):
        body = request.media if request.content_length else {}
        sample, refusal = self._build_sample(body)
        if sample is None or not sample.get('ok'):
            response.status = '422 Unprocessable Entity'
            response.media = refusal or sample
            return
        name = scene_name(
            body.get('cation') or 'Na', mr=body.get('mr'),
            state_key=(sample['groupsSource'].get('stateKey')
                       if isinstance(sample.get('groupsSource'), dict)
                       else None),
            seed=body.get('seed', 1))
        kwargs = {}
        if 'atomScale' in body:
            kwargs['atom_scale'] = float(body['atomScale'])
        if 'bondRadius' in body:
            kwargs['bond_radius'] = float(body['bondRadius'])
        verdict = scene_definition(sample, name, **kwargs)
        if not verdict['ok']:
            response.status = '422 Unprocessable Entity'
            response.media = verdict
            return
        materials_added = self._ensure_materials(
            geopolymer_materials(sample))
        action, persisted = self._upsert_scene(verdict['scene'])
        response.media = {
            'ok': True, 'sceneName': name, 'action': action,
            'persisted': persisted,
            'materialsAdded': materials_added,
            'counts': {**verdict['counts'], **sample['counts']},
            'density': sample.get('density'),
            'targetQ': sample['targetQ'],
            'achievedQ': sample['achievedQ'],
            'honesty': sample['honesty'],
            'groupsSource': sample['groupsSource'],
            'seed': sample['seed'],
        }

    def on_post_structure_stepped(self, request, response):
        """gsp-4b: groups after scientist-driven network steps."""
        body = request.media if request.content_length else {}
        if body.get('mr') is None:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'mr is required',
                              'suggestion': '{"cation": "Na", "mr": '
                                            '2.0, "steps": [{"rule": '
                                            '"...", "times": 1}]}'}
            return
        payload = stepped_groups(
            body.get('cation') or 'Na', float(body['mr']),
            steps=body.get('steps') or [],
            site=body.get('site'),
            conditions=body.get('conditions'))
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def on_post_structure_xrd(self, request, response):
        """gsp-5: Debye halo of a sampled cluster (same sampling
        params as /sample; the cluster is rebuilt deterministically)."""
        body = request.media if request.content_length else {}
        sample, refusal = self._build_sample(body)
        if sample is None or not sample.get('ok'):
            response.status = '422 Unprocessable Entity'
            response.media = refusal or sample
            return
        verdict = simulated_halo(
            sample,
            wavelength=body.get('wavelength') or 'CuKa',
            two_theta_max=float(body.get('twoThetaMax', 60.0)),
            points=int(body.get('points', 240)))
        if not verdict.get('ok'):
            response.status = '422 Unprocessable Entity'
            response.media = verdict
            return
        verdict['seed'] = sample['seed']
        verdict['achievedQ'] = sample['achievedQ']
        verdict['groupsSource'] = sample['groupsSource']
        response.media = verdict

    def _ensure_materials(self, rows):
        """Create any missing Material3DDefinition rows; returns the
        names added."""
        table = (getattr(self.manager, 'objectTables', None)
                 or {}).get('Material3DDefinition', {})
        existing_rows = (table.values() if isinstance(table, dict)
                         else table)
        existing = {getattr(r, 'name', '') for r in existing_rows}
        db = getattr(self.manager, 'db', None)
        added = []
        from simSpace3D.material_3d_definition import (
            Material3DDefinition,
        )
        for row in rows:
            if row['name'] in existing:
                continue
            instance = Material3DDefinition(**row,
                                            manager=self.manager)
            if db is not None:
                try:
                    db.saveInstanceInDB(instance)
                except Exception:
                    pass
            added.append(row['name'])
        return added

    def _upsert_scene(self, scene):
        """Create or rewrite the SimSpaceDefinition for one scene
        (crystal on_post_scene pattern)."""
        table = (getattr(self.manager, 'objectTables', None)
                 or {}).get('SimSpaceDefinition', {})
        rows = table.values() if isinstance(table, dict) else table
        existing = next(
            (r for r in rows
             if getattr(r, 'name', '') == scene['name']), None)
        if existing is None:
            from simSpace.sim_space_definition import (
                SimSpaceDefinition,
            )
            existing = SimSpaceDefinition(**scene,
                                          manager=self.manager)
            action = 'created'
        else:
            existing.definition = scene['definition']
            existing.viewport_json = scene['viewport_json']
            existing.description = scene['description']
            action = 'updated'
        persisted = False
        db = getattr(self.manager, 'db', None)
        if db is not None:
            try:
                persisted = bool(db.saveInstanceInDB(existing))
            except Exception:
                persisted = False
        return action, persisted
