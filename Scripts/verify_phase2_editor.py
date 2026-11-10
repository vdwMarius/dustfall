"""PIE runtime checks for the Phase 2 environment and player movement.

Run in a dedicated interactive editor via startup Python or editor_session.py.
Writes Saved/Codex/phase2_pie_report.json; never saves the map or quits editor.
Action injection does not validate keyboard mappings, focus, or visual quality.
"""
import json
import pathlib
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = ROOT / 'Saved/Codex/phase2_pie_report.json'
REPORT.parent.mkdir(parents=True, exist_ok=True)
MAP = '/Game/World/Maps/L_Dustfall_Foundation'
DIRECTOR = '/Game/World/Blueprints/BP_DustfallEnvironmentDirector'
MOVE = '/Game/Input/Actions/IA_Move.IA_Move'
result = {'status': 'running', 'checks': {}, 'errors': [],
          'scope': 'PIE action injection does not test physical inputs or visual quality.'}
state = {'stage': 'start', 'since': time.monotonic(), 'handle': None, 'owns_pie': False}
REQUIRED = ('director compile', 'director in world', 'possessed pawn', 'time progresses',
            'weather states', 'weather fog response', 'time control', 'movement during weather',
            'wind responds', 'day night lighting', 'automatic weather', 'environment query')


def check(name, passed, detail):
    result['checks'][name] = {'status': 'pass' if passed else 'fail', 'detail': detail}


def stage(name):
    state['stage'], state['since'] = name, time.monotonic()


