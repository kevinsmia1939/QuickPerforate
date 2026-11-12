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
- Curved faces and objects containing multiple solids are not supported.
- Very dense patterns are limited to 1,600 openings to keep recomputes manageable.
- Older files with combined pattern styles are mapped to the closest separate pattern and hole shape. Round Hole Staggered, Octagon Cane, Marietta, and Grecian can change geometry on recompute; inspect those results before using them.

This directory can be placed under FreeCAD's user `Mod` directory. In this workspace it is already in that location, so a FreeCAD restart is enough to load it.

Use **Flip every N holes** to rotate alternating blocks of N columns and rows by 180°, for any hole shape. Set 0 (Off) to disable, 1 to alternate each element, or 2 for two unchanged then two flipped. Hole rotation adjusts their overall orientation.

For alternating left/right triangle holes like pasted file3.jpg, choose **Triangle Tiling**, **Triangle** hole shape, **Flip every N holes: Off**, and zero rotations. Start with pitch 10 mm and opening size 4.6 mm. Pitch is the horizontal repeat of a pair; row spacing is pitch / (2√3).

Additional hole shapes: **Full Leaf Clover** (four rounded leaves), **Heart**, **Grecian** (angular Greek-key corner), **Plus Sign**, and **Marietta** (a diamond with four concave curved sides). Curved profiles use polygon approximations.
