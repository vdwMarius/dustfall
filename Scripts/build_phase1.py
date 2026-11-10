"""Run with UE 5.8's PythonScript commandlet. No game-time Python dependency."""
import pathlib
import runpy
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = ROOT / 'Saved/Codex/build_result.txt'
REPORT.parent.mkdir(parents=True, exist_ok=True)
try:
    runpy.run_path(str(ROOT / 'Scripts/build_player.py'), run_name='__main__')
    world = runpy.run_path(str(ROOT / 'Scripts/build_world.py'), run_name='__main__')
    runpy.run_path(str(ROOT / 'Scripts/build_habitat.py'),
                   init_globals={'HABITAT_ORIGIN': world['HABITAT_ORIGIN']}, run_name='__main__')
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    REPORT.write_text('Phase 1 asset build complete. In-editor play verification still required.', encoding='utf-8')
except Exception:
    REPORT.write_text(traceback.format_exc(), encoding='utf-8')
    raise
