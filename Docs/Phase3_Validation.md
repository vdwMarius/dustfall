# Phase 3 validation

## 2026-11-13 continuation and user-directed validation scope

The rounded custom pod and real landscape relief have now been authored.
`Phase3_TerrainResults.json` records current collision probes and PCG results.
These changes invalidate treating the historical regression results below as
current acceptance. The user explicitly requested leaving heavy testing for
their own playtest to reduce usage. Full gameplay/navigation/hazard regressions,
final reload/cooked-layout persistence, distance/view/weather acceptance and
performance profiling therefore remain **deferred to the user**. See the
current Phase 4 validation/handoff for build and brief smoke results.

The records below describe the earlier functional Phase 3 implementation.

UE 5.8.4, Windows. See `Phase3_TestResults.json` for the recorded runtime results.
The development editor is the sole asset writer. User Phase 3 acceptance has
not been performed; the earlier reported playtest was of Phase 2.

## Core gameplay and C++

The native `dustfallEditor Win64 Development` build succeeded. Both native
automation tests passed: resource integration/exhaustion and habitat boundaries.
Gameplay Blueprints call these C++ rules; rates/limits remain in data assets.

All five runtime suites passed: survival, habitat, player, environment and
navigation. Tests cover actual resource ticks, sprint depletion and recovery,
warning cooldown execution, power-driven flashlight shutdown, oxygen/integrity
deaths, clone spawn, repeat-death cache preservation, proximity recovery,
duplicate prevention, save/load, camera/input action behavior, collision,
airlock traversal/doorway obstruction, climate interpolation and lighting.

Navigation used real CharacterMovement collision at 4x game time through all
18 waypoints in day/calm, night/haze and day/storm, roughly 2 km per case.
Resources were topped up to isolate traversal. Airlock traversal was tested
separately with survival active. QA save slots were isolated and removed after
PIE ended; tests do not establish physical-key or subjective audio acceptance.

## PCG and visual review

Final audit passed: 64 spatial cells, 71,838 rock instances, 370 animated dust
sheets and 195 noninteractive industrial debris instances. No legacy scatter
or debris actors remained. Native PCG performs landscape sampling, slope/noise
filtering, strict exclusions, varied transforms and mesh instancing. Route
masks include endpoint caps; measured minimum centre clearances were about
7.80 m from routes and 23.49 m from home. Full collision navigation also passed.

Opaque rock assets use Nanite. Actual renderer CVars confirm Lumen GI and
reflections, Nanite and Virtual Shadow Maps enabled. World Partition runtime
streaming remains enabled; loading/pinning all authoring actors only affects
the editor. The earlier 7,881-instance layout survived editor restart before
the final density increase; final dense-layout reload/cooked persistence is
**not yet verified**.

The selected atmosphere uses persistent fog .18/.28/.45, EV100 0, sun 96,
day skylight 2, night skylight .0005, storm light multiplier .72, warm tint and
animated bounded dust sheets. Measured editor captures show recognizable
40/60/100 m silhouettes with distant hills obscured in storm. This is an editor
visual review, not human acceptance of the packaged first/third-person views.

Four-side captures of an actual composite cliff show outward scan surfaces and
retained texture/normal detail. Initial distant SceneCapture images were using
low texture mips; temporary capture-only residency exposed the correct detail.
That CVar/residency override was restored and is not a runtime performance setting.
The habitat has worn-material dressing and functional furnishings; habitat,
character and ship art do not yet match the references as finished assets.
On 2026-11-13 the user explicitly requested a less square/basic habitat and
actual hostile terrain relief, hills/mounds, jagged zones and pitfalls. These
remain unfinished work; passing functional tests does not accept current art.

## Performance and package

Seven editor cases completed; see `Phase3_EditorPerformance.json`. Actual viewport
was 691x464 High, editor visibility not asserted. Frame medians were
16.649–16.679 ms, p95 17.308–17.429 ms; Home Day had a 91.791 ms CPU hitch.
Loaded PCG cells changed from 64 near home/landmarks to 16 at the far corner;
no runtime PCG generation was observed. These are not 1080p packaged or
representative mid-range hardware results. Stable 60+ FPS remains unproven.

**No Phase 3 Windows package, packaged smoke test or packaged performance run
was completed.** Packaging/launcher scripts are prepared only. The Phase 2
package is historical. Human Phase 3 physical-key, audio and visual acceptance
remains open. Finish the new terrain/habitat corrections and repeat affected
checks before producing the next review build.
