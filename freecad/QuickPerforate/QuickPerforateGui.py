"""FreeCAD command and task panel for Quick Perforate."""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui
import Part

try:
    from PySide2 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide import QtCore, QtGui
    QtWidgets = QtGui

from . import QuickPerforate as QP


ICON = os.path.join(os.path.dirname(__file__), "Resources", "Icons", "quickperforate.svg")


def selected_faces():
    selection = Gui.Selection.getSelectionEx()
    if not selection or len({item.Object.Name for item in selection}) != 1:
        raise ValueError("Select faces on one source solid.")
    obj = selection[0].Object
    if not hasattr(obj, "Shape") or len(obj.Shape.Solids) != 1:
        raise ValueError("Select faces on an object containing one solid.")
    names = list(dict.fromkeys(name for item in selection for name in item.SubElementNames))
    QP.resolve_faces(obj.Shape, names)
    return obj, names


def selected_face():
    obj, names = selected_faces()
    return obj, names[0]


class PatternPreview(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 160)
        self.setAlignment(QtCore.Qt.AlignCenter)

    def update_pattern(self, pattern, hole_shape, size_ratio, pattern_angle,
                       hole_angle, offset_x, offset_y, flip_every=0, size2=0, pitch_y=1, row_offset=.5, custom_profile=None):
        """Draw five rows with five holes each in a square sample image."""
        canvas = QtGui.QPixmap(160, 160)
        canvas.fill(QtGui.QColor("#edf2f4"))
        painter = QtGui.QPainter(canvas)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor("#687e89"))
        painter.drawRect(8, 8, 144, 144)
        painter.setClipRect(8, 8, 144, 144)
        painter.setBrush(QtGui.QColor("#edf2f4"))

        sites = []
        flips = {}
        for row in range(-2, 3):
            candidates = []
            columns = range(-8, 9) if pattern == "Hexagon" else range(-2, 3)
            for col in columns:
                point = QP.grid_position(pattern, col, row, 1, pitch_y, row_offset)
                if point is not None:
                    candidates.append(point)
                    flips[point] = (QP.hole_flip(hole_shape, col, row, flip_every)
                                    != (pattern == "Triangle Tiling" and col % 2 != 0))
            if pattern == "Hexagon":
                candidates = sorted(candidates, key=lambda p: abs(p[0]))[:5]
            sites.extend(candidates)

        cx = (min(x for x, _ in sites) + max(x for x, _ in sites)) / 2
        cy = (min(y for _, y in sites) + max(y for _, y in sites)) / 2
        angle = math.radians(pattern_angle)
        ca, sa = math.cos(angle), math.sin(angle)
        centers = [((x - cx) * ca - (y - cy) * sa,
                    (x - cx) * sa + (y - cy) * ca) for x, y in sites]
        span_x = max(x for x, _ in centers) - min(x for x, _ in centers)
        span_y = max(y for _, y in centers) - min(y for _, y in centers)
        size_ratio = max(0.05, min(size_ratio, 0.9))
        scale = min(120 / (span_x + size_ratio),
                    120 / (span_y + size_ratio))
        shift_x = (offset_x * ca - offset_y * sa) * scale
        shift_y = (offset_x * sa + offset_y * ca) * scale
        profile = custom_profile if custom_profile is not None else QP.hole_profile(hole_shape, size_ratio, size2)
        hole_angle = math.radians(
            hole_angle + (90 + pattern_angle if pattern == "Triangle Tiling" else 0))
        hc, hs = math.cos(hole_angle), math.sin(hole_angle)
        for (x, y), site in zip(centers, sites):
            flip = -1 if flips[site] else 1
            px, py = 80 + x * scale + shift_x, 80 + y * scale + shift_y
            if profile[0] == "circle":
                radius = profile[1] * scale
                painter.drawEllipse(QtCore.QPointF(px, py), radius, radius)
            elif profile[0] == "face":
                path=QtGui.QPainterPath()
                path.setFillRule(QtCore.Qt.OddEvenFill)
                for wire in profile[1].Wires:
                    points=wire.discretize(Deflection=0.002)
                    for i,point in enumerate(points):
                        q=QtCore.QPointF(px+(point.x*hc-point.y*hs)*scale*flip,
                                        py+(point.x*hs+point.y*hc)*scale*flip)
                        if i == 0:
                            path.moveTo(q)
                        else:
                            path.lineTo(q)
                    path.closeSubpath()
                painter.drawPath(path)
            else:
                points = ([(p.x,p.y) for p in profile[1].discretize(Deflection=0.002)]
                          if profile[0] == "wire" else profile[1])
                polygon = QtGui.QPolygonF([
                    QtCore.QPointF(px + (vx * hc - vy * hs) * scale * flip,
                                   py + (vx * hs + vy * hc) * scale * flip)
                    for vx, vy in points])
                painter.drawPolygon(polygon)
        painter.end()
        self.setPixmap(canvas)


