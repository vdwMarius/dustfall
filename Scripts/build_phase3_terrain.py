"""Author real Landscape relief, then reseat sparse jagged scanned formations.

Requires the compiled editor-only DustfallTerrainLibrary and sole asset-writer
lease. Run BEFORE rebuilding native PCG and debris. The exact original base
heightfield is kept under Scripts/Data, allowing repeat authoring without drift.
No Python executes in a packaged game.
"""
import hashlib
import json
import math
import pathlib
import runpy
import time
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
TAG = 'DF_Phase3_Geology'
REPORT = ROOT / 'Saved/Codex/phase3_terrain_build.json'


def main():
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({'status':'authoring terrain','heavy_validation_deferred_to_user':True},indent=2))
    if unreal.EditorLevelLibrary.get_game_world():
        raise RuntimeError('Stop PIE before terrain authoring')
    runpy.run_path(str(ROOT/'Scripts/load_phase3_authoring_cells.py'), run_name='__main__')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    current = list(actors.get_all_level_actors())
    landscape = next((a for a in current if isinstance(a, unreal.Landscape)), None)
    if not landscape:
        raise RuntimeError('Load foundation Landscape actor and all landscape cells first')
    if '/Game/World/Maps/L_Dustfall_Foundation' not in landscape.get_path_name():
        raise RuntimeError('Wrong landscape map')
    if not hasattr(unreal, 'DustfallTerrainLibrary'):
        raise RuntimeError('Compile dustfallEditor and restart editor first')
    # Also supports first authoring before a Phase3 graph exists. Reuse the
    # existing all-sided scan assembly authoring, without starting generation.
    pcg_tools=runpy.run_path(str(ROOT/'Scripts/build_phase3_pcg.py'))
    for ident in ['xgoqfid','xgjnech','xgjodeb']:
        pcg_tools['assembly'](ident,pcg_tools['IDS'].index(ident))
    landmarks = json.loads((ROOT/'Saved/Codex/landmark_build_report.json').read_text())
    cruiser = (landmarks['Cruiser']['relative_x_cm'], landmarks['Cruiser']['relative_y_cm'])
    lines = runpy.run_path(str(ROOT/'Scripts/phase2_layout.py'))['route_polylines'](cruiser)
    routes = [(a,b) for line in lines.values() for a,b in zip(line,line[1:])]
    protections = [(0,0,3300),(15000,10000,2500),(35000,-25000,2200),(*cruiser,12500)]
    baseline = ROOT/'Scripts/Data/Phase3LandscapeBaseline.bin'
    status = unreal.DustfallTerrainLibrary.author_hostile_relief(landscape, str(baseline),
        [unreal.Vector(*d) for d in protections],
        [unreal.Vector(p[0],p[1],0) for pair in routes for p in pair])
    if not status.startswith('OK'):
        raise RuntimeError(status)
    unreal.log(status)
    hazard_cls=unreal.load_class(None,'/Script/dustfall.DustfallTerrainHazardDirector')
    if not hazard_cls:
        raise RuntimeError('Compile native terrain hazard director before authoring')
    hazard=next((a for a in current if a.get_class()==hazard_cls),None)
    if not hazard:
        hazard=actors.spawn_actor_from_class(hazard_cls,unreal.Vector(0,0,0))
    hazard.set_actor_label('DustfallTerrainHazardDirector')
    hazard.set_editor_property('is_spatially_loaded',False)
    hazard.set_folder_path('DUSTFALL/Systems')
    # Wait for Landscape render/collision update before tracing and reseating.
    state = {'handle':None,'since':time.monotonic()}
    def finish(delta):
        if time.monotonic()-state['since'] < 3.:
            return
        unreal.unregister_slate_post_tick_callback(state['handle'])
        unreal._dustfall_terrain_handle = None
        try:
            report = dress_geology(actors, routes, protections)
            report.update(status='complete', landscape_result=status,
                baseline_file=str(baseline.relative_to(ROOT)),
                baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
                pcg_rebuild_required=True,
                acceptance='terrain authored; navigation, recovery, visibility and package validation still required')
            unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_all_dirty_levels()
            REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
        except Exception as exc:
            import traceback
            REPORT.write_text(json.dumps({'status':'failed','error':str(exc),'traceback':traceback.format_exc()},indent=2))
            unreal.log_error(traceback.format_exc())
    state['handle']=unreal.register_slate_post_tick_callback(finish)
    unreal._dustfall_terrain_handle=state['handle']
    REPORT.write_text(json.dumps({'status':'waiting for landscape collision update','landscape_result':status},indent=2))


