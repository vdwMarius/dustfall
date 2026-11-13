"""Phase 3 player regression, preserving the walkable habitat and survival logic.

Results are written to Saved/Codex/pie_report.json. Enhanced Input action injection
exercises action bindings, not physical keys, mapping contexts, or OS input focus.
"""
import json
import pathlib
import time
import traceback
import unreal

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT = ROOT / 'Saved' / 'Codex' / 'phase3_player_pie.json'
QA_SLOT = 'Dustfall_QA_Player'
REPORT.parent.mkdir(parents=True, exist_ok=True)
MAP = '/Game/World/Maps/L_Dustfall_Foundation'
PAWN_PREFIXES = ('BP_ThirdPersonCharacter', 'BP_Dustfall')
ACTIONS = {'move': '/Game/Input/Actions/IA_Move.IA_Move',
           'jump': '/Game/Input/Actions/IA_Jump.IA_Jump'}
result = {'map': MAP, 'status': 'running', 'checks': {}, 'errors': [],
          'scope': 'Enhanced Input action injection is not a physical keyboard or mapping-context test.'}
state = {'stage': 'start', 'since': time.monotonic(), 'handle': None, 'owns_pie': False}

def check(name, status, detail):
    result['checks'][name] = {'status': status, 'detail': detail}

def write():
    REPORT.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')

def finish(status):
    if status == 'completed':
        required = ('possessed pawn', 'spawn above ground', 'safe interior spawn', 'active cameras', 'injected movement', 'injected jump', 'flashlight toggle', 'view toggle', 'sprint callable events', 'survival sprint limit', 'habitat collision by walking')
        failures = [k for k in required if result['checks'].get(k, {}).get('status') == 'fail']
        missing = [k for k in required if result['checks'].get(k, {}).get('status') != 'pass']
        result['status'] = 'failed' if failures else ('incomplete' if missing else 'passed')
        result['required_unpassed'] = missing
    else:
        result['status'] = status
    if state['owns_pie']:
        try:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        except Exception as exc:
            result['errors'].append('End PIE request: ' + str(exc))
    if state['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(state['handle'])
        state['handle'] = None
    if not state['owns_pie'] and 'slot_actor' not in state:
        write(); return
    def cleanup(delta):
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(): return
        if 'slot_actor' in state: state['slot_actor'].set_editor_property('SaveSlotName',state['original_slot'])
        unreal.GameplayStatics.delete_game_in_slot(QA_SLOT,0)
        result['isolated_save_slot']=QA_SLOT
        write()
        unreal.unregister_slate_post_tick_callback(state['cleanup'])
    state['cleanup']=unreal.register_slate_post_tick_callback(cleanup)
    unreal.log('DUSTFALL PIE report: ' + str(REPORT))

def stage(name):
    state['stage'] = name
    state['since'] = time.monotonic()

def check_ground(world, pawn, pos):
    try:
        end = unreal.Vector(pos.x, pos.y, pos.z - 1000)
        hit = unreal.SystemLibrary.line_trace_single(world, pos, end,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn],
            unreal.DrawDebugTrace.NONE, True)
        parts = unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method('BreakHitResult', (hit,))
        if parts[0]:
            impact = parts[5]
            clearance = pos.z - impact.z
            check('spawn above ground', 'pass' if clearance > 0 else 'fail',
                  {'vertical_distance_cm': clearance, 'ignores_pawn': True})
        else:
            check('spawn above ground', 'fail', 'No blocking surface within 1000 cm below settled pawn.')
    except Exception as exc:
        check('spawn above ground', 'unverified', 'Trace API unavailable: ' + str(exc))

