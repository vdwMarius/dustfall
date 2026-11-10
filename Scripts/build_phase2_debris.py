"""Dress exterior landmarks with licensed, non-interactive Quixel industrial props."""
import json
import math
import pathlib
import random
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
TAG = 'DF_Phase2_Debris'
ASSETS = [('wcljbdb', 170), ('ullibjd', 120), ('wdklears', 220), ('vkzidgds', 90)]


def build():
    report = json.loads((ROOT/'Saved/Codex/landmark_build_report.json').read_text())
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    current = list(actors.get_all_level_actors())
    world = unreal.EditorLevelLibrary.get_editor_world()
    ignore = [a for a in current if not isinstance(a, unreal.LandscapeProxy)]
    rng = random.Random(2042)
    meshes = []
    for ident, width in ASSETS:
        mesh = unreal.load_asset('/Game/World/QuixelPhase2/'+ident+'/SM_'+ident)
        if not mesh:
            raise RuntimeError('Missing imported debris mesh ' + ident)
        bounds = mesh.get_bounds().box_extent
        meshes.append((mesh, width/max(1,2*max(bounds.x,bounds.y,bounds.z))))
    placements = []
    for name, site in report.items():
        count, radius = (36, 16000) if name == 'Cruiser' else (28, 3500) if name == 'Wreck' else (16, 2300)
        for i in range(count):
            angle, r = rng.uniform(0,math.tau), rng.uniform(radius*.65,radius)
            x, y = site['relative_x_cm']+math.cos(angle)*r, site['relative_y_cm']+math.sin(angle)*r
            hit = unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
            parts = unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method('BreakHitResult',(hit,))
            if not parts[0]:
                raise RuntimeError('Debris ground trace missed; load landscape')
            index = rng.choices(range(4),[6,2,1,3])[0]
            placements.append((name,i,index,unreal.Vector(x,y,parts[5].z+5),rng.uniform(0,360)))
    for actor in current:
        if TAG in [str(t) for t in actor.tags]:
            actors.destroy_actor(actor)
    for name,i,index,position,yaw in placements:
        mesh,scale = meshes[index]
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,position)
        actor.set_actor_label('P2_Debris_%s_%02d'%(name,i))
        actor.tags=[unreal.Name(TAG)]
        actor.set_folder_path('DUSTFALL/Phase2_Debris/'+name)
        actor.set_editor_property('is_spatially_loaded',True)
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name('NoCollision')
        actor.static_mesh_component.set_editor_property('ld_max_draw_distance',18000.)
        actor.set_actor_scale3d(unreal.Vector(scale,scale,scale))
        actor.set_actor_rotation(unreal.Rotator(0,0,yaw),False)
        actor.modify()
    (ROOT/'Saved/Codex/debris_build_report.json').write_text(json.dumps({'seed':2042,'props':len(placements),'interactive':False},indent=2))


if __name__ == '__main__':
    build()
