"""Build native Unreal PCG environment graphs and editor-generated streamed cells.

Surface sampling, noise clustering, route exclusion, transform variation and
mesh instancing execute inside PCG. Python only authors graph/assembly assets.
Generation completes asynchronously; inspect Saved/Codex/phase3_pcg_build.json.
"""
import json
import math
import pathlib
import runpy
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
DEST = '/Game/World/Phase3'
TAG = 'DF_Phase3_PCG'
IDS = ['xgmdcay','xgncbgz','xgndbge','xgkmfcy','xgmncdu','xgoqfid','xgjnech','xgjodeb']
# Native PCG surface densities, not baked Python placements. The initial .0007
# per scan left the player's immediate ground sparse. This trial aims for about
# 50-70k small stones/piles across the map with closer Nanite instance culling.
SMALL_DENSITIES = [.009,.006,.004]
SMALL_CULL_DISTANCES_CM = [10000,12000,14000]
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = ROOT/'Saved/Codex/phase3_pcg_build.json'


def write_report(data):
    REPORT.write_text(json.dumps(data,indent=2),encoding='utf-8')


def connect(g,a,b,ap='Out',bp='In'):
    """Validate pin presence AND resulting topology; AddEdge returns To on error."""
    def find(node,side,label):
        available = list(node.get_editor_property(side))
        found = next((p for p in available if str(p.get_editor_property('properties').get_editor_property('label'))==label),None)
        if not found:
            raise RuntimeError('PCG pin missing '+label+'; available '+str([str(p.get_editor_property('properties').get_editor_property('label')) for p in available]))
        return found
    upstream = find(a,'output_pins',ap)
    downstream = find(b,'input_pins',bp)
    g.add_edge(a,unreal.Name(ap),b,unreal.Name(bp))
    if not any(e.get_editor_property('output_pin')==downstream for e in upstream.get_editor_property('edges')):
        raise RuntimeError('PCG edge not created: '+ap+' -> '+bp)


