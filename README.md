# Quick Perforate

A FreeCAD workbench that cuts decorative through holes in a solid from a selected planar face. The **Pattern** setting arranges hole centers on a square, triangular (staggered), or hexagonal (honeycomb) grid. **Hole shape** chooses the opening: round, square, triangle, hexagon, hexagon star, octagon, diamond, slot, airline slot, or clover.

## Use

1. Restart FreeCAD and switch to **Quick Perforate**.
2. Select exactly one planar face of an object containing one solid.
3. Click **Perforate selected face** on the toolbar.
4. Choose a pattern and hole shape. Set pitch, opening size, border clearance, independent pattern and hole rotations, and pattern X/Y offsets.
5. Click **Apply** to update the solid and keep the task panel open. Click **OK** to apply and close it. **Cancel** closes the panel without applying any changes made since the last Apply.

The original object is hidden beneath the new **Perforation** object in the model tree. Expand the result to see the source object. Double-click the result to reopen its task panel and change the pattern, dimensions, rotation, or selected face. You can also edit the numeric properties directly. The **OpeningCount** property reports how many openings were cut.

The preview is a square sample with five rows and five holes per row. Pattern offsets follow the rotated pattern axes; hole rotation changes only the opening outline.

## Notes

- Perforations go through the entire solid along the selected face's normal.
- Openings stay within the selected face, including its inner boundaries. A small or narrow face may need smaller openings or border clearance.
- The saved feature stores a face number such as `Face6`. If editing the source changes its face numbering, select the intended face again by updating **FaceName**.
- Objects containing multiple solids are not supported.
- Very dense patterns are limited to 1,600 openings to keep recomputes manageable.
- Older files with combined pattern styles are mapped to the closest separate pattern and hole shape. Round Hole Staggered, Octagon Cane, Marietta, and Grecian can change geometry on recompute; inspect those results before using them.

This directory can be placed under FreeCAD's user `Mod` directory. In this workspace it is already in that location, so a FreeCAD restart is enough to load it.

Use **Flip every N holes** to rotate alternating blocks of N columns and rows by 180°, for any hole shape. Set 0 (Off) to disable, 1 to alternate each element, or 2 for two unchanged then two flipped. Hole rotation adjusts their overall orientation.

For alternating left/right triangle holes like pasted file3.jpg, choose **Triangle Tiling**, **Triangle** hole shape, **Flip every N holes: Off**, and zero rotations. Start with pitch 10 mm and opening size 4.6 mm. Pitch is the horizontal repeat of a pair; row spacing is pitch / (2√3).

Additional hole shapes: **Full Leaf Clover** (four rounded leaves), **Heart**, **Grecian** (angular Greek-key corner), **Plus Sign**, and **Marietta** (a diamond with four concave curved sides). Curved profiles use native CAD curves.

## Installation and source layout

Place this repository in FreeCAD's user `Mod/QuickPerforate` folder and restart FreeCAD. The folder can be renamed; icons are resolved relative to the installed package.

The workbench follows the namespace package layout used by FreeCAD-BulletPhysics:

- `freecad/QuickPerforate/`: feature geometry and GUI modules.
- `freecad/QuickPerforate/init_gui.py`: workbench registration.
- `freecad/QuickPerforate/Resources/Icons/`: bundled icons.
- `package.xml`: FreeCAD addon metadata.
- `pyproject.toml`: Python package and resource configuration.
- `Examples/`: editable sample documents and previews.

Root-level Python modules preserve imports from older documents and macros. The `freecad` directory intentionally has no `__init__.py`, allowing other FreeCAD namespace packages to coexist.

## Multiple faces and continuous patterns

Select one or more planar faces of the same solid before starting. In the task panel, select more source faces in the 3D view and click **Add selected faces**. Select entries in the face list and click **Remove** to remove them. All listed faces share the pattern, hole shape, pitch, rotation, offsets, and flip interval.