def dress_geology(actors, routes, protections):
    current = list(actors.get_all_level_actors())
    world = unreal.EditorLevelLibrary.get_editor_world()
    ignore = [a for a in current if not isinstance(a,unreal.LandscapeProxy)]
    breaker = unreal.get_default_object(unreal.GameplayStatics.static_class())
    def trace(x,y):
        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,30000),
            unreal.Vector(x,y,-30000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            False,ignore,unreal.DrawDebugTrace.NONE,True)
        p=breaker.call_method('BreakHitResult',(hit,))
        if not p[0]:
            raise RuntimeError('Landscape trace missed at %s,%s'%(x,y))
        return p[5].z
    def distance(x,y,a,b):
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/max(dx*dx+dy*dy,1.)))
        return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
    # Deliberate erosion zones, not route-parallel rock fences. Composite scan
    # meshes already enclose backs; height/scale variation follows landforms.
    groups=[(8000,-11000,7),(23000,23000,7),(-18000,-13000,8),
            (48000,-5000,7),(-34000,-29000,7),(3000,43000,8),
            (65000,45000,6),(-68000,-43000,6),(-30000,61000,8)]
    meshes=[]
    for ident in ['xgoqfid','xgjnech','xgjodeb']:
        mesh=unreal.load_asset('/Game/World/Phase3/Meshes/SM_PCG_'+ident)
        mesh=mesh or unreal.load_asset('/Game/World/Phase3/Meshes/SM_SM_PCG_'+ident)
        if not mesh:
            raise RuntimeError('Build Phase3 PCG assembly meshes before terrain dressing')
        meshes.append(mesh)
    plans=[]
    for gi,(cx,cy,count) in enumerate(groups):
        for j in range(count):
            angle=j*2.39996+gi*.72
            radius=900.+(j%4)*850.
            x,y=cx+math.cos(angle)*radius,cy+math.sin(angle)*radius
            width=1400.+((j*7+gi*3)%6)*250.
            if any(math.hypot(x-a,y-b)<r+width*.7 for a,b,r in protections):
                continue
            if any(distance(x,y,a,b)<900.+width*.7 for a,b in routes):
                continue
            mesh=meshes[(gi+j)%len(meshes)]
            b=mesh.get_bounds()
            scale=width/max(b.box_extent.x*2,b.box_extent.y*2,1.)
            # Trace the centre and four footprint sides. Seat the bottom below
            # the lowest footprint sample to hide steep-slope bases.
            zs=[trace(x+dx*width*.3,y+dy*width*.3) for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]]
            bottom=min(zs)-70.
            z=bottom-(b.origin.z-b.box_extent.z)*scale
            plans.append((x,y,z,scale,math.degrees(angle),mesh))
    for actor in current:
        if TAG in [str(t) for t in actor.tags]:
            actors.destroy_actor(actor)
    for i,(x,y,z,scale,yaw,mesh) in enumerate(plans):
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x,y,z),unreal.Rotator(yaw=yaw))
        actor.set_actor_label('P3_JaggedOutcrop_%03d'%i)
        actor.tags=[unreal.Name(TAG)]
        actor.set_folder_path('DUSTFALL/Phase3_HostileGeology')
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name('BlockAll')
        actor.set_actor_scale3d(unreal.Vector(scale,scale,scale))
    # Abandoned survey stakes make the sinkhole lip legible in dust and at
    # night. They are cues, not invisible blockers or lethal trigger volumes.
    amber_path='/Game/World/Phase3/Materials/M_TerrainWarningAmber'
    amber=unreal.load_asset(amber_path)
    if not amber:
        amber=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_TerrainWarningAmber','/Game/World/Phase3/Materials',unreal.Material,unreal.MaterialFactoryNew())
        graph=unreal.MaterialEditingLibrary
        c=graph.create_material_expression(amber,unreal.MaterialExpressionConstant3Vector,-200,0)
        c.set_editor_property('constant',unreal.LinearColor(.7,.20,.025,1.))
        graph.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
        graph.connect_material_property(c,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        graph.recompile_material(amber)
        unreal.EditorAssetLibrary.save_loaded_asset(amber)
    pole_mesh=unreal.load_asset('/Engine/BasicShapes/Cylinder.Cylinder')
    plate_mesh=unreal.load_asset('/Engine/BasicShapes/Cube.Cube')
    dark=unreal.load_asset('/Game/Habitat/Materials/M_P3_Hab_Charcoal')
    stake_sites=[(-10400,-4000),(-8500,-3400),(-6500,-4200),(-5400,-6200),
                 (11000,-15500),(18000,-15300),(25000,-15800)]
    for i,(x,y) in enumerate(stake_sites):
        z=trace(x,y)
        for part,mesh,scale,offset,mat in [
            ('post',pole_mesh,(.065,.065,1.6),75.,dark),
            ('reflector',plate_mesh,(.36,.075,.23),150.,amber)]:
            actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x,y,z+offset))
            actor.set_actor_label('P3_HazardSurvey_%02d_%s'%(i,part))
            actor.tags=[unreal.Name(TAG)]
            actor.set_folder_path('DUSTFALL/Phase3_HostileGeology')
            actor.static_mesh_component.set_static_mesh(mesh)
            actor.static_mesh_component.set_collision_profile_name('NoCollision')
            actor.static_mesh_component.set_material(0,mat or amber)
            actor.set_actor_scale3d(unreal.Vector(*scale))
    samples={name:{'xy_cm':[x,y],'landscape_z_cm':trace(x,y)} for name,x,y in
        [('home',0,0),('near_hill',8000,-11000),('north_ridge',3000,43000),
         ('pit_floor',-8500,-6500),('pit_east_ramp',-6300,-6500),
         ('ravine_floor',18000,-18500),('crater_floor',28000,2000)]}
    # Lightweight authoring sanity at 5m intervals, not runtime navigation QA.
    max_grade=0.; route_samples=0
    for a,b in routes:
        n=max(1,math.ceil(math.dist(a,b)/500.))
        previous=None
        for j in range(n+1):
            t=j/n; x=a[0]+(b[0]-a[0])*t; y=a[1]+(b[1]-a[1])*t
            z=trace(x,y); route_samples+=1
            if previous:
                max_grade=max(max_grade,abs(z-previous[2])/max(math.hypot(x-previous[0],y-previous[1]),1.))
            previous=(x,y,z)
    return {'jagged_outcrops':len(plans),'hazard_warning_stakes':len(stake_sites),'probe_samples':samples,
            'protected_route_collision_samples':route_samples,'protected_route_max_grade':max_grade,
            'pit_escape_direction':'east ramp; terraced floor, 3m rim transition',
            'ravine_escape_direction':'broad south bank; protected route forms saddle',
            'hazards':[{'kind':'pit','xy_cm':[-8500,-6500]}, {'kind':'ravine','xy_cm':[18000,-18500]}]}


if __name__=='__main__':
    main()
