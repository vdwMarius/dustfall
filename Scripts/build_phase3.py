"""Build Phase 3 modules with one editor writer and serial PCG completion gates.

Run in the foundation editor with landscape loaded, no PIE and clean packages.
Build output is not verification; run verify_phase3_editor.py afterwards.
"""
import json
import pathlib
import runpy
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
REPORT = ROOT / 'Saved/Codex/phase3_build.json'
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('End PIE before authoring')
if '/Game/World/Maps/L_Dustfall_Foundation' not in editor.get_editor_world().get_path_name():
    raise RuntimeError('Open the foundation map first')
dirty = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
if dirty:
    raise RuntimeError('Resolve dirty packages before full rebuild: ' + ', '.join(p.get_name() for p in dirty))
result = {'status': 'building gameplay', 'errors': []}


def write():
    REPORT.write_text(json.dumps(result, indent=2))


def run(name):
    runpy.run_path(str(ROOT / 'Scripts' / name), run_name='__main__')


write()
for script in ['build_phase3_habitat.py', 'build_phase3_survival.py', 'build_phase3_hud.py', 'build_phase3_environment.py', 'build_phase3_terrain.py']:
    run(script)
state = {'stage': 'terrain', 'handle': None, 'since': time.monotonic()}
result['status'] = 'authoring landscape and collision'
write()


def poll(delta):
    try:
        filename = {'terrain':'phase3_terrain_build.json','core':'phase3_pcg_build.json',
                    'debris':'phase3_pcg_debris_build.json'}[state['stage']]
        data = json.loads((ROOT / 'Saved/Codex' / filename).read_text())
        if data['status'] == 'failed':
            raise RuntimeError(str(data))
        if data['status'] != 'complete':
            if time.monotonic() - state['since'] > 600:
                raise RuntimeError('Terrain/PCG completion timeout')
            return
        if state['stage'] == 'terrain':
            result['terrain']=data
            run('build_phase3_pcg.py')
            state.update(stage='core',since=time.monotonic())
            result['status']='generating core PCG on authored relief'
            write()
            return
        if state['stage'] == 'core':
            run('build_phase3_pcg_debris.py')
            state.update(stage='debris', since=time.monotonic())
            result['status'] = 'generating debris PCG'
            write()
            return
        result.update(status='built; runtime and visual verification required', core_pcg=json.loads((ROOT / 'Saved/Codex/phase3_pcg_build.json').read_text()), debris_pcg=data)
        write()
        unreal.unregister_slate_post_tick_callback(state['handle'])
    except Exception:
        result.update(status='failed', errors=[traceback.format_exc()])
        write()
        unreal.unregister_slate_post_tick_callback(state['handle'])


state['handle'] = unreal.register_slate_post_tick_callback(poll)
