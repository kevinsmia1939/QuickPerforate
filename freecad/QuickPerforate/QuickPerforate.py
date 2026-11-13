"""Parametric perforation feature and pattern geometry.

Planar and regular curved faces of a single solid are supported. Dimensions are
in FreeCAD's document units (normally millimetres).
"""

import math

import FreeCAD as App
import Part


ARRANGEMENTS = ("Square", "Triangle", "Hexagon", "Triangle Tiling", "Brick")
HOLE_SHAPES = (
    "Round", "Square", "Triangle", "Hexagon", "Octagon",
    "Hexagon Star", "Diamond", "Slot", "Airline Slot", "Clover",
    "Full Leaf Clover", "Heart", "Grecian", "Plus Sign", "Marietta",
)

# Older documents stored a combined style in Pattern. Map each style to the
# nearest independent arrangement and hole shape when such a file is opened.
LEGACY_STYLES = {
    "Round Hole Straight": ("Square", "Round"),
    "Round Hole Staggered": ("Triangle", "Round"),
    "Round Hole Slotted": ("Square", "Slot"),
    "Octagon Cane": ("Square", "Octagon"),
    "Airline": ("Square", "Airline Slot"),
    "Marietta": ("Square", "Diamond"),
    "Hexagon": ("Triangle", "Hexagon"),
    "Grecian": ("Square", "Triangle"),
    "Full Leaf Clover": ("Square", "Clover"),
    "Square": ("Square", "Square"),
}

MAX_OPENINGS = 1600


def _polygon(sides, radius, phase=0.0):
    return [(radius * math.cos(phase + i * 2 * math.pi / sides),
             radius * math.sin(phase + i * 2 * math.pi / sides))
            for i in range(sides)]


def _rectangle(width, height):
    return [(-width / 2, -height / 2), (width / 2, -height / 2),
            (width / 2, height / 2), (-width / 2, height / 2)]


def _capsule(length, width):
    radius = width / 2
    straight = (length - width) / 2
    return ([(straight + radius * math.cos(a), radius * math.sin(a))
             for a in [(-math.pi / 2 + i * math.pi / 12) for i in range(13)]]
            + [(-straight + radius * math.cos(a), radius * math.sin(a))
               for a in [(math.pi / 2 + i * math.pi / 12) for i in range(13)]])


def _clover(size):
    # A smooth four-lobed outline, approximated with short straight segments.
    return [((size / 2) * (0.72 + 0.28 * math.cos(4 * a)) * math.cos(a),
             (size / 2) * (0.72 + 0.28 * math.cos(4 * a)) * math.sin(a))
            for a in [i * 2 * math.pi / 64 for i in range(64)]]


def _curved_wire(shape, size, size2):
    """Native local XY wire; dimensions are overall X and Y extents."""
    v = lambda x,y: App.Vector(x,y,0)
    edges = []
    if shape == "Slot":
        width = size2 or size * .37
        if width > size:
            raise ValueError("For Slot, Size 2 must not exceed Size 1.")
        r, a = width/2, (size-width)/2
        if a < 1e-9:
            return Part.Wire([Part.makeCircle(r)])
        edges = [Part.makeLine(v(-a,-r),v(a,-r)),
                 Part.Arc(v(a,-r),v(a+r,0),v(a,r)).toShape(),
                 Part.makeLine(v(a,r),v(-a,r)),
                 Part.Arc(v(-a,r),v(-a-r,0),v(-a,-r)).toShape()]
        return Part.Wire(edges)
    if shape == "Full Leaf Clover":
        r=size/4
        for i in range(4):
            a=i*math.pi/2
            def turn(x,y):
                return v(x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a))
            edges.append(Part.Arc(turn(r,-r),turn(2*r,0),turn(r,r)).toShape())
    elif shape == "Marietta":
        r=size/2
        for i in range(4):
            a=i*math.pi/2
            def turn(x,y):
                return v(x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a))
            q=r*(1-1/math.sqrt(2))
            edges.append(Part.Arc(turn(0,r),turn(q,q),turn(r,0)).toShape())
    elif shape == "Heart":
        # Separate lobes and lower sides give a deep cleft, broad shoulders,
        # and a tapered point without the old arrow-like straight shoulders.
        spans = [((0,.20),(-.18,.62),(-.50,.55),(-.50,.15)),
                 ((-.50,.15),(-.50,-.08),(-.16,-.32),(0,-.50)),
                 ((0,-.50),(.16,-.32),(.50,-.08),(.50,.15)),
                 ((.50,.15),(.50,.55),(.18,.62),(0,.20))]
        for points in spans:
            curve=Part.BezierCurve()
            curve.setPoles([v(x*size,y*size) for x,y in points])
            edges.append(curve.toShape())
    elif shape == "Clover":
        curve=Part.BSplineCurve()
        curve.interpolate([v(x,y) for x,y in _clover(size)],PeriodicFlag=True)
        edges=[curve.toShape()]
    wire=Part.Wire(edges)
    box=wire.BoundBox
    matrix=App.Matrix()
    matrix.A11=size/box.XLength
    matrix.A22=(size2 or size)/box.YLength
    matrix.A14=-(box.XMin+box.XMax)/2*matrix.A11
    matrix.A24=-(box.YMin+box.YMax)/2*matrix.A22
    return Part.Wire(wire.transformGeometry(matrix).Edges)


