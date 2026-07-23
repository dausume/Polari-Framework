"""
@cross-cutting
@module materialsScience.crystal_structure_api
@tags @xc:bindings

HTTP surface for crystal structures (ssp-1; PeersAPI pattern —
self-registering falcon routes):

  GET /api/msci/structures            every structure with headline
                                      facts (built on the fly; build
                                      refusals reported per row, never
                                      hidden)
  GET /api/msci/structures/{name}     one structure: row fields +
                                      facts + full atom list + bonds
  POST /api/msci/structures/{name}/scene
                                      regenerate the structure's 3D
                                      lattice SimSpaceDefinition from
                                      the CURRENT row (the explicit
                                      knob — editing a structure never
                                      silently rewrites its scene).
                                      Body knobs: supercell [nx,ny,nz],
                                      atomScale, bondRadius,
                                      ghostReplicas, cellEdges.
  POST /api/msci/structures/{name}/phonons
                                      ssp-4 lattice dynamics: phonon
                                      dispersion + DOS for this
                                      structure. Body: potential,
                                      npoints, usePrimitive, dosGrid,
                                      fitSigmaToStructure.
  POST /api/msci/structures/{name}/elastic
                                      ssp-4 cubic elastic constants
                                      (clamped-ion). Body: potential,
                                      delta, fitSigmaToStructure.
  POST /api/msci/structures/{name}/analyze
                                      ssp-3 symmetry detection on the
                                      msci-engines worker (pymatgen):
                                      space group, Wyckoff sites, and
                                      the declared-vs-detected
                                      suggestion. Body: symprec.
  POST /api/msci/structures/{name}/xrd
                                      ssp-3 simulated powder XRD
                                      pattern (worker). Body:
                                      wavelength, twoThetaMax, topN.

Reads are pure except the lazy cache: a successful detail build
refreshes the row's built_facts_json (object coherence — the built
structure is inspectable AT the row via CRUDE).

@consumers
  - the crystal-structure frontend view (ssp-2)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience import crystal_ops


def _structure_rows(manager):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'CrystalStructureDefinition', {})
    rows = table.values() if isinstance(table, dict) else (table or [])
    return [row for row in rows if getattr(row, 'enabled', True)]


def find_structure(manager, name):
    for row in _structure_rows(manager):
        if getattr(row, 'name', '') == name:
            return row
    return None


class CrystalStructureAPI(treeObject):
    """Crystal-structure list + detail endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/msci/structures'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/msci/structures', self)
            polServer.falconServer.add_route(
                '/api/msci/structures/{name}', self, suffix='detail')
            polServer.falconServer.add_route(
                '/api/msci/structures/{name}/scene', self,
                suffix='scene')
            polServer.falconServer.add_route(
                '/api/msci/structures/{name}/phonons', self,
                suffix='phonons')
            polServer.falconServer.add_route(
                '/api/msci/structures/{name}/elastic', self,
                suffix='elastic')
            polServer.falconServer.add_route(
                '/api/msci/structures/{name}/analyze', self,
                suffix='analyze')
            polServer.falconServer.add_route(
                '/api/msci/structures/{name}/xrd', self,
                suffix='xrd')

    def on_get(self, request, response):
        structures = []
        for row in _structure_rows(self.manager):
            entry = {
                'name': getattr(row, 'name', ''),
                'displayName': getattr(row, 'display_name', ''),
                'materialName': getattr(row, 'material_name', ''),
                'spaceGroup': getattr(row, 'space_group', 0),
                'description': getattr(row, 'description', ''),
            }
            verdict = crystal_ops.structure_facts(row)
            if verdict['ok']:
                entry['facts'] = verdict['facts']
            else:
                entry['buildError'] = verdict.get('error', '')
                entry['suggestion'] = verdict.get('suggestion')
            structures.append(entry)
        structures.sort(key=lambda s: s['name'])
        response.media = {'ok': True, 'count': len(structures),
                          'structures': structures}

    def on_get_detail(self, request, response, name):
        row = find_structure(self.manager, name)
        if row is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no CrystalStructureDefinition named "
                         f"'{name}'"}
            return
        report = crystal_ops.refresh_built_facts(row, self.manager)
        if not report['ok']:
            response.media = {'ok': False, 'name': name, **{
                k: v for k, v in report.items() if k != 'ok'}}
            return
        from materialsScience.crystal_snapshot import scene_name
        response.media = {
            'ok': True,
            'name': getattr(row, 'name', ''),
            'displayName': getattr(row, 'display_name', ''),
            'description': getattr(row, 'description', ''),
            'materialName': getattr(row, 'material_name', ''),
            'spaceGroup': getattr(row, 'space_group', 0),
            'spaceGroupSetting': getattr(row, 'space_group_setting', 1),
            'bondCutoffScale': getattr(row, 'bond_cutoff_scale', 1.15),
            'provenance': getattr(row, 'provenance_id', ''),
            'notes': getattr(row, 'notes', ''),
            'sceneName': scene_name(getattr(row, 'name', '')),
            'facts': report['facts'],
            'cell': report['cell'],
            'atoms': report['atoms'],
            'bonds': report['bonds'],
        }

    def on_post_scene(self, request, response, name):
        """Regenerate the lattice scene from the CURRENT row —
        creates the SimSpaceDefinition when absent, else rewrites its
        freestanding blob in place (same scene name, viewer refetch
        picks it up)."""
        from materialsScience import crystal_snapshot
        row = find_structure(self.manager, name)
        if row is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no CrystalStructureDefinition named "
                         f"'{name}'"}
            return
        body = request.media if request.content_length else {}
        supercell = tuple(body.get('supercell', (1, 1, 1)))
        kwargs = {}
        if 'atomScale' in body:
            kwargs['atom_scale'] = float(body['atomScale'])
        if 'bondRadius' in body:
            kwargs['bond_radius'] = float(body['bondRadius'])
        if 'ghostReplicas' in body:
            kwargs['ghost_replicas'] = bool(body['ghostReplicas'])
        if 'cellEdges' in body:
            kwargs['cell_edges'] = bool(body['cellEdges'])
        verdict = crystal_snapshot.scene_definition(
            row, supercell=supercell, **kwargs)
        if not verdict['ok']:
            response.media = {'ok': False, 'name': name, **{
                k: v for k, v in verdict.items() if k != 'ok'}}
            return
        scene = verdict['scene']
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
        response.media = {'ok': True, 'name': name,
                          'sceneName': scene['name'],
                          'action': action,
                          'counts': verdict['counts'],
                          'persisted': persisted}

    def _run_lattice_dynamics(self, request, response, name, kind):
        from materialsScience.engines import lattice_dynamics_engine
        row = find_structure(self.manager, name)
        if row is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no CrystalStructureDefinition named "
                         f"'{name}'"}
            return
        body = request.media if request.content_length else {}
        if kind == 'phonons':
            verdict = lattice_dynamics_engine.phonon_dispersion(
                row,
                potential=body.get('potential') or {},
                npoints=body.get('npoints'),
                use_primitive=bool(body.get('usePrimitive', True)),
                dos_grid=body.get('dosGrid'),
                fit_sigma=bool(body.get('fitSigmaToStructure',
                                        False)))
        else:
            verdict = lattice_dynamics_engine.elastic_constants(
                row,
                potential=body.get('potential') or {},
                delta=float(body.get('delta', 0.005)),
                fit_sigma=bool(body.get('fitSigmaToStructure',
                                        False)))
        verdict['structure'] = name
        response.media = verdict

    def on_post_phonons(self, request, response, name):
        self._run_lattice_dynamics(request, response, name, 'phonons')

    def on_post_elastic(self, request, response, name):
        self._run_lattice_dynamics(request, response, name, 'elastic')

    def on_post_analyze(self, request, response, name):
        from materialsScience import crystal_analysis
        row = find_structure(self.manager, name)
        if row is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no CrystalStructureDefinition named "
                         f"'{name}'"}
            return
        body = request.media if request.content_length else {}
        report = crystal_analysis.analyze(
            row, self.manager,
            symprec=float(body.get('symprec', 0.01) or 0.01))
        report['structure'] = name
        response.media = report

    def on_post_xrd(self, request, response, name):
        from materialsScience import crystal_analysis
        row = find_structure(self.manager, name)
        if row is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'error': f"no CrystalStructureDefinition named "
                         f"'{name}'"}
            return
        body = request.media if request.content_length else {}
        report = crystal_analysis.xrd(
            row, self.manager,
            wavelength=body.get('wavelength', 'CuKa'),
            two_theta_max=float(body.get('twoThetaMax', 90.0)
                                or 90.0),
            top_n=int(body.get('topN', 30) or 30))
        report['structure'] = name
        response.media = report
