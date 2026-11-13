# Phase 4 validation — 2026-11-13

The user explicitly deferred heavy validation to their own playtest. None of
the historical Phase 3 regression/performance results accepts the new terrain,
pod or Phase 4 systems.

- Native editor build: passed after all final C++ changes, including the
  immediate out-of-world cache relocation. Final log:
  `Saved/Codex/phase4_native_build.log`.
- Phase 4 brief isolated PIE smoke: **19/19 passed**, zero recorded errors.
  Results `Phase4_SmokeResults.json`; screenshot `Phase4_HUDSmoke.png`.
  This checks callable gameplay and in-session save/load/migration, not
  physical keys, process restart, full navigation or subjective presentation.
- Terrain: real landscape collision measurements and protected-route grades
  recorded in `Phase3_TerrainResults.json`; two minimal art captures inspected.
  Final PCG layout persistence across restart/cook remains unverified.
- Wreck: nine ground probes and seven static capsule sweeps passed, including
  repaired ramp join. Full walking/traversal is deferred. See `Phase4_Wreck.md`.
- Phase 3 preliminary package: build/cook/stage/archive succeeded; isolated
  600-frame startup/clean-exit smoke passed, zero runtime errors. Its cook had
  one LoadProgress execution-pin warning. That bug is repaired in the current
  assets/source and actual legacy load passed the Phase 4 smoke. The old Phase 3
  package predates repair and is superseded by Phase 4.
- Final Phase 4 build/cook/stage/archive: **passed**, zero cook errors and
  zero warnings. `Builds/Phase4/Windows/Play_DUSTFALL.cmd` is runnable.
  Package log: `Saved/Codex/package_phase4.log`.
- Final Phase 4 packaged startup smoke: **passed** at 1920x1080 High,
  600 stationary frames, foundation map loaded, process exit code 0, clean
  shutdown and zero detected runtime errors. Uses an isolated UserDir.
  `Phase4_PackagedSmoke.json` preserves the result. Packaged interactions,
  traversal and performance were deliberately not claimed from this smoke.

Deferred: full Phase 3/4 regression, repeated deaths/hazard escape in real
CharacterMovement, final fresh-process persistence of dense/cooked streaming
layout and saves, first/third person 40/60/100m visibility in weather/night,
keyboard/audio/visual acceptance, packaged traversal/performance/PSO profiling
and representative mid-range 60 FPS. Use `Phase4_Playtest_Checklist.md`.
