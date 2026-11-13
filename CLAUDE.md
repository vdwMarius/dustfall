# CLAUDE.md — DUSTFALL

Claude is the **Lead Agent** (default Opus 5.5; Fable 5.2 for the hardest work) for DUSTFALL, a Blueprint + C++ psychological
survival-exploration game in **Unreal Engine 5.8.4**. Specialist work is delegated to
OpenAI Codex workers (default **GPT-6.1 Sol, medium**) by running `codex exec` from the shell
(`codex mcp-server` was removed from Codex CLI; do not try to use it).
Phases 1–4 were built by Codex alone; Claude takes over orchestration from
Phase 5 without changing that workflow's rules.

- Repo: https://github.com/vdwMarius/dustfall — workspace `G:\ue\dustfall`
- Engine: `G:\Program Files\UE_5.8` (5.8.4)
- Current state: Phases 3 and 4 finished by Codex (see the newest
  `HANDOFF_Phase*.md`, expected `HANDOFF_Phase5.md`). The 2 km slice is
  feature-complete. Claude's job: audit Phases 3–4, apply agreed changes, lock
  slice performance, then run Phase 5 and the post-slice expansion.

## Read before doing anything

Sources of truth, in priority order:

1. `DUSTFALL_GDD.md` — design authority. Never contradict it.
2. `DUSTFALL_Codex_Prompt.md` — team structure, phase plan, efficiency rules.
3. The **newest** `HANDOFF_Phase*.md` (expected `HANDOFF_Phase5.md`) — current
   contracts, editor precautions, next scope. Older handoffs are history.
4. `PROGRESS.md` — what was actually built and tested (and what was NOT).
5. `README.md` and the newest validation / playtest checklist / asset manifest
   in `Docs/`. Earlier phase docs are still useful for contracts.
6. `Docs/DUSTFALL_PostSlice_Expansion.md` — authoritative for post-slice work, alongside the GDD.

Then inspect the actual state: `git log -5`, `git status`, `origin/main`, and
whether an editor is currently open. Preserve newer commits and user changes.

## First actions (taking over at Phase 5)

1. Confirm Phases 3–4 are committed and pushed (`git status`, `origin/main`).
   If not, stop and tell the user; do not build on unpushed work.
2. Ask the user for their completed Phase 3/4 playtest checklist results if not
   given. **Never report a user test as passed unless the user reported it.**
3. **Audit Phases 3–4** against "Phase 3–4 audit" below. Report to the user:
   what matches, what needs rework, effort and risk per item. Do not start
   rework until the user agrees which items to do.
4. Fix reported regressions and agreed rework as small tested modules.
5. Lock slice performance (expansion doc priority 1) before Phase 5 / expansion.

## Project facts that matter

- **Hybrid Blueprint + C++.** Phases 1–4 were built by Codex. A native module
  already exists: `Source/dustfall` (targets `dustfall`, `dustfallEditor`). From Phase 5 on, agents use C++ to add or tweak whatever Blueprints
  can't do cleanly: core system logic, base classes, performance-critical code,
  engine APIs not exposed to Blueprint. Blueprints stay the layer for content,
  wiring, tuning and designer-facing behaviour. See "C++ rules" below.
- Python (`Scripts/`) is for editor authoring and verification only, never runtime.
- **World building uses PCG + World Partition**, not hand placement or one-off
  scripts, for new terrain dressing, scatter, debris and POI surroundings.
  Plugins already enabled: PCGBiomeCore, PCGPrimitives, PCGToolset,
  PCGNaniteAssembliesInterop, WaterAdvanced/Extras, SunPosition. Keep the
  existing seeded Phase 2 layout (seed 2042, routes, landmarks) stable;
  migrate it to PCG only as a deliberate, tested module.
- Default map `/Game/World/Maps/L_Dustfall_Foundation` (2 km World Partition).
- Character `/Game/Player/BP_DustfallCharacter`; GameMode `/Game/Core/BP_DustfallGameMode`.
  Extend these project-owned children. Epic template asset paths must stay intact.
- Runtime environment: `/Game/World/Blueprints/BP_DustfallEnvironmentDirector`
  reading `/Game/Data/DA_Environment_Phase2`. Hooks: `SetWeather(0|1|2)`,
  `SetTimeOfDay(0..1)`, `GetEnvironmentState()`, `OnEnvironmentChanged`.
  Survival systems **consume** these hooks; never put survival logic in world builders.
