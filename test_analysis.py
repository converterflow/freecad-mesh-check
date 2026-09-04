"""Runs the macro's analysis against real FreeCAD meshes with known defects.

Run inside a FreeCAD-bearing container:
    docker run --rm -v "$PWD/integrations/freecad-macro:/m" freecad-bench:latest \
        python3 /m/test_analysis.py

Not part of the frontend vitest suite: it needs FreeCAD, which the web build
does not have. The numbers asserted below are hand-checkable, which is the
point. A cube meshed as 12 triangles has 18 edges and 8 vertices; delete one
triangle and exactly 3 edges become boundary edges forming 1 loop.
"""
import sys

import FreeCAD
import Part
import MeshPart
import Mesh

NS = {'CONVERTERFLOW_IMPORT_ONLY': True}
with open('/m/ConverterFlowCheck.FCMacro') as fh:
    exec(compile(fh.read(), 'ConverterFlowCheck.FCMacro', 'exec'), NS)

analyse_mesh = NS['analyse_mesh']
analyse_topology = NS['analyse_topology']
format_report = NS['format_report']

failures = []


def check(label, got, want):
    ok = got == want
    print('  %s %-34s got %-8r want %r' % ('ok  ' if ok else 'FAIL', label, got, want))
    if not ok:
        failures.append(label)


def box_mesh(x=10.0, y=20.0, z=30.0, place=None):
    shape = Part.makeBox(x, y, z)
    if place is not None:
        shape.translate(place)
    return MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.1,
                                  AngularDeflection=0.5, Relative=False)


def rebuild(points, facets):
    return Mesh.Mesh([tuple(points[i] for i in f) for f in facets])


print('\n1. a closed cube')
m = box_mesh()
s = analyse_mesh(m)
check('facets', s['facets'], 12)
check('vertices', s['points'], 8)
check('edges', s['edges'], 18)
check('boundary edges', s['boundary_edges'], 0)
check('boundary loops', s['boundary_loops'], 0)
check('non-manifold edges', s['non_manifold_edges'], 0)
check('shells', s['shells'], 1)
check('winding consistent', s['winding_consistent'], True)
check('watertight', s['watertight'], True)
check('volume', round(s['volume'], 3), 6000.0)
check('bbox', tuple(round(v, 3) for v in s['bbox']), (10.0, 20.0, 30.0))
# FreeCAD's own verdict must agree with ours, or one of us is wrong.
check('agrees with mesh.isSolid()', s['watertight'], bool(m.isSolid()))

print('\n2. the same cube with one triangle deleted')
pts, facets = m.Topology[0], m.Topology[1]
holed = rebuild(pts, facets[:-1])
s = analyse_mesh(holed)
check('facets', s['facets'], 11)
check('boundary edges', s['boundary_edges'], 3)
check('boundary loops', s['boundary_loops'], 1)
check('watertight', s['watertight'], False)
check('agrees with mesh.isSolid()', s['watertight'], bool(holed.isSolid()))

print('\n3. two triangles deleted from faces sharing no vertex: two separate holes')
# Facets 0 and 2 share no vertices (checked against the cube's own topology),
# so the two holes are genuinely disconnected.
assert not (set(facets[0]) & set(facets[2])), 'test premise broken: facets 0 and 2 now touch'
two_holes = rebuild(pts, [f for i, f in enumerate(facets) if i not in (0, 2)])
s = analyse_mesh(two_holes)
check('boundary edges', s['boundary_edges'], 6)
check('boundary loops', s['boundary_loops'], 2)

print('\n3b. two holes meeting at a single corner count as ONE boundary')
# Facets 0 and 6 share vertex 2. The boundary is then one connected curve
# pinched at that corner, not two loops. This is a deliberate property of
# counting connected components, and the first draft of the test asserted 2
# here and was wrong. Pinned so the behaviour is a decision, not an accident.
assert set(facets[0]) & set(facets[6]), 'test premise broken: facets 0 and 6 no longer touch'
touching = rebuild(pts, [f for i, f in enumerate(facets) if i not in (0, 6)])
s = analyse_mesh(touching)
check('boundary edges', s['boundary_edges'], 6)
check('boundary loops (pinched, so 1)', s['boundary_loops'], 1)

print('\n4. two disjoint cubes in one mesh')
a = box_mesh()
b = box_mesh(place=FreeCAD.Vector(100, 0, 0))
both = Mesh.Mesh()
both.addMesh(a)
both.addMesh(b)
s = analyse_mesh(both)
check('shells', s['shells'], 2)
check('facets', s['facets'], 24)
check('watertight', s['watertight'], True)

print('\n5. one facet flipped, so the winding is inconsistent')
flipped = list(facets)
f = flipped[0]
flipped[0] = (f[0], f[2], f[1])
s = analyse_topology(pts, flipped)
check('winding consistent', s['winding_consistent'], False)
check('boundary edges still 0', s['boundary_edges'], 0)

print('\n6. a non-manifold edge: a third facet on an existing edge')
extra = list(facets)
e0, e1 = facets[0][0], facets[0][1]
spare = max(max(f) for f in facets) + 1
pts_plus = list(pts) + [FreeCAD.Vector(50, 50, 50)]
extra.append((e0, e1, spare))
s = analyse_topology(pts_plus, extra)
check('non-manifold edges', s['non_manifold_edges'], 1)
check('watertight', s['watertight'], False)

print('\n7. the report renders for a defective mesh')
text = format_report('part.stl', analyse_mesh(holed))
print('\n'.join('    | ' + ln for ln in text.split('\n')))
for must in ['not watertight', 'boundary edge', 'part.stl', 'bounding box']:
    check('report mentions %r' % must, must in text, True)

print('\n%s' % ('FAILURES: ' + ', '.join(failures) if failures else 'all checks passed'))
sys.exit(1 if failures else 0)
