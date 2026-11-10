"""Rebuild Phase 2 owned content in one editor; never rebuilds player logic.

Open the foundation map with landscape cells loaded. Imports are incremental.
Unrelated dirty map/content packages must be saved separately before running.
"""
import pathlib
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
world = unreal.EditorLevelLibrary.get_editor_world()
if '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name():
    raise RuntimeError('Open the foundation map before authoring Phase 2')
dirty = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
if dirty:
    raise RuntimeError('Save or resolve existing dirty packages before a full Phase 2 build: ' + ', '.join(p.get_name() for p in dirty))
for name in ['import_phase2_quixel', 'build_phase2_audio', 'build_phase2_landmarks',
             'build_phase2_routes', 'build_phase2_wasteland', 'build_phase2_debris',
             'build_phase2_environment']:
    runpy.run_path(str(ROOT / ('Scripts/' + name + '.py')), run_name='__main__')
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_all_dirty_levels()
unreal.log('DUSTFALL Phase 2 build complete; runtime and visual verification required.')