class PerforationTaskPanel:
    def __init__(self, source, face_name, feature=None):
        self.source = source
        self.face_names = list(getattr(feature, "FaceNames", [])) or ([face_name] if isinstance(face_name, str) else list(face_name))
        self.face_name = self.face_names[0]
        self.feature = feature
        self.edit_mode = feature is not None
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle("Edit Perforation" if feature else "Quick Perforate")
        layout = QtWidgets.QVBoxLayout(self.form)
        self.face_label = QtWidgets.QLabel()
        self.face_label.setWordWrap(True)
        layout.addWidget(self.face_label)
        self.face_list = QtWidgets.QListWidget()
        self.face_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.face_list.setMaximumHeight(100)
        layout.addWidget(self.face_list)
        self._update_face_label()
        pick_face = QtWidgets.QPushButton("Add selected faces")
        pick_face.setToolTip("Select a planar face in the 3D view, then click here")
        pick_face.clicked.connect(self.use_selected_face)
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.setToolTip("Update the perforation and keep this panel open")
        self.apply_button.clicked.connect(self.apply)
        button_row = QtWidgets.QHBoxLayout()
        button_row.addWidget(pick_face)
        remove_face = QtWidgets.QPushButton("Remove")
        remove_face.clicked.connect(self.remove_faces)
        button_row.addWidget(remove_face)
        button_row.addWidget(self.apply_button)
        layout.addLayout(button_row)

        form = QtWidgets.QFormLayout()
        layout.addLayout(form)
        self.pattern = QtWidgets.QComboBox()
        self.pattern.addItems(QP.ARRANGEMENTS)
        form.addRow("Pattern", self.pattern)
        self.hole_shape = QtWidgets.QComboBox()
        self.hole_shape.addItems(QP.HOLE_SHAPES)
        form.addRow("Hole shape", self.hole_shape)
        self.sketch = QtWidgets.QComboBox()
        self.sketch.addItem("Select a closed sketch", "")
        for obj in source.Document.Objects:
            if obj.isDerivedFrom("Sketcher::SketchObject") and (feature is None or obj != feature and feature not in obj.OutListRecursive):
                self.sketch.addItem(obj.Label,obj.Name)
        if feature and getattr(feature,"HoleSketch",None):
            self.sketch.setCurrentIndex(self.sketch.findData(feature.HoleSketch.Name))
        form.addRow("Hole sketch",self.sketch)
        self.preview = PatternPreview()
        layout.addWidget(self.preview, 0, QtCore.Qt.AlignHCenter)

        self.pitch = self._spin(feature.Pitch.Value if feature else 10,
                                0.1, 100000, " mm")
        self.size = self._spin(feature.OpeningSize.Value if feature else 5,
                               0.1, 100000, " mm")
        self.border = self._spin(feature.Border.Value if feature else 2,
                                 0, 100000, " mm")
        self.pattern_rotation = self._spin(
            feature.PatternRotation.Value if feature else 0, -360, 360, "°")
        self.hole_rotation = self._spin(
            feature.HoleRotation.Value if feature else 0, -360, 360, "°")
        self.depth = self._spin(feature.Depth.Value if feature and hasattr(feature, "Depth") else 2,
                                0.01, 100000, " mm")
        self.flip_every = QtWidgets.QSpinBox()
        self.flip_every.setRange(0, 100000)
        self.flip_every.setValue(getattr(feature, "FlipEvery", 0) if feature else 0)
        self.flip_every.setSpecialValueText("Off")
        self.flip_every.setToolTip("Rotate alternating blocks of N columns and rows by 180°. 0 disables flipping.")
        form.addRow("Flip every N holes", self.flip_every)
        self.offset_x = self._spin(feature.OffsetX.Value if feature else 0,
                                   -100000, 100000, " mm")
        self.offset_y = self._spin(feature.OffsetY.Value if feature else 0,
                                   -100000, 100000, " mm")
        self.pitch_label = QtWidgets.QLabel("Pitch")
        form.addRow(self.pitch_label, self.pitch)
        self.pitch_y = self._spin(feature.PitchY.Value if feature and hasattr(feature,"PitchY") else 10,
                                  .1, 100000, " mm")
        self.row_offset = self._spin(feature.RowOffset.Value if feature and hasattr(feature,"RowOffset") else 5,
                                     -100000, 100000, " mm")
        self.pitch_y_label = QtWidgets.QLabel("Brick Y spacing")
        self.row_offset_label = QtWidgets.QLabel("Brick row offset")
        form.addRow(self.pitch_y_label, self.pitch_y)
        form.addRow(self.row_offset_label, self.row_offset)
        form.addRow("Size 1", self.size)
        self.size2 = self._spin(feature.Size2.Value if feature and hasattr(feature,"Size2") else 0,
                                0, 100000, " mm")
        self.size2.setSpecialValueText("Automatic")
        self.size2.setToolTip("Slot: minor dimension. Rounded profiles: overall second dimension. Zero uses default.")
        form.addRow("Size 2", self.size2)
        self.partial_holes = QtWidgets.QCheckBox("Allow partial holes")
        self.partial_holes.setChecked(getattr(feature,"PartialHoles",False))
        form.addRow(self.partial_holes)
        form.addRow("Hole depth", self.depth)
        form.addRow("Border clearance", self.border)
        form.addRow("Pattern rotation", self.pattern_rotation)
        form.addRow("Hole rotation", self.hole_rotation)
        form.addRow("Pattern offset X", self.offset_x)
        form.addRow("Pattern offset Y", self.offset_y)
        note = QtWidgets.QLabel("Offsets follow the pattern's X and Y axes. "
                                "Depth is measured inward along each local surface normal.")
        note.setWordWrap(True)
        layout.addWidget(note)
        for combo in (self.pattern, self.hole_shape, self.sketch):
            combo.currentTextChanged.connect(self.update_preview)
        for spin in (self.pitch, self.pitch_y, self.row_offset, self.size, self.size2, self.pattern_rotation,
                     self.hole_rotation, self.offset_x, self.offset_y, self.flip_every):
            spin.valueChanged.connect(self.update_preview)
        if feature:
            self.pattern.setCurrentText(feature.Pattern)
            self.hole_shape.setCurrentText(feature.HoleShape)
        self.update_preview()

    def update_preview(self, *_):
        brick = self.pattern.currentText() == "Brick"
        self.pitch_label.setText("Brick X spacing" if brick else "Pitch")
        for widget in (self.pitch_y,self.row_offset,self.pitch_y_label,self.row_offset_label):
            widget.setVisible(brick)
        pitch = max(self.pitch.value(), 0.1)
        custom = self.hole_shape.currentText() == "Custom Sketch"
        self.sketch.setEnabled(custom)
        sketch=self.source.Document.getObject(self.sketch.currentData() or "")
        if custom and sketch is None:
            self.preview.setText("Select a closed sketch")
            return
        try:
            profile=QP.sketch_profile(sketch,self.size.value()/pitch) if custom else None
        except ValueError as exc:
            self.preview.setText(str(exc))
            return
        self.preview.update_pattern(
            self.pattern.currentText(), self.hole_shape.currentText(),
            self.size.value() / pitch,
            self.pattern_rotation.value(), self.hole_rotation.value(),
            self.offset_x.value() / pitch, self.offset_y.value() / pitch, self.flip_every.value(),
            self.size2.value()/pitch, self.pitch_y.value()/pitch, self.row_offset.value()/pitch, custom_profile=profile)

    def _update_face_label(self):
        self.face_label.setText("Faces on %s (first face anchors pattern)" % self.source.Label)
        self.face_list.clear()
        self.face_list.addItems(self.face_names)
        self.face_name = self.face_names[0] if self.face_names else ""

    def remove_faces(self):
        removed = {item.text() for item in self.face_list.selectedItems()}
        self.face_names = [name for name in self.face_names if name not in removed]
        self._update_face_label()

    def use_selected_face(self):
        try:
            source, names = selected_faces()
            if source != self.source:
                raise ValueError("Add faces from the same source solid. Expand the perforation in the tree to select its source.")
            self.face_names.extend(name for name in names if name not in self.face_names)
            self._update_face_label()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(None, "Quick Perforate", str(exc))

    @staticmethod
    def _spin(value, minimum, maximum, suffix):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(suffix)
        return spin

    def accept(self):
        return self._apply(close=True)

    def apply(self, *_):
        return self._apply(close=False)

    def _apply(self, close):
        doc = App.ActiveDocument
        if doc is None or self.source.Document != doc:
            QtWidgets.QMessageBox.warning(None, "Quick Perforate", "The source document is no longer active.")
            return False
        transaction_open = False
        try:
            pitch = self.pitch.value()
            size = self.size.value()
            if size >= pitch:
                raise ValueError("Opening size must be smaller than pitch.")
            sketch=self.source.Document.getObject(self.sketch.currentData() or "")
            profile=QP.sketch_profile(sketch,size) if self.hole_shape.currentText() == "Custom Sketch" else None
            faces = QP.resolve_faces(self.source.Shape, self.face_names)
            QP.perforate_faces(self.source.Shape, faces,
                         self.pattern.currentText(), self.hole_shape.currentText(),
                         pitch, size, self.border.value(),
                         self.pattern_rotation.value(),
                         self.hole_rotation.value(),
                         self.offset_x.value(), self.offset_y.value(), self.flip_every.value(),
                         depth=self.depth.value(), size2=self.size2.value(),
                         pitch_y=self.pitch_y.value(), row_offset=self.row_offset.value(),
                         partial_holes=self.partial_holes.isChecked(), custom_profile=profile)
            doc.openTransaction("Edit perforation" if self.feature else
                                "Create perforation")
            transaction_open = True
            if self.feature:
                obj = self.feature
                old_source = obj.Source
                obj.Source = self.source
                obj.FaceName = self.face_name
                obj.FaceNames = self.face_names
                obj.Pattern = self.pattern.currentText()
                obj.HoleShape = self.hole_shape.currentText()
                obj.HoleSketch = sketch
                obj.Pitch = pitch
                obj.PitchY = self.pitch_y.value()
                obj.RowOffset = self.row_offset.value()
                obj.OpeningSize = size
                obj.Size2 = self.size2.value()
                obj.Border = self.border.value()
                obj.PartialHoles = self.partial_holes.isChecked()
                obj.PatternRotation = self.pattern_rotation.value()
                obj.HoleRotation = self.hole_rotation.value()
                obj.Depth = self.depth.value()
                obj.FlipEvery = self.flip_every.value()
                obj.OffsetX = self.offset_x.value()
                obj.OffsetY = self.offset_y.value()
            else:
                old_source = None
                obj = QP.create_feature(
                    doc, self.source, self.face_names,
                    pattern=self.pattern.currentText(),
                    hole_shape=self.hole_shape.currentText(),
                    pitch=pitch, size=size, border=self.border.value(),
                    pattern_rotation=self.pattern_rotation.value(),
                    hole_rotation=self.hole_rotation.value(),
                    offset_x=self.offset_x.value(), offset_y=self.offset_y.value(),
                    flip_every=self.flip_every.value(),
                    depth=self.depth.value(), size2=self.size2.value(),
                         pitch_y=self.pitch_y.value(), row_offset=self.row_offset.value(),
                         partial_holes=self.partial_holes.isChecked(), hole_sketch=sketch)
            doc.recompute()
            if obj.Shape.isNull():
                raise RuntimeError("The perforated result could not be created.")
            if old_source and old_source != self.source:
                old_source.ViewObject.Visibility = True
            self.source.ViewObject.Visibility = False
            obj.ViewObject.Visibility = True
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(obj)
            doc.commitTransaction()
            transaction_open = False
            self.feature = obj
            self.form.setWindowTitle("Edit Perforation")
        except Exception as exc:
            if transaction_open:
                doc.abortTransaction()
            QtWidgets.QMessageBox.warning(None, "Quick Perforate", str(exc))
            return False
        if close:
            self._close()
        return True

    def reject(self):
        self._close()
        return True

    def _close(self):
        if self.edit_mode:
            Gui.ActiveDocument.resetEdit()
        else:
            Gui.Control.closeDialog()