The first listed face anchors the pattern. Across straight shared edges, the grid and hole orientation fold onto the neighboring face without resetting their coordinates. Shared edges have no border clearance; openings crossing them are clipped to each face's extrusion. Border clearance applies to exposed edges and inner boundaries. Disconnected face groups have independent anchors. Closed folds whose coordinates cannot agree are rejected; remove a face to open a seam. Continuous unfolding currently applies to planar faces connected by straight edges. Cutters still extend through the solid, so they can also intersect other walls.

`FaceNames` stores the selected face list. Older documents migrate their single `FaceName` automatically. As with single-face features, source topology edits may require selecting faces again.


## Curved faces

Add curved faces through the same face list. Each hole automatically follows the **local surface normal** at its center; hole rotation acts in that location's tangent plane. Cylinders use arc-length spacing around the circumference and linear spacing along their axis. Other regular surface parameter charts use the metric at the face midpoint, so physical spacing and distortion can vary on cones, spheres, and spline surfaces. Split faces away from singularities such as sphere poles.

Connected planar and cylindrical faces use shared developed pattern charts. Other curved faces use independent charts. A full cylinder's closing seam aligns only when the repeat fits its circumference. Cutters remain straight through the entire solid and may intersect opposite walls. Border clearance uses a conservative straight-line distance to real face edges; periodic seam edges are ignored.

## Hole depth

Set **Hole depth** to the inward cutting distance along each local surface normal. The same depth applies to all selected faces. A depth greater than a wall's thickness breaks through that wall. Older through-all features are converted to a finite depth larger than the source bounding box.

Connected planes and cylinders share developed pattern coordinates across their common edges. Internal shared edges do not receive border clearance. Other curved surface types still use independent charts; distortion can vary with the surface metric.


## Hole dimensions and true curves

**Size 1** sets the first overall dimension (stored as `OpeningSize` for document compatibility). **Size 2** sets the second overall dimension for Slot, Full Leaf Clover, Heart, Clover, and Marietta. Set Size 2 to Automatic (0) to use the original proportions. Slot Size 2 must not exceed Size 1. Other shapes currently use Size 1 only.

Slots use straight sides and semicircular ends. Full Leaf Clover uses four semicircular leaves; changing Size 2 stretches them into elliptical leaves. Heart uses cubic Bézier curves, Clover uses a periodic B-spline, and Marietta uses circular or elliptical concave arcs. These are native curved CAD edges; the task-panel preview and display tessellation may still show sampled segments. On curved surfaces the profile is placed in the local tangent plane and cut inward along the local normal; it is not wrapped onto the surface as a surface sketch.

## Brick arrangement

Choose **Brick** to set **Brick X spacing**, **Brick Y spacing**, and **Brick row offset**, all in millimetres. X and Y spacing are the center-to-center distances between columns and rows. The offset shifts every other row along the pattern X axis; it repeats every two rows. Zero offset gives a rectangular grid, and equal X/Y spacing with zero offset gives the Square arrangement. For a classic half-brick arrangement, set the offset to half the X spacing. Offsets wrap modulo X spacing. These settings control hole positions independently of hole shape and hole dimensions, and follow the same shared-face mapping as other patterns.

## Partial holes

Enable **Allow partial holes** to trim overlapping openings to the selected face and its border clearance instead of skipping the entire opening. The default remains disabled. Centers slightly outside the face are considered when their profile can overlap it. Inner boundaries are also protected. Shared selected edges do not receive a border strip. The setting is saved as `PartialHoles` and applies to all selected faces.

Planar clipping follows the face contour with border strips removed before extrusion. Curved clipping uses an inward offset volume; the border protection is conservative where its normal varies. Very tight curvature or excessive depth may prevent a valid offset; reduce depth or split the face if FreeCAD reports this.

Whole-hole placement checks the actual profile instead of its enclosing circle. On planar faces, the footprint must fit entirely and satisfy border clearance; zero clearance permits touching the boundary. Rotation and true curved profile edges are included in the check. On curved faces, exposed boundary intersections and distances are checked against the actual cutter.
