"""Parametric perforation feature and pattern geometry.

Only planar faces of a single solid are supported. Coordinates and dimensions are
in FreeCAD's document units (normally millimetres).
"""

import math

import FreeCAD as App
import Part


ARRANGEMENTS = ("Square", "Triangle", "Hexagon", "Triangle Tiling")
HOLE_SHAPES = (
    "Round", "Square", "Triangle", "Hexagon", "Octagon",
    "Hexagon Star", "Diamond", "Slot", "Airline Slot", "Clover",
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


def hole_profile(hole_shape, size):
    """Return a circle or polygon for one opening, centered at the origin."""
    r = size / 2
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


def grid_position(pattern, col, row, pitch):
    """Return a hole center in pattern coordinates, or None for an empty site."""
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
    return max(math.hypot(x, y) for x, y in data)


def _make_tool(profile, center, x_axis, y_axis, normal, half_depth):
    kind, data = profile
    base = center - normal * half_depth
    if kind == "circle":
        return Part.makeCylinder(data, 2 * half_depth, base, normal)
    points = [base + x_axis * x + y_axis * y for x, y in data]
    points.append(points[0])
    return Part.Face(Part.makePolygon(points)).extrude(normal * (2 * half_depth))


def perforate(source_shape, face, pattern, hole_shape, pitch, size, margin,
              pattern_angle=0, hole_angle=0, offset_x=0, offset_y=0, flip_every=0):
    """Cut an array of openings through the source solid at the selected face."""
    if source_shape.isNull() or len(source_shape.Solids) != 1:
        raise ValueError("Select a face on an object containing exactly one solid.")
    if not isinstance(face.Surface, Part.Plane):
        raise ValueError("Only planar faces are supported.")
    if pitch <= 0 or size <= 0 or margin < 0 or size >= pitch:
        raise ValueError("Use positive dimensions, with opening size smaller than pitch.")

    if pattern not in ARRANGEMENTS:
        raise ValueError("Choose a valid pattern arrangement.")
    profile = hole_profile(hole_shape, size)
    radius = _profile_radius(profile)
    origin, grid_x, grid_y, normal = _frame(face, pattern_angle)
    _, hole_x, hole_y, _ = _frame(
        face, hole_angle + (90 + pattern_angle if pattern == "Triangle Tiling" else 0))
    xmin, xmax, ymin, ymax = _bounds(face, origin, grid_x, grid_y)
    y_pitch = pitch if pattern == "Square" else pitch * math.sqrt(3) / 2
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
    for row in range(row_start, row_stop):
        for col in range(col_start, col_stop):
            position = grid_position(pattern, col, row, pitch)
            if position is None:
                continue
            x, y = position
            center = (origin + grid_x * (x + offset_x) +
                      grid_y * (y + offset_y))
            if not face.isInside(center, 1e-7, True):
                continue
            # A full circumcircle must clear every outer and inner edge.
            vertex = Part.Vertex(center)
            if any(wire.distToShape(vertex)[0] < radius + margin
                   for wire in face.Wires):
                continue
            flipped = hole_flip(hole_shape, col, row, flip_every)
            if pattern == "Triangle Tiling":
                flipped = flipped != (col % 2 != 0)
            flip = -1 if flipped else 1
            tools.append(_make_tool(profile, center, hole_x * flip, hole_y * flip,
                                    normal, half_depth))
            if len(tools) > MAX_OPENINGS:
                raise ValueError("More than %d openings. Increase the pitch." % MAX_OPENINGS)
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
        obj.addProperty("App::PropertyEnumeration", "Pattern", "Pattern",
                        "Arrangement of hole centers")
        obj.Pattern = list(ARRANGEMENTS)
        obj.addProperty("App::PropertyEnumeration", "HoleShape", "Hole",
                        "Shape of each opening")
        obj.HoleShape = list(HOLE_SHAPES)
        obj.addProperty("App::PropertyLength", "Pitch", "Pattern",
                        "Distance between pattern cells")
        obj.addProperty("App::PropertyLength", "OpeningSize", "Hole",
                        "Maximum opening dimension")
        obj.addProperty("App::PropertyLength", "Border", "Pattern",
                        "Minimum clear border around the face")
        obj.addProperty("App::PropertyAngle", "PatternRotation", "Pattern",
                        "Rotation of the arrangement on the face")
        obj.addProperty("App::PropertyAngle", "HoleRotation", "Hole",
                        "Rotation of each hole independently of the arrangement")
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
        name = obj.FaceName
        if not name.startswith("Face") or not name[4:].isdigit():
            raise ValueError("Select a face on the source solid.")
        index = int(name[4:]) - 1
        if index < 0 or index >= len(source.Shape.Faces):
            raise ValueError("The selected face no longer exists on the source.")
        result, count = perforate(source.Shape, source.Shape.Faces[index],
                                  obj.Pattern, obj.HoleShape, obj.Pitch.Value,
                                  obj.OpeningSize.Value, obj.Border.Value,
                                  obj.PatternRotation.Value,
                                  obj.HoleRotation.Value,
                                  obj.OffsetX.Value, obj.OffsetY.Value, obj.FlipEvery)
        obj.Shape = result
        obj.OpeningCount = count

    def onDocumentRestored(self, obj):
        properties = set(obj.PropertiesList)
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
            from QuickPerforateGui import PerforationViewProvider
            PerforationViewProvider(obj.ViewObject)
        if refresh_hexagon:
            obj.touch()
            obj.Document.recompute()  # update the saved cut once on opening


def create_feature(doc, source, face_name, pattern="Square", hole_shape="Round",
                   pitch=10, size=5, border=2, pattern_rotation=0,
                   hole_rotation=0, offset_x=0, offset_y=0, flip_every=0):
    obj = doc.addObject("Part::FeaturePython", "Perforation")
    PerforationFeature(obj)
    obj.Label = "%s perforated" % source.Label
    obj.Source = source
    obj.FaceName = face_name
    obj.Pattern = pattern
    obj.HoleShape = hole_shape
    obj.Pitch = pitch
    obj.OpeningSize = size
    obj.Border = border
    obj.PatternRotation = pattern_rotation
    obj.HoleRotation = hole_rotation
    obj.FlipEvery = flip_every
    obj.OffsetX = offset_x
    obj.OffsetY = offset_y
    if App.GuiUp:
        from QuickPerforateGui import PerforationViewProvider
        PerforationViewProvider(obj.ViewObject)
    return obj
