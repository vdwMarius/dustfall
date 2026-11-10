# Phase 2 validation

## Environment and player

UE 5.8.4, Windows 11; one authoring editor. Runtime Blueprint compilation,
possession, clock progression, three fog targets after 30-second blends,
automatic storm-to-haze transition, state query, wind playback/volume and
noon/midnight sun/skylight changes passed in PIE. Actual components were checked,
not merely state variables. Playback telemetry is not a subjective listening review.

The full Phase 1 player regression passed in the visible editor: spawn clearance,
one active camera, injected movement/jump, sprint settings, flashlight, view toggle
and habitat collision. The capsule stopped about 35 cm from the entrance surface,
matching its radius. Physical V/F/Space and mouse look were checked; telemetry
observed about 127.5 cm jump rise and 15.75 degrees of look change. A brief Shift
chord did not establish sustained physical sprint; callable events verify its speed.

## World

The first complete navigation pass covered 2.03 km per condition: day/calm,
night/haze and day/storm, including all landmark approaches and return home.
CharacterMovement and collision ran at 4x game time; this is not a benchmark.
It found and corrected inconsistent scatter-route coordinates and the 50 cm pad
edge exceeding the 45 cm step height; the exterior approach now has a gentle ramp.
The final pass after scan-pivot seating also passed all three conditions and
all 18 waypoints, covering over 6 km total. Background editor throttling was
temporarily disabled for reliable accelerated traversal and restored afterward.

The shared route layout is in Scripts/phase2_layout.py; scatter excludes full
mesh footprints. Geometry is baked with seed 2042 into 64 spatial HISM cells.
Texture dimensions, Nanite and larger-rock convex hulls are inspected separately.
The habitat remains sealed and no survival systems are implemented.

## Packaging and performance

Development BuildCookRun succeeded. Initial cook reported zero errors and zero
warnings. CommonUI requires Unreal's generated launch target under ignored
Intermediate/Binaries; no native gameplay logic or Source module was added.
The non-redistributable MCP authoring plugin is restricted to Editor targets.

Performance collection is in progress. Workstation: Ryzen 9 5950X, RTX 5080,
64 GB RAM. These measurements cannot establish the mid-range hardware target.
Final CSV results, streaming counts and packaged smoke observations will be added
when verified.
