"""Repair the existing LoadProgress execution link without rebuilding survival.
Single editor writer, PIE stopped. Preserves tuning and all instance state.
"""
import json
import pathlib
import runpy
import unreal
ROOT=pathlib.Path(unreal.Paths.project_dir())
if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop PIE before graph repair')
api=runpy.run_path(str(ROOT/'Scripts/build_phase3_survival.py'))
asset=unreal.load_asset('/Game/Systems/BP_SurvivalDirector')
graph=unreal.BlueprintEditorLibrary.find_graph(asset,'LoadProgress')
ed=unreal.BlueprintGraphEditor.get_graph_editor(graph)
entry=ed.find_graph_entry_pin().get_owning_node()
nodes=list(ed.list_all_nodes())
def pin_names(node):return [str(p.get_pin_name()) for p in node.list_all_pins()]
exists=next(n for n in nodes if 'Does Save Game Exist' in str(n.get_node_title()) or 'DoesSaveGameExist' in str(n.get_node_title()))
branch=next(n for n in nodes if 'Condition' in pin_names(n) and 'else' in pin_names(n))
# try_create_connection replaces the existing single input execution connection.
api['wire'](entry,'then',exists,'execute')
api['wire'](exists,'then',branch,'execute')
if not unreal.BlueprintEditorLibrary.compile_blueprint(asset):
    raise RuntimeError('LoadProgress repair failed to compile: '+str(ed.list_nodes_with_errors()))
if not unreal.EditorAssetLibrary.save_loaded_asset(asset,False):
    raise RuntimeError('LoadProgress repair failed to save')
(ROOT/'Saved/Codex/phase3_load_repair.json').write_text(json.dumps({'status':'repaired','change':'LoadProgress entry executes DoesSaveGameExist before branching','graph_errors':len(ed.list_nodes_with_errors())},indent=2),encoding='utf-8')
