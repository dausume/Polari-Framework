# State Projection — design (vector arrows, and the general concept)

Status: **BUILT (2026-06-23).** Backend verified locally (`selftest_newtonian_pendulum`
11/11 — emits 2 State-Projection vectors + 1 rod connection; companion classes
removed). Frontend implemented (renderer `setVectors` via `THREE.ArrowHelper` +
stable-key, snapshot types, `visibleVectors()`) but NOT `ng build`-verified — needs a
container rebuild. The doc below is the as-built design.

## 1. The concept

A **State Projection** is a *visualization-only* construct that renders an
internal property of a **real** simulation state, without being a simulation
state itself. It owns **no** physics, no `depends_on`, no persisted rows, no
runner involvement. It reads fields off a real state's row at render time and
draws a derived visual.

It exists to fix the architectural mistake we currently have: the force arrows
are modeled as real `*SimState` classes (`NewtonianPendulumGravityVectorSimState`,
`NewtonianPendulumNetVectorSimState`) that participate in the simulation purely
so they can be drawn. That pollutes the sim model and is fragile (extra classes,
extra rows, a cross-class dependency chain, an `arrow-tip` solution step).

The first and only projection type we need now is **`vector`** — an arrow from a
point (origin field-set) along a vector field-set, scaled. The same concept
generalizes later to `trail` (path history), `field` (sampled grid), `heatmap`,
etc. — all reading real-state data, all viz-only.

> Naming: the **construct/concept** is "State Projection." The concrete binding
> **kind** is `vector`. Keep them distinct so future kinds (`trail`, …) slot in.

## 2. Where it lives — a new binding KIND, not a new class

Today `SimSpaceBindingDefinition` has two kinds, resolved in
`simSpace/compilers/common.py` and dispatched in `compile_2d.py` / `compile_3d.py`:

- `object` — a mesh at a position (`_emit_instances`)
- `connection` — a line between two endpoints (`if kind == 'connection'`)

State Projection adds a third:

- `vector` — an arrow from `origin` along `vec`, length `scale·|vec|`

A binding kind (rather than a new registered construct) is deliberate: it's the
lightest realization, reuses the binding editor/registry, and keeps the
simulation model untouched. The binding targets the **real** state's class.

## 3. Binding config schema (`vector` kind)

Stored on `SimSpaceBindingDefinition` (the binding's JSON config), mirroring how
`connection` stores its endpoint specs:

```jsonc
{
  "kind": "vector",
  "classRef": { "className": "NewtonianPendulumBobSimState" },
  "origin": {                 // where the arrow tail sits — a ValueSourceConfig-style spec
    "kind": "fields",         // 'fields' (x,y,z field names) | 'vec3' (single vec3 field) | 'constant'
    "fields": { "x": "px", "y": "py", "z": "pz" }
  },
  "vector": {                 // the vector to draw FROM origin
    "kind": "fields",
    "fields": { "x": "fgrav_x", "y": "fgrav_y", "z": "fgrav_z" }
  },
  "scale": 0.03,              // world units per unit-magnitude (reuse viz_force_scale)
  "minLength": 0.0,           // optional: clamp tiny arrows to 0 (don't draw)
  "headScale": 0.18,          // arrowhead length as a fraction of shaft (ArrowHelper headLength)
  "styleRef": "arrow-gravity",// Material3DDefinition → color
  "temporal": { "kind": "time", "field": "time", "unit": "second", "cumulative": false }
}
```

`origin` and `vector` reuse the existing position-spec resolver in `common.py`
(`resolve_position_spec` / `read_*`), so 'fields' / 'vec3' / 'constant' all work
the same way connections already resolve endpoints. **No new resolver kind** —
`vector` just resolves two specs (origin point + a free vector) instead of two
points.

## 4. Compiler changes

### `common.py`
- Add `resolve_vector_spec(inst, spec)` → returns a 3-tuple `(x,y,z)` for the
  vector field-set (same machinery as the position resolver, minus the pivot
  offset — a vector is a free quantity, not a point).

### `compile_3d.py`
- New branch alongside `connection`:
  ```python
  elif binding_kind == 'vector':
      vectors.extend(_emit_vectors(manager, binding, warnings, run_filter))
  ```
- `_emit_vectors` mirrors `_emit_instances`/`_emit_connections`:
  - iterate the class's instances (apply the SAME `run_filter` predicate —
    `not hasattr(v,'simulation_run_ref') or ==run_filter` — see the eval fix; keep
    these three call sites byte-identical so renderer + eval + projections agree),
  - resolve `origin` → `[ox,oy,oz]`, `vector` → `[vx,vy,vz]`,
  - skip when `|vec|·scale < minLength`,
  - attach `temporalValue` via `read_temporal_value` (so projections scrub with
    the bob),
  - emit `{ kind:'vector', origin, vec, scale, headScale, styleRef, classRef,
    temporalValue, key }` where `key` is `binding.name + ':' + instance.name`
    (stable-key, see §6).
- `compile_3d` returns `(objects, connections, vectors)` — extend the tuple. (Or,
  to avoid touching every caller, fold vectors into `objects` with a discriminant
  `renderType`. Tuple-extend is cleaner; pick one and update the ~3 call sites +
  selftest.)

