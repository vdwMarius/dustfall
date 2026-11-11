# DUSTFALL — Phase 2 handoff / Phase 3 starting point

Phase 2 implementation is complete and a local Windows Development build is
ready for user acceptance. **Do not assume the user has tested it.** Read their
completed checklist, fix reported Phase 2 regressions, then begin Phase 3.
No survival/interior/death systems have been implemented in this phase.

## First actions in the next chat

1. Read `DUSTFALL_GDD.md`, `DUSTFALL_Codex_Prompt.md`, `PROGRESS.md`, `README.md`,
   this handoff, `Docs/Phase2_Validation.md`, `Docs/Phase2_Playtest_Checklist.md`
   and `Docs/Phase2_AssetManifest.json`. Phase 1 asset/habitat docs remain useful.
2. Inspect Git HEAD, status, origin/main and the actual open editor before writing.
   Main implementation commit is `7365782`; the subsequent Phase 2 finalization
   commit contains this handoff, final storm tuning, launcher and measured results.
   Preserve any newer commits and user changes. The repository is
   `https://github.com/vdwMarius/dustfall`, workspace `G:\ue\dustfall`.
3. Ask for checklist results only if missing; never report unperformed user tests
   as passed. The exact ready-to-run build and checklist are linked below.
4. Follow the five-person team structure in the project prompt. There are only
   four concurrent slots including lead, so sequence four specialist assignments.
   Prefer GPT-6.1 Terra Medium (or Sol Medium) as requested. Serialize editor writes.

## Build and acceptance

- Run `G:\ue\dustfall\Builds\Phase2\Windows\Play_DUSTFALL.cmd` for 1080p High.
  Keep the complete Windows folder; the EXE alone is insufficient. Alt+F4 exits.
- Follow `Docs/Phase2_Playtest_Checklist.md` and paste its results into the next chat.
- Rebuild saved assets with `Scripts/package_phase2.ps1` (UE default root
  `G:\Program Files\UE_5.8`). BuildCookRun includes `-build`: CommonUI requires
  Unreal's temporary generated launch target in ignored Intermediate/Binaries.
  There is still no native gameplay Source module. The engine MCP authoring
  plugin is restricted to Editor targets because it is non-redistributable.
- Builds/Saved/caches are ignored, so a clone must package its own runnable build.
  Engine is **5.8.4**. Controls: WASD/mouse, Space, hold Left Shift, F, V.
- See `Docs/Phase2_Validation.md` and performance JSON files for actual evidence.
  Listening, sustained physical sprint, route readability and representative
  target-hardware acceptance still require the user's playtest. Strong workstation
  measurements do not establish stable 60+ FPS on mid-range machines.
  Packaged 1080p High home capture passed startup/clean exit: frame median
  16.652 ms, p95 18.839 ms, p99 20.622 ms, max 107.442 ms after 600 warmup frames.
  Cold PSO creation hitches and later waits remain; see the validation report.
  Investigate PSO precaching/frame pacing if the user reports stutter before
  treating performance as accepted. GPU median 4.093 ms does not explain the
  near-60 frame pacing by itself. The editor was closed after verifying no dirty
  packages, and the packaged profiler exited automatically; inspect current state
  again rather than assuming an editor or game is still running.

## Current world and assets

- Default/editor map: `/Game/World/Maps/L_Dustfall_Foundation`, 2 km × 2 km landscape.
  Character `/Game/Player/BP_DustfallCharacter`, GameMode `/Game/Core/BP_DustfallGameMode`.
  Original Epic third-person template dependency paths must remain intact.
- Twenty licensed user-provided Quixel archives from `Saved/AssetInbox/Quixel`:
  eight 2K surfaces and twelve meshes. Provenance IDs, names and archive SHA256s
  are in `Docs/Phase2_AssetManifest.json`. Imports: `/Game/World/QuixelPhase2`.
- 2,185 Nanite rock instances in 64 spatial HISM cells, seed 2042; world-space
  sand/gravel material with slope rock. Eight mesh components per rock-cell BP.
  Scan pivots are centered and seated. Full footprints excluded from routes.
  Small scatter is nonblocking; larger rocks use convex hull collision.
  `get_simple_collision_count()` excludes convex hulls: include
  `get_convex_collision_count()` when verifying collision.
- Exterior wreck (+150 m,+100 m), ruin (+350 m,−250 m), ~200 m cruiser
  (−550 m,+50 m), 80 noninteractive scanned industrial props, 36 route stakes.
  Coordinates are relative to home/origin. `Scripts/phase2_layout.py` shares routes.
  These are prototype exteriors, not explorable finished interiors.
- Home is the original sealed shell with warm entrance lighting. A gentle exterior
  ramp solves the 50 cm pad edge versus the player's 45 cm step-height limit.

## Runtime environment integration

