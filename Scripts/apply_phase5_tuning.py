"""Apply the Phase 5 sprint tuning in the open editor (single writer only)."""
import json
import pathlib
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
ASSET = '/Game/Data/DA_Survival'
OVERRIDES = {'stamina_drain_per_second': 13.0, 'stamina_refill_per_second': 14.0}


def main():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('Stop PIE before authoring')
    tuning = unreal.load_asset(ASSET)
    if not tuning or not isinstance(tuning, unreal.DustfallSurvivalTuning):
        raise RuntimeError('DA_Survival is missing or has the wrong class')
    # Read every property first so an invalid name cannot leave a partial edit.
    before = {name: tuning.get_editor_property(name) for name in OVERRIDES}
    tuning.modify()
    for name, value in OVERRIDES.items():
        tuning.set_editor_property(name, value)
    if not unreal.EditorAssetLibrary.save_loaded_asset(tuning, False):
        raise RuntimeError('Could not save DA_Survival')
    after = {name: tuning.get_editor_property(name) for name in OVERRIDES}
    report = {'asset': ASSET, 'before': before, 'after': after}
    path = ROOT / 'Saved/Codex/phase5_tuning.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('Phase 5 sprint tuning applied: ' + str(path))


if __name__ == '__main__':
    main()
