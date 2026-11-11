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

Final storm fog density is 1.0 (previous base commit used .13). A repeated
environment suite passed against that saved asset: fog reached .997656 after
30 seconds, wind intensity .997546 / volume .798405, sun/skylight changed with
time and automatic storm-to-haze transition passed. Visual review showed strong
distance obscuration and flashlight backscatter; the warm home light remained a
faint cue at roughly 30 m. Precise visibility distance was not measured.

Final BuildCookRun completed successfully in 43 seconds and archived the local
Windows Development build to `Builds/Phase2/Windows`. No gameplay Source module
was added. `Scripts/package_phase2.ps1` reproduces it and adds the playtest launcher.

### Final editor capture

Ryzen 9 5950X, RTX 5080, 64 GB RAM, Windows 11, UE 5.8.4; High scalability,
100% render scale, dynamic resolution off, background throttle disabled, visible
PIE viewport **691×464**. This final run supersedes the earlier 1495×862 capture;
do not interpret these small-viewport results as a 1080p benchmark. Each case had
seven seconds settling followed by ten seconds / 600 CSV frames. Final storm
density 1.0 was included. See `Phase2_EditorPerformance.json` for all timings.

| Location | Loaded rock cells | Frame median ms | Frame p95 ms |
|---|---:|---:|---:|
| Home day | 42 | 16.684 | 17.815 |
| Wreck day | 45 | 16.670 | 17.465 |
| Ruin day | 38 | 16.684 | 18.314 |
| Cruiser day | 37 | 16.670 | 17.712 |
| Home night | 42 | 16.672 | 18.745 |
| Cruiser storm | 37 | 16.660 | 19.618 |
| Far corner | 15 | 16.683 | 19.313 |

Loaded cells changed from 45 near the wreck to 15 at the far corner, consistent
with World Partition streaming. GPU medians were 2.023–2.479 ms, while frame
times remained near editor pacing with p95 above 16.67 ms; isolated 79.643 ms
and 61.712 ms spikes occurred at home and in storm. Stable 60+ FPS is not
established by these editor results, nor on representative mid-range hardware.

### Packaged runtime capture

With the editor closed, the final Development build launched the default
foundation map using BP_DustfallGameMode on D3D12/SM6. Log metadata confirms
1920×1080; launch commands applied High scalability, 100% screen percentage,
no dynamic resolution, `t.MaxFPS 0` and `r.VSync 0`. Physical V/F produced
first-person view and visible flashlight illumination on the home exterior.
The CSV profiler completed 6,000 frames and requested a clean exit with status 0.
There were no `Error:` or fatal error entries in this smoke log.

After discarding the first 600 warmup frames, 5,400 frames had median
**16.652 ms**, p95 **18.839 ms**, p99 **20.622 ms**, maximum **107.442 ms**.
GPU median was **4.093 ms**, p95 **6.138 ms**. See
`Phase2_PackagedPerformance.json`. This was a stationary home haze/afternoon
capture with a brief camera/flashlight check, not a world traversal benchmark.
Frame pacing remained near 60 despite the uncapped console settings and low GPU
times; the cause of that pacing has not been isolated.

Cold startup logged 350 pipeline-state creation hitches (62 graphics/288 compute)
and later 100 ms PSO waits. The 107 ms post-warmup maximum means warmup exclusion
does not eliminate all stutter. Further PSO precaching/pacing investigation and
representative hardware testing remain performance work. The log also warned
that applying the batch of deferred launch commands took 39.27 ms; this was
startup overhead, not a gameplay error. Local raw evidence is in
`Saved/Codex/phase2_packaged_smoke.log` and the build's `dustfall/Saved/Profiling/CSV`.

### User acceptance

`Phase2_Playtest_Checklist.md` covers normal-time packaged routes, sustained
physical sprint, night/storm readability, subjective audio and stutter reports.
These manual acceptance items are pending the user's playtest. Phase 2 content
is implemented; Phase 3 should begin after reviewing those results. Landmarks
remain exterior prototypes, and habitat remains sealed by design.
