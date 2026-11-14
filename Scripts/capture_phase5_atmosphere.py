"""Lead-only, opt-in PIE game-view M6 evidence; never saves temporary probes.

Run after build_phase5_atmosphere.py. Wait for report.json terminal status, not
editor queue completion. Uses isolated survival+exploration slots, restores the
authored slot after PIE, deletes only its QA slots. No visual or GPU pass inferred.
Probes spawn temporarily in the editor world (the Lead found Python PIE spawn
unavailable in this build), and are destroyed after PIE. The native
capture slot setter bypasses Modify/PostEditChange and restores the original string
without changing the survival package dirty flag. Dirty package differences are reported; no editor packages are saved.
Source-verified APIs still need live validation (see M6 final handoff summary).
"""
import json
import math
import pathlib
import time
import traceback
import struct
import zlib
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
OUT = ROOT/'Saved/Codex/Phase5Atmosphere'
QA = 'Dustfall_M6_AtmosphereCapture_QA'
BASE_CASES = [('calm_day', 0, .5, False), ('haze_day', 1, .5, False), ('storm_day', 2, .5, False),
         ('dusk', 1, .75, False), ('midnight_off', 1, 0., False),
         ('midnight_on', 1, 0., True), ('midnight_moon', 1, 0., False)]
CASES = [(name+suffix, weather, clock, light, heading)
         for name, weather, clock, light in BASE_CASES
         for suffix, heading in [('', 'probes'), ('_horizon', 'horizon')]]


def read_png(path):
    """Stdlib PNG decoder: noninterlaced 8-bit RGB/RGBA, all five row filters."""
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Not PNG')
    pos, payload = 8, bytearray()
    width = height = channels = None
    while pos < len(data):
        length = struct.unpack_from('>I', data, pos)[0]
        kind, chunk = data[pos+4:pos+8], data[pos+8:pos+8+length]
        pos += length+12
        if kind == b'IHDR':
            width, height, bits, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', chunk)
            if bits != 8 or color not in (2, 6) or compression or filtering or interlace:
                raise ValueError('Only noninterlaced RGB/RGBA8 PNG supported')
            channels = 3 if color == 2 else 4
        elif kind == b'IDAT':
            payload.extend(chunk)
        elif kind == b'IEND':
            break
    if not channels:
        raise ValueError('Missing IHDR')
    raw = zlib.decompress(payload)
    stride, rows, previous, offset = width*channels, [], bytearray(width*channels), 0
    if len(raw) != height*(stride+1):
        raise ValueError('Incomplete PNG data')
    for _ in range(height):
        mode = raw[offset]; offset += 1
        row = bytearray(raw[offset:offset+stride]); offset += stride
        for x in range(stride):
            left = row[x-channels] if x >= channels else 0
            up = previous[x]
            upper_left = previous[x-channels] if x >= channels else 0
            if mode == 1:
                predictor = left
            elif mode == 2:
                predictor = up
            elif mode == 3:
                predictor = (left+up)//2
            elif mode == 4:
                q = left+up-upper_left
                distances = [abs(q-left), abs(q-up), abs(q-upper_left)]
                predictor = [left, up, upper_left][distances.index(min(distances))]
            elif mode == 0:
                predictor = 0
            else:
                raise ValueError('Unknown PNG filter')
            row[x] = (row[x]+predictor) & 255
        rows.append(row)
        previous = row
    return width, height, channels, rows


