"""Lead-only, opt-in PIE game-view M6 evidence; never saves temporary probes.

Run after build_phase5_atmosphere.py. Wait for report.json terminal status, not
editor queue completion. Uses isolated survival+exploration slots, restores the
authored slot after PIE, deletes only its QA slots. No visual or GPU pass inferred.
Temporary actors are authored before PIE, copied into PIE, destroyed after PIE.
Source-verified APIs still need live validation (see M6 final handoff summary).
"""
import json
import math
import pathlib
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
OUT = ROOT/'Saved/Codex/Phase5Atmosphere'
QA = 'Dustfall_M6_AtmosphereCapture_QA'
CASES = [('calm_day', 0, .5, False), ('storm_day', 2, .5, False),
         ('dusk', 1, .75, False), ('midnight_off', 1, 0., False),
         ('midnight_on', 1, 0., True), ('midnight_moon', 1, 0., False)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world_sub = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if world_sub.get_game_world():
        raise RuntimeError('Stop PIE first')
    world = world_sub.get_editor_world()
    if '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name():
        raise RuntimeError('Foundation map required')
    current = list(actor_sub.get_all_level_actors())
    source = next(a for a in current if a.get_class().get_name() == 'BP_SurvivalDirector_C')
    if not any(isinstance(a, unreal.DustfallAtmosphereFX) for a in current):
        raise RuntimeError('Author M6 atmosphere first')
    original_slot = source.get_editor_property('SaveSlotName')
    report = {'status': 'running', 'method': 'PIE game-view HighResShot 1920x1080',
              'scope': 'Visual evidence only; inspect 15m detail, 150m silhouette, grey night, moon and flashlight. GPU budget unmeasured.',
              'targets': [], 'captures': [], 'errors': []}
    state = {'stage': 'start', 'since': time.monotonic(), 'index': 0, 'handle': None, 'restored': False}
    temporary = []

    def write():
        (OUT/'report.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')

    def cleanup():
        if state['restored']:
            return
        source.set_editor_property('SaveSlotName', original_slot)
        for actor in temporary:
            if unreal.SystemLibrary.is_valid(actor):
                actor_sub.destroy_actor(actor)
        for slot in [QA, QA+'_Exploration']:
            unreal.GameplayStatics.delete_game_in_slot(slot, 0)
        if state['handle'] is not None:
            unreal.unregister_slate_post_tick_callback(state['handle'])
        state['restored'] = True
        report['cleanup'] = 'PIE stopped; temporary actors destroyed; authored slot restored; QA slots deleted; nothing saved'
        write()

    def stop():
        editor.editor_request_end_play()
        state.update(stage='end', since=time.monotonic())
        write()

    try:
        cube = unreal.load_asset('/Engine/BasicShapes/Cube')
        sphere = unreal.load_asset('/Engine/BasicShapes/Sphere')
        dark = unreal.load_asset('/Game/Habitat/Materials/M_P3_Hab_Charcoal')
        if not cube or not sphere or not dark:
            raise RuntimeError('Probe meshes/dark material missing; build Phase3 habitat first')
        breaker = unreal.get_default_object(unreal.GameplayStatics.static_class())
        ignored = [a for a in current if not isinstance(a, unreal.LandscapeProxy)]

        def ground(x, y):
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 100000), unreal.Vector(x, y, -100000),
                        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignored, unreal.DrawDebugTrace.NONE, True)
            parts = breaker.call_method('BreakHitResult', (hit,))
            if not parts[0]:
                raise RuntimeError('Load authoring cells for capture terrain at '+str((x, y)))
            return parts[5].z

        def mesh(mesh_asset, position, scale):
            actor = actor_sub.spawn_actor_from_class(unreal.StaticMeshActor, position)
            if not actor:
                raise RuntimeError('Temporary probe spawn failed')
            temporary.append(actor)
            actor.set_actor_label('TEMP_M6_AtmosphereProbe')
            actor.set_editor_property('is_spatially_loaded', False)
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            component.set_static_mesh(mesh_asset)
            component.set_collision_profile_name('NoCollision')
            component.set_material(0, dark)
            actor.set_actor_scale3d(scale)

        cx, cy = 2500., -4000.
        camera_position = unreal.Vector(cx, cy, ground(cx, cy)+180.)
        report['camera_cm'] = [camera_position.x, camera_position.y, camera_position.z]
        for distance, angle in [(5., -24.), (10., -8.), (15., 8.), (25., 24.)]:
            radians = math.radians(angle)
            x, y = cx+distance*100*math.cos(radians), cy+distance*100*math.sin(radians)
            z = ground(x, y)
            mesh(cube, unreal.Vector(x, y, z+112), unreal.Vector(.35, .6, .85))
            mesh(sphere, unreal.Vector(x, y, z+165), unreal.Vector(.3, .3, .3))
            for offset in [-15, 15]:
                mesh(cube, unreal.Vector(x, y+offset, z+35), unreal.Vector(.27, .22, .7))
            report['targets'].append({'kind': 'human_1.8m', 'horizontal_distance_m': distance,
                                      'angle_degrees': angle, 'foot_cm': [x, y, z]})
        z = ground(cx+15000, cy)
        mesh(cube, unreal.Vector(cx+15000, cy, z+600), unreal.Vector(6, 10, 12))
        report['targets'].append({'kind': 'dark_box_12m', 'horizontal_distance_m': 150, 'foot_cm': [cx+15000, cy, z]})
        camera = actor_sub.spawn_actor_from_class(unreal.CameraActor, camera_position, unreal.Rotator())
        if not camera:
            raise RuntimeError('Temporary camera spawn failed')
        temporary.append(camera)
        camera.tags = [unreal.Name('TEMP_M6_Camera')]
        camera.set_editor_property('is_spatially_loaded', False)
        camera_component = camera.get_component_by_class(unreal.CameraComponent)
        camera_component.set_field_of_view(65.)
        camera_component.set_editor_property('aspect_ratio', 1920./1080.)
        camera_component.set_editor_property('constrain_aspect_ratio', False)
        source.set_editor_property('SaveSlotName', QA)
        for slot in [QA, QA+'_Exploration']:
            unreal.GameplayStatics.delete_game_in_slot(slot, 0)

        def tick(delta):
            try:
                stage = state['stage']
                elapsed = time.monotonic()-state['since']
                worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
                if stage == 'end':
                    if not worlds:
                        cleanup()
                    elif elapsed > 30:
                        report['status'] = 'failed: PIE did not stop; cleanup pending'
                        write()
                        editor.editor_request_end_play()
                        state['since'] = time.monotonic()
                    return
                if elapsed > 45:
                    raise RuntimeError('Capture stage timed out: '+stage)
                if stage == 'start':
                    editor.editor_request_begin_play()
                    state.update(stage='wait', since=time.monotonic())
                    return
                if not worlds:
                    if stage != 'wait':
                        raise RuntimeError('PIE ended before captures finished')
                    return
                pie = worlds[0]
                if stage == 'wait':
                    if elapsed < 3:
                        return
                    env_class = unreal.load_class(None, '/Game/World/Blueprints/BP_DustfallEnvironmentDirector.BP_DustfallEnvironmentDirector_C')
                    survival_class = unreal.load_class(None, '/Game/Systems/BP_SurvivalDirector.BP_SurvivalDirector_C')
                    env = unreal.GameplayStatics.get_actor_of_class(pie, env_class)
                    survival = unreal.GameplayStatics.get_actor_of_class(pie, survival_class)
                    player = unreal.GameplayStatics.get_player_pawn(pie, 0)
                    controller = unreal.GameplayStatics.get_player_controller(pie, 0)
                    cameras = unreal.GameplayStatics.get_all_actors_of_class(pie, unreal.CameraActor)
                    view = next(a for a in cameras if 'TEMP_M6_Camera' in [str(t) for t in a.tags])
                    if not env or not survival or not player or not controller:
                        raise RuntimeError('PIE directors/player missing')
                    if str(survival.get_editor_property('SaveSlotName')) != QA:
                        raise RuntimeError('PIE did not inherit isolated QA slot')
                    player.set_actor_location(camera_position-unreal.Vector(0, 0, 88), False, True)
                    player.set_actor_rotation(unreal.Rotator(), False)
                    controller.set_control_rotation(unreal.Rotator())
                    controller.set_view_target_with_blend(view, 0.)
                    movement = player.get_component_by_class(unreal.CharacterMovementComponent)
                    if movement:
                        movement.disable_movement()
                    lights = player.get_components_by_class(unreal.SpotLightComponent)
                    light = next((c for c in lights if 'Flashlight' in c.get_name()), None)
                    if not light:
                        raise RuntimeError('Player flashlight component not found')
                    state.update(env=env, survival=survival, light=light, view=view, stage='apply', since=time.monotonic())
                    return
                env = state['env']
                name, weather, clock, flashlight = CASES[state['index']]
                # Pin input hooks during evidence; the director still executes its
                # own density/light graph and AtmosphereFX runs after it.
                env.set_editor_property('TimeOfDay', clock)
                env.set_editor_property('Weather', weather)
                env.set_editor_property('StormIntensity', 1. if weather == 2 else 0.)
                env.set_editor_property('WeatherElapsed', 0.)
                for resource in ['Oxygen', 'Power', 'Integrity']:
                    state['survival'].set_editor_property(resource, 100.)
                state['light'].set_visibility(flashlight, True)
                if stage == 'apply':
                    state['view'].set_actor_rotation(unreal.Rotator(pitch=75., yaw=180.) if name == 'midnight_moon' else unreal.Rotator(), False)
                    data = env.get_editor_property('EnvironmentData')
                    env.set_editor_property('CurrentFogDensity', data.get_editor_property(['CalmFogDensity', 'HazeFogDensity', 'StormFogDensity'][weather]))
                    for suffix in ['.png', '.bmp']:
                        path = OUT/(name+suffix)
                        if path.exists():
                            path.unlink()
                    state.update(stage='settle', since=time.monotonic())
                elif stage == 'settle' and elapsed >= 8:
                    path = (OUT/(name+'.png')).as_posix()
                    unreal.SystemLibrary.execute_console_command(pie, 'HighResShot 1920x1080 filename="'+path+'"')
                    state.update(stage='shot', since=time.monotonic())
                elif stage == 'shot' and elapsed >= 1:
                    path = OUT/(name+'.png')
                    if not path.exists():
                        return
                    report['captures'].append({'file': path.name, 'weather': weather, 'time_of_day': clock,
                                               'flashlight': flashlight, 'fog_density': env.get_editor_property('CurrentFogDensity'),
                                               'bytes': path.stat().st_size})
                    state['index'] += 1
                    write()
                    if state['index'] == len(CASES):
                        report['status'] = 'complete; visual review and GPU profiling required'
                        stop()
                    else:
                        state.update(stage='apply', since=time.monotonic())
            except Exception:
                report['status'] = 'failed'
                report['errors'].append(traceback.format_exc())
                stop()

        write()
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
    except Exception:
        report['status'] = 'failed'
        report['errors'].append(traceback.format_exc())
        cleanup()
        raise


if __name__ == '__main__':
    main()
