# Development progress

## 2026-11-10 — Phase 1: Core Foundation

Completed a Blueprint foundation using UE 5.8.4's third-person template and
project-owned character / GameMode children. Added first-person switching,
camera-mounted flashlight and sprint. Created the project-owned Open World map
with World Partition, dense warm volumetric dust, fixed exposure, brown terrain,
and a sealed temporary habitat shell with a warm entrance light. Both startup
and game default maps point to the foundation.

Player and atmosphere values live in Blueprint Data Assets and are applied by
editor authoring scripts. Python has no gameplay runtime role. Epic template
dependencies retain their original paths. Fab / Quixel acquisition is planned
for Phase 2; no acquired packs are claimed in this phase.

Validated in the editor:

- Template and project player / GameMode Blueprints compile without errors.
- The project character is possessed at the intended exterior spawn; the
  settled capsule centre is about 92 cm above the collision surface.
- Enhanced Input action injection moves the pawn about 413 cm and produces a
  jump of about 128 cm. Walking toward the habitat stops against the shell.
- Flashlight toggles, camera arm switches 400 cm to 0 cm and back, and sprint
  speed changes 500 to 750 cm/s and restores correctly.
- Physical viewport input confirms F, V, Space, brief movement and mouse look.
  Automated callable events validate sprint; the short physical Shift chord
  did not provide a sustained speed measurement.
- World Settings shows Enable Streaming checked. Runtime CVars confirm Nanite,
  Lumen GI / reflections and virtual shadows enabled.
- A repeated full authoring build succeeds. Visual review confirms warm dust,
  a visible entrance lamp and flashlight illumination in first person.
- Editor spot check: approximately 60 FPS / 16.7 ms. This is not a representative
  mid-range hardware benchmark; stable 60+ FPS remains a profiling target.

Reports are local under `Saved/Codex` (`pie_report.json`, `keyboard_report.json`,
editor logs); they are intentionally ignored by Git. A packaged build / cook has
not been validated.

Next: **Phase 2 — World & Atmosphere**. Acquire and integrate Fab / Quixel
Megascans surfaces, rocks and debris; develop dust storms, day/night, wind
ambience, wreck / cruiser / ruin landmarks, and profile streaming and frame time.
Survival, habitat interior / airlock, death and respawn remain Phase 3. Hidden
Strain and temporary hallucinations follow the later phases in the GDD.

Fresh editor startup loaded the saved foundation map without an explicit map
argument, and the complete PIE smoke test passed again with no reported errors.
No Phase 1 implementation blockers remain.

GitHub rejected the first push because the original unpublished history contained
a 122 MB generated asset-registry cache. The original history is preserved locally
on `codex/phase1-before-history-cleanup`. Generated `Intermediate`, `Saved` and
`DerivedDataCache` entries were removed from `main` history; the tested game tree
was unchanged. Only `main` is pushed.
