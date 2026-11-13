# Phase 4 accessible crashed transport section

`Scripts/build_phase4_wreck.py` replaces only the tagged Phase 2 transport wreck
at (15000,10000,0) cm and its own tagged replacement. The giant cruiser and ruin
remain intact. The initial explorable section contains an open cargo deck,
side lockers, a recorder alcove, exposed ribs, torn wedge-shaped hull plates,
broken fin and amber edge markers. It is a modular review-build environment;
fine bespoke fractured ship art and further cruiser rooms remain later work.

Authoring completed and saved 2026-11-13. Stable discovery coordinates are in
`Saved/Codex/phase4_wreck_build.json`: salvage (14350,10320,290) and
(15500,10320,290), recorder lore on the accessible console front lip
(15900,9435,300). Entry approaches from (13100,9650), up a 7.5-degree ramp to
the deck at Z100. The central aisle is clear; the recorder also has a south
approach along Y9350.

Lightweight editor sanity found ground under nine approach/deck points. A
static 42cm-radius/96cm-half-height capsule sweep found a 10cm ramp lip; the
ramp was lowered 10cm and the affected join sweep repeated successfully. Seven
approach/aisle sweeps now have no blockers. Report:
`Saved/Codex/phase4_wreck_sanity.json`. This is static collision sanity, not
CharacterMovement traversal, packaged acceptance or a stress/performance test.
The user deferred those heavier checks.
