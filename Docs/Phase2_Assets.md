# Phase 2 asset provenance and integration

The user confirmed their Quixel library rights on 2026-11-10. The signed-in
Purchased collection and ownership marks were inspected in LibreWolf. The user
supplied the twenty 2K archives in `Phase2_DownloadList.md` under ignored
`Saved/AssetInbox/Quixel`. Original archives are preserved unchanged.

`Phase2_AssetManifest.json` records exact names, IDs, archive SHA-256 hashes and
imported paths. Publisher: Quixel. These are legacy Quixel Purchased acquisitions;
no new purchase or Fab Standard License is inferred. The owner retains original
account/acquisition terms and receipts; these were not supplied for a separate audit.

## Game assets

- `/Game/World/QuixelPhase2`: eight surfaces and twelve meshes. Materials use 2K
  albedo/normal/roughness; meshes use Nanite. Larger rocks have convex collision;
  small scatter and industrial dressing are nonblocking.
- `/Game/World/Materials/M_Wasteland_Phase2`: project-authored world-coordinate
  sand/gravel blend, slope-driven exposed rock and broad color variation.
- `/Game/World/Blueprints/BP_DustfallRockCell`: eight HISM components per streamed
  cell. Seed 2042 bakes the consistent layout; no runtime Python is involved.
- Wreck, cruiser and ruined habitat: replaceable exterior prototypes built from
  Epic engine primitives, dressed with Quixel metal/concrete and scanned props.
- `/Game/Audio/Environment/S_WindBed_Phase2`: project-owned periodic synthesized
  wind from `build_phase2_audio.py`, seed 2042. No recording, voice or third-party
  sample is used. This version uses a looping SoundWave and Blueprint AudioComponent,
  not a MetaSound graph.

## Earlier local cache imports

The licensed Documents/Megascans Library cache supplied Stained Concrete Floor
(`vkmjddd`) and Rusty Metal (`tjxncc2aw`) source JPGs, used on exterior blockouts
under `/Game/World/Megascans/Phase2`. Cracked Shale Beach Rock (`wiqmfcmn`)
supplied three self-contained Tier2 textures at their metadata-declared original
`/Game/Megascans/Surfaces` path. Its missing-parent material instance was excluded;
the optional dusty shale material is project-authored. This is a surface, not a mesh.

Sphere-mound experiments were replaced by scanned rocks. The retired
`build_phase2_terrain.py` refuses to overwrite the scanned-rock world and is not
called by the complete Phase 2 builder. Unrelated later Fab additions under
`Content/Megascans_8k` and the source ZIP in Content are preserved separately and
are not included in the curated import. Epic template dependency paths remain intact.

The local import, asset inspection, route and runtime reports are in Saved/Codex.
See Phase2_Validation.md and PROGRESS.md for actual results and limitations.