def inspect_world(world, pawn):
    try:
        partition = world.get_world_settings().get_editor_property('world_partition')
        details = {'present': bool(partition)}
        if partition:
            try:
                details['streaming'] = partition.get_editor_property('bEnableStreaming')
            except Exception as exc:
                details['streaming'] = 'unverified: ' + str(exc)
        check('world partition', 'pass' if partition else 'fail', details)
    except Exception as exc:
        check('world partition', 'unverified', 'Python binding unavailable: ' + str(exc))
    try:
        fogs = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ExponentialHeightFog)
        entries = []
        for fog in fogs:
            component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
            entries.append({'density': component.get_editor_property('fog_density'),
                            'height_falloff': component.get_editor_property('fog_height_falloff')})
        check('fog', 'observed' if entries else 'fail', entries)
    except Exception as exc:
        check('fog', 'unverified', str(exc))
    cvars = {}
    for name in ('r.DynamicGlobalIlluminationMethod', 'r.ReflectionMethod',
                 'r.Shadow.Virtual.Enable', 'r.Nanite.ProjectEnabled'):
        try:
            cvars[name] = unreal.SystemLibrary.get_console_variable_int_value(name)
        except Exception as exc:
            cvars[name] = 'unverified: ' + str(exc)
    check('renderer CVars', 'observed', cvars)

def check_controls(pawn, cameras, lights):
    # Calling events checks their behavior, not whether physical keys are mapped.
    for label, event, component in (
        ('flashlight toggle', 'df_toggle_flashlight', lights[0] if lights else None),
        ('view toggle', 'df_toggle_view', cameras[0] if cameras else None)):
        try:
            event_name = {'df_toggle_flashlight': 'DF_ToggleFlashlight', 'df_toggle_view': 'DF_ToggleView'}[event]
            func = lambda: pawn.call_method(event_name)
            if component is None:
                raise RuntimeError('Expected component absent')
            arm = pawn.get_component_by_class(unreal.SpringArmComponent)
            before = component.is_visible() if label.startswith('flashlight') else arm.get_editor_property('target_arm_length')
            func()
            after = component.is_visible() if label.startswith('flashlight') else arm.get_editor_property('target_arm_length')
            func()  # restore
            check(label, 'pass' if before != after else 'fail', {'before': before, 'after': after, 'event': event})
        except Exception as exc:
            check(label, 'unverified', 'Callable test event unavailable: ' + str(exc))
    try:
        movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
        initial = movement.get_editor_property('max_walk_speed')
        pawn.call_method('DF_StartSprint')
        sprint = movement.get_editor_property('max_walk_speed')
        pawn.call_method('DF_StopSprint')
        restored = movement.get_editor_property('max_walk_speed')
        check('sprint callable events', 'pass' if sprint > restored and restored > 0 else 'fail',
              {'initial': initial, 'sprint': sprint, 'restored': restored, 'scope':'Immediate callable events; survival polls held physical Shift on following tick.'})
    except Exception as exc:
        check('sprint callable events', 'unverified', 'Callable test events unavailable: ' + str(exc))