def finish(status='completed'):
    if status == 'completed':
        missing = [name for name in REQUIRED if result['checks'].get(name, {}).get('status') != 'pass']
        result['required_unpassed'] = missing
        status = 'passed' if not missing else 'failed'
    result['status'] = status
    if state['owns_pie']:
        try:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        except Exception as exc:
            result['errors'].append('End PIE request: ' + str(exc))
    REPORT.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    if state['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(state['handle'])
        state['handle'] = None
    unreal.log('DUSTFALL Phase 2 PIE report: ' + str(REPORT))


def tick(delta):
    try:
        elapsed = time.monotonic() - state['since']
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if state['stage'] == 'start':
            if editor.get_game_world():
                result['errors'].append('Existing PIE session; refusing to alter it.')
                finish('blocked')
                return
            if MAP not in editor.get_editor_world().get_path_name():
                raise RuntimeError('Open the saved foundation map first; verifier does not replace unsaved scenes')
            bp = unreal.EditorAssetLibrary.load_asset(DIRECTOR)
            if not bp:
                raise RuntimeError('Missing director ' + DIRECTOR)
            compiled = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            check('director compile', bool(compiled), str(compiled))
            state['director_class'] = bp.generated_class()
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['owns_pie'] = True
            stage('wait')
        elif state['stage'] == 'wait':
            world = editor.get_game_world()
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0) if world else None
            if not pawn:
                if elapsed > 90:
                    raise RuntimeError('Timed out waiting for PIE pawn')
                return
            actors = unreal.GameplayStatics.get_all_actors_of_class(world, state['director_class'])
            check('director in world', len(actors) == 1, {'count': len(actors)})
            check('possessed pawn', bool(pawn.get_controller()), pawn.get_class().get_name())
            if len(actors) != 1:
                finish()
                return
            state.update(world=world, pawn=pawn, director=actors[0])
            state['initial_time'] = float(actors[0].get_editor_property('TimeOfDay'))
            stage('clock')
        elif state['stage'] == 'clock':
            if elapsed < 3:
                return
            director = state['director']
            now = float(director.get_editor_property('TimeOfDay'))
            before = state['initial_time']
            advance = (now - before) % 1.0
            check('time progresses', 0 < advance < 0.5, {'before': before, 'after': now, 'advance': advance})
            state['weather_results'] = []
            state['weather_index'] = 0
            stage('weather_set')
        elif state['stage'] == 'weather_set':
            value = state['weather_index']
            state['director'].call_method('SetWeather', (value,))
            stage('weather_observe')
        elif state['stage'] == 'weather_observe':
            if elapsed < 30:
                return
            expected = state['weather_index']
            actual = int(state['director'].get_editor_property('Weather'))
            fogs = unreal.GameplayStatics.get_all_actors_of_class(state['world'], unreal.ExponentialHeightFog)
            densities = [float(fog.get_component_by_class(unreal.ExponentialHeightFogComponent).get_editor_property('fog_density')) for fog in fogs]
            state['weather_results'].append({'expected': expected, 'actual': actual, 'fog_densities': densities})
            state['weather_index'] += 1
            if state['weather_index'] < 3:
                stage('weather_set')
                return
            values = state['weather_results']
            check('weather states', all(x['actual'] == x['expected'] for x in values), values)
            # A single controlled fog actor should visibly respond, with storm
            # denser than haze and haze denser than calm; no hardcoded tuning.
            fog_ok = all(len(x['fog_densities']) == 1 for x in values)
            if fog_ok:
                fog_ok = values[0]['fog_densities'][0] < values[1]['fog_densities'][0] < values[2]['fog_densities'][0]
            data = state['director'].get_editor_property('EnvironmentData')
            targets = [float(data.get_editor_property(n)) for n in ['CalmFogDensity','HazeFogDensity','StormFogDensity']]
            fog_ok = fog_ok and all(abs(v['fog_densities'][0]-target)<.002 for v,target in zip(values,targets))
            check('weather fog response', fog_ok, {'observed':values,'targets':targets,'settle_seconds':30})
            wind = state['director'].get_component_by_class(unreal.AudioComponent)
            intensity = float(state['director'].get_editor_property('StormIntensity'))
            check('wind responds', bool(wind) and wind.is_playing() and intensity>.98 and wind.get_editor_property('volume_multiplier')>.7,
                  {'playing':wind.is_playing() if wind else False,'storm_intensity':intensity,'volume':wind.get_editor_property('volume_multiplier') if wind else None})
            query = state['director'].call_method('GetEnvironmentState')
            check('environment query', len(query)==3 and int(query[0])==2, str(query))
            state['director'].call_method('SetTimeOfDay', (.5,))
            stage('noon')
        elif state['stage'] == 'noon':
            if elapsed < 1:
                return
            d=state['director']
            state['noon']={'sun':d.get_editor_property('SunComponent').get_editor_property('intensity'),
                           'sky':d.get_editor_property('SkyComponent').get_editor_property('intensity')}
            d.call_method('SetTimeOfDay',(0.,))
            stage('midnight')
        elif state['stage'] == 'midnight':
            if elapsed < 1:
                return
            d=state['director']
            night={'sun':d.get_editor_property('SunComponent').get_editor_property('intensity'),
                   'sky':d.get_editor_property('SkyComponent').get_editor_property('intensity')}
            check('day night lighting',state['noon']['sun']>1 and night['sun']<.001 and night['sky']<.01 and state['noon']['sky']>night['sky'],{'noon':state['noon'],'midnight':night})
            d.set_editor_property('WeatherElapsed',99999.)
            stage('automatic')
        elif state['stage'] == 'automatic':
            if elapsed < 1:
                return
            actual=int(state['director'].get_editor_property('Weather'))
            check('automatic weather',actual==1,{'storm_to_haze':actual,'forced_elapsed_seconds':99999})
            state['director'].call_method('SetTimeOfDay', (0.75,))
            stage('time_observe')
        elif state['stage'] == 'time_observe':
            if elapsed < 0.5:
                return
            actual = float(state['director'].get_editor_property('TimeOfDay'))
            check('time control', 0.74 <= actual < 0.8, {'requested': 0.75, 'actual': actual})
            pc = unreal.GameplayStatics.get_player_controller(state['world'], 0)
            lib_class = unreal.load_class(None, '/Script/Engine.SubsystemBlueprintLibrary')
            lib = unreal.get_default_object(lib_class)
            state['input'] = lib.call_method('GetLocalPlayerSubSystemFromPlayerController', (pc, unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
            state['action'] = unreal.load_asset(MOVE)
            if not state['input'] or not state['action']:
                raise RuntimeError('Enhanced Input subsystem or movement action missing')
            state['start_location'] = state['pawn'].get_actor_location()
            stage('move')
        elif state['stage'] == 'move':
            if elapsed < 1:
                state['input'].inject_input_vector_for_action(state['action'], unreal.Vector(1, 0, 0), [], [])
                return
            start, end = state['start_location'], state['pawn'].get_actor_location()
            distance = ((end.x-start.x)**2 + (end.y-start.y)**2)**0.5
            check('movement during weather', distance > 5, {'horizontal_cm': distance})
            finish()
    except Exception:
        result['errors'].append(traceback.format_exc())
        finish('error')


REPORT.write_text(json.dumps(result, indent=2), encoding='utf-8')
state['handle'] = unreal.register_slate_post_tick_callback(tick)
