# Phase 3 survival runtime contract

Author with `Scripts/build_phase3_survival.py` in the single development editor,
after the habitat builder and compiling the C++ module. Resource integration,
sanctuary boundary checks and exhaustion rules call `UDustfallSurvivalLibrary`
in the native `dustfall` runtime module; Blueprint assets orchestrate the loop.
Python is only an authoring/testing tool. Run `Scripts/verify_phase3_survival_editor.py`
for the isolated-save-slot PIE regression. Consult its generated JSON report
for the actual result; a successful build alone does not establish behavior.

## Assets and public interface

- `/Game/Systems/BP_SurvivalDirector`: always-loaded world actor. Public state:
  `Oxygen`, `Power`, `Integrity`, `Stamina`, `InHabitat`, `SprintExhausted`,
  `CloneGeneration`, `CarriedScrap`, `CrateScrap`, `CrateActive`, `CrateLocation`.
- `/Game/Data/DA_Survival_Phase3`: maximum stats, drain/refill rates, sprint
  speeds, storm wear, recovery radius, save interval and oxygen warning settings.
- `GetSuitState()` returns four stats and clone generation. `SaveProgress()`,
  `LoadProgress()`, `RecoverCrate()` and `RespawnClone()` are callable functions.
- F5 saves, F9 loads, E recovers the cache within 250 cm. E does not consume
  input, so the habitat airlock can also process it. Existing player controls
  and Enhanced Input template graphs remain intact.

Stats integrate elapsed seconds and clamp to their data-driven maxima. Oxygen
and power drain outdoors and refill inside the habitat. Storm intensity from
the environment director causes exterior suit wear. Depleted power forces the
flashlight off. Low oxygen requests a project-owned warning tone at a tunable
threshold/cooldown; `OxygenWarningCount` records playback-node executions, not
subjective audio quality. Stamina drains at sprint velocity and regenerates
otherwise. Exhaustion limits movement until stamina reaches 25.

The habitat contract is a world-space `HabitatCenter`/`HabitatHalfExtent` box and
`CloneSpawn` position sourced from the live saved habitat anchor. Airlock chamber is
outside the sanctuary box. A safe interior refills resources; suit integrity
repair/progression is not part of the basic refill behavior.

## Death, cache and saving

Oxygen or integrity zero creates one new clone identity, resets suit resources
and teleports the possessed character to the tested interior spawn. This reuses
the existing character actor and animation/input setup; it does not create a
second pawn or leave an uncontrolled corpse.

One always-loaded recovery cache represents the minimal Phase 4 inventory
contract. `CarriedScrap` is a scalar payload placeholder, initially zero; full
item inventory and salvage nodes remain Phase 4. Repeated deaths accumulate
unrecovered payload at the latest death position rather than deleting it.
Recovery transfers it once, hides the cache and saves the recovered state.
The cache has an amber material/beacon and an E RECOVER label. It is
nonblocking so its placement cannot trap the player.

`BP_DustfallSaveGame` schema version 1 stores suit stats, player location, clone
generation, carried scrap and pending cache state. The default local slot is
`Dustfall_Phase3` (`SaveSlotName` on the director). BeginPlay attempts to load;
F5, periodic autosave, death and recovery save the current state. F9 restores.
Unsupported schemas or failed casts do not apply state. `LastSaveSucceeded`
reports the synchronous save result. Save I/O frequency is deliberately low;
larger future inventory/world saves should move to asynchronous serialization.

The verifier uses `Dustfall_Phase3_AutomatedQA`, restores the original editor
slot setting and removes only its own QA slot. It exercises real resource
ticks, warning cooldown telemetry, power exhaustion, both death conditions,
repeated cache accumulation, proximity, save/load and duplicate prevention.
Its callable tests do not establish physical keyboard mappings, subjective
warning volume or terrain streaming safety at every possible saved position.