class PerforationViewProvider:
    """Show the source as a child and reopen the task panel for editing."""

    def __init__(self, vobj):
        self.Object = vobj.Object
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def claimChildren(self):
        return [self.Object.Source] if self.Object.Source else []

    def getIcon(self):
        return ICON

    def doubleClicked(self, vobj):
        Gui.ActiveDocument.setEdit(vobj.Object.Name)
        return True

    def setEdit(self, vobj, mode=0):
        if mode != 0:
            return None  # Let the native view provider handle Transform.
        obj = vobj.Object
        Gui.Control.showDialog(PerforationTaskPanel(obj.Source, obj.FaceName,
                                                    feature=obj))
        return True

    def unsetEdit(self, vobj, mode=0):
        if mode != 0:
            return None
        Gui.Control.closeDialog()
        return True

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        pass


class CreatePerforationCommand:
    def GetResources(self):
        return {"Pixmap": ICON,
                "MenuText": "Perforate selected face...",
                "ToolTip": "Select faces of a solid and choose a perforation pattern"}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            source, face_name = selected_faces()
        except ValueError as exc:
            QtWidgets.QMessageBox.information(None, "Quick Perforate", str(exc))
            return
        Gui.Control.showDialog(PerforationTaskPanel(source, face_name))


Gui.addCommand("QuickPerforate_Create", CreatePerforationCommand())