def assembly(ident, index):
    """Normalize scan pivot and conceal unfinished backs with three rotated copies.

    Small scatter is a seated single scan; larger formations overlap the same
    scan around a common centre. Source meshes and material assets are unchanged.
    """
    path = DEST+'/Meshes/SM_PCG_'+ident
    mesh = unreal.load_asset(path) or unreal.load_asset(DEST+'/Meshes/SM_SM_PCG_'+ident)
    if mesh:
        subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        nanite = mesh.get_editor_property('nanite_settings')
        if not nanite.get_editor_property('enabled'):
            nanite.set_editor_property('enabled',True)
            subsystem.set_nanite_settings(mesh,nanite,True)
            LIB.save_loaded_asset(mesh)
        if index>=3 and subsystem.get_convex_collision_count(mesh)==0:
            subsystem.set_convex_decomposition_collisions(mesh,4,16,100000)
            LIB.save_loaded_asset(mesh)
        return mesh
    source = unreal.load_asset('/Game/World/QuixelPhase2/'+ident+'/SM_'+ident)
    if not source:
        raise RuntimeError('Missing imported scan '+ident)
    bounds = source.get_bounds()
    width = max(bounds.box_extent.x,bounds.box_extent.y)*2.
    target_width = 100. if index < 3 else 600. if index < 6 else 1400.
    scale = target_width/max(width,1.)
    copies = 1 if index < 3 else 3
    temporary = []
    try:
        for j in range(copies):
            yaw = j*120.
            r = math.radians(yaw)
            # Opposed fronts wrap a shared volume; the open backs overlap inside.
            x = -scale*(bounds.origin.x*math.cos(r)-bounds.origin.y*math.sin(r))
            y = -scale*(bounds.origin.x*math.sin(r)+bounds.origin.y*math.cos(r))
            z = -scale*(bounds.origin.z-bounds.box_extent.z)
            actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(x,y,z),unreal.Rotator(yaw=yaw))
            temporary.append(actor)
            actor.tags = [unreal.Name('DF_Phase3_MergeTemporary')]
            actor.set_actor_scale3d(unreal.Vector(scale,scale,scale))
            actor.static_mesh_component.set_static_mesh(source)
            actor.static_mesh_component.set_collision_profile_name('NoCollision')
        options = unreal.MergeStaticMeshActorsOptions()
        # Merge utility prepends SM_ to the package basename itself.
        options.set_editor_property('base_package_name',DEST+'/Meshes/PCG_'+ident)
        options.set_editor_property('new_actor_label','P3_TemporaryMerge_'+ident)
        options.set_editor_property('destroy_source_actors',False)
        options.set_editor_property('spawn_merged_actor',True)
        settings = options.get_editor_property('mesh_merging_settings')
        settings.set_editor_property('pivot_type',unreal.MeshMergePivotType.WORLD_ORIGIN)
        settings.set_editor_property('merge_materials',False)
        settings.set_editor_property('merge_physics_data',False)
        settings.set_editor_property('generate_light_map_uv',False)
        settings.set_editor_property('lod_selection_type',unreal.MeshLODSelectionType.SPECIFIC_LOD)
        settings.set_editor_property('specific_lod',0)
        nanite = settings.get_editor_property('nanite_settings')
        nanite.set_editor_property('enabled',True)
        settings.set_editor_property('nanite_settings',nanite)
        options.set_editor_property('mesh_merging_settings',settings)
        result = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).merge_static_mesh_actors(temporary,options)
        merged = result[-1] if isinstance(result,tuple) else result
        if merged and isinstance(merged,unreal.StaticMeshActor):
            temporary.append(merged)
            mesh = merged.static_mesh_component.static_mesh
        else:
            mesh = unreal.load_asset(path)
        if not mesh:
            raise RuntimeError('Could not merge assembly '+ident+': '+str(result))
        if mesh.get_path_name().split('.')[0] != path:
            # The merge utility may add SM_ itself. Keep the actual output path.
            unreal.log('Assembly generated at '+mesh.get_path_name())
        if index >= 3:
            unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_convex_decomposition_collisions(mesh,4,16,100000)
        LIB.save_loaded_asset(mesh)
        return mesh
    finally:
        for actor in temporary:
            if unreal.SystemLibrary.is_valid(actor):
                ACTORS.destroy_actor(actor)


def exclusions(padding, protect_routes=True, protect_landmarks=True):
    report = json.loads((ROOT/'Saved/Codex/landmark_build_report.json').read_text())
    cruiser = (report['Cruiser']['relative_x_cm'],report['Cruiser']['relative_y_cm'])
    routes = runpy.run_path(str(ROOT/'Scripts/phase2_layout.py'))['route_polylines'](cruiser)
    points = []
    def box(x,y,ex,ey,yaw=0):
        p = unreal.PCGPoint()
        p.set_editor_property('transform',unreal.Transform(location=unreal.Vector(x,y,0),rotation=unreal.Rotator(yaw=yaw)))
        p.set_editor_property('bounds_min',unreal.Vector(-ex,-ey,-50000))
        p.set_editor_property('bounds_max',unreal.Vector(ex,ey,50000))
        p.set_editor_property('steepness',1.)
        points.append(p)
    areas=[(0,0,2100)]
    if protect_landmarks:
        areas.extend([(15000,10000,2000),(35000,-25000,1500),(*cruiser,12000)])
    for x,y,r in areas:
        box(x,y,r+padding,r+padding)
    if protect_routes:
        for line in routes.values():
            for a,b in zip(line,line[1:]):
                length = math.hypot(b[0]-a[0],b[1]-a[1])
                # Extend the same traversal guard beyond BOTH endpoints. A
                # width-only rectangle leaves the Euclidean segment end caps
                # unprotected, especially at the terminal landmark approach.
                box((a[0]+b[0])/2,(a[1]+b[1])/2,length/2+550+padding,550+padding,
                    math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])))
    return points


