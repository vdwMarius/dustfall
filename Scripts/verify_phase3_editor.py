"""Run the Phase 3 runtime regression suites serially in one editor.

The sub-suites own/close their PIE sessions and isolate their save slots. Native
PCG generation and all asset writing must be finished before starting this.
"""
import json
import pathlib
import runpy
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
REPORT = ROOT / 'Saved/Codex/phase3_verification.json'
SUITES = [
    ('survival', 'verify_phase3_survival_editor.py', 'phase3_survival_verification.json'),
    ('habitat', 'verify_phase3_habitat_editor.py', 'phase3_habitat_pie.json'),
    ('player', 'verify_phase3_player_editor.py', 'phase3_player_pie.json'),
    ('environment', 'verify_phase3_environment_editor.py', 'phase3_environment_verification.json'),
    ('navigation', 'verify_phase3_routes_editor.py', 'phase3_route_pie_report.json'),
]
result = {'status': 'running', 'suites': {}, 'errors': [],
          'scope': 'Runtime Blueprint, injected controls and collision checks. Visual acceptance, physical controls and representative hardware performance are separate.'}
state = {'index': 0, 'active': False, 'handle': None, 'since': time.monotonic()}
resume = globals().get('RESUME_AT')
if resume:
    index = next(i for i, item in enumerate(SUITES) if item[0] == resume)
    previous = json.loads(REPORT.read_text())
    for name, _, _ in SUITES[:index]:
        if previous.get('suites', {}).get(name, {}).get('status') != 'passed':
            raise RuntimeError('Cannot resume past unpassed suite: ' + name)
        result['suites'][name] = previous['suites'][name]
    state['index'] = index
    result['resumed_at'] = resume


def write():
    REPORT.write_text(json.dumps(result, indent=2), encoding='utf-8')


def finish(status):
    result['status'] = status
    write()
    unreal.unregister_slate_post_tick_callback(state['handle'])


def tick(delta):
    try:
        if state['index'] >= len(SUITES):
            finish('passed')
            return
        name, script, report = SUITES[state['index']]
        if not state['active']:
            if time.monotonic() - state['since'] < 1:
                return
            if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
                if time.monotonic() - state['since'] > 30:
                    raise RuntimeError('Existing PIE or previous suite did not close')
                return
            runpy.run_path(str(ROOT / 'Scripts' / script), run_name='__main__')
            state.update(active=True, since=time.monotonic())
            result['active_suite'] = name
            write()
            return
        path = ROOT / 'Saved/Codex' / report
        data = json.loads(path.read_text())
        if data['status'] == 'running':
            if time.monotonic() - state['since'] > 900:
                raise RuntimeError(name + ' suite timed out')
            return
        result['suites'][name] = data
        if data['status'] != 'passed':
            finish('failed')
            return
        state.update(index=state['index'] + 1, active=False, since=time.monotonic())
        write()
    except Exception:
        result['errors'].append(traceback.format_exc())
        finish('error')


write()
state['handle'] = unreal.register_slate_post_tick_callback(tick)
