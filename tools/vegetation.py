#!/usr/bin/env python3
"""Generate the planting sources (sources/planting/*.json).

    python tools/vegetation.py      then  python tools/build.py

Plants are fixed meshes, one per type, sized to the species (height and crown
width of a mature plant), in a low-poly style: the engine draws every face
edge, so a few large facets read better than a dense mesh.

- Trees grow their branches by space colonization (Runions, Lane and
  Prusinkiewicz, "Modeling trees with a space colonization algorithm", 2007):
  attraction points fill the crown envelope and the branch tips grow towards
  them. Branch thickness follows the pipe model (the cross-section below a
  fork matches those above it, r^n = sum of the children's r^n), and the
  branch tips gather into foliage clumps, jittered icospheres.
- Palms have a leaning, tapering stem and arching fronds lofted along a
  curved spine with a V-folded section.
- Conifers stack drooping tiers with a jagged rim; columnar ones and shrubs
  are clusters of clumps.

Every plant comes from a fixed seed, so running this again gives the same files.
"""

from __future__ import annotations

import json
import math
import random
import re
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "planting"

MATERIALS = {
    "Folhagem": [78, 122, 58],
    "Folhagem escura": [46, 92, 56],
    "Folhagem clara": [118, 158, 70],
    "Floração amarela": [232, 190, 40],
    "Casca de árvore": [102, 78, 58],
    "Estipe de palmeira": [150, 140, 122],
    "Palmito": [104, 140, 76],
    "Terracota": [176, 98, 66],
    "Terra vegetal": [74, 56, 42],
}


# --- vectors -----------------------------------------------------------------------

def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def length(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = length(a)
    return mul(a, 1 / n) if n > 1e-12 else a


def perpendicular(t):
    """A unit vector perpendicular to `t`."""
    u = cross(t, (0, 0, 1))
    if length(u) < 1e-6:
        u = cross(t, (1, 0, 0))
    return unit(u)


UP = (0.0, 0.0, 1.0)


# --- meshes ------------------------------------------------------------------------

class Mesh:
    """Vertices and polygon faces, each face counter-clockwise seen from outside."""

    def __init__(self):
        self.vertices: list[tuple] = []
        self.faces: list[list[int]] = []

    def vertex(self, p) -> int:
        self.vertices.append(tuple(p))
        return len(self.vertices) - 1

    def face(self, idx: list[int], outward):
        """Add a face, flipped if needed so that its normal agrees with `outward`."""
        pts = [self.vertices[i] for i in idx]
        n = (0.0, 0.0, 0.0)
        for a, b in zip(pts, pts[1:] + pts[:1]):  # Newell's normal
            n = add(n, ((a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])))
        if dot(n, outward) < 0:
            idx = idx[::-1]
        self.faces.append(idx)

    def centroid(self, idx):
        pts = [self.vertices[i] for i in idx]
        return mul(tuple(map(sum, zip(*pts))), 1 / len(pts))

    def transform(self, fn):
        self.vertices = [fn(p) for p in self.vertices]

    def shape(self) -> dict:
        return {"Mesh": {"vertices": [[round(c, 3) + 0.0 for c in p] for p in self.vertices], "faces": self.faces}}