def measure_box(path, camera, rotation, fov, foot, horizon=False):
    width, height, channels, rows = read_png(path)
    pitch, yaw = math.radians(rotation.pitch), math.radians(rotation.yaw)
    forward = (math.cos(pitch)*math.cos(yaw), math.cos(pitch)*math.sin(yaw), math.sin(pitch))
    right = (-math.sin(yaw), math.cos(yaw), 0.)
    up = (-math.sin(pitch)*math.cos(yaw), -math.sin(pitch)*math.sin(yaw), math.cos(pitch))

    def project(point):
        delta = [point[i]-[camera.x, camera.y, camera.z][i] for i in range(3)]
        dot = lambda v: sum(a*b for a, b in zip(delta, v))
        z = dot(forward)
        if z <= 0:
            raise ValueError('Box behind camera')
        scale = width/(2*math.tan(math.radians(fov)/2)*z)
        return round(width/2+dot(right)*scale), round(height/2-dot(up)*scale)

    def patch(point):
        x, y = project(point)
        if not (3 <= x < width-3 and 3 <= y < height-3):
            raise ValueError('Patch outside image')
        samples = []
        for py in range(y-3, y+4):
            for px in range(x-3, x+4):
                rgb = rows[py][px*channels:px*channels+3]
                # Screenshot is display-referred sRGB; report linear relative luminance.
                linear = [v/255/12.92 if v/255 <= .04045 else ((v/255+.055)/1.055)**2.4 for v in rgb]
                samples.append(sum(a*b for a, b in zip(linear, [.2126, .7152, .0722])))
        return {'center_px': [x, y], 'size_px': 7, 'average_luminance': sum(samples)/len(samples)}

    # Upper part avoids the sloping ground that obscures the box's lower face.
    # Select the face toward this camera for either +/-X heading. The horizon
    # view uses sky just ABOVE the box's skyline, not adjacent sloping ground.
    face = foot[0] + (300 if camera.x > foot[0] else -300)
    box = patch([face, foot[1], foot[2]+1000])
    sky = patch([face, foot[1], foot[2]+1450]) if horizon else patch([face, foot[1]+850, foot[2]+1000])
    return {'box': box, 'adjacent_sky': sky, 'contrast': (sky['average_luminance']-box['average_luminance'])/max(sky['average_luminance'], 1e-8),
            'reference': 'sky above silhouette skyline in horizon view' if horizon else 'adjacent sky in probe view',
            'note': 'Projected 7x7 patches, linearized sRGB; visually confirm sky patch is unobstructed.'}



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

    def dirty_packages():
        packages = list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        return sorted(p.get_path_name() for p in packages)

    initial_dirty = dirty_packages()
    report = {'status': 'running', 'method': 'PIE game-view HighResShot 1920x1080',
              'scope': 'Visual evidence only; inspect 15m detail, 150m silhouette, grey night, moon and flashlight. GPU budget unmeasured.',
              'targets': [], 'captures': [], 'errors': [], 'initial_dirty_packages': initial_dirty}
    editor_probes = []
    state = {'stage': 'start', 'since': time.monotonic(), 'index': 0, 'handle': None, 'restored': False, 'slot_changed': False}
    temporary = []
    probe_specs = []

    def write():
        (OUT/'report.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')

    def cleanup():
        if state['restored']:
            return
        if state['slot_changed'] and not unreal.DustfallAtmosphereFX.set_capture_save_slot(source, original_slot):
            raise RuntimeError('Could not restore authored save slot')
        temporary.clear()
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for probe in editor_probes:
            if unreal.SystemLibrary.is_valid(probe):
                actor_subsystem.destroy_actor(probe)
        editor_probes.clear()
        for slot in [QA, QA+'_Exploration']:
            unreal.GameplayStatics.delete_game_in_slot(slot, 0)
        if state['handle'] is not None:
            unreal.unregister_slate_post_tick_callback(state['handle'])
        state['restored'] = True
        if not report['errors']:
            report['status'] = 'complete; visual review and GPU profiling required'
        report['new_dirty_packages'] = sorted(set(dirty_packages())-set(initial_dirty))
        report['cleanup'] = 'PIE stopped; temporary actors destroyed; authored slot restored without editor notifications; temporary editor probes destroyed; QA slots deleted; no editor packages saved'
        write()

    def stop():
        editor.editor_request_end_play()
        state.update(stage='end', since=time.monotonic())
        write()

    try:
        cube = unreal.load_asset('/Engine/BasicShapes/Cube')
        sphere = unreal.load_asset('/Engine/BasicShapes/Sphere')
        dark = unreal.load_asset('/Game/Habitat/Materials/M_P3_Hab_Charcoal')
        player_tuning = unreal.load_asset('/Game/Data/DA_PlayerFoundation_Phase1')
        if not player_tuning:
            raise RuntimeError('Player camera tuning missing')
        eye_offset = player_tuning.get_editor_property('FirstPersonEyeOffset')
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
            probe_specs.append((mesh_asset, position, scale))

        def spawn_in_pie(pie, kind, position, scale):
            transform = unreal.Transform(location=position, scale=scale)
            actor = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(pie, kind, transform,
                        unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN)
            if not actor:
                raise RuntimeError('PIE-only probe spawn failed')
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            if component:
                component.set_mobility(unreal.ComponentMobility.MOVABLE)
            actor = unreal.GameplayStatics.finish_spawning_actor(actor, transform)
            temporary.append(actor)
            return actor

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
        boxes = {}
        for heading, direction in [('probes', 1), ('horizon', -1)]:
            x = cx+direction*15000
            z = ground(x, cy)
            mesh(cube, unreal.Vector(x, cy, z+600), unreal.Vector(6, 10, 12))
            boxes[heading] = [x, cy, z]
            report['targets'].append({'kind': 'dark_box_12m', 'heading': heading,
                'horizontal_distance_m': 150, 'foot_cm': boxes[heading]})
        if not unreal.DustfallAtmosphereFX.set_capture_save_slot(source, QA):
            raise RuntimeError('Native editor capture slot helper missing; rebuild first')
        state['slot_changed'] = True
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
                    # GameplayStatics.begin_deferred_actor_spawn_from_class is not exposed to
                    # Python in this build (probed live). Spawn unsaved probes in the editor
                    # world before PIE; PIE duplicates them. They are destroyed in cleanup.
                    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
                    for mesh_asset, position, scale in probe_specs:
                        probe = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, position)
                        if not probe:
                            raise RuntimeError('Probe spawn failed')
                        editor_probes.append(probe)
                        probe.set_actor_label('TEMP_AtmosphereProbe')
                        probe.set_editor_property('is_spatially_loaded', False)
                        component = probe.static_mesh_component
                        component.set_static_mesh(mesh_asset)
                        component.set_collision_profile_name('NoCollision')
                        component.set_material(0, dark)
                        probe.set_actor_scale3d(scale)
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
                    if not env or not survival or not player or not controller:
                        raise RuntimeError('PIE directors/player missing')
                    if str(survival.get_editor_property('SaveSlotName')) != QA:
                        raise RuntimeError('PIE did not inherit isolated QA slot')
                    player.set_actor_location(camera_position-unreal.Vector(0, 0, eye_offset), False, True)
                    player.set_actor_rotation(unreal.Rotator(), False)
                    controller.set_control_rotation(unreal.Rotator())
                    for boom in player.get_components_by_class(unreal.SpringArmComponent):
                        boom.set_editor_property('target_arm_length', 0.)
                    for mesh_component in player.get_components_by_class(unreal.SkeletalMeshComponent):
                        mesh_component.set_owner_no_see(True)
                    for camera_component in player.get_components_by_class(unreal.CameraComponent):
                        camera_component.set_editor_property('relative_location', unreal.Vector(0, 0, eye_offset))
                        camera_component.set_field_of_view(65.)
                        camera_component.set_editor_property('aspect_ratio', 1920./1080.)
                        camera_component.set_editor_property('constrain_aspect_ratio', False)
                    controller.set_view_target_with_blend(player, 0.)
                    movement = player.get_component_by_class(unreal.CharacterMovementComponent)
                    if movement:
                        movement.disable_movement()
                    lights = player.get_components_by_class(unreal.SpotLightComponent)
                    light = next((c for c in lights if 'Flashlight' in c.get_name()), None)
                    if not light:
                        raise RuntimeError('Player flashlight component not found')
                    state.update(env=env, survival=survival, light=light, view=player, controller=controller, stage='apply', since=time.monotonic())
                    return
                env = state['env']
                name, weather, clock, flashlight, heading = CASES[state['index']]
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
                    rotation = unreal.Rotator(pitch=5., yaw=180.) if heading == 'horizon' else (
                        unreal.Rotator(pitch=75., yaw=180.) if name == 'midnight_moon' else unreal.Rotator())
                    state['controller'].set_control_rotation(rotation)
                    state['view'].set_actor_rotation(unreal.Rotator(yaw=rotation.yaw), False)
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
                    capture = {'file': path.name, 'weather': weather, 'time_of_day': clock,
                                               'flashlight': flashlight, 'fog_density': env.get_editor_property('CurrentFogDensity'),
                                               'bytes': path.stat().st_size, 'heading': heading}
                    manager = unreal.GameplayStatics.get_player_camera_manager(pie, 0)
                    location, rotation = manager.get_camera_location(), manager.get_camera_rotation()
                    capture['camera_cm'] = [location.x, location.y, location.z]
                    capture['rotation'] = [rotation.pitch, rotation.yaw, rotation.roll]
                    try:
                        if clock == 0. and heading != 'horizon':
                            capture['silhouette_luminance'] = {'skipped': 'Night silhouette acceptance uses the matching horizon view.'}
                        else:
                            capture['silhouette_luminance'] = measure_box(path, location, rotation, manager.get_fov_angle(), boxes[heading], horizon=heading == 'horizon')
                    except (ValueError, OSError, zlib.error, struct.error) as exc:
                        capture['silhouette_luminance'] = {'skipped': str(exc)}
                    report['captures'].append(capture)
                    state['index'] += 1
                    write()
                    if state['index'] == len(CASES):
                        report['status'] = 'stopping; cleanup pending'
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