def hole_profile(hole_shape, size, size2=0):
    """Return a circle or polygon for one opening, centered at the origin."""
    if hole_shape in ("Slot", "Full Leaf Clover", "Heart", "Clover", "Marietta"):
        return "wire", _curved_wire(hole_shape,size,size2)
    r = size / 2
    if hole_shape == "Full Leaf Clover":
        # Four semicircular leaves joined by a small central square.
        points = []
        leaf_radius = size / 4
        for quadrant in range(4):
            for step in range(17):
                a = -math.pi / 2 + step * math.pi / 16
                x = leaf_radius * (1 + math.cos(a))
                y = leaf_radius * math.sin(a)
                turn = quadrant * math.pi / 2
                points.append((x * math.cos(turn) - y * math.sin(turn),
                               x * math.sin(turn) + y * math.cos(turn)))
        return "polygon", points
    if hole_shape == "Heart":
        points = []
        for i in range(96):
            a = -i * 2 * math.pi / 96
            x = 16 * math.sin(a) ** 3
            y = (13 * math.cos(a) - 5 * math.cos(2 * a)
                 - 2 * math.cos(3 * a) - math.cos(4 * a))
            points.append((x * size / 32, (y + 2.5) * size / 32))
        return "polygon", points
    if hole_shape == "Plus Sign":
        return "polygon", [(x * r, y * r) for x, y in
                           [(-1, -.35), (-.35, -.35), (-.35, -1),
                            (.35, -1), (.35, -.35), (1, -.35),
                            (1, .35), (.35, .35), (.35, 1),
                            (-.35, 1), (-.35, .35), (-1, .35)]]
    if hole_shape == "Grecian":
        # Angular Greek-key corner, repeated by the chosen arrangement.
        return "polygon", [(x * r, y * r) for x, y in
                           [(-1, -1), (1, -1), (1, -.3),
                            (-.3, -.3), (-.3, 1), (-1, 1)]]
    if hole_shape == "Marietta":
        # Four curved sides meeting at the cardinal tips.
        points = []
        for quadrant in range(4):
            for i in range(16):
                a = math.pi + i * math.pi / 32
                x, y = r * (1 + math.cos(a)), r * (1 + math.sin(a))
                turn = quadrant * math.pi / 2
                points.append((x * math.cos(turn) - y * math.sin(turn),
                               x * math.sin(turn) + y * math.cos(turn)))
        return "polygon", points
    if hole_shape == "Round":
        return "circle", r
    if hole_shape == "Square":
        return "polygon", _rectangle(size, size)
    if hole_shape == "Triangle":
        return "polygon", _polygon(3, r, math.pi / 2)
    if hole_shape == "Hexagon":
        return "polygon", _polygon(6, r, math.pi / 6)
    if hole_shape == "Hexagon Star":
        # Six-point star outline: six tips and six concave corners.
        return "polygon", [
            ((r if i % 2 == 0 else r / 2) * math.cos(math.pi / 2 + i * math.pi / 6),
             (r if i % 2 == 0 else r / 2) * math.sin(math.pi / 2 + i * math.pi / 6))
            for i in range(12)]
    if hole_shape == "Octagon":
        return "polygon", _polygon(8, r, math.pi / 8)
    if hole_shape == "Diamond":
        return "polygon", _polygon(4, r)
    if hole_shape == "Slot":
        return "polygon", _capsule(size, size * 0.37)
    if hole_shape == "Airline Slot":
        return "polygon", _rectangle(size, size * 0.16)
    if hole_shape == "Clover":
        return "polygon", _clover(size)
    raise ValueError("Unknown hole shape: " + str(hole_shape))