def _icosphere():
    t = (1 + math.sqrt(5)) / 2
    verts = [unit(v) for v in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
                               (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
             (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    mids: dict = {}

    def mid(a, b):
        key = (min(a, b), max(a, b))
        if key not in mids:
            verts.append(unit(mul(add(verts[a], verts[b]), 0.5)))
            mids[key] = len(verts) - 1
        return mids[key]

    out = []
    for a, b, c in faces:
        ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
        out += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
    return verts, out


ICO_VERTS, ICO_FACES = _icosphere()  # 42 vertices, 80 faces


def clump(mesh: Mesh, center, radii, rnd: random.Random, jitter=0.12):
    """A foliage clump: an icosphere stretched to `radii`, its vertices jittered."""
    base = len(mesh.vertices)
    for v in ICO_VERTS:
        k = 1 + rnd.uniform(-jitter, jitter)
        mesh.vertex(add(center, (v[0] * radii[0] * k, v[1] * radii[1] * k, v[2] * radii[2] * k)))
    for f in ICO_FACES:
        idx = [base + i for i in f]
        mesh.face(idx, sub(mesh.centroid(idx), center))


def tube(mesh: Mesh, path, radii, sides=6):
    """A closed tube along `path` (points) with a radius at each point."""
    rings = []
    normal = None
    for i, p in enumerate(path):
        t = unit(sub(path[min(i + 1, len(path) - 1)], path[max(i - 1, 0)]))
        # Parallel transport keeps the rings from twisting along the tube.
        normal = perpendicular(t) if normal is None else unit(sub(normal, mul(t, dot(normal, t))))
        binormal = cross(t, normal)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            ring.append(mesh.vertex(add(p, add(mul(normal, math.cos(a) * radii[i]), mul(binormal, math.sin(a) * radii[i])))))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(sides):
            idx = [rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]]
            axis = mul(add(path[i], path[i + 1]), 0.5)
            mesh.face(idx, sub(mesh.centroid(idx), axis))
    mesh.face(list(rings[0]), sub(path[0], path[1]))
    mesh.face(list(rings[-1]), sub(path[-1], path[-2]))


def loft(mesh: Mesh, sections):
    """A closed solid through `sections` (lists of points, the same count each);
    a section of a single point closes the end in a tip."""
    # A thin solid has faces almost edge-on to any "from the inside out" test,
    # so the faces are wound consistently from the ring order instead and the
    # whole solid is flipped if its volume comes out negative.
    rings = [[mesh.vertex(p) for p in s] for s in sections]
    faces = []
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for k in range(n):
            if len(b) == 1:
                faces.append([a[k], a[(k + 1) % n], b[0]])
            else:  # two triangles: the sections twist, so a quad would not be planar
                faces += [[a[k], a[(k + 1) % n], b[(k + 1) % n]], [a[k], b[(k + 1) % n], b[k]]]
    if len(rings[0]) > 2:
        faces.append(rings[0][::-1])
    if len(rings[-1]) > 2:
        faces.append(list(rings[-1]))
    v = mesh.vertices
    volume = sum(dot(v[f[0]], cross(v[f[i]], v[f[i + 1]])) for f in faces for i in range(1, len(f) - 1))
    mesh.faces += [f[::-1] for f in faces] if volume < 0 else faces


def bounds(meshes):
    pts = [p for m in meshes for p in m.vertices]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def fit(meshes, width, height, z0=0.0):
    """Scale and move `meshes` to `width` (largest plan side) by `height`, centered, from `z0` up."""
    lo, hi = bounds(meshes)
    kxy = width / max(hi[0] - lo[0], hi[1] - lo[1])
    kz = height / (hi[2] - lo[2])
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    for m in meshes:
        m.transform(lambda p: ((p[0] - cx) * kxy, (p[1] - cy) * kxy, z0 + (p[2] - lo[2]) * kz))


# --- trees: space colonization -------------------------------------------------------

def colonize(rnd, trunk_top, center, radii, points=260, step=None, influence=None, kill=None, tropism=0.15):
    """Grow a branch skeleton from a trunk up to `trunk_top` into the ellipsoid
    `center`/`radii`. Returns node positions and parents (-1 for the root)."""
    step = step or max(radii) / 5
    influence = influence or max(radii) * 1.2
    kill = kill or step * 1.6
    attractors = []
    while len(attractors) < points:
        p = (rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))
        if dot(p, p) <= 1:
            attractors.append(add(center, (p[0] * radii[0], p[1] * radii[1], p[2] * radii[2])))
    nodes, parents = [(0.0, 0.0, 0.0)], [-1]
    segments = max(2, round(trunk_top / step))
    for k in range(1, segments + 1):
        nodes.append((0.0, 0.0, trunk_top * k / segments))
        parents.append(k - 1)
    for _ in range(80):
        pull: dict[int, tuple] = {}
        for a in attractors:
            best, dist = -1, influence
            for i, n in enumerate(nodes):
                d = length(sub(a, n))
                if d < dist:
                    best, dist = i, d
            if best >= 0:
                pull[best] = add(pull.get(best, (0.0, 0.0, 0.0)), unit(sub(a, nodes[best])))
        if not pull:
            break
        grown = []
        for i, d in sorted(pull.items()):
            p = add(nodes[i], mul(unit(add(unit(d), mul(UP, tropism))), step))
            if all(length(sub(p, nodes[j])) > step * 0.3 for j in range(len(nodes)) if parents[j] == i):
                nodes.append(p)
                parents.append(i)
                grown.append(p)
        if not grown:
            break
        attractors = [a for a in attractors if all(length(sub(a, g)) > kill for g in grown)]
        if not attractors:
            break
    return nodes, parents


def pipe_radii(parents, trunk_radius, tip=1.0, exponent=2.5):
    """Branch radii by the pipe model, the root scaled to `trunk_radius`."""
    r = [0.0] * len(parents)
    children = [[] for _ in parents]
    for i, p in enumerate(parents):
        if p >= 0:
            children[p].append(i)
    for i in range(len(parents) - 1, -1, -1):  # children always come after their parent
        r[i] = tip if not children[i] else sum(r[c] ** exponent for c in children[i]) ** (1 / exponent)
    k = trunk_radius / r[0]
    return [x * k for x in r], children


def chains(children, radii, min_radius):
    """Paths of nodes to draw as tubes: each fork continues along its thickest
    child and starts new paths at the others; thin twigs are left out."""
    out, stack = [], [[0]]
    while stack:
        chain = stack.pop()
        node = chain[-1]
        while True:
            kids = sorted((c for c in children[node] if radii[c] >= min_radius), key=lambda c: -radii[c])
            if not kids:
                break
            for c in kids[1:]:
                stack.append([node, c])
            chain.append(kids[0])
            node = kids[0]
        if len(chain) > 1:
            out.append(chain)
    return out


def kmeans(points, k, rnd, rounds=12):
    """Cluster `points` into `k` groups (farthest-point start); returns the groups."""
    centers = [points[rnd.randrange(len(points))]]
    while len(centers) < min(k, len(points)):
        centers.append(max(points, key=lambda p: min(length(sub(p, c)) for c in centers)))
    for _ in range(rounds):
        groups = [[] for _ in centers]
        for p in points:
            groups[min(range(len(centers)), key=lambda i: length(sub(p, centers[i])))].append(p)
        centers = [mul(tuple(map(sum, zip(*g))), 1 / len(g)) if g else c for g, c in zip(groups, centers)]
    return [(c, g) for c, g in zip(centers, groups) if g]


def tree(seed, height, crown, clear, trunk, *, flowers=0.0, clumps=None, flat=1.0, jitter=0.14):
    """A broadleaf tree: `height` and `crown` width, `clear` trunk height, `trunk` diameter."""
    rnd = random.Random(seed)
    R, Hc = crown / 2, height - clear
    center = (0.0, 0.0, clear + Hc * 0.55)
    radii = (R * 0.8, R * 0.8, Hc / 2 * 0.8 * flat)
    nodes, parents = colonize(rnd, clear + Hc * 0.1, center, radii)
    radii_n, children = pipe_radii(parents, trunk / 2)
    wood = Mesh()
    for chain in chains(children, radii_n, max(0.015, trunk * 0.09)):
        rs = [radii_n[i] for i in chain]
        tube(wood, [nodes[i] for i in chain], rs, 7 if rs[0] > trunk * 0.3 else 5)
    tips = [nodes[i] for i in range(len(nodes)) if not children[i]]
    k = clumps or max(7, min(16, round(5 + R * 1.4)))
    leaves, bloom = Mesh(), Mesh()
    groups = kmeans(tips, k, rnd)
    for n, (c, g) in enumerate(groups):
        spread = math.sqrt(sum(dot(sub(p, c), sub(p, c)) for p in g) / len(g))
        r = max(R * 0.3, min(R * 0.5, spread * 1.2 + R * 0.12))
        target = bloom if n < round(len(groups) * flowers) else leaves
        clump(target, c, (r, r, r * 0.85 * flat), rnd, jitter)
    clump(leaves, (center[0], center[1], center[2]), (R * 0.55, R * 0.55, Hc * 0.35 * flat), rnd, jitter)
    # Center the crown on the trunk base and size it to the species: the crown
    # moves whole, the trunk bends towards it from the ground.
    crown_meshes = [m for m in (leaves, bloom) if m.vertices]
    lo, hi = bounds(crown_meshes)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    kxy = crown / max(hi[0] - lo[0], hi[1] - lo[1])
    kz = height / hi[2]

    def place(p, bend=True):
        w = min(1.0, max(0.0, p[2] / clear)) ** 2 if bend else 1.0
        return ((p[0] - cx * w) * kxy, (p[1] - cy * w) * kxy, p[2] * kz)

    wood.transform(place)
    for m in crown_meshes:
        m.transform(lambda p: place(p, False))
    return wood, leaves, bloom


def conifer(seed, height, crown, clear, trunk, *, tiers=6, points=9, droop=0.35):
    """A conifer of drooping tiers, each a cone with a jagged rim."""
    rnd = random.Random(seed)
    R, Hc = crown / 2, height - clear
    wood, leaves = Mesh(), Mesh()
    tube(wood, [(0, 0, 0), (0, 0, clear + Hc * 0.4)], [trunk / 2, trunk * 0.35], 7)
    for i in range(tiers):
        t = i / (tiers - 1)
        base = clear + Hc * 0.78 * t
        top = height if i == tiers - 1 else base + Hc * 0.34
        r = R * (1 - 0.78 * t)
        spin = rnd.uniform(0, 2 * math.pi)
        rim = []
        for k in range(points * 2):
            a = spin + math.pi * k / points
            rr = r * (1.0 if k % 2 == 0 else 0.72) * rnd.uniform(0.92, 1.05)
            z = base - (droop * rr * 0.35 if k % 2 == 0 else 0) + rnd.uniform(-0.03, 0.03) * r
            rim.append(leaves.vertex((math.cos(a) * rr, math.sin(a) * rr, z)))
        apex = leaves.vertex((0, 0, top))
        under = leaves.vertex((0, 0, base + (top - base) * 0.12))
        n = len(rim)
        for k in range(n):
            a, b = rim[k], rim[(k + 1) % n]
            side = [a, b, apex]
            mid = leaves.centroid(side)
            leaves.face(side, (mid[0], mid[1], 0.3 * r))
            leaves.face([a, b, under], (0, 0, -1))
    fit([wood, leaves], crown, height)
    return wood, leaves


def column(seed, height, crown, clear, trunk, *, clumps=6, jitter=0.1):
    """A columnar conifer (cypress, thuja): stacked clumps narrowing to the top."""
    rnd = random.Random(seed)
    R, Hc = crown / 2, height - clear
    wood, leaves = Mesh(), Mesh()
    tube(wood, [(0, 0, 0), (0, 0, clear + Hc * 0.3)], [trunk / 2, trunk * 0.4], 6)
    for i in range(clumps):
        t = i / (clumps - 1)
        r = R * (1 - 0.6 * t ** 1.5)
        z = clear + Hc * (0.12 + 0.76 * t)
        off = (rnd.uniform(-0.08, 0.08) * R, rnd.uniform(-0.08, 0.08) * R, 0)
        clump(leaves, add((0, 0, z), off), (r, r, Hc / clumps * 0.95), rnd, jitter)
    fit([wood, leaves], crown, height)
    return wood, leaves


def shrub(seed, height, width, *, clumps=5, jitter=0.12, z0=0.0):
    """A shrub: a core clump with others around and above it, from `z0` up."""
    rnd = random.Random(seed)
    R = width / 2
    leaves = Mesh()
    clump(leaves, (0, 0, height * 0.5), (R * 0.75, R * 0.75, height * 0.45), rnd, jitter)
    for k in range(clumps - 1):
        a = 2 * math.pi * k / (clumps - 1) + rnd.uniform(-0.3, 0.3)
        d = R * rnd.uniform(0.4, 0.5)
        r = R * rnd.uniform(0.45, 0.55)
        clump(leaves, (math.cos(a) * d, math.sin(a) * d, height * rnd.uniform(0.35, 0.6)), (r, r, r * 0.9), rnd, jitter)
    fit([leaves], width, height, z0)
    return leaves


# --- palms -------------------------------------------------------------------------

def palm(seed, height, crown, stem, *, fronds=16, droop=0.7, lean=0.0, shaft=False, frond_w=0.12, rise=(60, -10)):
    rnd = random.Random(seed)
    R = crown / 2
    L = R * 1.05  # frond length
    h = height - L * 0.35
    wood, leaves, green = Mesh(), Mesh(), Mesh()
    ts = [i / 7 for i in range(8)]
    path = [(lean * h * t ** 1.6, 0.0, h * t) for t in ts]
    tube(wood, path, [stem / 2 * ((1.35 if t == 0 else 1.15) - 0.25 * t) for t in ts], 9)
    top = path[-1]
    if shaft:  # the green crownshaft of royal palms
        tube(green, [add(top, (0, 0, -h * 0.02)), add(top, (0, 0, h * 0.1))], [stem / 2 * 1.08, stem / 2 * 0.9], 9)
        top = add(top, (0, 0, h * 0.1))
    for k in range(fronds):
        az = 2 * math.pi * k / fronds * 2.0 + rnd.uniform(-0.15, 0.15)  # two turns around the stem
        frac = k / max(fronds - 1, 1)
        el = math.radians(rise[0] + (rise[1] - rise[0]) * (rnd.random() * 0.5 + frac * 0.5))
        d = (math.cos(az), math.sin(az), 0.0)
        side = (-math.sin(az), math.cos(az), 0.0)
        Lk = L * rnd.uniform(0.85, 1.05)
        sections = []
        steps = 9
        for i in range(steps + 1):
            t = i / steps
            s = add(top, mul(add(mul(d, math.cos(el) * t), mul(UP, math.sin(el) * t - droop * t * t)), Lk))
            if i == steps:
                sections.append([s])
                continue
            tang = unit(add(mul(d, math.cos(el)), mul(UP, math.sin(el) - 2 * droop * t)))
            nrm = unit(cross(side, tang))
            nrm = nrm if nrm[2] >= 0 else mul(nrm, -1)
            w = Lk * frond_w * (0.15 + 0.85 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.6)
            th = max(0.01, w * 0.05)
            fold = w * 0.35  # leaflets hang below the rachis: a V section
            sections.append([
                add(s, mul(nrm, th)),
                add(add(s, mul(side, w)), mul(nrm, -fold)),
                add(s, mul(nrm, -th)),
                add(add(s, mul(side, -w)), mul(nrm, -fold)),
            ])
        loft(leaves, sections)
    # Size the crown to the species about the top of the stem, then the whole
    # palm to its height; the stem's base stays at the origin.
    lo, hi = bounds([leaves])
    k = crown / max(hi[0] - lo[0], hi[1] - lo[1])
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    leaves.transform(lambda p: (top[0] + (p[0] - cx) * k, top[1] + (p[1] - cy) * k, top[2] + (p[2] - top[2]) * k))
    meshes = [m for m in (wood, leaves, green) if m.vertices]
    kz = height / bounds(meshes)[1][2]
    for m in meshes:
        m.transform(lambda p: (p[0], p[1], p[2] * kz))
    return wood, leaves, green


# --- sources -------------------------------------------------------------------------
# The engine keeps one definition per component and its types differ only in
# parameter values, so each species, with its own mesh, is its own component.

def item(name, material, mesh, in_plan):
    return {"name": name, "material": material, "in_plan": in_plan, "shape": mesh.shape()}


def seed(name):
    return zlib.crc32(name.encode("utf-8"))


def source(component, type_name, description, items):
    used = list(dict.fromkeys(i["material"] for i in items))
    return {
        "component": component,
        "def": {"kind": "Generic", "params": [], "items": items},
        "types": [{"name": type_name, "values": {}, "info": {"description": description}}],
        "materials": [{"name": n, "color": MATERIALS[n]} for n in used],
    }


def trees():
    # file, species, height, crown, clear trunk, trunk diameter, foliage, share of flowering clumps
    for file, name, H, C, F, T, mat, fl in [
        ("ipe-amarelo", "Ipê-amarelo", 8.0, 6.0, 2.2, 0.3, "Folhagem", 0.75),
        ("reseda", "Resedá", 5.0, 4.0, 1.8, 0.2, "Folhagem", 0.0),
        ("pau-brasil", "Pau-brasil", 10.0, 7.0, 2.5, 0.35, "Folhagem escura", 0.0),
        ("oiti", "Oiti", 10.0, 10.0, 2.2, 0.4, "Folhagem escura", 0.0),
        ("mangueira", "Mangueira", 12.0, 12.0, 2.0, 0.6, "Folhagem escura", 0.0),
        ("sibipiruna", "Sibipiruna", 15.0, 12.0, 3.0, 0.5, "Folhagem", 0.0),
    ]:
        wood, leaves, bloom = tree(seed(name), H, C, F, T, flowers=fl)
        items = [item("Tronco", "Casca de árvore", wood, False), item("Copa", mat, leaves, True)]
        if bloom.vertices:
            items.append(item("Floração", "Floração amarela", bloom, True))
        yield file, source(name, f"{name} {H:g} m", f"Árvore de copa arredondada, {H:g} m de altura, copa Ø{C:g} m", items)


def conifers():
    for file, name, H, C, F, T, make in [
        ("tuia-holandesa", "Tuia-holandesa", 4.0, 1.2, 0.15, 0.1, column),
        ("cipreste-italiano", "Cipreste-italiano", 8.0, 1.6, 0.3, 0.2, column),
        ("pinheiro", "Pinheiro", 12.0, 5.0, 1.8, 0.4, conifer),
    ]:
        wood, leaves = make(seed(name), H, C, F, T)
        items = [item("Tronco", "Casca de árvore", wood, False), item("Copa", "Folhagem escura", leaves, True)]
        yield file, source(name, f"{name} {H:g} m", f"Conífera, {H:g} m de altura, copa Ø{C:g} m", items)


def palms():
    for file, name, H, C, D, kw in [
        ("palmeira-imperial", "Palmeira-imperial", 15.0, 6.0, 0.45, {"fronds": 16, "shaft": True, "droop": 0.6}),
        ("jeriva", "Jerivá", 8.0, 5.0, 0.3, {"fronds": 14, "droop": 0.8, "lean": 0.03}),
        ("palmeira-real-australiana", "Palmeira-real-australiana", 10.0, 4.0, 0.25,
         {"fronds": 12, "shaft": True, "droop": 0.55}),
        ("washingtonia", "Washingtonia", 12.0, 4.0, 0.6, {"fronds": 22, "droop": 0.35, "frond_w": 0.3, "rise": (55, -35)}),
    ]:
        wood, leaves, green = palm(seed(name), H, C, D, **kw)
        items = [item("Estipe", "Estipe de palmeira", wood, False)]
        if green.vertices:
            items.append(item("Palmito", "Palmito", green, False))
        items.append(item("Folhas", "Folhagem", leaves, True))
        yield file, source(name, f"{name} {H:g} m", f"Palmeira de estipe único, {H:g} m de altura, copa Ø{C:g} m", items)


def shrubs():
    for file, name, H, C, n, j, mat in [
        ("buxinho", "Buxinho", 0.5, 0.5, 3, 0.04, "Folhagem escura"),
        ("ixora", "Ixora", 0.8, 0.8, 5, 0.1, "Folhagem"),
        ("pingo-de-ouro", "Pingo-de-ouro", 1.0, 1.0, 6, 0.12, "Folhagem clara"),
        ("hibisco", "Hibisco", 1.8, 1.5, 7, 0.15, "Folhagem"),
    ]:
        items = [item("Folhagem", mat, shrub(seed(name), H, C, clumps=n, jitter=j), True)]
        yield file, source(name, f"{name} Ø{C * 100:g}", f"Arbusto de canteiro ou cerca viva, {H:g} m de altura, Ø{C:g} m",
                           items)


def pots():
    for DV, HV, DP, HP in [(0.4, 0.4, 0.5, 0.6), (0.6, 0.55, 0.8, 1.0), (0.8, 0.7, 1.1, 1.4)]:
        size = f"Ø{DV * 100:g}"
        pot = {"Revolution": {"plane": "Front", "offset": "0", "axis": "0", "angle": "360", "points": [
            {"u": "0", "v": "0", "radius": ""}, {"u": f"{DV * 0.38:g}", "v": "0", "radius": ""},
            {"u": f"{DV / 2:g}", "v": f"{HV:g}", "radius": ""}, {"u": "0", "v": f"{HV:g}", "radius": ""}]}}
        soil = {"Cylinder": {"x": "0", "y": "0", "z": f"{HV:g}", "radius": f"{DV / 2 - 0.02:g}", "height": "0.01"}}
        plant = shrub(seed(f"Vaso {size}"), HP, DP, clumps=5, jitter=0.12, z0=HV * 0.9)
        items = [
            {"name": "Vaso", "material": "Terracota", "in_plan": True, "shape": pot},
            {"name": "Terra", "material": "Terra vegetal", "in_plan": False, "shape": soil},
            item("Planta", "Folhagem", plant, True),
        ]
        yield f"vaso-planta-{DV * 100:g}", source(f"Vaso com planta {size}", f"Vaso {size}",
                                                  "Vaso de terracota com planta ornamental", items)


def dumps(src) -> str:
    """JSON with two-space indents, number lists kept on one line."""
    text = json.dumps(src, ensure_ascii=False, indent=2)
    return re.sub(r"\[\s+(-?[\d.e-]+(?:,\s+-?[\d.e-]+)*)\s+\]", lambda m: "[" + re.sub(r",\s+", ", ", m.group(1)) + "]",
                  text) + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):  # the folder is all generated
        old.unlink()
    for make in (trees, conifers, palms, shrubs, pots):
        for file, src in make():
            (OUT / f"{file}.json").write_text(dumps(src), encoding="utf-8", newline="\n")
            print(f"sources/planting/{file}.json")


if __name__ == "__main__":
    main()