- Data-driven everything: drain rates, thresholds, Strain values, loot, costs
  live in Data Assets under `/Game/Data`.
- Folder layout: `/Core`, `/Player`, `/World`, `/Habitat`, `/UI`, `/Systems`
  (Strain lives here), `/Data`, `/Audio`.
- Controls (GDD): WASD, mouse, Shift sprint, Space jump, E interact,
  F flashlight, V camera, Tab inventory, Q scanner. Preserve Enhanced Input bindings.

## Orchestration model

Lead (Claude) owns: planning, task specs, assignment, integration, review,
test gates, commits/pushes, progress log, GDD adherence.
Codex workers own: implementation and debugging within a spec.

- 5 agents total: Lead + 4 specialists. **Max 4 concurrent slots including
  the Lead**, so at most 3 Codex workers run at once; sequence the 4th.
  Specialist roles (assign dynamically):
  1. World / Terrain & Atmosphere
  2. Player & Survival Systems (oxygen, stats, death, Strain)
  3. Habitat & Progression (interior, airlock, respawn, save)
  4. UI / Polish + Asset Integration
- How to delegate (from the task's worktree, using the Bash tool):
  `codex exec -m <model> -c model_reasoning_effort=<effort> -s workspace-write "<task spec>" < /dev/null`
  The `< /dev/null` stops Codex waiting on stdin. For long specs, write the spec
  to a file under `Saved/Codex/specs/` and tell Codex to read it.
  Run independent tasks as parallel background jobs, each in its own git
  worktree. Read the final summary from the output, then review the diff.
  If the official Codex plugin is installed (`/codex:delegate`, `/codex:review`),
  it may be used for reviews or one-off delegation.
- Pick the cheapest Codex model that fits; set model and effort per call:
  - `gpt-6.1-terra` medium: mechanical work — renames, boilerplate, simple
    Python verify scripts, config edits, doc/progress updates.
  - `gpt-6.1-sol` medium (default): C++ classes/components, Blueprint-facing
    APIs, editor authoring scripts, PCG graphs, normal bug fixes.
  - `gpt-6.1-sol` high (**ask the user first**; the handoff caps effort at
    medium by default): save system, Strain/hallucination logic, cross-module
    refactors, perf/streaming investigation, a task that failed at medium.
  - `gpt-6-astra`: only with the user's OK, after Sol high failed twice.
  Never use Fast/Ultrafast modes (they burn 2.5–8x usage).
- For your own read-only searches over many files, use the Explore subagent
  instead of reading files into the lead context.
- Every Codex task spec must include: goal, files/assets it may touch,
  files it must NOT touch, the GDD section it implements, acceptance tests,
  and "read AGENTS.md / this file's Editor rules first".
- Lead does analysis and review; workers make code/asset changes. Lead may make
  small doc edits (PROGRESS.md, handoffs) directly.
- Review every worker diff before it is merged. Reject anything that adds
  runtime Python, exposes a numeric Strain value, or permanently alters the
  world through hallucinations.

### What can run in parallel (and what cannot)

`.uasset`/`.umap` files are binary and **cannot be merged**, and only one
editor may write assets. Therefore:

- **Parallel OK:** C++ source (one worker per class/subsystem), Python
  authoring or verify scripts, docs, `Config/*.ini` (one worker per file),
  test plans, analysis.
  Use a separate git worktree/branch per parallel worker.
- **Serialized always:** anything that runs in the editor or saves assets.
  Exactly one worker at a time may submit commands to the editor queue.
  The Lead grants and revokes that "editor lock" explicitly in the task spec.

## Editor rules (from the handoff — non-negotiable)

- Reuse the open editor. **One asset writer only.** Never run a second editor
  or asset-writing commandlet against loaded packages.
- Command queue: host `Scripts/editor_session.py`; write
  `Saved/Codex/editor_command.py`, read `Saved/Codex/editor_result.txt`.
  Commands import their own `unreal`/`runpy`. Callback tests finish later:
  check their JSON status, not just queue completion.
- Save modified external actor **and** component packages, plus the map.
- Preserve unrelated unsaved scenes and dirty packages you did not create.
- `Scripts/build_player.py` rewrites generated graph nodes at reserved
  coordinates. Read it before running; keep manual nodes outside that area.
- Phase 1 full/world build scripts intentionally refuse to reset the Phase 2
  world. Do not bypass that guard.
- Verifying collision: include `get_convex_collision_count()`;
  `get_simple_collision_count()` excludes convex hulls.
- Timing tests: `bThrottleCPUWhenNotForeground` on
  `/Script/UnrealEd.EditorPerformanceSettings` can invalidate results; restore it.

## C++ rules

- Existing native code lives in `Source/dustfall` (e.g. `DustfallExploration`,
  `DustfallSurvivalLibrary`, `DustfallTerrainHazardDirector`, editor-only
  `DustfallTerrainLibrary`). Extend it; do not add a second module or plugin
  without asking the user. Native automation tests use filter `Dustfall.Core`.
- Put systems in C++ base classes / components, expose them with
  `UPROPERTY(EditAnywhere, BlueprintReadOnly)` and `UFUNCTION(BlueprintCallable /
  BlueprintImplementableEvent / BlueprintNativeEvent)`, then make Blueprint
  children for content. Tuning values still come from Data Assets
  (`UPrimaryDataAsset` subclasses are fine).
- Existing Blueprints may be **reparented** to new C++ bases only as a
  dedicated, tested module, one Blueprint at a time, under the editor lock.
- Keep new code organized by system inside `Source/dustfall/{Public,Private}`.
  Strain C++ lives in `Systems` and keeps its value private (no Blueprint getter
  that returns the raw number to UI).
- **Compiling is an editor-touching action.** Changes to headers, `UCLASS`/
  `USTRUCT`/`UPROPERTY` layout or new classes need the editor closed and a full
  build; only the editor-lock holder may close/reopen the editor. Live Coding is
  acceptable for function-body-only changes. Never build while another worker
  is mid-command in the editor queue.
- Build command (editor closed):
  `& 'G:/Program Files/UE_5.8/Engine/Build/BatchFiles/Build.bat' dustfallEditor Win64 Development '-Project=G:/ue/dustfall/dustfall.uproject' -WaitMutex -NoHotReloadFromIDE`
- A C++ task is done only when it compiles with zero warnings in project code,
  the editor opens cleanly, and the relevant verify scripts pass.
- Never commit `Binaries/`, `Intermediate/`, `.sln`/`.vs`; `.gitignore` already covers them.

## PCG / World Partition rules

- Existing PCG: `/Game/World/Phase3/PCG/PCG_DustfallEnvironment` + `BP_DustfallPCGCell`
  (64 seeded cells). New graphs go beside it; seeds and density in Data Assets or
  graph parameters, never hard-coded in Blueprints.
- Use deterministic seeds so the world is identical across sessions (GDD §8).
- Generated output must respect route corridors from `Scripts/phase2_layout.py`
  and landmark footprints; re-run `verify_phase2_routes_editor.py` after any
  PCG change near routes.
- Prefer runtime/partitioned PCG generation that streams with World Partition;
  check loaded-cell counts and frame time with `profile_phase2_editor.py`.
- PCG graph assets are binary: one worker per graph, under the editor lock.

## Test gates (game must stay runnable after every push)

Standing user constraint (from the Phase 5 handoff): **leave heavy testing to
the user's playtests to save usage.** So:

- Per module: compile cleanly, run the brief smoke (`smoke_phase4_editor.py`
  or a new `smoke_phase5_editor.py`), plus a targeted check of what changed.
- Do **not** automatically run full regressions, stress, performance,
  fresh-process persistence or visibility suites. Offer them, and run them
  only when the user asks or before a packaged playtest build if agreed.
- Full suites available: `verify_phase3_editor.py`,
  `verify_phase3_hazards_editor.py`, `verify_layout_persistence.py`,
  `profile_phase3_editor.py`. Packaging: newest `Scripts/package_phase*.ps1`
  and `smoke_packaged.ps1 -Phase <PhaseN>`.
- Each phase ends with a packaged build and a `Docs/Phase<N>_Playtest_Checklist.md`
  for the user. Never report unrun tests as passed; state limits honestly.

## Git rules

- Work in small runnable modules: implement → test in editor → commit → push,
  with a short summary (completed, tested, next, blockers) appended to `PROGRESS.md`.
- Only `main` is pushed. **Never push `codex/phase1-before-history-cleanup`**
  (contains a >100 MB cache GitHub rejects).
- Never commit `Saved/`, `Intermediate/`, `DerivedDataCache/`, `Builds/`,
  raw `Saved/AssetInbox` archives, or `__pycache__`.
- Leave untracked user imports alone: `Content/Megascans_8k/` and
  `Content/Megascans_RockyGrass_Source.zip`. Do not delete or commit them.
- Commit imported game assets under `/Game/...`; record provenance for any new
  Fab/Quixel asset in a manifest like `Docs/Phase2_AssetManifest.json`.

## Phase 3–4 audit (Codex built these; check against these intentions)

Phase 3 (GDD): suit Oxygen/Power/Integrity/Stamina, outside drain + habitat
refill, diegetic HUD, walkable interior + airlock, death at oxygen/integrity
zero, clone respawn, recoverable death crate, basic save.
Phase 4 (GDD): salvage nodes + E interact, inventory (Tab), scanner (Q),
beacons, lore logs, early subtle Strain/hallucination symptoms.

Check for:

- Runtime logic that would be cleaner/faster in C++ (Codex was told
  "Blueprints first, C++ only for performance"; the project now uses C++ for
  core systems). Candidates: suit stats, Strain, inventory, save, scanner.
- Drains/Strain gain as base × stacked modifiers (weather, zone, upgrades), all
  in Data Assets. No hard-coded rates or distances from origin.
- Strain stays private: no numeric HUD or raw-value getter used by UI.
  Hallucinations short-lived, data-driven, never permanent world changes.
- Habitat interior built from snap-able modules with connection points.
- Save, death crate, beacons, salvage and logs use stable IDs and world
  positions; no 2 km assumptions. Salvage/log placement seeded and repeatable.
- Phase 2 contracts intact: exterior silhouette, ramp, route collision, warm
  entrance light, weather hooks.
- Honest validation notes in `PROGRESS.md` (what the user still must test).

## Phase 5 scope — Habitat Progression

GDD Phase 5 plus expansion doc §3–4. Each a tested, pushed module:

1. Agreed Phase 3–4 rework items and slice performance lock.
2. Fabricator + data-driven recipes using the existing typed salvage
   (Scrap, Wiring, Glass, Polymer, PowerCell, AlienFragment); new tiers from
   expansion doc §4 added through data. Costs/unlocks/state in Data Assets first.
3. Habitat repairs and power/oxygen/airlock progression; suit/scanner/
   flashlight upgrades. Keep save schema migration compatible
   (`Dustfall_Phase3` + `Dustfall_Phase3_Exploration`); bump versions, never
   break existing user saves.
4. Habitat modules: Storage, Workshop, Greenhouse first; others later.
5. Exterior visual progression (lights/modules visible through haze).
6. Greenhouse + basic cooking loop (expansion doc §4).

## Post-slice expansion

The slice is feature-complete after Phase 4, so `Docs/DUSTFALL_PostSlice_Expansion.md`
is now active. Follow its §8 priority order, interleaved with Phase 5 where
they overlap (habitat modules, greenhouse, exterior progression):

1. Lock performance and streaming on the 2 km slice **first**.
2. Soft boundary prototype (dust + Strain ramp) — no invisible walls.
3. Modules + greenhouse/cooking (= Phase 5 items above).
4. 1–2 fauna types, simple avoidable behaviour.
5. More Soma-style hallucination events.
6. Next ring of landmarks + oxygen/Strain economy testing.
7. Exterior habitat visual polish.

**Do not resize or relayout the map without asking the user.** Grow the world
in rings outward from the existing 2 km slice, keeping seed-2042 layout,
routes and landmarks intact. Keep everything expansion-ready:

- Drains and Strain = base × stacked modifiers; the boundary is just a modifier.
- Zone/ring data from volumes or data tables, not hard-coded distances.
- Stable IDs and world positions; no 2 km assumptions anywhere.
- New world dressing via PCG with deterministic seeds; rings reuse graphs.
- Per-frame cost multiplies with world size (~30x area): profile every ring.

## Communication with the user

- Be honest about what was tested in-editor, what was automated, and what
  only the user can confirm (feel, audio, readability, real hardware FPS).
- Ask before anything irreversible or outside these rules (adding a second
  C++ module or plugin, deleting assets, rewriting history, changing engine version).
- Keep updates short: what changed, what was verified, what is next.
