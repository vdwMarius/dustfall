# DUSTFALL habitat kit

Run from the project root with Blender 5.2.4 LTS:

```powershell
& 'C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe' -b -t 4 -P Scripts/blender/habitat_kit.py -- --manifest --preview
```

Default output: `Saved/AssetInbox/HabitatKit/` (ignored). There are 36 pieces,
each containing one render mesh, named UCX convex hulls where blocking is needed,
and `SOCKET_Hull_n` / `SOCKET_Door_n` empties where connectable. Geometry is
authored in cm, converted to Blender metres, and exported with FBX unit metadata,
`-Y` forward, `Z` up and identity render-mesh transforms. UE import scale is 1.
Export bakes UE's Y handedness reflection and socket yaw conversion; the source
and previews use the contract coordinates. A direct Blender reimport therefore
appears mirrored in Y, with socket yaw `180 - contract yaw`. The verifier applies
the target conversion. The engine's standalone FBX SDK (without running Unreal)
was also used to check its exact mesh/socket conversion formulas.

```powershell
# Export selected pieces to a different directory (short names also accepted).
& 'C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe' -b -t 4 -P Scripts/blender/habitat_kit.py -- --out Saved/AssetInbox/HabitatKitReview --only SM_Hab_Fabricator,SM_Hab_HullSegment_B --manifest --preview
```

Every run constructs and numerically validates the complete kit before exporting
the selected pieces. `manifest.json` records geometry hashes, vertex/triangle
counts, cm bounds, socket transforms, collision boxes and capsule checks. Compare
two manifests for deterministic geometry; FBX container timestamps are not a
geometry determinism guarantee. UV0 uses dominant-axis cube projection at one UV
unit per 200 cm, including consistent density on bevels. No lightmap UVs.

```powershell
# Verify FBX units/axes, triangles, UV0, UCX counts and sockets after round trip.
& 'C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe' -b -t 4 -P Scripts/blender/verify_habitat_kit.py -- Saved/AssetInbox/HabitatKit
# Add --compare Saved/AssetInbox/HabitatKitDeterminism to require byte-identical
# manifests from a second independent generation.
```

The inner rounded rectangle contains the sanctuary box centered at `(500,0,185)`
with half extents `(475,325,185)` across five 200 cm hull segments. The front cap
occupies X -40..0, airlock -440..-40 and dome 1000..1120 in the reference assembly.
Origins are at floor datum on the X axis. Door sockets use the floor datum as
their shared mating centre; their +X axis points outwards. The +Y side door is
centered at `(100,420,0)`; rotate a collar +90 degrees to connect it. DoorLeaf
is a separate movable mesh; omit its blocking hull from open-door traversal.
The dome is solid beyond the sanctuary's end. The ramp's low end is X0 and high
end X400; its exact rise is `400*tan(7.5 degrees)`. Offset it down by that rise
when attaching its high end to a door at Z0. Skids and roof equipment are
attachments with their origin at their local mounting datum.

Round-two previews are 1600 x 1200 Cycles renders (24 samples, denoised), with
distinct slot colours, transmissive glass, separate warm window panes, glow,
a ground plane, low warm key and soft fill. Inspect `ASSEMBLED_Exterior.png`
(hatch), `ASSEMBLED_RearDamage.png` (dome and torn skin), and
`ASSEMBLED_InteriorCutaway.png` (165 cm eye height) first. The interior cutaway
opens the front, retaining the curved shoulder ribs, ceiling and service trays.
Furniture is preview dressing; sanctuary containment describes the empty shell.
The two windows in B each have a 110 x 80 cm aperture; they are stacked vertically
to fit both within the unchanged 200 cm segment. The inner shoulder fillet is
45 cm, contained by the 170 cm outer corner radius; the sanctuary contract is
unchanged. `SM_Hab_Int_AlcoveFrame` has a 180 x 220 cm opening and a 60 cm deep sill.
No material slot names changed, so the existing importer needs no modification.

To re-render exported FBXs without rebuilding the source geometry:

```powershell
& 'C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe' -b -t 6 -P Scripts/blender/preview_habitat_kit.py --
# Add --assembled-only to render just the three assembled scenes.
# Or --only Fabricator --skip-assembled for a single exported-mesh review.
```

`habitat_art.py` contains reusable curved plate, stepped hatch, raised bitmap
lettering, closed rumpled blanket and review-scene builders. Structural and
export contracts remain in `habitat_kit.py`. Generation asserts closed manifold
components and per-piece triangle budgets (120k for hulls/airlock/fabricator,
60k for other pieces), and checks capsule passage through the new alcove.
See `ROUND2_REVIEW.md` for the itemized art pass, measured counts and validation.

Unreal authoring is a separate serialized step, performed only by the editor-lock
holder via the existing command queue:

```python
import runpy
import unreal
runpy.run_path(unreal.Paths.project_dir() + 'Scripts/import_phase5_habitat_kit.py', run_name='__main__')
```

The importer reads every FBX and the complete manifest, creates assets and
placeholder material instances under `/Game/Habitat/Kit`, preserves UCX, enables
Nanite and checks imported cm bounds, sockets (position and outward +X), and
convex hull counts. It saves only its own assets, never the level or unrelated
dirty packages. The JSON report goes to
`Saved/Codex/phase5_habitat_kit_import.json`. Existing parent materials remain
unchanged. The glass slot uses the existing solar parent for review; hazard
paint gets a yellow preview parent inside Kit. Final glass/paint materials can be assigned later. The generator does not run
Unreal. Numerical capsule checks do not claim CharacterMovement acceptance.
