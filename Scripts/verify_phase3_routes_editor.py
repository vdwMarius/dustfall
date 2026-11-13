"""Phase 3 exterior navigation regression; airlock traversal has its own suite."""
import pathlib
import runpy

runpy.run_path(str(pathlib.Path(__file__).with_name('verify_phase2_routes_editor.py')),
               run_name='__main__', init_globals={'PHASE3': True})
