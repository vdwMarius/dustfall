# Habitat kit round two

Scope: source changes only under `Scripts/blender/`; generated FBXs, manifests,
logs and previews remain under ignored `Saved/AssetInbox/`. Changes are uncommitted.
Material slot names are unchanged; the Unreal importer was not modified or run.

## Exterior items

1. **Silhouette:** outer corner radius increased from 80 to 170 cm at both top
   and bottom. The inner 45 cm fillet fits within the rounded exterior and still
   contains the exact sanctuary box. The dome is a smooth, 18-ring ellipsoidal
   bulge, 120 cm deep, at the opposite end from the airlock.
2. **Hatch:** painted barrel and matching movable leaf; three stepped rounded
   frames, hex bolts, hinge/actuator housings, vent, framed warm porthole,
   overhead and side caged lamps, hazard edging. The leaf is present in the
   exterior assembly, separate from the open-door collision tests.
3. **Windows:** two real 110 x 80 cm apertures, deep layered bolted frames and
   projecting sills. Separate `M_Hab_Emissive_Warm` panes sit behind glass.
   They are stacked vertically to fit both on the +Y side of a 200 cm segment.
4. **Hull breakup:** different seam divisions, access plates, recessed grips,
   conduits and clamps, vents, strapped tanks, ladder and raised numbered plates.
   Damage cuts through the outer skin, exposing ribs/cables behind peeled metal;
   the inner pressure liner remains sealed. Bolted patch plates flank the tear.
5. **Roof:** cells tilt 23 degrees on triangular supports, with cable runs;
   three differently sized mast instances and warm shoulder lamp housings.
6. **Stance:** shorter cradles/pads and irregular rubble skirts. In the assembled
   review, soil meets the ramp toe and partly buries the foundation skirts.
7. **Wear:** seeded 1–3 mm plate depth variation, a few buckled corners,
   replacement bare-metal plates and missing skin around the torn opening.

## Interior items

1. **Structure:** curved shoulder/ceiling ribs, upper wall lining bent inward
   to fit the hull, overhead cable trays, pipes,
   thick wall panels, duct and junction boxes, open service panels and cables.
   Cool strip lights and warm caged ceiling fixtures provide practical glow.
2. **Bunk:** wall mounting brackets, thick mattress, pillow, a closed irregular
   rumpled blanket mesh and three handled storage drawers.
3. **Furnishings:** stocked shelf canisters/boxes, helmet and tool forms;
   workbench drawers, articulated lamp and chair; terminal bezels and lit screen
   strokes. The shelf is placed at the back for visibility in the eye-height view.
4. **Fabricator:** two top handles, chamber glazing, print bed, gantry,
   leadscrew/nozzle and specimen, lit side controls, raised block-letter
   FABRICATOR plate and rubber feet.
5. **Alcove:** new `SM_Hab_Int_AlcoveFrame`, 180 x 220 cm clear opening,
   60 cm deep frame/sill, paired sockets and portal-preserving UCX hulls.

## Validation

- Blender 5.2.4 LTS ran headlessly; 36 individual FBXs exported.
- All render components passed the existing closed-manifold assertion; UV0
  remains dominant-axis projection at 1 UV unit per 200 cm.
- Sanctuary, 200 cm segment grid, 120 x 210 doorways, socket transforms,
  7.5-degree ramp and furnished aisle checks pass. All 1,637 existing capsule
  samples pass, plus the new alcove approach/passage samples.
- Every mesh is below its applicable 60k/120k triangle budget.
- Two independent full generation runs produced byte-identical manifest JSON:
  SHA256 `869994da388bd0d1dd3cfc4ea6d0939b02cdcc464f421073b646892e533dc4c1`.
  That includes geometry hashes/counts, bounds, sockets and collision records.
- All 36 exported FBXs passed `verify_habitat_kit.py`: target axes/scale,
  bounds, triangle counts, finite UV0, normals, UCX counts and socket positions
  and outward orientations survived the round trip.
- **Contract adjustments: none.** The larger inner fillet is an art parameter;
  required clearance dimensions and the sanctuary volume are unchanged.
- Unreal was not run; CharacterMovement/gameplay acceptance remains a later
  integration step. No user playtest is claimed.

## Review these first

All previews are 1600 x 1200 with simple distinct slot colours, warm low key,
soft shadows, ground and emissive glow. Source generation uses the same preview
builders as the faster exported-FBX review utility.

1. `Saved/AssetInbox/HabitatKit/previews/ASSEMBLED_Exterior.png`: closed hero
   hatch, large hull radii, tilted solar and settled stance.
2. `Saved/AssetInbox/HabitatKit/previews/ASSEMBLED_RearDamage.png`: curved dome,
   missing outer plating, peeled edges and exposed structure.
3. `Saved/AssetInbox/HabitatKit/previews/ASSEMBLED_InteriorCutaway.png`: 165 cm
   eye height, bedding, stocked shelving, workbench/fabricator and layered services.

## Triangle counts

| Piece (SM_Hab_ prefix) | Triangles |
| --- | ---: |
| Airlock | 92,656 |
| AntennaMast | 5,652 |
| Bunk | 14,772 |
| CableBundle | 30,804 |
| Collar | 10,552 |
| Crate_L | 7,932 |
| Crate_S | 7,932 |
| DoorLeaf | 12,396 |
| EndCap_Dome | 8,286 |
| EndCap_Door | 21,356 |
| ExteriorLamp | 7,124 |
| Fabricator | 97,012 |
| Floodlight | 9,156 |
| HullSegment_A | 42,776 |
| HullSegment_B | 46,112 |
| HullSegment_C | 65,164 |
| HullSegment_Damaged | 47,080 |
| HullSegment_SideDoor | 41,944 |
| Int_AlcoveFrame | 3,568 |
| Int_CeilingLight | 7,104 |
| Int_CeilingPanel | 27,224 |
| Int_FloorPanel | 21,372 |
| Int_WallPanel_A | 16,684 |
| Int_WallPanel_B | 22,984 |
| Int_WallPanel_C | 30,412 |
| Int_WindowFrame | 13,004 |
| Locker | 7,932 |
| O2Tank | 6,116 |
| Ramp | 18,588 |
| RoofRack | 6,096 |
| ShelfUnit | 22,480 |
| Skid | 22,292 |
| SolarPanel | 13,676 |
| Stool | 8,456 |
| WallTerminal | 24,464 |
| Workbench | 21,168 |
