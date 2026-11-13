"""Extend the native Phase 3 PCG graph with landmark-centred debris fields.

Run after build_phase3_pcg.py reports complete. Debris remains noninteractive;
this replaces Phase 2 Python-scattered decorative props with native PCG output.
"""
import json
import pathlib
import runpy
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
runpy.run_path(str(ROOT/'Scripts/load_phase3_authoring_cells.py'),run_name='__main__')
core = runpy.run_path(str(ROOT/'Scripts/build_phase3_pcg.py'))
g = unreal.load_asset('/Game/World/Phase3/PCG/PCG_DustfallEnvironment')
if not g:
    raise RuntimeError('Build Phase 3 PCG rocks first')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cells = [a for a in actors.get_all_level_actors() if 'DF_Phase3_PCG' in [str(t) for t in a.tags]]
if len(cells)!=64:
    raise RuntimeError('Load all 64 PCG authoring owners before adding debris; loaded '+str(len(cells)))
previous_handle = getattr(unreal,'_dustfall_phase3_pcg_debris_handle',None)
if previous_handle is not None:
    unreal.unregister_slate_post_tick_callback(previous_handle)
    unreal._dustfall_phase3_pcg_debris_handle = None
for old in list(g.get_editor_property('nodes')):
    if str(old.get_editor_property('node_title')).startswith('Debris:'):
        g.remove_node(old)
landscape = next(n for n in g.get_editor_property('nodes') if str(n.get_editor_property('node_title'))=='Landscape source')


def node(cls,title,x,y,**props):
    n,s = g.add_node_of_type(cls)
    n.set_editor_property('node_title',unreal.Name('Debris: '+title)); n.set_node_position(x,y)
    for k,v in props.items(): s.set_editor_property(k,v)
    return n,s


def edge(a,b,ap='Out',bp='In'):
    core['connect'](g,a,b,ap,bp)


sites = json.loads((ROOT/'Saved/Codex/landmark_build_report.json').read_text())
regions = []
for name,data in sites.items():
    p = unreal.PCGPoint()
    p.set_editor_property('transform',unreal.Transform(location=unreal.Vector(data['relative_x_cm'],data['relative_y_cm'],0)))
    r = 18000 if name=='Cruiser' else 5500 if name=='Wreck' else 3300
    p.set_editor_property('bounds_min',unreal.Vector(-r,-r,-50000))
    p.set_editor_property('bounds_max',unreal.Vector(r,r,50000))
    p.set_editor_property('steepness',1.)
    regions.append(p)
assets = [('wcljbdb',.9,2.),('ullibjd',.8,1.6),('wdklears',1.5,2.7),('vkzidgds',.6,1.2)]
clearance_points=core['exclusions'](250,protect_landmarks=False)
# Decorative debris belongs near ship/ruin geometry, inside the broader rock
# exclusion zones. Protect actual authored pieces rather than excluding their
# whole surrounding debris regions. These are world-space footprint volumes.
for actor in actors.get_all_level_actors():
    if 'DF_Phase2_Landmark' not in [str(t) for t in actor.tags]: continue
    center,extent=actor.get_actor_bounds(False)
    p=unreal.PCGPoint()
    p.set_editor_property('transform',unreal.Transform(location=unreal.Vector(center.x,center.y,0)))
    p.set_editor_property('bounds_min',unreal.Vector(-extent.x-250,-extent.y-250,-50000))
    p.set_editor_property('bounds_max',unreal.Vector(extent.x+250,extent.y+250,50000))
    p.set_editor_property('steepness',1.)
    clearance_points.append(p)