def hole_flip(hole_shape, col, row, flip_every=0):
    """Flip alternating blocks of N grid positions; zero disables flipping."""
    return flip_every > 0 and (col // flip_every + row // flip_every) % 2 != 0


def grid_position(pattern, col, row, pitch, pitch_y=10, row_offset=5, partial_holes=False):
    """Return a hole center in pattern coordinates, or None for an empty site."""
    if pattern == "Brick":
        return (col * pitch + (row % 2) * (row_offset % pitch), row * pitch_y)
    if pattern == "Triangle Tiling":
        return ((col // 2 + (col % 2) / 3 + (row % 2) / 2) * pitch,
                row * pitch / (2 * math.sqrt(3)))
    if pattern == "Square":
        return col * pitch, row * pitch
    if pattern in ("Triangle", "Hexagon"):
        # Alternating rows are wrapped back to the same displayed X range.
        # Convert the displayed column to the unwrapped triangular-lattice
        # coordinate before choosing one of its three color classes to omit.
        axial_col = col - row // 2
        if pattern == "Hexagon" and (axial_col - row) % 3 == 0:
            return None  # removing one color class makes a regular honeycomb
        return ((col + (row % 2) / 2) * pitch,
                row * pitch * math.sqrt(3) / 2)
    raise ValueError("Unknown arrangement: " + str(pattern))


def _frame(face, angle):
    normal = face.normalAt(0, 0)
    normal.normalize()
    rotation = App.Rotation(App.Vector(0, 0, 1), normal).multiply(
        App.Rotation(App.Vector(0, 0, 1), angle))
    return face.CenterOfMass, rotation.multVec(App.Vector(1, 0, 0)), \
        rotation.multVec(App.Vector(0, 1, 0)), normal


def _bounds(face, origin, x_axis, y_axis):
    # The bounding box corners also cover circular and spline edges, for which
    # vertex positions alone would give an incomplete extent.
    box = face.BoundBox
    xs, ys = [], []
    for x in (box.XMin, box.XMax):
        for y in (box.YMin, box.YMax):
            for z in (box.ZMin, box.ZMax):
                delta = App.Vector(x, y, z) - origin
                xs.append(delta.dot(x_axis))
                ys.append(delta.dot(y_axis))
    return min(xs), max(xs), min(ys), max(ys)


def _profile_radius(profile):
    kind, data = profile
    if kind == "circle":
        return data
    if kind == "wire":
        box=data.BoundBox
        return math.hypot(max(abs(box.XMin),abs(box.XMax)), max(abs(box.YMin),abs(box.YMax)))
    return max(math.hypot(x, y) for x, y in data)


def _make_tool(profile, center, x_axis, y_axis, normal, half_depth, depth=2):
    kind, data = profile
    if depth is not None and depth <= 0:
        raise ValueError("Hole depth must be positive.")
    # Small outward overlap avoids coincident faces at the mouth of a pocket.
    travel = 2 * half_depth if depth is None else depth + 1e-5
    base = center - normal * (half_depth if depth is None else depth)
    if kind == "circle":
        return Part.makeCylinder(data, travel, base, normal)
    if kind == "wire":
        matrix=App.Matrix()
        for row in range(3):
            for col,axis in enumerate((x_axis,y_axis,normal)):
                setattr(matrix,"A%d%d"%(row+1,col+1),axis[row])
        wire=data.copy()
        wire.Placement=App.Placement(base,App.Rotation(matrix))
        return Part.Face(wire).extrude(normal*travel)
    points = [base + x_axis * x + y_axis * y for x, y in data]
    points.append(points[0])
    return Part.Face(Part.makePolygon(points)).extrude(normal * travel)


def resolve_faces(shape, names):
    faces = []
    for name in names:
        if not name.startswith("Face") or not name[4:].isdigit():
            raise ValueError("Select faces on the source solid.")
        index = int(name[4:]) - 1
        if index < 0 or index >= len(shape.Faces):
            raise ValueError("A selected face no longer exists.")
        face = shape.Faces[index]
        faces.append(face)
    if not faces:
        raise ValueError("Add at least one face.")
    return faces


def connected_frames(faces, angle):
    """Develop connected planes and cylinders into a common pattern chart."""
    frames, charts = {}, {}
    seams = [[] for _ in faces]
    neighbors = [[] for _ in faces]
    for i, face in enumerate(faces):
        for j in range(i):
            for edge in face.Edges:
                if any(edge.isSame(other) for other in faces[j].Edges):
                    neighbors[i].append((j, edge))
                    neighbors[j].append((i, edge))
                    seams[i].append(edge)
                    seams[j].append(edge)
    def normal(face, point):
        u,v = face.Surface.parameter(point)
        return face.normalAt(u,v)
    def cylinder_chart(face, point):
        u,v = face.Surface.parameter(point)
        tangent = face.Surface.value(u+1e-5,v)-face.Surface.value(u-1e-5,v)
        tangent.normalize()
        return u,v,point,tangent,face.Surface.Radius
    for seed in range(len(faces)):
        if seed in frames:
            continue
        face = faces[seed]
        if isinstance(face.Surface, Part.Cylinder):
            u0,u1,v0,v1 = face.ParameterRange
            point = face.Surface.value((u0+u1)/2,(v0+v1)/2)
            chart = cylinder_chart(face,point)
            charts[seed] = chart
            hx = chart[3]
            n = normal(face,point)
            hy = n.cross(hx)
            rotation = App.Rotation(n, angle)
            frames[seed] = (point,rotation.multVec(hx),rotation.multVec(hy),n,hx,hy)
        else:
            origin,gx,gy,n = _frame(face,angle)
            _,hx,hy,_ = _frame(face,0)
            frames[seed] = origin,gx,gy,n,hx,hy
        queue = [seed]
        for i in queue:
            for j,edge in neighbors[i]:
                if j in frames:
                    continue
                if not all(isinstance(faces[k].Surface,(Part.Plane,Part.Cylinder)) for k in (i,j)):
                    raise ValueError("Continuous shared-edge patterns currently require planes or cylinders.")
                point = edge.CenterOfMass
                origin,gx,gy,n,hx,hy = frames[i]
                if i in charts:
                    uref,vref,pref,tangent,radius = charts[i]
                    u,v = faces[i].Surface.parameter(point)
                    # Evaluate the developed frame at this outgoing seam.
                    axis = faces[i].Surface.Axis
                    rot = App.Rotation(axis,math.degrees(u-uref))
                    virtual = pref + tangent*((u-uref)*radius) + axis*(v-vref)
                    origin = point + rot.multVec(origin-virtual)
                    gx,gy,hx,hy = [rot.multVec(vec) for vec in (gx,gy,hx,hy)]
                    n = normal(faces[i],point)
                target = normal(faces[j],point)
                rot = App.Rotation(n,target)
                frames[j] = (point+rot.multVec(origin-point),rot.multVec(gx),
                             rot.multVec(gy),target,rot.multVec(hx),rot.multVec(hy))
                if isinstance(faces[j].Surface,Part.Cylinder):
                    charts[j] = cylinder_chart(faces[j],point)
                queue.append(j)
    return frames, seams, charts


def _opening_face(profile, center, x_axis, y_axis, normal):
    kind,data=profile
    if kind == "circle":
        return Part.Face(Part.Wire([Part.makeCircle(data,center,normal)]))
    if kind == "wire":
        matrix=App.Matrix()
        for row in range(3):
            for col,axis in enumerate((x_axis,y_axis,normal)):
                setattr(matrix,"A%d%d"%(row+1,col+1),axis[row])
        wire=data.copy()
        wire.Placement=App.Placement(center,App.Rotation(matrix))
        return Part.Face(wire)
    points=[center+x_axis*x+y_axis*y for x,y in data]
    return Part.Face(Part.makePolygon(points+[points[0]]))


def _fits_opening(profile, center, x_axis, y_axis, normal, face, boundary, margin, seams):
    opening=_opening_face(profile,center,x_axis,y_axis,normal)
    tolerance=max(1e-9,opening.Area*1e-8)
    if not seams and opening.cut(face).Area > tolerance:
        return False
    for edge in boundary:
        if margin > 1e-7:
            if opening.distToShape(edge)[0] < margin-1e-7:
                return False
        elif seams and opening.common(edge).Length > 1e-7:
            return False
    return True


def _sweep_border(pipe, travel):
    end=pipe.copy()
    end.translate(travel)
    pieces=[pipe,end]
    for face in pipe.Faces:
        try:
            swept=face.extrude(travel)
            if swept.Solids and swept.Volume>1e-10:
                pieces.append(swept)
        except Part.OCCError:
            continue
    return pieces[0].multiFuse(pieces[1:])


def _partial_region(face, boundary, margin, depth, normal=None):
    """Build a clipping volume and remove border strips only at exposed edges."""
    if normal is not None:
        region=face.copy()
    else:
        region=face.makeOffsetShape(-depth,1e-6,fill=True)
        if region.isNull() or not region.isValid() or not region.Solids:
            raise ValueError("Cannot build a partial-hole region for this curved face. Reduce depth or split the face.")
    if margin > 0:
        for edge in boundary:
            # A circular pipe about the edge, swept inward, protects a border
            # of the requested width, including curved boundary edges.
            tangent=edge.tangentAt(edge.FirstParameter)
            circle=Part.Wire([Part.makeCircle(margin,edge.Vertexes[0].Point,tangent)])
            pipe=Part.Wire([edge]).makePipeShell([circle],True,False)
            if normal is not None:
                strip=pipe
            else:
                # Offset the boundary tube inward with the surface's local
                # normal; curved boundary protection is conservative.
                u,v=face.Surface.parameter(edge.CenterOfMass)
                n=face.normalAt(u,v)
                strip=_sweep_border(pipe,-n*depth)
            region=region.cut(strip)
    if normal is not None:
        region.translate(normal*1e-5)
        region=region.extrude(-normal*(depth+2e-5))
    return region


def perforate_curved(source_shape, face, pattern, hole_shape, pitch, size, margin,
                     pattern_angle=0, hole_angle=0, offset_x=0, offset_y=0, flip_every=0, depth=2, _transport=None, _seams=(), _chart=None, size2=0, pitch_y=10, row_offset=5, partial_holes=False):
    """Place cutters in a surface parameter chart and follow local normals.

    Cylinder U distances are arc lengths. Other surfaces use the metric at the
    chart midpoint, so spacing varies where the surface metric changes.
    """
    if pattern == "Brick" and pitch_y <= 0:
        raise ValueError("Brick Y spacing must be positive.")
    if pitch <= 0 or size <= 0 or size >= pitch or margin < 0:
        raise ValueError("Use positive dimensions, with opening size smaller than pitch.")
    u0, u1, v0, v1 = face.ParameterRange
    um, vm = (u0+u1)/2, (v0+v1)/2
    surface = face.Surface
    def point(u, v):
        return surface.value(u, v)
    du, dv = max((u1-u0)*1e-5, 1e-7), max((v1-v0)*1e-5, 1e-7)
    su = (point(um+du, vm)-point(um-du, vm)).Length/(2*du)
    sv = (point(um, vm+dv)-point(um, vm-dv)).Length/(2*dv)
    if min(su, sv) < 1e-8:
        raise ValueError("This surface has a singular parameter chart. Split the face away from its pole.")
    width, height = (u1-u0)*su, (v1-v0)*sv
    extent = math.hypot(width, height) + abs(offset_x)+abs(offset_y)+pitch
    if _transport is not None and _chart is not None:
        extent += (_transport[0]-_chart[2]).Length
    n = math.ceil(extent/min(pitch, pitch_y) if pattern == "Brick" else extent/pitch)*2+4
    if n*n > MAX_OPENINGS*32:
        raise ValueError("Pattern is too dense for this curved face. Increase pitch.")
    profile = hole_profile(hole_shape, size, size2)
    radius = _profile_radius(profile)
    box = source_shape.BoundBox
    half_depth = math.sqrt(box.XLength**2+box.YLength**2+box.ZLength**2)+1
    angle = math.radians(pattern_angle)
    ca, sa = math.cos(angle), math.sin(angle)
    tools, centers = [], []
    # Seam edges of periodic surfaces are not physical borders.
    edges = [edge for edge in face.Edges if not edge.isSeam(face)
             and not any(edge.isSame(seam) for seam in _seams)]
    clip = _partial_region(face,edges,margin,depth) if partial_holes else None
    for row in range(-n, n+1):
        for col in range(-n, n+1):
            site = grid_position(pattern, col, row, pitch, pitch_y, row_offset)
            if site is None:
                continue
            x, y = site[0]+offset_x, site[1]+offset_y
            u = um+(x*ca-y*sa)/su
            v = vm+(x*sa+y*ca)/sv
            if _transport is not None and _chart is not None:
                origin,gx,gy,_,_,_ = _transport
                ur,vr,ref,tangent,radius = _chart
                delta = origin+gx*x+gy*y-ref
                u = ur+delta.dot(tangent)/radius
                v = vr+delta.dot(surface.Axis)
            if not (u0-radius/su <= u <= u1+radius/su and v0-radius/sv <= v <= v1+radius/sv):
                continue
            center = point(u,v)
            if not face.isInside(center, 1e-6, True):
                if not partial_holes and (not _seams or min(edge.distToShape(Part.Vertex(center))[0] for edge in _seams) >= radius):
                    continue
            if any((center-other).Length < 1e-6 for other in centers):
                continue
            normal = face.normalAt(u,v)
            normal.normalize()
            hx = point(u+du,v)-point(u-du,v)
            hx.normalize()
            hy = normal.cross(hx)
            hy.normalize()
            # Align positive local Y with increasing surface V.
            if hy.dot(point(u,v+dv)-point(u,v-dv)) < 0:
                hy = -hy
            if _transport is not None and _chart is not None:
                rot = App.Rotation(surface.Axis, math.degrees(u-_chart[0]))
                hx,hy = [rot.multVec(vec) for vec in _transport[4:6]]
            turn = hole_angle + (90+pattern_angle if pattern == "Triangle Tiling" else 0)
            flipped = hole_flip(hole_shape,col,row,flip_every)
            if pattern == "Triangle Tiling":
                flipped = flipped != (col % 2 != 0)
            turn = math.radians(turn+(180 if flipped else 0))
            tx = hx*math.cos(turn)+hy*math.sin(turn)
            ty = hy*math.cos(turn)-hx*math.sin(turn)
            tool=_make_tool(profile,center,tx,ty,normal,half_depth,depth)
            if not partial_holes:
                # Test real cutter intersections rather than a bounding circle.
                if any(tool.common(edge).Length > 1e-7 or
                       (margin > 1e-7 and tool.distToShape(edge)[0] < margin-1e-7)
                       for edge in edges):
                    continue
            if clip is not None:
                tool=tool.common(clip)
                if tool.isNull() or tool.Volume<1e-9:
                    continue
            tools.append(tool)
            centers.append(center)
            if len(tools)>MAX_OPENINGS:
                raise ValueError("Too many curved-face openings. Increase pitch.")
    return tools, len(tools)


def perforate_faces(source_shape, faces, pattern, hole_shape, pitch, size, margin,
                    pattern_angle=0, hole_angle=0, offset_x=0, offset_y=0, flip_every=0, depth=2, size2=0, pitch_y=10, row_offset=5, partial_holes=False):
    frames, seams, charts = connected_frames(faces, pattern_angle)
    tools, count = [], 0
    for i, face in enumerate(faces):
        if isinstance(face.Surface, Part.Plane):
            cutters, n = perforate(source_shape, face, pattern, hole_shape, pitch, size,
                                  margin, pattern_angle, hole_angle, offset_x, offset_y,
                                  flip_every, _transport=frames[i],
                                  _seams=seams[i], _tools_only=True, depth=depth, size2=size2, pitch_y=pitch_y, row_offset=row_offset, partial_holes=partial_holes)
        else:
            cutters, n = perforate_curved(source_shape, face, pattern, hole_shape,
                                         pitch, size, margin, pattern_angle,
                                         hole_angle, offset_x, offset_y, flip_every, depth=depth,
                                         _transport=frames[i] if i in charts else None,
                                         _seams=seams[i], _chart=charts.get(i), size2=size2, pitch_y=pitch_y, row_offset=row_offset, partial_holes=partial_holes)
        tools.extend(cutters)
        count += n
        if count > MAX_OPENINGS:
            raise ValueError("Too many openings. Increase the pitch.")
    if not tools:
        raise ValueError("No openings fit on the selected faces.")
    result = source_shape.cut(Part.makeCompound(tools))
    if result.isNull() or not result.isValid():
        raise RuntimeError("The boolean cut failed. Increase pitch or reduce opening size.")
    return result, count


def perforate(source_shape, face, pattern, hole_shape, pitch, size, margin,
              pattern_angle=0, hole_angle=0, offset_x=0, offset_y=0, flip_every=0,
              _transport=None, _seams=(), _tools_only=False, depth=2, size2=0, pitch_y=10, row_offset=5, partial_holes=False):
    """Cut an array of openings through the source solid at the selected face."""
    if source_shape.isNull() or len(source_shape.Solids) != 1:
        raise ValueError("Select a face on an object containing exactly one solid.")
    if not isinstance(face.Surface, Part.Plane):
        raise ValueError("Only planar faces are supported.")
    if pattern == "Brick" and pitch_y <= 0:
        raise ValueError("Brick Y spacing must be positive.")
    if pitch <= 0 or size <= 0 or margin < 0 or size >= pitch:
        raise ValueError("Use positive dimensions, with opening size smaller than pitch.")

    if pattern not in ARRANGEMENTS:
        raise ValueError("Choose a valid pattern arrangement.")
    profile = hole_profile(hole_shape, size, size2)
    radius = _profile_radius(profile)
    origin, grid_x, grid_y, normal = _frame(face, pattern_angle)
    _, hole_x, hole_y, _ = _frame(
        face, hole_angle + (90 + pattern_angle if pattern == "Triangle Tiling" else 0))
    if _transport is not None:
        origin, grid_x, grid_y, normal, hx, hy = _transport
        angle = math.radians(hole_angle + (90 + pattern_angle if pattern == "Triangle Tiling" else 0))
        hole_x = hx * math.cos(angle) + hy * math.sin(angle)
        hole_y = hy * math.cos(angle) - hx * math.sin(angle)
    xmin, xmax, ymin, ymax = _bounds(face, origin, grid_x, grid_y)
    y_pitch = pitch_y if pattern == "Brick" else (pitch if pattern == "Square" else pitch * math.sqrt(3) / 2)
    if pattern == "Triangle Tiling":
        y_pitch = pitch / (2 * math.sqrt(3))
    col_start = math.floor((xmin - offset_x) / pitch) - 2
    col_stop = math.ceil((xmax - offset_x) / pitch) + 3
    row_start = math.floor((ymin - offset_y) / y_pitch) - 2
    row_stop = math.ceil((ymax - offset_y) / y_pitch) + 3
    if pattern == "Triangle Tiling":
        col_start *= 2
        col_stop *= 2
    nx = col_stop - col_start
    ny = row_stop - row_start
    if nx * ny > MAX_OPENINGS * 8:
        raise ValueError("Pattern is too dense for this face. Increase the pitch.")

    # The cutter spans the entire object's bounding box in both normal
    # directions, so it works even when the selected face normal is reversed.
    box = source_shape.BoundBox
    half_depth = math.sqrt(box.XLength ** 2 + box.YLength ** 2 +
                           box.ZLength ** 2) + 1
    tools = []
    boundary = [edge for edge in face.Edges
                if not any(edge.isSame(seam) for seam in _seams)]
    clip = None
    if _seams:
        base = face.copy()
        base.translate(-normal * half_depth)
        clip = base.extrude(normal * (2 * half_depth))
    if partial_holes:
        clip = _partial_region(face,boundary,margin,depth,normal)
    for row in range(row_start, row_stop):
        for col in range(col_start, col_stop):
            position = grid_position(pattern, col, row, pitch, pitch_y, row_offset)
            if position is None:
                continue
            x, y = position
            center = (origin + grid_x * (x + offset_x) +
                      grid_y * (y + offset_y))
            inside = face.isInside(center, 1e-7, True)
            if not inside and (not (_seams or partial_holes) or face.distToShape(Part.Vertex(center))[0] >= radius):
                continue
            flipped = hole_flip(hole_shape, col, row, flip_every)
            if pattern == "Triangle Tiling":
                flipped = flipped != (col % 2 != 0)
            flip = -1 if flipped else 1
            if not partial_holes and not _fits_opening(
                    profile,center,hole_x*flip,hole_y*flip,normal,
                    face,boundary,margin,_seams):
                continue
            tool = _make_tool(profile, center, hole_x * flip, hole_y * flip,
                              normal, half_depth, depth)
            if clip is not None:
                tool = tool.common(clip)
                if tool.isNull() or tool.Volume < 1e-9:
                    continue
            tools.append(tool)
            if len(tools) > MAX_OPENINGS:
                raise ValueError("More than %d openings. Increase the pitch." % MAX_OPENINGS)
    if _tools_only:
        return tools, len(tools)
    if not tools:
        raise ValueError("No openings fit on this face. Reduce size or border clearance.")
    result = source_shape.cut(Part.makeCompound(tools))
    if result.isNull() or not result.isValid():
        raise RuntimeError("The boolean cut failed. Try a larger pitch or smaller opening.")
    return result, len(tools)


class PerforationFeature:
    def __init__(self, obj):
        obj.addProperty("App::PropertyLink", "Source", "Perforation",
                        "Solid to perforate")
        obj.addProperty("App::PropertyString", "FaceName", "Perforation",
                        "Selected planar face, e.g. Face1")
        obj.addProperty("App::PropertyStringList", "FaceNames", "Perforation",
                        "Selected faces; the first face anchors the pattern")
        obj.addProperty("App::PropertyEnumeration", "Pattern", "Pattern",
                        "Arrangement of hole centers")
        obj.Pattern = list(ARRANGEMENTS)
        obj.addProperty("App::PropertyEnumeration", "HoleShape", "Hole",
                        "Shape of each opening")
        obj.HoleShape = list(HOLE_SHAPES)
        obj.addProperty("App::PropertyLength", "Pitch", "Pattern",
                        "Distance between pattern cells")
        obj.addProperty("App::PropertyLength", "PitchY", "Pattern", "Brick spacing between rows")
        obj.PitchY = 10
        obj.addProperty("App::PropertyDistance", "RowOffset", "Pattern", "Brick shift of alternating rows")
        obj.RowOffset = 5
        obj.addProperty("App::PropertyLength", "OpeningSize", "Hole",
                        "Maximum opening dimension")
        obj.addProperty("App::PropertyLength", "Size2", "Hole", "Second profile dimension; zero uses the shape default")
        obj.Size2 = 0
        obj.addProperty("App::PropertyBool", "PartialHoles", "Pattern", "Trim partially fitting holes to the face and border")
        obj.PartialHoles = False
        obj.addProperty("App::PropertyLength", "Border", "Pattern",
                        "Minimum clear border around the face")
        obj.addProperty("App::PropertyAngle", "PatternRotation", "Pattern",
                        "Rotation of the arrangement on the face")
        obj.addProperty("App::PropertyAngle", "HoleRotation", "Hole",
                        "Rotation of each hole independently of the arrangement")
        obj.addProperty("App::PropertyLength", "Depth", "Hole", "Blind hole depth inward from the surface")
        obj.Depth = 2
        obj.addProperty("App::PropertyIntegerConstraint", "FlipEvery", "Hole",
                        "Flip holes by 180 degrees every N columns and rows; 0 disables")
        obj.FlipEvery = (0, 0, 100000, 1)
        obj.addProperty("App::PropertyLength", "OffsetX", "Pattern",
                        "Translate the arrangement along its X axis")
        obj.addProperty("App::PropertyLength", "OffsetY", "Pattern",
                        "Translate the arrangement along its Y axis")
        obj.addProperty("App::PropertyInteger", "OpeningCount", "Result",
                        "Number of cut openings")
        obj.addProperty("App::PropertyInteger", "GridVersion", "Internal",
                        "Version of the arrangement geometry")
        obj.setEditorMode("OpeningCount", 1)
        obj.setEditorMode("GridVersion", 2)
        obj.Pattern = "Square"
        obj.HoleShape = "Round"
        obj.Pitch = 10
        obj.OpeningSize = 5
        obj.Border = 2
        obj.PatternRotation = 0
        obj.HoleRotation = 0
        obj.OffsetX = 0
        obj.OffsetY = 0
        obj.GridVersion = 2
        obj.Proxy = self

    def execute(self, obj):
        source = obj.Source
        if source is None:
            raise ValueError("Perforation source is missing.")
        names = list(obj.FaceNames) or [obj.FaceName]
        faces = resolve_faces(source.Shape, names)
        result, count = perforate_faces(source.Shape, faces,
                                  obj.Pattern, obj.HoleShape, obj.Pitch.Value,
                                  obj.OpeningSize.Value, obj.Border.Value,
                                  obj.PatternRotation.Value,
                                  obj.HoleRotation.Value,
                                  obj.OffsetX.Value, obj.OffsetY.Value, obj.FlipEvery,
                                  depth=obj.Depth.Value, size2=obj.Size2.Value,
                                  pitch_y=obj.PitchY.Value, row_offset=obj.RowOffset.Value,
                                  partial_holes=obj.PartialHoles)
        obj.Shape = result
        obj.OpeningCount = count

    def onDocumentRestored(self, obj):
        properties = set(obj.PropertiesList)
        if "PartialHoles" not in properties:
            obj.addProperty("App::PropertyBool", "PartialHoles", "Pattern", "Trim partially fitting holes to face and border")
            obj.PartialHoles = False
        if "PitchY" not in properties:
            obj.addProperty("App::PropertyLength", "PitchY", "Pattern", "Brick spacing between rows")
            obj.PitchY = obj.Pitch.Value
        if "RowOffset" not in properties:
            obj.addProperty("App::PropertyDistance", "RowOffset", "Pattern", "Brick shift of alternating rows")
            obj.RowOffset = obj.Pitch.Value/2
        if "Size2" not in properties:
            obj.addProperty("App::PropertyLength", "Size2", "Hole", "Second profile dimension; zero uses default")
            obj.Size2 = 0
        if "ThroughAll" in properties:
            if obj.ThroughAll and obj.Source:
                box = obj.Source.Shape.BoundBox
                obj.Depth = math.sqrt(box.XLength**2+box.YLength**2+box.ZLength**2)+1
            obj.removeProperty("ThroughAll")
        if "Depth" not in properties:
            obj.addProperty("App::PropertyLength", "Depth", "Hole", "Blind hole depth inward from the surface")
            obj.Depth = 2
        if "FaceNames" not in properties:
            obj.addProperty("App::PropertyStringList", "FaceNames", "Perforation",
                            "Selected faces")
            obj.FaceNames = [obj.FaceName]

        if "FlipEvery" not in properties:
            obj.addProperty("App::PropertyIntegerConstraint", "FlipEvery", "Hole",
                            "Flip holes every N columns and rows; 0 disables")
            obj.FlipEvery = (1 if getattr(obj, "HoleShape", "") == "Triangle" else 0, 0, 100000, 1)
        old_pattern = str(obj.Pattern)
        obj.Pattern = list(ARRANGEMENTS)
        obj.Pattern = old_pattern
        old_style = "HoleShape" not in properties
        grid_version = obj.GridVersion if "GridVersion" in properties else 0
        refresh_hexagon = (not old_style and old_pattern == "Hexagon" and
                           grid_version < 2)
        if "GridVersion" not in properties:
            obj.addProperty("App::PropertyInteger", "GridVersion", "Internal",
                            "Version of the arrangement geometry")
        if grid_version < 2:
            obj.GridVersion = 2
        obj.setEditorMode("GridVersion", 2)
        if old_style:
            obj.addProperty("App::PropertyEnumeration", "HoleShape", "Hole",
                            "Shape of each opening")
            obj.HoleShape = list(HOLE_SHAPES)
        if not old_style:
            saved_shape = str(obj.HoleShape)
            obj.HoleShape = list(HOLE_SHAPES)
            obj.HoleShape = saved_shape
        if "PatternRotation" not in properties:
            obj.addProperty("App::PropertyAngle", "PatternRotation", "Pattern",
                            "Rotation of the arrangement on the face")
            obj.PatternRotation = obj.Rotation.Value if "Rotation" in properties else 0
        if "HoleRotation" not in properties:
            obj.addProperty("App::PropertyAngle", "HoleRotation", "Hole",
                            "Rotation of each hole")
            obj.HoleRotation = 0
        for name in ("OffsetX", "OffsetY"):
            if name not in properties:
                obj.addProperty("App::PropertyLength", name, "Pattern",
                                "Translate the arrangement along its %s axis" % name[-1])
                setattr(obj, name, 0)
        if old_style:
            arrangement, hole_shape = LEGACY_STYLES.get(old_pattern,
                                                        ("Square", "Round"))
            obj.Pattern = list(ARRANGEMENTS)
            obj.Pattern = arrangement
            obj.HoleShape = hole_shape
            if old_pattern == "Round Hole Slotted":
                obj.HoleRotation = 90
            if old_pattern in ("Round Hole Staggered", "Octagon Cane",
                               "Marietta", "Grecian"):
                App.Console.PrintWarning(
                    "Quick Perforate: '%s' was converted to a separate "
                    "pattern and hole shape. Check its geometry after "
                    "recomputing.\n" % old_pattern)
        if "Rotation" in properties:
            obj.setEditorMode("Rotation", 2)
        obj.Proxy = self
        if App.GuiUp:
            from .QuickPerforateGui import PerforationViewProvider
            PerforationViewProvider(obj.ViewObject)
        if refresh_hexagon:
            obj.touch()
            obj.Document.recompute()  # update the saved cut once on opening


def create_feature(doc, source, face_name, pattern="Square", hole_shape="Round",
                   pitch=10, size=5, border=2, pattern_rotation=0,
                   hole_rotation=0, offset_x=0, offset_y=0, flip_every=0, depth=2, size2=0, pitch_y=10, row_offset=5, partial_holes=False):
    obj = doc.addObject("Part::FeaturePython", "Perforation")
    PerforationFeature(obj)
    obj.Label = "%s perforated" % source.Label
    obj.Source = source
    names = [face_name] if isinstance(face_name, str) else list(face_name)
    obj.FaceName = names[0]
    obj.FaceNames = names
    obj.Pattern = pattern
    obj.HoleShape = hole_shape
    obj.Pitch = pitch
    obj.PitchY = pitch_y
    obj.RowOffset = row_offset
    obj.OpeningSize = size
    obj.Size2 = size2
    obj.Border = border
    obj.PartialHoles = partial_holes
    obj.PatternRotation = pattern_rotation
    obj.HoleRotation = hole_rotation
    obj.Depth = depth
    obj.FlipEvery = flip_every
    obj.OffsetX = offset_x
    obj.OffsetY = offset_y
    if App.GuiUp:
        from .QuickPerforateGui import PerforationViewProvider
        PerforationViewProvider(obj.ViewObject)
    return obj