def tick(delta):
    try:
        elapsed = time.monotonic() - state['since']
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if state['stage'] == 'start':
            if editor.get_game_world():
                result['errors'].append('An existing PIE session is running; refusing to alter it.')
                finish('blocked')
                return
            if MAP not in editor.get_editor_world().get_path_name():
                raise RuntimeError('Open the saved foundation map first; do not replace unsaved scenes')
            slot_actor=next((a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_class().get_name()=='BP_SurvivalDirector_C'),None)
            if slot_actor:
                state.update(slot_actor=slot_actor,original_slot=slot_actor.get_editor_property('SaveSlotName'))
                slot_actor.set_editor_property('SaveSlotName',QA_SLOT)
            unreal.GameplayStatics.delete_game_in_slot(QA_SLOT,0)
            for path in ('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter',
                         '/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode',
                         '/Game/Player/BP_DustfallCharacter', '/Game/Core/BP_DustfallGameMode'):
                asset = unreal.EditorAssetLibrary.load_asset(path)
                if asset:
                    try:
                        compiled = unreal.BlueprintEditorLibrary.compile_blueprint(asset)
                        check('compile ' + path, 'pass' if compiled else 'fail', 'BlueprintEditorLibrary.compile_blueprint returned ' + str(compiled))
                    except Exception as exc:
                        check('compile ' + path, 'unverified', str(exc))
                else:
                    check('compile ' + path, 'unverified', 'Asset not found.')
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['owns_pie'] = True
            stage('wait_world')
        elif state['stage'] == 'wait_world':
            world = editor.get_game_world()
            if not world:
                if elapsed > 90:
                    raise RuntimeError('Timed out waiting for PIE game world.')
                return
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0) if pc else None
            if not pawn:
                if elapsed > 90:
                    raise RuntimeError('Timed out waiting for possessed player pawn.')
                return
            state.update(world=world, pc=pc, pawn=pawn)
            habitat_data=json.loads((ROOT/'Saved/Codex/phase3_habitat_build.json').read_text())
            state['origin']=unreal.Vector(*habitat_data['origin_cm'])
            state['clone_spawn']=unreal.Vector(*habitat_data['CloneSpawn'])
            # A saved game may resume outside; test the authored safe respawn as
            # well as the loaded player's movement. This only changes PIE state.
            starts=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.PlayerStart)
            spawn=state['clone_spawn']
            correct=any(sum((getattr(a.get_actor_location(),axis)-getattr(spawn,axis))**2 for axis in ['x','y','z'])<25 for a in starts)
            check('safe interior spawn','pass' if correct else 'fail',{'expected':str(spawn),'player_starts':[str(a.get_actor_location()) for a in starts]})
            pawn.set_actor_location(spawn,False,True)
            pawn.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
            stage('settle')
        elif state['stage'] == 'settle':
            if elapsed < 3.0:
                return
            world = editor.get_game_world()
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
            state.update(world=world, pc=pc, pawn=pawn)
            inspect_world(world, pawn)
            name = pawn.get_class().get_name()
            check('possessed pawn', 'pass' if name.startswith(PAWN_PREFIXES) else 'fail', name)
            pos = pawn.get_actor_location()
            check('spawn location', 'observed', {'x': pos.x, 'y': pos.y, 'z': pos.z})
            check_ground(world, pawn, pos)
            cameras = pawn.get_components_by_class(unreal.CameraComponent)
            active = [c.get_name() for c in cameras if c.is_active()]
            check('active cameras', 'pass' if len(active) == 1 else 'fail', {'count': len(cameras), 'active': active})
            lights = pawn.get_components_by_class(unreal.SpotLightComponent)
            check('spotlights', 'observed' if lights else 'fail', [{'name': l.get_name(), 'visible': l.is_visible()} for l in lights])
            check_controls(pawn, cameras, lights)
            survival=next((a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_class().get_name()=='BP_SurvivalDirector_C'),None)
            state['survival']=survival
            if survival:
                state['expected_walk']=float(survival.get_editor_property('Tuning').get_editor_property('WalkSpeed'))
            pc.set_control_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0))
            state['start_location'] = pos
            try:
                lib_class = unreal.load_class(None, '/Script/Engine.SubsystemBlueprintLibrary')
                lib = unreal.get_default_object(lib_class)
                state['input'] = lib.call_method('GetLocalPlayerSubSystemFromPlayerController', (pc, unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
                check('input subsystem', 'pass' if state['input'] else 'fail', str(state['input']))
            except Exception as exc:
                state['input_error'] = str(exc)
                state['input'] = None
            state['move_action'] = unreal.load_asset(ACTIONS['move'])
            state['jump_action'] = unreal.load_asset(ACTIONS['jump'])
            stage('move')
        elif state['stage'] == 'move':
            if 'sprint_checked' not in state:
                movement=state['pawn'].get_component_by_class(unreal.CharacterMovementComponent)
                speed=float(movement.get_editor_property('max_walk_speed'))
                key=unreal.Key()
                key.set_editor_property('key_name',unreal.Name('LeftShift'))
                held=state['pc'].is_input_key_down(key)
                expected=state.get('expected_walk',500.)
                check('survival sprint limit','pass' if (not held and abs(speed-expected)<1) else 'unverified',{'held_shift':held,'actual_max_speed':speed,'expected_walk_speed':expected})
                state['sprint_checked']=True
            subsystem, action = state['input'], state['move_action']
            if not subsystem or not action:
                check('injected movement', 'unverified', 'Input subsystem/action unavailable: ' + state.get('input_error', ACTIONS['move']))
                stage('jump')
                return
            if elapsed < 1.0:
                subsystem.inject_input_vector_for_action(action, unreal.Vector(1, 0, 0), [], [])
                return
            end = state['pawn'].get_actor_location()
            start = state['start_location']
            distance = ((end.x-start.x)**2 + (end.y-start.y)**2)**0.5
            check('injected movement', 'pass' if distance > 5 else 'fail', {'horizontal_cm': distance, 'action': ACTIONS['move']})
            stage('jump')
        elif state['stage'] == 'jump':
            subsystem, action = state['input'], state['jump_action']
            if not subsystem or not action:
                check('injected jump', 'unverified', 'Input subsystem or jump action unavailable: ' + ACTIONS['jump'])
                finish('completed')
                return
            if 'jump_z' not in state:
                movement = state['pawn'].get_component_by_class(unreal.CharacterMovementComponent)
                try:
                    grounded = movement.is_moving_on_ground()
                except Exception as exc:
                    check('injected jump', 'unverified', 'Cannot confirm grounded before jump: ' + str(exc))
                    finish('completed')
                    return
                if not grounded:
                    if elapsed < 5.0:
                        return
                    check('injected jump', 'unverified', 'Pawn did not settle on ground before jump.')
                    finish('completed')
                    return
                stage('jump')
                state['jump_z'] = state['pawn'].get_actor_location().z
                state['jump_max'] = state['jump_z']
            state['jump_max'] = max(state['jump_max'], state['pawn'].get_actor_location().z)
            if elapsed < 0.2:
                subsystem.inject_input_vector_for_action(action, unreal.Vector(1, 0, 0), [], [])
            if elapsed < 1.2:
                return
            rise = state['jump_max'] - state['jump_z']
            check('injected jump', 'pass' if rise > 5 else 'fail', {'rise_cm': rise, 'action': ACTIONS['jump']})
            stage('collision_setup')
        elif state['stage'] == 'collision_setup':
            pawn, pc = state['pawn'], state['pc']
            origin=state['origin']
            start = unreal.Vector(origin.x+300,origin.y,origin.z+148)
            pawn.set_actor_location(start, False, True)
            pawn.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
            pc.set_control_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0))
            # Trace the actual approach so the test follows the habitat if its
            # blockout is repositioned, and cannot pass on an unrelated obstacle.
            end = unreal.Vector(start.x + 450, start.y, start.z)
            hit = unreal.SystemLibrary.line_trace_single(state['world'], start, end,
                unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn],
                unreal.DrawDebugTrace.NONE, True)
            parts = unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method('BreakHitResult', (hit,))
            actor = parts[9] if parts[0] else None
            tags = [str(tag) for tag in actor.get_editor_property('tags')] if actor else []
            if not actor or 'DF_Phase3_Habitat' not in tags or actor.get_actor_label()!='P3_Hab_InnerDoor':
                check('habitat collision by walking', 'fail', {'reason': 'Approach trace did not hit tagged habitat', 'hit': str(actor)})
                finish('completed')
                return
            state['collision_start_x'] = start.x
            state['collision_impact_x'] = parts[5].x
            state['collision_actor'] = str(actor)
            stage('collision_walk')
        elif state['stage'] == 'collision_walk':
            if elapsed < 1.5:
                state['input'].inject_input_vector_for_action(state['move_action'], unreal.Vector(0, 1, 0), [], [])
                return
            end = state['pawn'].get_actor_location()
            start_x = state['collision_start_x']
            radius = state['pawn'].get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_radius()
            clearance = state['collision_impact_x'] - end.x
            passed = abs(clearance - radius) <= 20 and end.x > start_x + 50
            check('habitat collision by walking', 'pass' if passed else 'fail',
                  {'start_x': start_x, 'end_x': end.x, 'impact_x': state['collision_impact_x'],
                   'capsule_radius': radius, 'clearance': clearance, 'actor': state['collision_actor'],
                   'basis': 'injected forward input toward traced habitat'})
            finish('completed')
    except Exception:
        result['errors'].append(traceback.format_exc())
        finish('error')

write()
state['handle'] = unreal.register_slate_post_tick_callback(tick)
