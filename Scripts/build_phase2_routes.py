"""Place replaceable, nonblocking route stakes on loaded landscape cells.

Run after Phase 2 landmarks in the dedicated editor. Does not save the level.
Tracing is validated before replacing old route actors; missed cells abort.
"""
import json
import math
import pathlib
import runpy
import unreal

TAG = 'DF_Phase2_Route'
RAMP_TAG = 'DF_Phase2_HomeApproach'
ROOT = pathlib.Path(unreal.Paths.project_dir())
REPORT = ROOT / 'Saved/Codex/route_build_report.json'
LANDMARKS = ROOT / 'Saved/Codex/landmark_build_report.json'


def build():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.EditorLevelLibrary.get_editor_world()
    current = list(actors.get_all_level_actors())
    bases = [a for a in current if a.get_actor_label() == 'Hab_Base_Temporary'
             and 'DF_Phase1_Habitat_Blockout' in [str(t) for t in a.tags]]
    if len(bases) != 1:
        raise RuntimeError('Expected exactly one loaded habitat base')
    base = bases[0].get_actor_location()
    origin = (base.x, base.y)
    ignored = [a for a in current if not isinstance(a, unreal.LandscapeProxy)]
    if len(ignored) == len(current):
        raise RuntimeError('No loaded landscape')
    cruiser = (-55000.0, 5000.0)
    if LANDMARKS.exists():
        report = json.loads(LANDMARKS.read_text(encoding='utf-8'))
        cruiser = (float(report['Cruiser']['relative_x_cm']), float(report['Cruiser']['relative_y_cm']))
    lines = runpy.run_path(str(ROOT/'Scripts/phase2_layout.py'))['route_polylines'](cruiser)
    routes = [(name+'_%d'%i,a,b) for name,points in lines.items() for i,(a,b) in enumerate(zip(points,points[1:]))]
    report = {'spacing_cm': 2500, 'home_exclusion_radius_cm': 1500, 'routes': {}, 'trace_gaps': []}
    positions = []
    breaker = unreal.get_default_object(unreal.GameplayStatics.static_class())
    for name, start, end in routes:
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        count = max(1, int(math.ceil(length / 2500.0)))
        previous = None
        slopes = []
        samples = 0
        for i in range(count + 1):
            t = i / count
            x = origin[0] + start[0] + (end[0] - start[0]) * t
            y = origin[1] + start[1] + (end[1] - start[1]) * t
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 100000),
                unreal.Vector(x, y, -100000), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                False, ignored, unreal.DrawDebugTrace.NONE, True)
            parts = breaker.call_method('BreakHitResult', (hit,))
            if not parts[0]:
                report['trace_gaps'].append({'route': name, 'x_cm': x, 'y_cm': y})
                previous = None
                continue
            z = parts[5].z
            samples += 1
            if previous:
                horizontal = math.hypot(x - previous[0], y - previous[1])
                if horizontal:
                    slopes.append(math.degrees(math.atan2(abs(z - previous[2]), horizontal)))
            previous = (x, y, z)
            # Keep the landing pad and future airlock approach unobstructed.
            if math.hypot(x - origin[0], y - origin[1]) >= 1500 and 0 < i < count:
                positions.append((name, i, x, y, z))
        report['routes'][name] = {'length_cm': length, 'sample_count': samples,
                                  'max_sampled_slope_degrees': max(slopes) if slopes else None,
                                  'start_relative_cm': start, 'end_relative_cm': end}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if report['trace_gaps']:
        raise RuntimeError('Route traces missed landscape; load cells and retry. See ' + str(REPORT))
    mesh = unreal.load_asset('/Engine/BasicShapes/Cube.Cube')
    material = unreal.load_asset('/Game/Habitat/Blockout/M_Hab_Blockout_DustyMetal')
    if not mesh or not material:
        raise RuntimeError('Missing engine cube or dusty metal material')
    for actor in current:
        if any(str(t) in [TAG, RAMP_TAG] for t in actor.tags):
            actors.destroy_actor(actor)
    # The 50 cm foundation pad is taller than the capsule's 45 cm step.
    ramp = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(origin[0]+1230, origin[1], base.z-43))
    ramp.set_actor_label('P2_Home_Approach_Ramp')
    ramp.tags = [unreal.Name(RAMP_TAG)]
    ramp.set_folder_path('DUSTFALL/Phase2_Routes')
    ramp.static_mesh_component.set_static_mesh(mesh)
    ramp.static_mesh_component.set_material(0, material)
    ramp.static_mesh_component.set_collision_profile_name('BlockAll')
    ramp.set_actor_scale3d(unreal.Vector(5.4, 5., .2))
    ramp.set_actor_rotation(unreal.Rotator(pitch=-5.71, yaw=0, roll=0), False)
    for name, index, x, y, z in positions:
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z + 45.0))
        if not actor:
            raise RuntimeError('Could not spawn route stake')
        actor.set_actor_label('P2_Route_%s_%03d' % (name, index))
        actor.tags = [unreal.Name(TAG)]
        actor.set_folder_path('DUSTFALL/Phase2_Routes/' + name)
        actor.set_editor_property('is_spatially_loaded', True)
        component = actor.static_mesh_component
        component.set_static_mesh(mesh)
        component.set_material(0, material)
        component.set_collision_profile_name('NoCollision')
        actor.set_actor_scale3d(unreal.Vector(0.10, 0.10, 0.90))
    report['placed_stakes'] = len(positions)
    report['home_approach_ramp'] = True
    REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('Phase 2 routes built; report: ' + str(REPORT))


if __name__ == '__main__':
    build()