for i,(ident,lo,hi) in enumerate(assets):
    mesh = core['assembly'](ident,0)
    y = 6500+i*600
    sample,_ = node(unreal.PCGSurfaceSamplerSettings,ident,0,y,
                    points_per_squared_meter=.00045,point_extents=unreal.Vector(160,160,60),looseness=1.,seed=6140+i)
    edge(landscape,sample,'Out','Surface')
    region,_ = node(unreal.PCGCreatePointsSettings,'Landmark debris regions',230,y+160,points_to_create=regions)
    exclusion,_ = node(unreal.PCGCreatePointsSettings,'Keep approaches clear',230,y+360,points_to_create=clearance_points)
    difference,_ = node(unreal.PCGDifferenceSettings,'Protect traversal',460,y,
                        density_function=unreal.PCGDifferenceDensityFunction.BINARY,
                        mode=unreal.PCGDifferenceMode.DISCRETE,keep_zero_density_points=False)
    # Perform strict exclusion while the source is explicitly sampled points,
    # before forming a composite spatial intersection with large region boxes.
    edge(sample,difference,bp='Source'); edge(exclusion,difference,bp='Differences')
    intersection,_ = node(unreal.PCGOuterIntersectionSettings,'Concentrate around crash sites',700,y)
    edge(difference,intersection,bp='Primary Source'); edge(region,intersection,bp='Source1')
    transform,_ = node(unreal.PCGTransformPointsSettings,'Scattered industrial salvage',920,y,
                       rotation_min=unreal.Rotator(pitch=-10,yaw=0,roll=-8),rotation_max=unreal.Rotator(pitch=10,yaw=360,roll=8),
                       scale_min=unreal.Vector(lo,lo,lo),scale_max=unreal.Vector(hi,hi,hi),
                       offset_min=unreal.Vector(0,0,-6),offset_max=unreal.Vector(0,0,-2),seed=6140+i)
    edge(intersection,transform)
    spawn,settings = node(unreal.PCGStaticMeshSpawnerSettings,'Instanced '+ident,1140,y,synchronous_load=True)
    settings.set_mesh_selector_type(unreal.PCGMeshSelectorWeighted)
    selector = settings.get_editor_property('mesh_selector_parameters')
    descriptor = unreal.PCGSoftISMComponentDescriptor()
    descriptor.set_editor_property('static_mesh',mesh)
    descriptor.set_editor_property('component_class',unreal.InstancedStaticMeshComponent)
    descriptor.set_editor_property('instance_start_cull_distance',13000)
    descriptor.set_editor_property('instance_end_cull_distance',18000)
    descriptor.set_editor_property('component_tags',[unreal.Name('DF_Phase3_PCGDebris')])
    body = descriptor.get_editor_property('body_instance')
    body.set_editor_property('collision_profile_name',unreal.Name('NoCollision'))
    descriptor.set_editor_property('body_instance',body)
    entry = unreal.PCGMeshSelectorWeightedEntry()
    entry.set_editor_property('descriptor',descriptor)
    selector.set_editor_property('mesh_entries',[entry])
    edge(transform,spawn)
unreal.EditorAssetLibrary.save_loaded_asset(g)
labels = [a.get_actor_label() for a in cells]
for actor in cells:
    actor.set_editor_property('is_spatially_loaded',False)
started = time.monotonic()
state = {'handle':None,'generation_started':False,'last_report':0.}
report_path = ROOT/'Saved/Codex/phase3_pcg_debris_build.json'


def completed(delta):
    try:
        live = {a.get_actor_label():a for a in actors.get_all_level_actors() if 'DF_Phase3_PCG' in [str(t) for t in a.tags]}
        if time.monotonic()-started>300: raise RuntimeError('PCG debris regeneration timeout')
        if any(label not in live for label in labels): return
        current = [live[label] for label in labels]
        comps = [a.get_component_by_class(unreal.PCGComponent) for a in current]
        if not all(unreal.SystemLibrary.is_valid(c) for c in comps): return
        if not state['generation_started']:
            if time.monotonic()-started<1.: return
            for component in comps:
                component.modify()
                component.set_graph(g)
                component.generate(True)
            state['generation_started']=True
            state['generation_since']=time.monotonic()
            return
        # Generate is deferred. Do not confuse the previous completed graph's
        # flags with completion of this newly extended graph.
        if time.monotonic()-state['generation_since']<2.: return
        if time.monotonic()-state['last_report']>5.:
            state['last_report']=time.monotonic()
            report_path.write_text(json.dumps({'status':'generating','loaded_cells':len(current),
                                               'generated_cells':sum(c.get_editor_property('generated') for c in comps),
                                               'generating_cells':sum(c.get_editor_property('generation_in_progress') for c in comps)},indent=2))
        if not all(c.get_editor_property('generated') and not c.get_editor_property('generation_in_progress') for c in comps): return
        count = sum(c.get_instance_count() for a in current for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)
                    if 'DF_Phase3_PCGDebris' in [str(t) for t in c.component_tags])
        if count<12:
            if time.monotonic()-state['generation_since']<15.: return
            raise RuntimeError('Too little actual PCG debris output: '+str(count))
        for old in list(actors.get_all_level_actors()):
            if 'DF_Phase2_Debris' in [str(t) for t in old.tags]: actors.destroy_actor(old)
        for a in current:
            a.modify()
            for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent): c.modify()
            a.set_editor_property('is_spatially_loaded',True)
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_all_dirty_levels()
        report_path.write_text(json.dumps({'status':'complete','native_pcg_debris_instances':count,'cells':len(cells),'interactive':False},indent=2))
        unreal.unregister_slate_post_tick_callback(state['handle'])
        unreal._dustfall_phase3_pcg_debris_handle = None
    except Exception as exc:
        report_path.write_text(json.dumps({'status':'failed','error':str(exc),'traceback':traceback.format_exc()},indent=2))
        unreal.log_error(str(exc))
        unreal.unregister_slate_post_tick_callback(state['handle'])
        unreal._dustfall_phase3_pcg_debris_handle = None
state['handle'] = unreal.register_slate_post_tick_callback(completed)
unreal._dustfall_phase3_pcg_debris_handle = state['handle']
report_path.write_text(json.dumps({'status':'generating','cells':len(cells)}))
