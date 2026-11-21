# Curved profile verification

Run `curved_profiles.FCMacro` in FreeCAD to exercise 16 hole profiles (including a custom sketch with separate and nested loops), 5 arrangements, 3 trimmed surfaces, and partial holes off/on: 480 combinations. It closes only its test document and writes JSONL results to the system temporary directory. Expect a long run for difficult curved booleans.

The 2026-11-21 results in `curved_profiles_results.csv` combine the initial complete matrix with targeted retests after fixes. All 480 combinations passed: each produced a non-null valid result, at least one placement, and a measurable reduction in source volume. Tests used the requested FreeCAD weekly 2026.10.07 AppImage.

Representative dimensions: 12 mm cylinder/sphere radius; torus radii 12 and 4 mm; pitch 9 mm; hole size 3 mm; depth 1 mm; border clearance 0.3 mm. Brick uses Y spacing 7 mm and offset 3 mm. Slot Size 2 is 1.5 mm. Surfaces are trimmed to exercise real boundaries.

These checks validate subtractive geometry, not every possible dimension, visual appearance, full-period seam configuration, or protrusion mode. CSV timings include profiling/validation overhead and concurrent test runs; they are not performance benchmarks.

Run `mirrored_cylinder_profiles.FCMacro` to check all 16 hole profiles on a cylindrical sector and its mirror. It compares opening areas at different positions around the bend and checks them against the planar profile area to catch incomplete openings on cylinders whose U parameter runs in the opposite direction.
