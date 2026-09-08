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
  POST /api/pspp/sinter/fire                 MSC densify + grain + L2
  GET  /api/pspp/sinter/master-curves        available master curves
  GET  /api/pspp/ceramics/samples            samples + temp ladder
  GET  /api/pspp/ceramics/ladder             furnace escalation ladder
  POST /api/pspp/sinter/stages               sample a firing in stages
  GET  /api/pspp/ceramics/geopolymer-transition  geopolymer->ceramic
  GET  /api/pspp/characterization/methods    XRD + FTIR explainers
  POST /api/pspp/characterization/ftir       simulated FTIR bands
  GET  /api/pspp/research-tools              buildable instruments
  GET  /api/pspp/glass/refinement            viscosity fit + windows
  POST /api/pspp/sinter/viscous              viscous (glass) firing
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.custom.cure_checkpoints import (
    apply_cure_checkpoint, plan_cure_checkpoint,
)
from pspp.custom.experiment_guidance import experiment_guide
from pspp.custom.network_stepping import (
    reachable_frameworks, solution_inventory,
)
from pspp.custom.pspp_views import (
    dataset_catalog, dataset_curve, grade_payload, network_graph,
    state_dag,
)
from pspp.custom.progress_engine import cure_progress
from pspp.custom.structure_groups import most_likely_groups, stepped_groups
from pspp.custom.structure_sampling import build_geopolymer_sample
from pspp.custom.structure_scene import (
    geopolymer_materials, scene_definition, scene_name,
)
from pspp.custom.structure_validation import simulated_halo
from pspp.custom.solgel_structure import (
    solgel_route_demo, solgel_stepped_groups,
)
from pspp.solgel_sourcing_basis import (
    COMMUNITY_ROUTES, SEED_PRECURSOR_SOURCES, route_accessibility,
    route_report, substitution_map,
)
from pspp.custom.sintering_engine import (
    grain_size, relative_density, sinter_stages, work_of_sintering,
)
from pspp.custom.geopolymer_ceramic_transition import transition_stages
from pspp.characterization_seed import (
    characterization_methods, simulated_ftir,
)
from pspp.research_tools_basis import SEED_RESEARCH_TOOLS, research_tools
from pspp.custom.sintering_structure import plan_sinter_structure
from pspp.custom.glass_refinement import (
    GLASS_THRESHOLD_WINDOWS, process_map, refinement_report,
)
from pspp.custom.viscous_sintering import viscous_fire
from pspp.ceramics_samples_basis import (
    SEED_CERAMIC_SAMPLES, samples_meeting_temp, temperature_ladder,
    validate_samples,
)
from pspp.ceramics_ladder_basis import (
    SEED_LADDER_RUNGS, ladder_path, validate_ladder,
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
            add('/api/pspp/sinter/fire', self, suffix='sinter_fire')
            add('/api/pspp/sinter/master-curves', self,
                suffix='sinter_curves')
            add('/api/pspp/ceramics/samples', self,
                suffix='ceramics_samples')
            add('/api/pspp/ceramics/ladder', self,
                suffix='ceramics_ladder')
            add('/api/pspp/sinter/stages', self,
                suffix='sinter_stages')
            add('/api/pspp/ceramics/geopolymer-transition', self,
                suffix='geopolymer_transition')
            add('/api/pspp/characterization/methods', self,
                suffix='char_methods')
            add('/api/pspp/characterization/ftir', self,
                suffix='char_ftir')
            add('/api/pspp/research-tools', self,
                suffix='research_tools')
            add('/api/pspp/glass/refinement', self,
                suffix='glass_refinement')
            add('/api/pspp/sinter/viscous', self,
                suffix='sinter_viscous')

    def on_get_char_methods(self, request, response):
        """XRD + FTIR as data — plain-language what/how, diagnostic
        signals, local-buildability + safety."""
        response.media = characterization_methods()

    def on_post_char_ftir(self, request, response):
        """Simulated FTIR diagnostic bands. Body: {siAlRatio?,
        hasWater?, hasCarbonate?}. Positions approximate; intensities
        refuse."""
        body = request.media if request.content_length else {}
        response.media = simulated_ftir(
            si_al_ratio=body.get('siAlRatio'),
            has_water=body.get('hasWater', True),
            has_carbonate=body.get('hasCarbonate', False))

    def on_get_research_tools(self, request, response):
        """Buildable open-source instruments (easiest first). ?domain=
        materials|food|water|soil|carbon filters. Reads live
        ResearchTool rows when present."""
        rows = self._live('ResearchTool', SEED_RESEARCH_TOOLS)
        response.media = research_tools(
            domain=request.get_param('domain'), samples=rows)

    def on_post_sinter_stages(self, request, response):
        """Sample a firing at N checkpoints — the ceramic at different
        stages during sintering. Body: {schedule, activationEnergy,
        masterCurve?, grain?, nStages?}. ρ/grain refuse in place where
        their calibration is absent (honest stage-by-stage)."""
        body = request.media if request.content_length else {}
        curve = self._master_curve(body.get('masterCurve'))
        payload = sinter_stages(
            body.get('schedule') or [], body.get('activationEnergy'),
            master_curve=curve, grain=body.get('grain'),
            n_stages=int(body.get('nStages', 5)))
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def on_get_geopolymer_transition(self, request, response):
        """The DATA-BACKED geopolymer -> ceramic thermal-conversion
        ladder (Table 8.8) + the glass branch. ?temperature=<C> reads
        the porosity/stage at one temperature."""
        temp = request.get_param_as_float('temperature')
        if temp is not None:
            from pspp.custom.geopolymer_ceramic_transition import porosity_at
            response.media = porosity_at(temp)
            return
        response.media = transition_stages()

    # -- ceramic samples + escalation ladder (MTT2 ceramics) --

    def on_get_ceramics_samples(self, request, response):
        """The ceramic sample ladder. Filters: ?minTemp=<C> (meets a
        service temp), ?local=true (drop the mined olivine track),
        ?carbonNegative=true. No filter = the whole temperature
        ladder. Reads live CeramicSample rows when present."""
        rows = self._live('CeramicSample', SEED_CERAMIC_SAMPLES)
        min_temp = request.get_param_as_float('minTemp')
        if min_temp is not None:
            response.media = samples_meeting_temp(
                min_temp, samples=rows,
                local_only=(request.get_param('local') == 'true'),
                carbon_negative_only=(
                    request.get_param('carbonNegative') == 'true'))
            return
        response.media = {
            'ok': True,
            'ladder': temperature_ladder(rows),
            'validation': validate_samples(rows),
            'note': 'ascending by max service temperature — the '
                    'gradual escalating temperature-resistance ladder; '
                    'temps are literature-approximate',
        }

    def on_get_ceramics_ladder(self, request, response):
        """The furnace escalation ladder (geopolymer oven -> '
        steelmaking) + its physical bootstrapping validation."""
        rungs = self._live('LadderRung', SEED_LADDER_RUNGS)
        samples = self._live('CeramicSample', SEED_CERAMIC_SAMPLES)
        response.media = {
            'ok': True,
            'rungs': ladder_path(rungs),
            'bootstrapCheck': validate_ladder(rungs, samples),
            'note': 'each rung is built from the output of the one '
                    'below it — the thermal strain of material '
                    'refinement, from a geopolymer oven up to a '
                    'steelmaking-capable basic-lined furnace',
        }

    # -- ceramic sintering surface (MTT2 Part B) --

    def _master_curve(self, name):
        """Resolve a master-curve DigitizedDataset by name from live
        rows -> the dataset_dict shape the engine reads; None if
        absent."""
        from pspp.digitized_datasets_basis import dataset_index
        return dataset_index(self.manager).get(name) if name else None

    def on_get_sinter_curves(self, request, response):
        """List the DigitizedDataset rows shaped as ρ(log10 Θ) master
        curves, with their readiness (provisional ones refuse)."""
        from pspp.digitized_datasets_basis import dataset_index
        curves = []
        for name, ds in dataset_index(self.manager).items():
            indep = ds.get('independentVariables') or []
            if 'relativeDensity' not in (
                    ds.get('dependentVariables') or []):
                continue
            if 'log10Theta' in indep:
                kind = 'solid-state'
            elif 'log10Lambda' in indep:
                kind = 'viscous'
            else:
                continue
            curves.append({
                'name': name, 'status': ds.get('status'),
                'kind': kind,
                'ready': ds.get('status') == 'ready'
                and bool(ds.get('points')),
                'source': ds.get('sourceReference')})
        response.media = {'ok': True, 'masterCurves': curves}

    def on_post_sinter_fire(self, request, response):
        """One firing: Θ always; ρ if a master curve resolves and Θ is
        in-range; grain size if kinetics are given; the L2 structure
        plan when both ρ and grain size exist. Every missing piece
        refuses in place — the engine invents no Q, curve, or kinetics.
        Body: {schedule, activationEnergy, masterCurve?, grain?:{d0,n,
        k0,Qg}, stateKey?, theoreticalDensity?}."""
        body = request.media if request.content_length else {}
        schedule = body.get('schedule') or []
        q = body.get('activationEnergy')
        out = {'ok': True}
        out['work'] = work_of_sintering(schedule, q)
        curve = self._master_curve(body.get('masterCurve'))
        out['density'] = relative_density(schedule, q, master_curve=curve)
        grain_in = body.get('grain') or {}
        if grain_in:
            out['grain'] = grain_size(
                schedule, grain_in.get('d0'), grain_in.get('n'),
                grain_in.get('k0'), grain_in.get('Qg'))
        density_ok = out['density'].get('ok')
        grain_ok = out.get('grain', {}).get('ok')
        if density_ok and grain_ok and body.get('stateKey'):
            out['structurePlan'] = plan_sinter_structure(
                body['stateKey'],
                out['density']['relativeDensity'],
                out['grain']['grainSizeUm'],
                theoretical_density_g_cm3=body.get('theoreticalDensity'))
        if not out['work'].get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = out

    # -- glass refinement + viscous sintering (MTT2 glass core) --

    def _glass_points(self):
        """Live soda-lime viscosity points when the dataset row has
        been edited; None falls back to the module seeds."""
        from pspp.digitized_datasets_basis import dataset_index
        ds = dataset_index(self.manager).get(
            'soda-lime-viscosity-reference-points')
        pts = (ds or {}).get('points') or []
        return pts if len(pts) >= 3 else None

    def _glass_windows(self):
        """Live silicate-glass banded windows when rows exist, else
        the module seeds."""
        rows = self._live('ThresholdReactionWindow',
                          GLASS_THRESHOLD_WINDOWS)
        mine = [w for w in rows
                if self._g(w, 'material_family') in
                ('silicate-glass',)
                or self._g(w, 'name').startswith('soda-lime-glass:')]
        return mine or GLASS_THRESHOLD_WINDOWS

    def on_get_glass_refinement(self, request, response):
        """The glass-refinement surface: reference points + the exact
        VFT fit (+ residual honesty) + process windows + the devit
        data ask. ?temperature=<C> grades every gate at that
        temperature instead."""
        points = self._glass_points()
        windows = self._glass_windows()
        temp = request.get_param_as_float('temperature')
        if temp is not None:
            from pspp.custom.glass_refinement import fit_vft
            response.media = process_map(
                temp, vft=fit_vft(points), windows=windows)
            return
        response.media = refinement_report(points=points,
                                           windows=windows)

    def on_post_sinter_viscous(self, request, response):
        """One VISCOUS (glass) firing: Λ always; ρ via master curve /
        Frenkel-while-valid / the refusal naming the asks; the MS
        final stage from a measured closed-pore checkpoint; the
        amorphous L2 plan. Body: {schedule, particleRadiusUm, gamma?,
        greenDensity?, masterCurve?, measured?:{density,
        poreRadiusUm}, stateKey?}."""
        body = request.media if request.content_length else {}
        curve = self._master_curve(body.get('masterCurve'))
        if body.get('masterCurve') and curve is None:
            response.status = '422 Unprocessable Entity'
            response.media = {
                'ok': False,
                'refusal': f"master curve {body['masterCurve']!r} "
                           'resolves to no DigitizedDataset row',
                'suggestion': 'GET /api/pspp/sinter/master-curves '
                              'lists the candidates'}
            return
        payload = viscous_fire(
            body.get('schedule') or [],
            body.get('particleRadiusUm'),
            gamma_n_per_m=body.get('gamma'),
            green_density=body.get('greenDensity'),
            master_curve=curve,
            measured=body.get('measured'),
            points=self._glass_points(),
            state_key=body.get('stateKey'))
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

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
        from pspp.benchmark_cases_basis import benchmark_catalog
        response.media = benchmark_catalog(self.manager)

    def on_get_overlay(self, request, response, name):
        from pspp.benchmark_cases_basis import benchmark_overlay_by_name
        payload = benchmark_overlay_by_name(self.manager, name)
        if not payload.get('ok'):
            response.status = '404 Not Found'
        response.media = payload

    def on_get_wax_states(self, request, response):
        from pspp.custom.wax_states import wax_state_map
        payload = wax_state_map(self.manager)
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def _live(self, table, seeds):
        from pspp.custom.pspp_views import _seed_or_rows
        return _seed_or_rows(self.manager, table, seeds)

    def on_get_pathways(self, request, response):
        from pspp.reaction_network_basis import SEED_REACTION_RULES
        from pspp.threshold_windows_basis import SEED_THRESHOLD_WINDOWS
        cation = request.get_param('cation') or ''
        try:
            mr = float(request.get_param('mr') or '')
        except ValueError:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'mr must be a number',
                              'suggestion': '?cation=Na&mr=1.0'}
            return
        from pspp.custom.pspp_views import _datasets
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