### `compile_2d.py`
- Same `vector` branch. In 2D the "arrow" is a line + SVG `marker-end` triangle
  (see §5b). Origin/vec resolve identically (z dropped).

## 5. Renderer — 3D (`three-renderer.service.ts`)

- New `setVectors(vectors: SnapshotVector[])`, called wherever `setObjects` /
  `setConnections` are (initial load + `onScrubberChange` + temporal filtering via
  `visibleVectors()`).
- Per vector use **`THREE.ArrowHelper`**:
  ```ts
  const dir = new THREE.Vector3(v.vec[0], v.vec[1], v.vec[2]);
  const len = dir.length() * v.scale;
  if (len < 1e-6) { /* hide */ }
  dir.normalize();
  const origin = new THREE.Vector3(...v.origin);
  const color = this.styleColor(v.styleRef) ?? 0x888888;
  // reuse existing arrow if keyed (stable-key), else create:
  arrow.setColor(color);
  arrow.position.copy(origin);
  arrow.setDirection(dir);
  arrow.setLength(len, len * v.headScale, len * v.headScale * 0.6);
  ```
- ArrowHelper gives shaft + cone head for free — no composite mesh, no new
  Mesh3DDefinition. (The `cone` primitive could be used for a fancier head later,
  but ArrowHelper is the right first cut.)

### 5b. Renderer — 2D (`sim-space-2d` / d3)
- Append `<line>` with `marker-end="url(#arrowhead)"`; define one `<marker>` per
  color in `<defs>`. Origin = (ox,oy), tip = (ox+vx·scale, oy+vy·scale). Same
  visible-by-temporal filter as objects.

## 6. Stable-key reuse (consistency with the meshes)

The user's standing rule (from the 3D pendulum fix): meshes are **bound to a
state-object via a stable key** and we apply position/orientation updates rather
than tearing down + recreating each frame. Projections follow the same rule:

- key = `bindingName:instanceName` (e.g. `newt-gravity-vector:bob-0`).
- Keep a `Map<string, THREE.ArrowHelper>`; on update, reuse the keyed arrow and
  set position/dir/length/color. Only create on first sight, only dispose on
  removal. No per-frame `new ArrowHelper`. This avoids the double-renderer-race
  class of bugs and is cheap.

## 7. Snapshot model (frontend types)

- `SimSpaceSnapshot` gains `vectors: SnapshotVector[]`.
- `SnapshotVector = { key, origin:[x,y,z], vec:[x,y,z], scale, headScale,
  styleRef, classRef, temporalValue? }`.
- `sim-space.service.ts` snapshot parse passes them through. The viewer tracks
  `visibleVectors()` (temporal filter, mirrors `visibleObjects`).

## 8. The Newtonian migration (what this deletes)

Replace the two companion classes with two `vector` bindings on the bob:

- **gravity**: origin `px,py,pz`, vector `fgrav_x,fgrav_y,fgrav_z`, style
  `arrow-gravity`, scale `viz_force_scale`.
- **net**: origin `px,py,pz`, vector `fnet_x,fnet_y,fnet_z`, style `arrow-net`.

Delete (in `newtonian_pendulum_seed.py` + `newtonian_pendulum_viz_states.py` +
`polariServer.py` registration + selftest):
- classes `NewtonianPendulumGravityVectorSimState`, `…NetVectorSimState`
- their step solutions (the `arrow-tip` / arrow `src/tip` Complete steps)
- their seed rows `SEED_NEWTON_GRAV_ROWS`, `SEED_NEWTON_NET_ROWS`
- the two `connection` bindings `arrow-gravity` / `arrow-net`
- their entries in `defClassList` + `seed_pairs`

The bob already persists `fgrav_*` and `fnet_*` as **core fields**, so the
projections have real data every step with zero new runner work. Net win: −2
classes, −2 solutions, −2 seed row sets, −1 dependency edge.

## 9. No-code editor (binding editor, not the node editor)

The SimSpace binding editor needs a `vector` form: pick the target class, the
origin field-set (x/y/z dropdowns over the class's numeric fields), the vector
field-set, scale, color (styleRef), head scale. This reuses the same
field-picker the `connection` endpoint editor uses. Defer until the data path +
renderer are verified.

## 10. Tests

- Extend `selftest_newtonian_pendulum.py` compile check: assert the scene emits
  **2 vectors** (not 2 arrow-connections), each with the right `origin` (= bob
  position), `vec` (= fgrav / fnet from the step-0 row), and `styleRef`.
- A focused `selftest_state_projection.py`: synthetic bob rows → `compile_3d`
  emits a `vector` with origin/vec resolved from 'fields', honors `minLength`,
  and respects `run_filter` (reuse the run-scoping predicate).

## 11. Open questions (decide with the user)

1. **Tuple-extend vs `renderType` discriminant** for `compile_3d`'s return —
   tuple is cleaner but touches all callers; discriminant is less churn. Lean
   tuple-extend.
2. **One arrow or two endpoints?** Net force could also be drawn tail-to-tip
   from gravity (force composition diagram) later. v1: independent arrows from
   the bob.
3. **Auto-scale vs fixed scale** — fixed `viz_force_scale` now; an auto-fit
   (normalize the largest force to a target screen length) could come with the
   `field` projection type.
4. **2D parity now or later?** The Newtonian is 3D; 2D arrows can follow.
