"""Reapply atmosphere and rebuild the temporary foundation habitat."""
import pathlib
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
if unreal.EditorAssetLibrary.does_asset_exist('/Game/World/Blueprints/BP_DustfallEnvironmentDirector'):
    runpy.run_path(str(ROOT / 'Scripts/build_phase2_environment.py'), run_name='__main__')
else:
    world = runpy.run_path(str(ROOT / 'Scripts/build_world.py'), run_name='__main__')
    runpy.run_path(str(ROOT / 'Scripts/build_habitat.py'),
                   init_globals={'HABITAT_ORIGIN': world['HABITAT_ORIGIN']}, run_name='__main__')
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
