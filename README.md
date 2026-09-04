# ConverterFlow Mesh Check

A FreeCAD macro that tells you *why* a mesh is not a solid.

FreeCAD will say a mesh "is not a solid" and stop there. The question you
actually have is what is wrong with it and whether it is worth fixing. This
prints the numbers.

```
bracket.stl: 5,300 triangles, 4,102 vertices, 2 shells
  BAD not watertight: 14 boundary edges in 3 loops
  BAD 6 non-manifold edges (an edge shared by more than two facets)
  OK  consistent winding
  OK  no self-intersections
  bounding box 194.00 x 145.00 x 18.00
  volume 41220.55, surface area 30188.20

  Fix the items marked BAD before slicing or converting.
  FreeCAD can do some of it: Mesh Design has Fill holes,
  Harmonize normals and Remove components.
```

## Nothing is uploaded

The analysis runs on your machine against FreeCAD's own mesh data. The macro
makes no network calls at all. It can open a web page in your browser, and only
when you click a button that says so.

## Install

**Addon Manager:** Tools then Addon Manager, search for "ConverterFlow Mesh
Check", install, restart FreeCAD.

**By hand:** copy `ConverterFlowCheck.FCMacro` and `ConverterFlowCheck.svg` into
your macro directory (Macro then Macros, the path is shown at the top of the
dialog).

## Use

1. Select a mesh in the tree or the 3D view. Part solids are not meshes; mesh
   one first with Part then Create mesh from shape.
2. Run the macro.
3. Read the report in the Report view (View then Panels then Report view).

Several meshes can be selected at once and each gets its own report.

## What each check means

| Check | What it means when it fails |
|---|---|
| Boundary edges | The surface has holes. Each edge belongs to only one triangle, so the mesh encloses no volume and a slicer cannot tell inside from outside. Loops are the number of separate holes. |
| Non-manifold edges | An edge shared by more than two triangles. Usually two shells welded at a seam, or a boolean that left internal faces behind. |
| Shells | Disconnected pieces. More than one is fine when intended, and a sign of stray debris when it is not, which is common in scan output. |
| Winding | Some triangles face inwards. Renderers and slicers disagree about what is solid. FreeCAD's Harmonize normals fixes this. |
| Self-intersections | Triangles pass through each other. This is the hardest class to repair automatically. |

Two things worth knowing about the numbers:

- **Two holes meeting at a single corner count as one loop.** The boundary is
  one connected curve pinched at that vertex, so "loops" means connected
  boundary components. This is checked by the test suite rather than left to
  chance.
- **Self-intersection is skipped above 100,000 triangles** and reported as "not
  checked" rather than left blank. The check is quadratic and would hang the
  interface on a scan-sized mesh. A blank in a report reads as a pass, which
  would be worse than saying nothing.

## How this differs from what FreeCAD already has

Mesh Design has Evaluate and repair mesh, which is more thorough and can fix
things this macro only reports. Use it. What this adds is a single readable
summary you can run on a selection without opening a dialog and stepping through
each analysis in turn, plus the bounding box and volume in one place.

If you want an STL health check outside FreeCAD, ADMesh
(github.com/admesh/admesh) is a long-established C library and CLI that checks
and repairs unconnected facets, bad normals and degenerate facets. It is the
better tool for scripting over a directory of files.

## The hosted tools

ConverterFlow runs free browser tools for the jobs that need more than a report:
mesh repair, and STL to STEP conversion that attempts to rebuild real planes and
cylinders rather than wrapping triangles in a STEP container. Those upload your
file, which this macro does not, and the macro only ever offers them after it has
already given you the report.

- Repair: converterflow.io/tools/stl-repair
- STL to STEP: converterflow.io/tools/stl-to-step

## Requirements

FreeCAD 0.19 or newer. No Python packages beyond what FreeCAD ships.

Almost everything is derived from `mesh.Topology` rather than from Mesh
convenience methods, because that API has moved between 0.19 and 1.x. On 0.19,
`dir()` on a Mesh object segfaults, so feeling out what exists at runtime is not
an option either.

## Tests

`test_analysis.py` runs the analysis against real FreeCAD meshes with known,
hand-checkable defects: a cube meshed as 12 triangles has 18 edges and 8
vertices, and deleting one triangle makes exactly 3 edges boundary edges forming
1 loop. It needs a FreeCAD-bearing Python:

```
docker run --rm -v "$PWD:/m" IMAGE_WITH_FREECAD python3 /m/test_analysis.py
```

## Licence

MIT. See LICENSE.
