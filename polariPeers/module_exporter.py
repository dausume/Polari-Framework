"""
@cross-cutting
@module polariPeers.module_exporter
@tags @xc:bindings

Module exporter — turn LIVE Polari content into a module bundle by
walking the reference closure from a scope's roots. Export what exists,
don't re-author it.

Scope shape:
    {
      'name': ..., 'description': ...,
      'simulations': ['<sim def name>', ...],     # sim-space roots
      'msim': '<MultiScaleSimulationDefinition>', # composition root
      'solutions': [...], 'scenes': [...], 'icInterfaces': [...],
      'displays': ['<DisplayDefinition name>', ...],
      'classRows': {'<Class>': ['<row name>', ...]},  # any class
      'classDisplays': {'<Class>': ['<def name>']} | False,
      'dependsOn': ['<module>', ...],
      'excludeClosureOf': [<scope>, ...],   # subtract dependency content
    }

ANY class can be carried: `classRows` takes rows of any class by name,
and CLASS_LOAD_ORDER is a dependency ORDERING, not a whitelist —
classes it does not list simply load after SimulationRun. (One catch:
a definition class missing from that list is treated as a state class
and becomes a REQUIREMENT of the importing node rather than carried
content, so genuinely new definition classes belong in the list.)

PARTITIONING one class across modules: `classRows` already selects
rows by name, and `classDisplays` does the same for a class's
TableDefinition/GraphDefinition rows — so the M0 table can live in one
module and the M1 table in another off the same class.

Closure edges walked (per the known reference graph):
  sim def → its SimulationExecutionSolutions → their SolutionDefinitions
          → equations referenced in graphs (calculus `equationName`,
            `matrixEquationName` → MatrixEquationDefinition operands →
            stored MatrixDefinitions / EquationDefinitions, recursively)
          → its IC-validator solution
          → participating *SimState classes (→ requiredClasses
            fingerprints + template runs + their seed rows)
          → scenes binding those classes → bindings → referenced 3D
            materials/meshes → the scenes' evaluation equations
          → GraphDefinitions over those classes
          → SolutionTestCases of the exported solutions
  msim    → members (as sim roots) + couplings (→ sampler equations)
          + IC interfaces + panel graphs/scenes + stage gate solutions

Template runs = non-attempt, non-live runs of the sim; their state rows
export at step 0 only, EXCEPT status='precomputed' runs whose full baked
trajectory is itself seed content.

@consumers
  - polariPeers.peers_api (POST /api/modules/export)
@see /OVERLAP_MAP.md
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple

from polariPeers.module_bundle import (
    class_fields_fingerprint,
    make_bundle,
    resolve_class,
    serialize_row,
)


def export_module(manager, scope: Dict[str, Any]) -> Dict[str, Any]:
    """Export the closure of `scope` as a bundle."""
    walker = _ClosureWalker(manager)
    _walk_scope(walker, scope)

    # Subtract dependency modules' closures so bundles stay disjoint.
    for dep_scope in scope.get('excludeClosureOf') or []:
        dep = _ClosureWalker(manager)
        _walk_scope(dep, dep_scope)
        walker.subtract(dep)

    objects, required = walker.serialized()
    return make_bundle(
        name=scope.get('name') or 'unnamed-module',
        description=scope.get('description') or '',
        required_classes=required,
        depends_on=list(scope.get('dependsOn') or []),
        objects=objects,
    )


def _walk_scope(walker: '_ClosureWalker', scope: Dict[str, Any]) -> None:
    """Walk every root kind a scope may declare. Beyond sim/msim roots,
    scopes can name explicit roots the reference graph can't reach from
    a sim alone: gate SOLUTIONS (referenced by msim stages, not by the
    sim), standalone SCENES (e.g. a selection space with no bound
    classes), IC INTERFACES (whose choices tie to appearance rows), and
    DISPLAYS."""
    if 'classDisplays' in scope:
        walker.class_displays = scope.get('classDisplays')
    for sim in scope.get('simulations') or []:
        walker.walk_simulation(sim)
    if scope.get('msim'):
        walker.walk_msim(scope['msim'])
    for sol in scope.get('solutions') or []:
        walker.walk_solution(sol)
    for scene in scope.get('scenes') or []:
        walker._walk_scene(scene)
    for ic in scope.get('icInterfaces') or []:
        walker.walk_ic_interface(ic)
    for display in scope.get('displays') or []:
        walker.walk_display(walker._add_by_name('DisplayDefinition', display))
    # ncg-7: generic rows-by-class roots — lets NON-sim content
    # (logic designs, circuits, breadboards, judicial procedures,
    # test packs) export as module objects through the same scope
    # knob. {'classRows': {'LogicBlockDesign': ['demo-counter2']}}.
    # Closure convenience lives in polariPeers.ncg_module_scopes.
    for class_name, names in (scope.get('classRows') or {}).items():
        # The carried class is also a REQUIREMENT: the importing
        # instance must hold a fingerprint-matching definition, same
        # contract as the sim-walk's state classes.
        walker.required.add(class_name)
        walker.add_class_displays(class_name)
        for row_name in names:
            walker._add_by_name(class_name, row_name)


def suggest_module_scopes(manager) -> List[Dict[str, Any]]:
    """The natural partition of the current sample content — offered as
    suggestions (the export scope stays a knob)."""
    sims = {getattr(r, 'name', '') for r in
            (manager.objectTables.get('SimulationDefinition', {}) or {}).values()}
    msims = {getattr(r, 'name', '') for r in
             (manager.objectTables.get('MultiScaleSimulationDefinition', {}) or {}).values()}

    out: List[Dict[str, Any]] = []
    core_sims = [s for s in ('pendulum-2d', 'newtonian-pendulum-3d') if s in sims]
    if core_sims:
        out.append({
            'name': 'pendulum-core',
            'description': 'The pendulum spaces: the precomputed 2D demo and '
                           'the Newtonian 3D pendulum with its scene.',
            'simulations': core_sims, 'dependsOn': [],
        })
    if 'wind-field-3d' in sims:
        out.append({
            'name': 'wind-space',
            'description': 'The wind-field space: grid state, gust evolution, '
                           'field sampling.',
            'simulations': ['wind-field-3d'], 'dependsOn': [],
        })
    scenes = {getattr(r, 'name', '') for r in
              (manager.objectTables.get('SimSpaceDefinition', {}) or {}).values()}
    if 'material-condensation' in sims:
        out.append({
            'name': 'material-space',
            'description': 'The first-principles materials space: condensation '
                           'search, the solid-ball gate.',
            'simulations': ['material-condensation'],
            'solutions': ['solid-ball-achievable'],
            'dependsOn': [],
        })
    if 'pendulum-in-wind' in msims:
        deps = [s for s in out]
        out.append({
            'name': 'pendulum-in-wind-composition',
            'description': 'The multi-scale composition weaving the pendulum, '
                           'wind, and material spaces (couplings, stages, '
                           'picker, graphs). Requires the three space modules.',
            'msim': 'pendulum-in-wind',
            'dependsOn': [d['name'] for d in deps],
            'excludeClosureOf': [
                {k: v for k, v in d.items() if k in ('simulations', 'msim')}
                for d in deps
            ],
        })
    # A self-contained EXPERIENCE module (appended after the composition
    # so the space-partition dependency computation above stays exact —
    # this one deliberately overlaps material-space).
    if 'material-condensation' in sims and 'solid-material-selector' in scenes:
        out.append({
            'name': 'solid-materials-selection-module',
            'description': (
                'The solid-materials selection experience: the condensation '
                'space + gate, the phase-appearance scene (ball solidifying '
                'live), the fixed-camera 3D material selection space with '
                'per-substance textures/appearances, the material picker, '
                'and the explainability graphs.'
            ),
            'simulations': ['material-condensation'],
            'solutions': ['solid-ball-achievable'],
            'scenes': ['material-condensation-viz', 'solid-material-selector'],
            'icInterfaces': ['bob-material-picker'],
            'dependsOn': [],
        })
    return out


# ---------------------------------------------------------------------------
# The walker
# ---------------------------------------------------------------------------


class _ClosureWalker:
    def __init__(self, manager):
        self.manager = manager
        # {class_name: {row_name: instance}}
        self.collected: Dict[str, Dict[str, Any]] = {}
        self.required: Set[str] = set()
        #: See add_class_displays — None = carry every display of a
        #: rooted class; dict = carry only what it names (per-class
        #: partitioning); False = carry none.
        self.class_displays: Any = None
        self._seen_solutions: Set[str] = set()
        self._seen_matrix_eqs: Set[str] = set()

    # -- primitives --------------------------------------------------------

    def _table(self, cls: str) -> Dict[str, Any]:
        return (self.manager.objectTables.get(cls, {}) or {})

    def _add(self, cls: str, inst) -> None:
        name = str(getattr(inst, 'name', '') or '')
        if name:
            self.collected.setdefault(cls, {})[name] = inst

    def _add_by_name(self, cls: str, name: str) -> Optional[Any]:
        if not name:
            return None
        for inst in self._table(cls).values():
            if getattr(inst, 'name', '') == name:
                self._add(cls, inst)
                return inst
        return None

    def _add_by_id(self, cls: str, row_id: str) -> Optional[Any]:
        """Definitions embedded in a display are referenced by ID, not
        by name (graphConfigId / tableConfigId), so the closure needs
        both lookups."""
        if not row_id:
            return None
        for inst in self._table(cls).values():
            if str(getattr(inst, 'id', '')) == str(row_id):
                self._add(cls, inst)
                return inst
        return None

    def add_class_displays(self, class_name: str) -> None:
        """Carry a class's OWN display configuration with it.

        Per-object definitions are how presentation is expressed here:
        a TableDefinition/GraphDefinition names its `source_class`, and
        other displays reference it for specific context. So exporting
        a class without them ships data that renders as an alphabetical
        dump of every field — which is exactly the raw-JSON problem
        these definitions exist to solve.

        PARTITIONING. One class's configuration may legitimately split
        across modules — the M0 table in one, the M1 table in another,
        off the same class. So the scope decides how much comes along:

          (omitted)                  every display of the class
          {'<Class>': ['<name>']}    only those, by name
          {'<Class>': []}            none for that class
          False                      none at all, for any class

        Without this a scope that named one row of a class would drag
        every sibling module's displays for that class in with it."""
        if not class_name or self.class_displays is False:
            return
        selection = None
        if isinstance(self.class_displays, dict):
            if class_name not in self.class_displays:
                # A partitioned scope is explicit: a class it does not
                # name carries no displays, rather than silently all.
                return
            selection = {str(n) for n in
                         (self.class_displays.get(class_name) or [])}
        for cls in ('TableDefinition', 'GraphDefinition'):
            for inst in self._table(cls).values():
                if getattr(inst, 'source_class', '') != class_name:
                    continue
                if selection is not None and \
                        str(getattr(inst, 'name', '')) not in selection:
                    continue
                self._add(cls, inst)

    def walk_display(self, display) -> None:
        """Follow what a display's items actually reference.

        Nothing used to parse `definition`, so a page built from
        embeddedGraph/embeddedTable exported WITHOUT the graph and
        table it renders — the bundle imported as empty panels."""
        if display is None:
            return
        definition = _parse(getattr(display, 'definition', '') or '{}', {})
        for row in (definition.get('rows') or []):
            for item in (row.get('items') or []):
                props = (item.get('componentProps') or {})
                inputs = (props.get('inputs') or {})
                self._add_by_id('GraphDefinition',
                                inputs.get('graphConfigId', ''))
                self._add_by_id('TableDefinition',
                                inputs.get('tableConfigId', ''))
                # A component pointed at a class needs that class
                # present on the importing node, and needs the class's
                # own display configuration to render as authored.
                bound = inputs.get('className', '')
                if bound:
                    self.required.add(bound)
                    self.add_class_displays(bound)
                # Sim/msim embeds name their space by name.
                self._add_by_name('SimSpaceDefinition',
                                  inputs.get('simSpaceName', ''))
        source_class = getattr(display, 'source_class', '')
        if source_class:
            self.required.add(source_class)
            self.add_class_displays(source_class)

    # -- edges --------------------------------------------------------------

    def walk_simulation(self, sim_name: str) -> None:
        sim_def = self._add_by_name('SimulationDefinition', sim_name)
        if sim_def is None:
            return
        # Step solutions + their graphs.
        for s in self._table('SimulationExecutionSolution').values():
            if getattr(s, 'simulation_definition_ref', '') != sim_name:
                continue
            self._add('SimulationExecutionSolution', s)
            self.walk_solution(getattr(s, 'solution_definition_ref', ''))
        self.walk_solution(
            getattr(sim_def, 'initial_conditions_validator_ref', '') or '')

        # State classes → requirements + template runs + seed rows.
        classes = _parse(getattr(
            sim_def, 'participating_sim_state_classes_json', '') or '[]', [])
        classes = [c for c in classes if isinstance(c, str)]
        self.required.update(classes)
        template_runs: Dict[str, str] = {}
        for r in self._table('SimulationRun').values():
            rname = getattr(r, 'name', '')
            if getattr(r, 'simulation_ref', '') != sim_name:
                continue
            if '-attempt-' in rname or '-live-' in rname:
                continue
            self._add('SimulationRun', r)
            template_runs[rname] = getattr(r, 'status', '')
        for cls in classes:
            for inst in self._table(cls).values():
                run_ref = getattr(inst, 'simulation_run_ref', '')
                if run_ref not in template_runs:
                    continue
                step = getattr(inst, 'step', None)
                # Step-0 seeds; precomputed runs keep their whole baked
                # trajectory (it IS the seed content).
                if step == 0 or template_runs[run_ref] == 'precomputed':
                    self._add(cls, inst)

        # Scenes over those classes (+ bindings, viz refs, eval eqs).
        self._walk_scenes_for_classes(set(classes))

        # Graphs over those classes.
        for g in self._table('GraphDefinition').values():
            if getattr(g, 'source_class', '') in classes:
                self._add('GraphDefinition', g)

        # Test cases of exported solutions.
        sol_names = set(self.collected.get('SolutionDefinition', {}).keys())
        for t in self._table('SolutionTestCase').values():
            if getattr(t, 'solution_id', '') in sol_names:
                self._add('SolutionTestCase', t)

    def walk_msim(self, msim_name: str) -> None:
        msim = self._add_by_name('MultiScaleSimulationDefinition', msim_name)
        if msim is None:
            return
        for sim in _parse(getattr(
                msim, 'member_simulation_refs_json', '') or '[]', []):
            if isinstance(sim, str):
                self.walk_simulation(sim)
        for cname in _parse(getattr(msim, 'coupling_refs_json', '') or '[]', []):
            coupling = self._add_by_name('SimulationCouplingDefinition', cname)
            if coupling is not None:
                self.walk_matrix_equation(
                    getattr(coupling, 'sampler_equation_ref', '') or '')
                for side in ('target_class_name', 'source_class_name'):
                    cls = getattr(coupling, side, '')
                    if cls:
                        self.required.add(cls)
        for panel in _parse(getattr(msim, 'panels_json', '') or '[]', []):
            if not isinstance(panel, dict):
                continue
            if panel.get('graphRef'):
                self._add_by_name('GraphDefinition', panel['graphRef'])
            if panel.get('icInterfaceRef'):
                self.walk_ic_interface(panel['icInterfaceRef'])
            if panel.get('simSpaceRef'):
                self._walk_scene(panel['simSpaceRef'])
            if panel.get('displayId'):
                self._add_by_name('DisplayDefinition', panel['displayId'])
        if getattr(msim, 'display_ref', ''):
            self._add_by_name('DisplayDefinition',
                              getattr(msim, 'display_ref'))
        for stage in _parse(getattr(msim, 'stages_json', '') or '[]', []):
            if not isinstance(stage, dict):
                continue
            gate = (stage.get('gate') or {}).get('solutionRef', '')
            self.walk_solution(gate)

    def walk_ic_interface(self, ic_name: str) -> None:
        """IC interface + the appearance rows its substances wear: each
        choice key ties to MaterialPhaseAppearance rows (substance_ref),
        whose materials (map values + default) + their textures follow."""
        ic = self._add_by_name('InitialConditionInterfaceDefinition', ic_name)
        if ic is None:
            return
        if getattr(ic, 'target_class_name', ''):
            self.required.add(getattr(ic, 'target_class_name'))
        config = _parse(getattr(ic, 'config_json', '') or '{}', {})
        choice_keys = {c.get('key') for c in (config.get('choices') or [])
                       if isinstance(c, dict)}
        for row in self._table('MaterialPhaseAppearance').values():
            if getattr(row, 'substance_ref', '') not in choice_keys:
                continue
            self._add('MaterialPhaseAppearance', row)
            appearance_map = _parse(
                getattr(row, 'appearance_map_json', '') or '{}', {})
            refs = set(appearance_map.values()) \
                if isinstance(appearance_map, dict) else set()
            refs.add(getattr(row, 'default_material_ref', '') or '')
            for ref in refs - {''}:
                self._add_material(str(ref))

    def walk_solution(self, solution_name: str) -> None:
        if not solution_name or solution_name in self._seen_solutions:
            return
        self._seen_solutions.add(solution_name)
        row = self._add_by_name('SolutionDefinition', solution_name)
        if row is None:
            return
        graph = _parse(getattr(row, 'definition', '') or '{}', {})
        states = graph.get('stateInstances') or graph.get('states') or []
        for state in states if isinstance(states, list) else []:
            if not isinstance(state, dict):
                continue
            fv = state.get('boundObjectFieldValues') or {}
            if fv.get('equationName'):
                self._add_by_name('EquationDefinition', fv['equationName'])
            if fv.get('matrixEquationName') or fv.get('matrixEquationRef'):
                self.walk_matrix_equation(
                    fv.get('matrixEquationName') or fv.get('matrixEquationRef'))

    def walk_matrix_equation(self, eq_name: str) -> None:
        if not eq_name or eq_name in self._seen_matrix_eqs:
            return
        self._seen_matrix_eqs.add(eq_name)
        row = self._add_by_name('MatrixEquationDefinition', eq_name)
        if row is None:
            return
        operation = _parse(getattr(row, 'operation_json', '') or '{}', {})
        if isinstance(operation, dict) and operation.get('equationRef'):
            self._add_by_name('EquationDefinition', operation['equationRef'])
        operands = _parse(getattr(row, 'operands_json', '') or '{}', {})
        for spec in (operands or {}).values() if isinstance(operands, dict) else []:
            if not isinstance(spec, dict):
                continue  # bare runtime bindings need no export
            ref = spec.get('ref') or spec.get('matrixRef') or ''
            kind = spec.get('kind')
            if kind == 'matrix':
                self._add_by_name('MatrixDefinition', ref)
            elif kind == 'matrixEquation':
                self.walk_matrix_equation(ref)
            elif kind == 'equation':
                self._add_by_name('EquationDefinition', ref)

    # -- scenes + viz refs ---------------------------------------------------

    def _walk_scenes_for_classes(self, classes: Set[str]) -> None:
        for scene in self._table('SimSpaceDefinition').values():
            bound = _parse(getattr(scene, 'bound_classes_json', '') or '[]', [])
            bound_names = {e.get('className') for e in bound
                           if isinstance(e, dict)}
            if bound_names & classes:
                self._walk_scene(getattr(scene, 'name', ''), classes)

    def _walk_scene(self, scene_name: str,
                    limit_classes: Optional[Set[str]] = None) -> None:
        scene = self._add_by_name('SimSpaceDefinition', scene_name)
        if scene is None:
            return
        style_refs: Set[str] = set()
        shape_refs: Set[str] = set()
        blob = _parse(getattr(scene, 'definition', '') or '{}', {})
        for entry in (blob.get('freestanding') or []) if isinstance(blob, dict) else []:
            if isinstance(entry, dict):
                style_refs |= _visual_refs(entry.get('styleRef'))
                shape_refs |= _visual_refs(entry.get('shapeRef'))
        bound = _parse(getattr(scene, 'bound_classes_json', '') or '[]', [])
        scene_classes = {e.get('className') for e in bound if isinstance(e, dict)}
        wanted = scene_classes if limit_classes is None \
            else (scene_classes | limit_classes)
        for b in self._table('SimSpaceBindingDefinition').values():
            if getattr(b, 'class_name', '') not in wanted:
                continue
            self._add('SimSpaceBindingDefinition', b)
            self.required.add(getattr(b, 'class_name', ''))
            binding = _parse(getattr(b, 'binding_json', '') or '{}', {})
            visual = binding.get('visual') or {} if isinstance(binding, dict) else {}
            style_refs |= _visual_refs(visual.get('styleRef'))
            shape_refs |= _visual_refs(visual.get('shapeRef'))
        for ev in self._table('SimSpaceEvaluationEquation').values():
            if getattr(ev, 'sim_space_ref', '') == scene_name:
                self._add('SimSpaceEvaluationEquation', ev)
                self._add_by_name('EquationDefinition',
                                  getattr(ev, 'equation_ref', '') or '')
        for ref in style_refs - {''}:
            self._add_material(ref)
        for ref in shape_refs - {''}:
            self._add_by_name('Mesh3DDefinition', ref)

    def _add_material(self, ref: str) -> None:
        """A material + the texture it references (map_texture_ref)."""
        material = self._add_by_name('Material3DDefinition', ref)
        if material is not None and getattr(material, 'map_texture_ref', ''):
            self._add_by_name('Texture3DDefinition',
                              getattr(material, 'map_texture_ref'))

    # -- output ---------------------------------------------------------------

    def subtract(self, other: '_ClosureWalker') -> None:
        for cls, rows in other.collected.items():
            mine = self.collected.get(cls)
            if not mine:
                continue
            for name in rows:
                mine.pop(name, None)
            if not mine:
                self.collected.pop(cls, None)
        # Recompute requirements from what REMAINS.
        self.required = self._requirements_of_remaining()

    def _requirements_of_remaining(self) -> Set[str]:
        req: Set[str] = set()
        for sim in self.collected.get('SimulationDefinition', {}).values():
            req.update(c for c in _parse(getattr(
                sim, 'participating_sim_state_classes_json', '') or '[]', [])
                if isinstance(c, str))
        for c in self.collected.get('SimulationCouplingDefinition', {}).values():
            for side in ('target_class_name', 'source_class_name'):
                if getattr(c, side, ''):
                    req.add(getattr(c, side))
        for ic in self.collected.get(
                'InitialConditionInterfaceDefinition', {}).values():
            if getattr(ic, 'target_class_name', ''):
                req.add(getattr(ic, 'target_class_name'))
        for b in self.collected.get('SimSpaceBindingDefinition', {}).values():
            if getattr(b, 'class_name', ''):
                req.add(getattr(b, 'class_name'))
        # State rows carried directly also require their class.
        from polariPeers.module_bundle import CLASS_LOAD_ORDER
        for cls in self.collected:
            if cls not in CLASS_LOAD_ORDER:
                req.add(cls)
        return req

    def serialized(self) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, str]]:
        objects: Dict[str, List[Dict[str, Any]]] = {}
        for cls, rows in self.collected.items():
            klass = resolve_class(self.manager, cls)
            if klass is None:
                continue
            objects[cls] = [serialize_row(klass, inst) for inst in rows.values()]
        required: Dict[str, str] = {}
        for cls in sorted(self.required):
            klass = resolve_class(self.manager, cls)
            if klass is not None:
                required[cls] = class_fields_fingerprint(klass)
        return objects, required


def _parse(text: str, default: Any) -> Any:
    try:
        return json.loads(text) if text else default
    except (ValueError, TypeError):
        return default


def _visual_refs(cfg: Any) -> Set[str]:
    """Every library name a binding's shape/style spec can reference:
    a bare string, or the per-phase {fromField, map, default} form
    (map VALUES + default are the refs; the field name is not)."""
    if isinstance(cfg, str):
        return {cfg}
    if isinstance(cfg, dict):
        refs: Set[str] = set()
        value_map = cfg.get('map')
        if isinstance(value_map, dict):
            refs.update(str(v) for v in value_map.values())
        if cfg.get('default'):
            refs.add(str(cfg['default']))
        return refs
    return set()