def dust_material():
    """Lit translucent wind sheets, procedural noise, soft edges and depth fade.

    Bounded planes cost less than unbounded overlapping particle volumes. An
    explicit 25m home mask prevents airborne sheets entering the sanctuary even
    when an instance bounds or terrain changes. Global fog remains separate.
    """
    path = DEST+'/Materials/M_WindblownDust'
    mat = unreal.load_asset(path)
    if not mat:
        mat = TOOLS.create_asset('M_WindblownDust',DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('two_sided',True)
    def expr(cls,x,y):
        return mel.create_material_expression(mat,cls,x,y)
    def link(a,b,pin,op=''):
        names = list(mel.get_material_expression_input_names(b))
        if pin=='Input':
            pin='None'
        elif pin=='Position':
            pin='World Position'
        elif pin not in names and len(names)==1:
            pin=names[0]
        outputs = list(mel.get_material_expression_output_names(a))
        if not op and outputs:
            op=outputs[0]
        if not mel.connect_material_expressions(a,op,b,pin):
            raise RuntimeError('Dust material cannot link '+pin)
    uv = expr(unreal.MaterialExpressionTextureCoordinate,-1400,0)
    pan = expr(unreal.MaterialExpressionPanner,-1200,0)
    pan.set_editor_property('speed_x',.16)
    pan.set_editor_property('speed_y',.035)
    link(uv,pan,'Coordinate')
    append = expr(unreal.MaterialExpressionAppendVector,-1000,0)
    link(pan,append,'A')
    zero = expr(unreal.MaterialExpressionConstant,-1200,180); zero.set_editor_property('r',0.)
    link(zero,append,'B')
    stretch = expr(unreal.MaterialExpressionMultiply,-800,0)
    stretch.set_editor_property('const_b',5.)
    link(append,stretch,'A')
    noise = expr(unreal.MaterialExpressionNoise,-600,0)
    noise.set_editor_property('levels',2)
    noise.set_editor_property('output_min',0.)
    noise.set_editor_property('output_max',1.)
    noise.set_editor_property('scale',1.)
    link(stretch,noise,'Position')
    center = expr(unreal.MaterialExpressionSubtract,-1200,400)
    center.set_editor_property('const_b',.5); link(uv,center,'A')
    absolute = expr(unreal.MaterialExpressionAbs,-1000,400); link(center,absolute,'Input')
    twice = expr(unreal.MaterialExpressionMultiply,-800,400)
    twice.set_editor_property('const_b',2.); link(absolute,twice,'A')
    edge = expr(unreal.MaterialExpressionOneMinus,-600,400); link(twice,edge,'Input')
    edge_x = expr(unreal.MaterialExpressionComponentMask,-400,400)
    edge_x.set_editor_property('r',True); edge_x.set_editor_property('g',False)
    edge_y = expr(unreal.MaterialExpressionComponentMask,-400,600)
    edge_y.set_editor_property('r',False); edge_y.set_editor_property('g',True)
    link(edge,edge_x,'Input'); link(edge,edge_y,'Input')
    edge_mul = expr(unreal.MaterialExpressionMultiply,-200,400)
    link(edge_x,edge_mul,'A'); link(edge_y,edge_mul,'B')
    opacity = expr(unreal.MaterialExpressionMultiply,0,0)
    link(noise,opacity,'A'); link(edge_mul,opacity,'B')
    density = expr(unreal.MaterialExpressionMultiply,200,0)
    density.set_editor_property('const_b',.13); link(opacity,density,'A')
    fade = expr(unreal.MaterialExpressionDepthFade,400,0)
    fade.set_editor_property('fade_distance_default',160.)
    link(density,fade,'Opacity')
    # SphereMask fades dust out within the home footprint (XY distance only).
    world = expr(unreal.MaterialExpressionWorldPosition,-600,-500)
    xy = expr(unreal.MaterialExpressionComponentMask,-400,-500)
    xy.set_editor_property('r',True); xy.set_editor_property('g',True)
    xy.set_editor_property('b',False); link(world,xy,'Input')
    dist = expr(unreal.MaterialExpressionDistance,-200,-500)
    link(xy,dist,'A'); link(zero,dist,'B')
    subtract = expr(unreal.MaterialExpressionSubtract,0,-500)
    subtract.set_editor_property('const_b',2300.); link(dist,subtract,'A')
    divide = expr(unreal.MaterialExpressionDivide,200,-500)
    divide.set_editor_property('const_b',500.); link(subtract,divide,'A')
    clamp = expr(unreal.MaterialExpressionClamp,400,-500); link(divide,clamp,'Input')
    final = expr(unreal.MaterialExpressionMultiply,600,0)
    link(fade,final,'A'); link(clamp,final,'B')
    color = expr(unreal.MaterialExpressionConstant3Vector,500,300)
    color.set_editor_property('constant',unreal.LinearColor(.40,.25,.13,1.))
    mel.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(final,'',unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    LIB.save_loaded_asset(mat)
    return mat


def graph(meshes, dust):
    path = DEST+'/PCG/PCG_DustfallEnvironment'
    g = unreal.load_asset(path)
    if not g:
        g = TOOLS.create_asset('PCG_DustfallEnvironment',DEST+'/PCG',unreal.PCGGraph,unreal.PCGGraphFactory())
    for n in list(g.get_editor_property('nodes')):
        g.remove_node(n)
    g.set_editor_property('description',unreal.Text('Seeded terrain-aware rock formations. Surface Sampler -> spatial density -> route exclusion -> varied transforms -> Nanite ISM.'))
    g.set_editor_property('auto_refresh_on_quality_settings_changed',False)
    g.set_editor_property('auto_refresh_on_render_state_refresh',False)
    inp = g.get_input_node()
    def node(cls,title,x,y,**props):
        n,s = g.add_node_of_type(cls)
        n.set_editor_property('node_title',unreal.Name(title))
        n.set_node_position(x,y)
        for k,v in props.items():
            s.set_editor_property(k,v)
        return n,s
    def edge(a,b,ap='Out',bp='In'):
        connect(g,a,b,ap,bp)
    landscape,_ = node(unreal.PCGGetLandscapeSettings,'Landscape source',-300,0,unbounded=False)
    def spawner(title,x,y,mesh,material=None,blocking=False,cull=22000):
        spawn,settings = node(unreal.PCGStaticMeshSpawnerSettings,title,x,y,synchronous_load=True)
        settings.set_mesh_selector_type(unreal.PCGMeshSelectorWeighted)
        selector = settings.get_editor_property('mesh_selector_parameters')
        desc = unreal.PCGSoftISMComponentDescriptor()
        desc.set_editor_property('static_mesh',mesh)
        desc.set_editor_property('component_class',unreal.InstancedStaticMeshComponent)
        desc.set_editor_property('instance_start_cull_distance',int(cull*.72))
        desc.set_editor_property('instance_end_cull_distance',cull)
        desc.set_editor_property('component_tags',[unreal.Name(TAG)])
        if material:
            desc.set_editor_property('override_materials',[material])
            desc.set_editor_property('cast_shadow',False)
            desc.set_editor_property('affect_distance_field_lighting',False)
        body = desc.get_editor_property('body_instance')
        body.set_editor_property('collision_profile_name',unreal.Name('BlockAll' if blocking else 'NoCollision'))
        desc.set_editor_property('body_instance',body)
        e = unreal.PCGMeshSelectorWeightedEntry()
        e.set_editor_property('descriptor',desc)
        e.set_editor_property('weight',1)
        selector.set_editor_property('mesh_entries',[e])
        return spawn
    for i,mesh in enumerate(meshes):
        y = i*600
        density = SMALL_DENSITIES[i] if i<3 else .000065 if i<6 else .000006
        maxscale = 1.5 if i<3 else 1.75
        width = max(mesh.get_bounds().box_extent.x,mesh.get_bounds().box_extent.y)*2
        radius = width*maxscale*.75
        sample,_ = node(unreal.PCGSurfaceSamplerSettings,'Terrain '+IDS[i],0,y,
                        points_per_squared_meter=density,point_extents=unreal.Vector(radius,radius,100),
                        looseness=1.,seed=2042+i*23)
        edge(landscape,sample,'Out','Surface')
        slope,_ = node(unreal.PCGNormalToDensitySettings,'Terrain slope',130,y+100,
                       normal=unreal.Vector(0,0,1),strength=1.)
        edge(sample,slope)
        stable,_ = node(unreal.PCGDensityFilterSettings,'Stable ground',240,y+100,lower_bound=.72,upper_bound=1.)
        edge(slope,stable)
        noise,_ = node(unreal.PCGSpatialNoiseSettings,'Geological clusters',220,y,
                       transform=unreal.Transform(scale=unreal.Vector(.00015,.00015,.00015)),
                       iterations=3,brightness=.15,contrast=1.4,seed=2042)
        edge(stable,noise)
        filt,_ = node(unreal.PCGDensityFilterSettings,'Wind-scoured gaps',440,y,lower_bound=.48,upper_bound=1.)
        edge(noise,filt)
        exc,_ = node(unreal.PCGCreatePointsSettings,'Routes and landmark footprints',430,y+200,
                    points_to_create=exclusions(radius))
        diff,_ = node(unreal.PCGDifferenceSettings,'Protect traversal',660,y,
                       density_function=unreal.PCGDifferenceDensityFunction.BINARY,
                       mode=unreal.PCGDifferenceMode.DISCRETE,keep_zero_density_points=False)
        edge(filt,diff,bp='Source'); edge(exc,diff,bp='Differences')
        transform,_ = node(unreal.PCGTransformPointsSettings,'Size height and orientation',880,y,
                           rotation_min=unreal.Rotator(pitch=-4,yaw=0,roll=-3),
                           rotation_max=unreal.Rotator(pitch=4,yaw=360,roll=3),
                           scale_min=unreal.Vector(.35 if i<3 else .55,.35 if i<3 else .55,.35 if i<3 else .55),
                           scale_max=unreal.Vector(maxscale,maxscale,maxscale),
                           offset_min=unreal.Vector(0,0,-15 if i<3 else -70),
                           offset_max=unreal.Vector(0,0,-4 if i<3 else -25),seed=2042+i*19)
        edge(diff,transform)
        spawn = spawner('Nanite '+IDS[i],1100,y,mesh,blocking=i>=3,cull=SMALL_CULL_DISTANCES_CM[i] if i<3 else 65000)
        edge(transform,spawn)
    # Airborne dust regions use PCG surface distribution too. Lit material pans
    # procedural turbulence continuously; the bounded sheets fade against depth.
    plane = unreal.load_asset('/Engine/BasicShapes/Plane')
    for j in range(2):
        y = (len(meshes)+j)*600
        sample,_ = node(unreal.PCGSurfaceSamplerSettings,'Dust regions '+str(j),0,y,
                        points_per_squared_meter=.00007,point_extents=unreal.Vector(1400,1400,100),
                        looseness=1.,seed=5130+j)
        edge(landscape,sample,'Out','Surface')
        exc,_ = node(unreal.PCGCreatePointsSettings,'Dust exterior clearance',240,y+180,
                    points_to_create=exclusions(3000,False))
        diff,_ = node(unreal.PCGDifferenceSettings,'Keep dust outside habitat',460,y,
                       density_function=unreal.PCGDifferenceDensityFunction.BINARY,
                       mode=unreal.PCGDifferenceMode.DISCRETE,keep_zero_density_points=False)
        edge(sample,diff,bp='Source'); edge(exc,diff,bp='Differences')
        trans,_ = node(unreal.PCGTransformPointsSettings,'Wind-driven dust sheets',700,y,
                       offset_min=unreal.Vector(0,0,75 if j==0 else 260),
                       offset_max=unreal.Vector(0,0,160 if j==0 else 500),
                       rotation_min=unreal.Rotator(pitch=4 if j==0 else 78,yaw=45,roll=-5),
                       rotation_max=unreal.Rotator(pitch=12 if j==0 else 88,yaw=80,roll=5),
                       scale_min=unreal.Vector(22,6 if j==0 else 4,1),
                       scale_max=unreal.Vector(48,12 if j==0 else 8,1),uniform_scale=False,seed=5130+j)
        edge(diff,trans)
        spawn = spawner('Soft airborne dust',940,y,plane,material=dust,cull=13000)
        edge(trans,spawn)
    LIB.save_loaded_asset(g)
    return g


def cell_blueprint(g):
    path = DEST+'/Blueprints/BP_DustfallPCGCell'
    bp = unreal.load_asset(path)
    if not bp:
        f = unreal.BlueprintFactory(); f.set_editor_property('parent_class',unreal.Actor)
        bp = TOOLS.create_asset('BP_DustfallPCGCell',DEST+'/Blueprints',None,f)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for name,cls in [('GenerationBounds',unreal.BoxComponent),('PCG',unreal.PCGComponent)]:
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
        entry = next((lib.get_associated_object(lib.get_data(h)) for h in handles if str(lib.get_variable_name(lib.get_data(h)))==name),None)
        if not entry:
            h,reason = sub.add_new_subobject(unreal.AddNewSubobjectParams(handles[0],cls,bp))
            if not reason.is_empty(): raise RuntimeError(str(reason))
            sub.rename_subobject(h,unreal.Text(name))
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            handles = sub.k2_gather_subobject_data_for_blueprint(bp)
            entry = next(lib.get_associated_object(lib.get_data(h)) for h in handles if str(lib.get_variable_name(lib.get_data(h)))==name)
        if name=='GenerationBounds':
            entry.set_editor_property('box_extent',unreal.Vector(12490,12490,30000))
            entry.set_collision_profile_name('NoCollision')
            entry.set_editor_property('hidden_in_game',True)
        else:
            entry.set_editor_property('generation_trigger',unreal.PCGComponentGenerationTrigger.GENERATE_ON_DEMAND)
            entry.set_editor_property('is_component_partitioned',False)
            entry.set_editor_property('regenerate_in_editor',False)
            entry.set_graph(g)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    # Blueprint reconstruction resets component instances to their templates.
    # Put the graph on the compiled template, not solely on placed instances.
    handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    template = next(lib.get_associated_object(lib.get_data(h)) for h in handles if str(lib.get_variable_name(lib.get_data(h)))=='PCG')
    template.set_graph(g)
    LIB.save_loaded_asset(bp)
    return bp


def main():
    runpy.run_path(str(ROOT/'Scripts/load_phase3_authoring_cells.py'),run_name='__main__')
    previous_handle = getattr(unreal,'_dustfall_phase3_pcg_handle',None)
    if previous_handle is not None:
        unreal.unregister_slate_post_tick_callback(previous_handle)
        unreal._dustfall_phase3_pcg_handle = None
    world = unreal.EditorLevelLibrary.get_editor_world()
    if '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name():
        raise RuntimeError('Open foundation map first')
    write_report({'status':'building assemblies'})
    meshes = [assembly(ident,i) for i,ident in enumerate(IDS)]
    dust = dust_material()
    g = graph(meshes,dust)
    bp = cell_blueprint(g)
    previous = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
    for a in previous:
        ACTORS.destroy_actor(a)
    cells = []
    for ix in range(-4,4):
        for iy in range(-4,4):
            actor = ACTORS.spawn_actor_from_class(bp.generated_class(),unreal.Vector(ix*25000+12500,iy*25000+12500,0))
            actor.set_actor_label('P3_PCGCell_%d_%d'%(ix,iy))
            actor.tags = [unreal.Name(TAG)]
            actor.set_folder_path('DUSTFALL/Phase3_PCG')
            # Keep authoring owners loaded until all asynchronous PCG tasks have
            # completed; restore spatial streaming only after validation.
            actor.set_editor_property('is_spatially_loaded',False)
            pcg = actor.get_component_by_class(unreal.PCGComponent)
            pcg.set_editor_property('seed',2042)
            pcg.set_graph(g)
            cells.append((actor,pcg))
    started = time.monotonic()
    state = {'callback':None,'generation_started':False,'last_report':0.}
    cell_labels = [a.get_actor_label() for a,c in cells]
    def completed(delta):
        try:
            if time.monotonic()-started>300:
                raise RuntimeError('PCG generation timed out')
            # Saving/reinstancing can invalidate component Python wrappers.
            # Resolve actors/components afresh each tick rather than retaining
            # references to the first generated UObject instance.
            live = {a.get_actor_label():a for a in ACTORS.get_all_level_actors()
                    if TAG in [str(t) for t in a.tags]}
            if any(label not in live for label in cell_labels):
                return
            current = [(live[label],live[label].get_component_by_class(unreal.PCGComponent)) for label in cell_labels]
            if not state['generation_started']:
                # Let spawn/reconstruction finish before assigning instances.
                if time.monotonic()-started<1.: return
                for actor,component in current:
                    component.modify()
                    component.set_graph(g)
                    component.generate(True)
                state['generation_started']=True
                return
            if time.monotonic()-state['last_report']>5.:
                state['last_report']=time.monotonic()
                write_report({'status':'generating','loaded_cells':len(current),
                              'generated_cells':sum(1 for a,c in current if c.get_editor_property('generated')),
                              'generating_cells':sum(1 for a,c in current if c.get_editor_property('generation_in_progress')),
                              'graph_assigned_cells':sum(1 for a,c in current if c.get_graph() is not None)})
            if not all(unreal.SystemLibrary.is_valid(c) and c.get_editor_property('generated') and not c.get_editor_property('generation_in_progress') for a,c in current):
                return
            counts = {a.get_actor_label():sum(c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)) for a,p in current}
            count = sum(counts.values())
            rock_paths = {m.get_path_name() for m in meshes}
            rock_count = sum(c.get_instance_count() for a,p in current for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)
                             if c.static_mesh and c.static_mesh.get_path_name() in rock_paths)
            nonempty = sum(1 for n in counts.values() if n>0)
            if rock_count<500 or nonempty<48:
                raise RuntimeError('PCG output unexpectedly sparse: %s rocks / %s nonempty cells'%(rock_count,nonempty))
            # Remove the old scatter only after actual native PCG output exists.
            for old in list(ACTORS.get_all_level_actors()):
                if 'DF_Phase2_RockCell' in [str(t) for t in old.tags]:
                    ACTORS.destroy_actor(old)
            for a,p in current:
                a.modify(); p.modify()
                for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent): c.modify()
                a.set_editor_property('is_spatially_loaded',True)
            unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_all_dirty_levels()
            write_report({'status':'complete','seed':2042,'cells':len(current),'instances':count,
                          'instances_per_cell':counts,
                          'rock_instances':rock_count,'dust_sheet_instances':count-rock_count,
                          'nonempty_cells':nonempty,
                          'graph':g.get_path_name(),'meshes':[m.get_path_name() for m in meshes],
                          'elapsed_seconds':time.monotonic()-started,'visual_validation_required':True})
            unreal.unregister_slate_post_tick_callback(state['callback'])
            unreal._dustfall_phase3_pcg_handle = None
        except Exception as exc:
            write_report({'status':'failed','error':str(exc),'traceback':traceback.format_exc()})
            unreal.log_error(str(exc))
            unreal.unregister_slate_post_tick_callback(state['callback'])
            unreal._dustfall_phase3_pcg_handle = None
    state['callback'] = unreal.register_slate_post_tick_callback(completed)
    unreal._dustfall_phase3_pcg_handle = state['callback']
    write_report({'status':'generating','cells':len(cells),'seed':2042})


if __name__=='__main__':
    main()
