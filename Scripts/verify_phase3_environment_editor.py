"""Run the existing weather integration suite with a Phase 3 isolated save slot."""
import json
import pathlib
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
REPORT = ROOT / 'Saved/Codex/phase3_environment_verification.json'
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('End existing PIE before verification')
cls = unreal.load_class(None, '/Game/Systems/BP_SurvivalDirector.BP_SurvivalDirector_C')
actor = unreal.GameplayStatics.get_all_actors_of_class(editor.get_editor_world(), cls)[0]
original = actor.get_editor_property('SaveSlotName')
slot = 'Dustfall_QA_Environment'
actor.set_editor_property('SaveSlotName', slot)
unreal.GameplayStatics.delete_game_in_slot(slot, 0)
REPORT.write_text(json.dumps({'status': 'running'}))
runpy.run_path(str(ROOT / 'Scripts/verify_phase2_editor.py'), run_name='__main__')
state = {'handle': None}


def poll(delta):
    data = json.loads((ROOT / 'Saved/Codex/phase2_pie_report.json').read_text())
    if data['status'] == 'running' or editor.get_game_world():
        return
    actor.set_editor_property('SaveSlotName', original)
    unreal.GameplayStatics.delete_game_in_slot(slot, 0)
    data['isolated_save_slot'] = slot
    REPORT.write_text(json.dumps(data, indent=2))
    unreal.unregister_slate_post_tick_callback(state['handle'])


state['handle'] = unreal.register_slate_post_tick_callback(poll)