`/Game/World/Blueprints/BP_DustfallEnvironmentDirector` reads
`/Game/Data/DA_Environment_Phase2` during gameplay. Python is authoring/testing only.
The Blueprint data class is `/Game/Data/BP_EnvironmentPhase2Data`.

- `SetWeather(Value)`: integer 0 calm / 1 haze / 2 storm; resets weather age.
- `SetTimeOfDay(Value)`: normalized 0 midnight / .25 sunrise / .5 noon / .75 sunset.
- `GetEnvironmentState()`: weather integer, normalized time and storm intensity.
- `OnEnvironmentChanged`: no-argument dispatcher after updates; query current state.

Defaults: 1800-second day, initial time .65/haze, haze120s → calm180s → haze120s
→ storm60s → haze. Fog .018 / .045 / **1.0**; blend speed .2 (about 30s settling).
Sun15, sky .6 day/.002 night, storm light multiplier .22. Warm fog RGB .30/.115/.055.
Wind .15 to .8 volume. Project-owned synthesized looping SoundWave
`/Game/Audio/Environment/S_WindBed_Phase2` uses an AudioComponent, not MetaSound.
Movable sun/sky/fog refs are explicitly assigned; skylight real-time capture enabled.
These are neutral hooks for future oxygen/power/hidden Strain consumers.

The Phase 1 data assets are authoring-time only, unlike this runtime data asset.
Avoid rebuilding atmosphere from Phase 1 values. Blueprint builder removes all
old generated method variants and compiles before recreating canonical methods;
this prevents Unreal suffixing names to `SetWeather_0` after repeat builds.

## Safe authoring and verification

- Reuse the open editor where possible. One asset writer only; never run a second
  editor/asset-writing commandlet against loaded packages. Preserve unrelated
  unsaved scenes. Save modified external actor AND component packages.
- Dedicated queue host: `Scripts/editor_session.py`; command file
  `Saved/Codex/editor_command.py`, result `Saved/Codex/editor_result.txt`.
  Commands must import their own `unreal`/`runpy`. Callback tests finish later;
  inspect their JSON status rather than just queue completion.
- Full build `Scripts/build_phase2.py` rejects existing dirty packages and the wrong
  map; modules split Quixel import, terrain/scatter, landmarks, routes, debris,
  wind and runtime environment. Source archives stay ignored; imported assets tracked.
- `build_environment.py` now delegates to Phase 2. Phase 1 full/world scripts guard
  against resetting this world. `build_player.py` removes generated graph nodes at
  reserved coordinates and affects template-parent logic: read it before use.
  Prefer extending project-owned children, and preserve Enhanced Input bindings.
- `verify_phase2_editor.py`: ~100s, actual component response after weather blends,
  day/night, auto weather, clock/query/audio/movement. Relative .5% storm fog tolerance
  accommodates the asymptotic eased blend at 30s; absolute minimum tolerance .002.
- `verify_phase1_editor.py`: player regression. `verify_phase2_routes_editor.py`:
  18 waypoints using CharacterMovement, three conditions, ~2.03 km per case at 4x
  game time. Navigation tests are not frame-rate benchmarks.
- `inspect_phase2_assets.py`: texture dimensions/Nanite/convex collision.
  `profile_phase2_editor.py`: seven steady-state locations, CSV frame times and
  loaded rock-cell counts. `summarize_phase2_csv.py`: offline median/p95/p99 analysis.
- Editor background throttle can invalidate timing: settings class is loaded from
  `/Script/UnrealEd.EditorPerformanceSettings`, exact property
  `bThrottleCPUWhenNotForeground`. Verification/profile scripts restore it.
- `preview_phase2_editor.py` changes PIE instances only; see checklist for presets.

Unrelated user imports `Content/Megascans_8k/` and
`Content/Megascans_RockyGrass_Source.zip` were intentionally left untracked.
Do not delete or sweep them into a commit. Never push local backup branch
`codex/phase1-before-history-cleanup`; its historical generated cache exceeds
GitHub's limit. Keep generated caches, raw inbox archives and builds out of Git.

## Phase 3 scope after acceptance

Use the GDD as authority: suit Oxygen, Power, Integrity, Stamina; outside drain
and habitat refill; walkable habitat sanctuary/interior and airlock; death at
oxygen/integrity zero, new clone respawn, recoverable death crate, basic save.
Build small runnable modules and test/commit/push each. The recoverable crate
can have a minimal data contract; full scavenging/inventory/scanner/lore belongs
to Phase 4. Crafting/modules/progression belong later.

Keep hidden Strain extension points private and data-driven. Do not expose a
numeric Strain HUD or implement permanent hallucination world changes. Define
weather-consumer interfaces without putting survival behavior into world builders.
Preserve Phase 2 climate, route collision and landmark identity while making the
habitat genuinely walkable. Re-run player/environment/navigation regressions after
collision, spawn, input or runtime-light changes.
