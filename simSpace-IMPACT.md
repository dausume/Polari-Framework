# Sim Space — Backend Cross-Cutting Module

This file is the impact-check companion to
`/home/user/Desktop/polari-suite/polari-rf-node/OVERLAP_MAP.md`.
Read both before editing anything under any `simSpace*` directory.

## Three directories, three responsibilities

```
simSpace/        simSpace2D/        simSpace3D/
```

- **`simSpace/`** — shared. `SimSpaceDefinition` base class (registered in
  `defClassList`), `SimSpaceBinding` model on class config, the
  dimensionality-dispatching snapshot endpoint.

- **`simSpace2D/`** — 2D-specific Definition classes (`SimSpace2DDefinition`,
  `Shape2DDefinition`, `Style2DDefinition`) + 2D snapshot compiler.

- **`simSpace3D/`** — 3D-specific Definition classes (`SimSpace3DDefinition`,
  `Mesh3DDefinition`, `Material3DDefinition`, `Texture3DDefinition`) + 3D
  snapshot compiler + glTF upload pipeline.

## What changes here affects

| If you edit … | Run these smoke checks |
|---|---|
| `simSpace/` definition base | All viewers (every `SimSpaceDefinition` subclass) |
| `simSpace/` snapshot dispatcher | All viewers — 2D and 3D round-trips |
| `simSpace2D/*` | SimSpace2D viewer + per-class 2D binding tab |
| `simSpace3D/*` | SimSpace3D viewer + per-class 3D binding tab |
| `simSpace*/api/*` | Frontend services calling those endpoints |
| Adding a class to `defClassList` | DB table creation on fresh boot; restore-on-restart on existing boots |

## Header comment

Every `.py` file inside these directories carries the `@cross-cutting`
docstring header (Python analog of the TS header in OVERLAP_MAP.md). When you
add a new consumer (Angular service that hits the endpoint, another backend
module that imports the model), update both the header and the OVERLAP_MAP
row in the same PR.
