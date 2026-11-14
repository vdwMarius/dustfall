"""Sole-writer editor authoring after terrain v2. Never invoke from runtime.

Wait for Saved/Codex/phase5_dressing_build.json status complete (queue return is
not completion). Rules live in Data/world_dressing_phase5.json, PCG creates
and instances baked, landscape-sampled points. All 64 cells rebuild because
the scatter rules changed. Existing dust/debris branches are retained.
"""
import collections
import hashlib
import json
import math
import pathlib
import random
import runpy
import struct
import time
import traceback

DEST='/Game/World/Phase5'
TAG='DF_Phase5_Dressing'


def tuning_asset(unreal, rules, author=False):
    """Designer-editable data asset; JSON provides initial/new defaults only."""
    lib=unreal.EditorAssetLibrary; bel=unreal.BlueprintEditorLibrary
    path='/Game/Data/DA_WorldDressing_Phase5'; bp_path='/Game/Data/BP_WorldDressingData_Phase5'
    def leaves(value,parts=()):
        if isinstance(value,dict):
            for k,v in value.items():yield from leaves(v,parts+(k,))
        elif isinstance(value,list):
            for k,v in enumerate(value):yield from leaves(v,parts+(k,))
        else:yield parts,value
    flat=list(leaves(rules)); data=unreal.load_asset(path)
    if not author and not data:raise RuntimeError('World dressing tuning asset has not been authored')
    if author:
        bp=unreal.load_asset(bp_path)
        if not bp:
            factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.PrimaryDataAsset)
            bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset(bp_path.rsplit('/',1)[1],'/Game/Data',None,factory)
        previous=set(map(str,bel.list_member_variable_names(bp,False)));added=False
        for parts,value in flat:
            name='_'.join(map(str,parts))
            if name not in previous:
                if not bel.add_member_variable(bp,name,bel.get_basic_type_by_name('int' if isinstance(value,int) else 'real')):
                    raise RuntimeError('Cannot create dressing tuning field '+name)
                bel.set_blueprint_variable_instance_editable(bp,name,True);added=True
        if added:
            bel.compile_blueprint(bp)
            data=unreal.load_asset(path)
        if not data:
            factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',bp.generated_class())
            data=unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_WorldDressing_Phase5','/Game/Data',None,factory)
            previous=set()
        for parts,value in flat:
            name='_'.join(map(str,parts))
            if name not in previous:data.set_editor_property(name,value)
        lib.save_loaded_asset(bp);lib.save_loaded_asset(data)
    for parts,default in flat:
        value=data.get_editor_property('_'.join(map(str,parts)));target=rules
        for part in parts[:-1]:target=target[part]
        target[parts[-1]]=int(value) if isinstance(default,int) else float(value)
    return rules


def load_inputs(root, author=False):
    import unreal
    pure=runpy.run_path(str(root/'Scripts/phase5_dressing_rules.py'))
    rules=json.loads((root/'Scripts/Data/world_dressing_phase5.json').read_text())
    rules=tuning_asset(unreal,rules,author)
    if rules['schema_version']!=1 or rules['cell_size_cm']!=25000 or not 0<rules['max_rock_instances']<=82434:
        raise RuntimeError('Invalid dressing schema, existing cell grid or +15 percent budget')
    for kind in ('flats','slopes','talus','cliffs'):
        rule=rules[kind]
        if rule['step_cm']<=0 or not 0<=rule['keep_probability']<=1 or not 0<=rule['slope_degrees'][0]<rule['slope_degrees'][1]<=90:
            raise RuntimeError('Invalid scatter rules '+kind)
    if rules['spires']['tiers']<1 or not 0<=rules['spires']['overlap_fraction']<1:raise RuntimeError('Invalid spire tiers')
    terrain=json.loads((root/'Docs/Phase5_TerrainResults.json').read_text())
    if terrain['status']!='complete': raise RuntimeError('Terrain v2 must complete first')
    features=json.loads((root/'Saved/Codex/terrain_features_v2_resolved.json').read_text())
    source=root/'Scripts/Data/terrain_features_v2.json'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=terrain['feature_sha256']:
        raise RuntimeError('Terrain source changed since last terrain build')
    native=terrain['native']; folder=root/'Saved/Codex/TerrainMasks'
    paths=json.loads((folder/'polylines.json').read_text())['paths']
    return pure, pure['Inputs'](rules,features,paths,native['mask_world_bounds_cm'],native['mask_size'],
                               (folder/'paths.raw').read_bytes(),(folder/'cliffs.raw').read_bytes())


def path_material(unreal, root, inputs):
    """Duplicate the existing automatic material, wrap its three output chains.

    Original sand/gravel/steep-rock texture and normal networks are preserved.
    Native raw rows are flipped only for TGA's bottom-left origin. UV maps
    extrema to texel centres, avoiding the half-texel shift at world bounds.
    """
    lib=unreal.EditorAssetLibrary; mel=unreal.MaterialEditingLibrary
    source='/Game/World/Materials/M_Wasteland_Phase2'
    signature=hashlib.sha256(json.dumps([inputs.bounds,inputs.rules['paths']],sort_keys=True).encode()).hexdigest()[:12]
    path=DEST+'/Materials/M_Wasteland_Tracks_'+signature
    mat=unreal.load_asset(path)
    if not mat: mat=lib.duplicate_asset(source,path)
    if not mat: raise RuntimeError('Missing Phase2 automatic landscape material')
    props=[unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_ROUGHNESS,unreal.MaterialProperty.MP_NORMAL]
    mark=lib.get_metadata_tag(mat,'DF_P5_PathConfigured')
    original=[]
    for prop in props if not mark else []:
        node=mel.get_material_property_input_node(mat,prop)
        output=mel.get_material_property_input_node_output_name(mat,prop)
        if not node: raise RuntimeError('Landscape material output missing: '+str(prop))
        original.append((node,output))
    size=inputs.size
    tga=root/'Saved/Codex/TerrainMasks/paths_phase5.tga'
    header=struct.pack('<BBBHHBHHHHBB',0,0,3,0,0,0,0,0,size,size,8,0)
    tga.write_bytes(header+b''.join(inputs.path_mask[y*size:(y+1)*size] for y in range(size-1,-1,-1)))
    task=unreal.AssetImportTask(); task.filename=str(tga); task.destination_path=DEST+'/Materials'
    task.destination_name='T_TerrainPaths'; task.automated=True; task.replace_existing=True; task.save=False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=unreal.load_asset(DEST+'/Materials/T_TerrainPaths')
    if not texture: raise RuntimeError('Could not import track mask')
    texture.set_editor_property('srgb',False)
    texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_GRAYSCALE)
    texture.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
    lib.save_loaded_asset(texture)
    if mark:
        bounds=json.loads(lib.get_metadata_tag(mat,'DF_P5_PathBounds'))
        if bounds!=inputs.bounds:
            raise RuntimeError('Track material world bounds changed: review UV mapping before reuse')
    else:
        def expr(cls):
            e=mel.create_material_expression(mat,cls,-1800,1600)
            e.set_editor_property('desc','DF_P5_PathMask'); return e
        def link(a,b,pin,out=''):
            if not mel.connect_material_expressions(a,out,b,pin): raise RuntimeError('Path material pin '+pin)
        world=expr(unreal.MaterialExpressionWorldPosition)
        xy=expr(unreal.MaterialExpressionComponentMask)
        for k,v in dict(r=True,g=True,b=False,a=False).items(): xy.set_editor_property(k,v)
        link(world,xy,'None')
        origin=expr(unreal.MaterialExpressionConstant2Vector)
        origin.set_editor_property('r',inputs.bounds[0]); origin.set_editor_property('g',inputs.bounds[1])
        sub=expr(unreal.MaterialExpressionSubtract); link(xy,sub,'A'); link(origin,sub,'B')
        factor=expr(unreal.MaterialExpressionConstant2Vector)
        factor.set_editor_property('r',(size-1)/size/(inputs.bounds[2]-inputs.bounds[0]))
        factor.set_editor_property('g',(size-1)/size/(inputs.bounds[3]-inputs.bounds[1]))
        mul=expr(unreal.MaterialExpressionMultiply); link(sub,mul,'A'); link(factor,mul,'B')
        offset=expr(unreal.MaterialExpressionAdd); offset.set_editor_property('const_b',.5/size); link(mul,offset,'A')
        sample=expr(unreal.MaterialExpressionTextureSample); sample.set_editor_property('texture',texture)
        sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        link(offset,sample,'UVs')
        for index,((old,out),prop) in enumerate(zip(original,props)):
            lerp=expr(unreal.MaterialExpressionLinearInterpolate); lerp.set_editor_property('desc','DF_P5_PathOutput')
            link(old,lerp,'A',out); link(sample,lerp,'Alpha','R')
            if index==0:
                target=expr(unreal.MaterialExpressionMultiply); link(old,target,'A',out)
                target.set_editor_property('const_b',inputs.rules['paths']['darken'])
            elif index==1:
                target=expr(unreal.MaterialExpressionConstant); target.set_editor_property('r',inputs.rules['paths']['roughness'])
            else:
                target=expr(unreal.MaterialExpressionLinearInterpolate); link(old,target,'A',out)
                flat=expr(unreal.MaterialExpressionConstant3Vector); flat.set_editor_property('constant',unreal.LinearColor(0,0,1,1))
                link(flat,target,'B'); target.set_editor_property('const_alpha',inputs.rules['paths']['normal_flatten'])
            link(target,lerp,'B'); mel.connect_material_property(lerp,'',prop)
        lib.set_metadata_tag(mat,'DF_P5_PathConfigured','1')
        lib.set_metadata_tag(mat,'DF_P5_PathBounds',json.dumps(inputs.bounds))
        lib.set_metadata_tag(mat,'DF_P5_PathRules',json.dumps(inputs.rules['paths'],sort_keys=True))
    if lib.get_metadata_tag(mat,'DF_P5_PathRules')!=json.dumps(inputs.rules['paths'],sort_keys=True):
        raise RuntimeError('Path look rules changed; update task-owned material wrapper before rebake')
    mel.recompile_material(mat); lib.save_loaded_asset(mat)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actors.get_all_level_actors():
        if isinstance(actor,unreal.LandscapeProxy):
            current=actor.get_editor_property('landscape_material')
            if current and current.get_path_name().split('.')[0]!=source and not current.get_path_name().startswith(DEST+'/Materials/M_Wasteland_Tracks_'):
                raise RuntimeError('Unexpected landscape material; preserve it and review wrapper')
            actor.modify(); actor.set_editor_property('landscape_material',mat)
    return mat.get_path_name()


def main():
    import unreal
    root=pathlib.Path(unreal.Paths.project_dir()); report_file=root/'Saved/Codex/phase5_dressing_build.json'
    report_file.parent.mkdir(parents=True,exist_ok=True)
    report=dict(status='starting',visual_validation_required=True,heavy_tests_run=False)
    def write(): report_file.write_text(json.dumps(report,indent=2),encoding='utf-8')
    write()
    def dirty():
        s=unreal.EditorLoadingAndSavingUtils
        return list(s.get_dirty_map_packages())+list(s.get_dirty_content_packages())
    old_handle=getattr(unreal,'_dustfall_phase5_dressing_handle',None)
    if old_handle is not None: raise RuntimeError('Previous dressing callback still active; wait for its report')
    world=unreal.EditorLevelLibrary.get_editor_world()
    if unreal.EditorLevelLibrary.get_game_world() or '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name():
        raise RuntimeError('Open foundation and stop PIE')
    # Refuse pre-existing dirty packages that this task could modify. Never save
    # unrelated user packages through the Phase3 global save-all helper.
    before={p.get_path_name() for p in dirty()}
    if any('L_Dustfall_Foundation' in p or p.startswith(DEST) or 'WorldDressing' in p for p in before):
        raise RuntimeError('Task-owned map/assets already dirty; resolve those changes before build')
    pure,inputs=load_inputs(root,author=True); rules=inputs.rules
    report['effective_rules']=rules
    report['rules_sha256']=hashlib.sha256(json.dumps(rules,sort_keys=True).encode()).hexdigest()
    report['mask_sha256']={name:hashlib.sha256(value).hexdigest() for name,value in [('paths',inputs.path_mask),('cliffs',inputs.cliff_mask)]}
    runpy.run_path(str(root/'Scripts/load_phase3_authoring_cells.py'))
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors=list(actors.get_all_level_actors())
    cells={a.get_actor_label():a for a in all_actors if 'DF_Phase3_PCG' in map(str,a.tags)}
    if len(cells)!=64: raise RuntimeError('Load all 64 original PCG owners first')
    core=runpy.run_path(str(root/'Scripts/build_phase3_pcg.py'))
    meshsub=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    lib=unreal.EditorAssetLibrary
    # Source assemblies are read-only. Clone large meshes before adding convex
    # hulls so collision improvement cannot alter historical Phase3 content.
    meshes=[]
    for i,ident in enumerate(core['IDS']):
        src=unreal.load_asset('/Game/World/Phase3/Meshes/SM_PCG_'+ident) or unreal.load_asset('/Game/World/Phase3/Meshes/SM_SM_PCG_'+ident)
        if not src: raise RuntimeError('Missing existing licensed assembly '+ident)
        path=DEST+'/Meshes/SM_Dressing_'+ident
        mesh=unreal.load_asset(path) or lib.duplicate_asset(src.get_path_name().split('.')[0],path)
        if not mesh: raise RuntimeError('Could not duplicate assembly '+ident)
        nanite=mesh.get_editor_property('nanite_settings'); nanite.set_editor_property('enabled',True)
        meshsub.set_nanite_settings(mesh,nanite,True)
        if i>=3 and meshsub.get_convex_collision_count(mesh)==0:
            meshsub.set_convex_decomposition_collisions(mesh,rules['collision_hulls'],rules['collision_vertices'],rules['collision_precision'])
            if meshsub.get_convex_collision_count(mesh)==0: raise RuntimeError('Assembly missing convex collision '+ident)
        lib.save_loaded_asset(mesh); meshes.append(mesh)
    stakepath=DEST+'/Meshes/SM_OldRouteStake'
    stake=unreal.load_asset(stakepath) or lib.duplicate_asset('/Engine/BasicShapes/Cube',stakepath)
    nanite=stake.get_editor_property('nanite_settings'); nanite.set_editor_property('enabled',True)
    meshsub.set_nanite_settings(stake,nanite,True)
    material=unreal.load_asset('/Game/Habitat/Blockout/M_Hab_Blockout_DustyMetal')
    if not material: raise RuntimeError('Missing existing route stake material')
    stake.set_material(0,material); lib.save_loaded_asset(stake); meshes.append(stake)
    bounds=[]
    for mesh in meshes:
        b=mesh.get_bounds(); bounds.append(([b.origin.x,b.origin.y,b.origin.z],[b.box_extent.x,b.box_extent.y,b.box_extent.z]))
    ignore=[a for a in all_actors if not isinstance(a,unreal.LandscapeProxy)]
    breaker=unreal.get_default_object(unreal.GameplayStatics.static_class())
    def ground(x,y):
        a,b,c,d=inputs.bounds
        x=max(a+1,min(c-1,x)); y=max(b+1,min(d-1,y))
        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
        if hit is None: raise RuntimeError('Loaded landscape collision missing at '+str((x,y)))
        parts=breaker.call_method('BreakHitResult',(hit,))
        if not parts[0]: raise RuntimeError('Loaded landscape collision missing at '+str((x,y)))
        return parts[5].z,parts[7]
    plans=collections.defaultdict(list); counts=collections.Counter(); spire_positions=[]
    def add(kind,x,y,z,index,scale,yaw,pitch=0,roll=0,embed=0):
        radius,low=pure['footprint'](bounds[index],scale,pitch,roll)
        if not inputs.clear(x,y,radius): return False
        a,b,c,d=inputs.bounds
        size=rules['cell_size_cm']; ix=math.floor(x/size); iy=math.floor(y/size)
        label='P3_PCGCell_%d_%d'%(ix,iy)
        # Landscape mask includes an 8m border outside the original PCG grid.
        # Keep the existing owners/grid rather than creating outlying cells.
        if label not in cells: return False
        plans[label].append(dict(kind=kind,mesh=index,xyz=[x,y,z-low-embed],scale=scale,rotation=[pitch,yaw,roll]))
        counts[kind]+=1; return True
    def process(candidate):
        kind,x,y,seed,_=candidate; rule=rules[kind]; rng=random.Random(seed)
        if not inputs.clear(x,y,0): return
        z,normal=ground(x,y); slope=math.degrees(math.acos(max(-1,min(1,normal.z))))
        if 'slope_degrees' in rule and not rule['slope_degrees'][0]<=slope<=rule['slope_degrees'][1]: return
        if 'height_cm' in rule and not rule['height_cm'][0]<=z<=rule['height_cm'][1]: return
        yaw=rng.uniform(0,360); pitch=roll=0; embed=0
        if kind=='stakes':
            index=8; scale=[v/100 for v in rule['size_cm']]; roll=rng.uniform(-rule['lean_degrees'],rule['lean_degrees'])
        else:
            index=rng.randrange(3) if kind in ('flats','edges') else rng.randrange(3,8)
            width=max(bounds[index][1][:2])*2; height=bounds[index][1][2]*2
            desired=rng.uniform(*rule['size_cm'])
            if kind=='talus':
                distance=inputs.wall(x,y)[0]
                desired=rule['size_cm'][1]+(rule['size_cm'][0]-rule['size_cm'][1])*min(1,distance/rule['wall_search_cm'])
            if kind=='slopes':
                # Convex upper shoulders: uphill rise dwindles while the ground
                # still drops downhill. This distinguishes tops from steep feet.
                downhill=ground(x+normal.x*rule['step_cm'],y+normal.y*rule['step_cm'])[0]
                uphill=ground(x-normal.x*rule['step_cm'],y-normal.y*rule['step_cm'])[0]
                crest=max(0,min(1,1-max(0,uphill-z)/max(.01,z-downhill)))
                lo,hi=rule['crest_probability']
                if rng.random()>lo+(hi-lo)*crest: return
            scale=[desired/width]*3
            if kind=='rims': scale[2]*=rng.uniform(*rule['height_ratio'])
            if kind=='cliffs':
                if not inputs.walls: return
                distance,tangent,cross=inputs.wall(x,y)
                if not 0<=cross<=1:return
                yaw=math.degrees(math.atan2(tangent[1],tangent[0]))+rng.uniform(-rule['yaw_jitter_degrees'],rule['yaw_jitter_degrees'])
                scale=[desired/(bounds[index][1][0]*2),rng.uniform(*rule['depth_cm'])/(bounds[index][1][1]*2),rng.uniform(*rule['height_size_cm'])/height]
                roll=rng.uniform(-rule['roll_degrees'],rule['roll_degrees'])
                # Seat tile down into the sampled wall; terrain fills its back.
                embed=height*scale[2]*rule['embed_fraction']
        add(kind,x,y,z,index,scale,yaw,pitch,roll,embed)
    def spires():
        rng=random.Random(rules['seed']); r=rules['spires']; fields={}
        for field in inputs.features['features']:
            if field['type']!='spire_base': continue
            cx,cy,rx,ry,_,_=field['parameters']; desc=field['dressing']; made=0
            for attempt in range(r['placement_attempts']):
                if made==desc['count']: break
                angle=rng.uniform(0,math.tau); radial=math.sqrt(rng.random())
                x,y=cx+math.cos(angle)*radial*rx,cy+math.sin(angle)*radial*ry
                height=rng.uniform(*desc['height_cm']); lean=0 if field['id']=='needles_north' else rng.uniform(*r['lean_degrees'])
                slender=r['pillar_slenderness'] if field['id']=='needles_north' else r['sentinel_slenderness'] if field['id']=='sentinels_east' else r['slenderness']
                width=height*rng.uniform(*slender); yaw=rng.uniform(0,360)
                radius=width+height*math.sin(math.radians(lean))
                if not inputs.clear(x,y,radius) or any(math.hypot(x-px,y-py)<r['separation_factor']*(radius+pr) for px,py,pr in spire_positions): continue
                z,_=ground(x,y); tierheight=(height+r['embed_cm'])/(r['tiers']-(r['tiers']-1)*r['overlap_fraction'])
                pieces=[]
                for tier in range(r['tiers']):
                    index=rng.randrange(3,8); taper=1-tier/r['tiers']*r['taper_fraction']
                    scale=[width*taper/(bounds[index][1][0]*2),width*taper/(bounds[index][1][1]*2),tierheight/(bounds[index][1][2]*2)]
                    lift=tier*tierheight*(1-r['overlap_fraction']); drift=lift*math.tan(math.radians(lean))
                    px=x+math.cos(math.radians(yaw))*drift; py=y+math.sin(math.radians(yaw))*drift
                    radius_piece,low=pure['footprint'](bounds[index],scale,lean,0)
                    if not inputs.clear(px,py,radius_piece): break
                    pieces.append((px,py,z+lift,index,scale,yaw+rng.uniform(-r['tier_yaw_degrees'],r['tier_yaw_degrees']),lean,0,r['embed_cm']))
                if len(pieces)!=r['tiers']: continue
                for piece in pieces:
                    if not add('spires',*piece): raise RuntimeError('Spire placement clearance changed')
                spire_positions.append((x,y,radius)); made+=1
            if made!=desc['count']: raise RuntimeError('Cannot seat all spires in '+field['id']+': '+str(made))
            fields[field['id']]=dict(spires=made,assemblies=made*r['tiers'],height_cm=desc['height_cm'])
        report['spire_fields']=fields
    source=unreal.load_asset('/Game/World/Phase3/PCG/PCG_DustfallEnvironment')
    if not source: raise RuntimeError('Missing existing PCG graph')
    # All graph edits target task-owned duplicates; Phase3 graph stays intact.
    def graph(label):
        path=DEST+'/PCG/PCG_Dressing_'+label.removeprefix('P3_PCGCell_').replace('-','n')
        g=unreal.load_asset(path) or lib.duplicate_asset(source.get_path_name().split('.')[0],path)
        # Retain only ancestors of dust/debris spawners. This prunes prior baked
        # dressing branches on rerun as well as all original uniform rocks.
        nodes=list(g.get_editor_property('nodes')); keep=set()
        def ancestors(n):
            if n in keep:return
            keep.add(n)
            for pin in n.get_editor_property('input_pins'):
                for e in pin.get_editor_property('edges'):
                    ancestors(e.get_editor_property('input_pin').get_editor_property('node'))
        for n in nodes:
            title=str(n.get_editor_property('node_title'))
            if title=='Soft airborne dust' or title.startswith('Debris: Instanced '): ancestors(n)
        for n in nodes:
            if n not in keep: g.remove_node(n)
        # Extra debris exclusions use actual mesh-conservative 7m padding and
        # analytic corridors/discs. Preserve the existing landmark pieces mask.
        extra=[]
        def box(x,y,ex,ey,yaw=0):
            p=unreal.PCGPoint();p.transform=unreal.Transform(location=unreal.Vector(x,y,0),rotation=unreal.Rotator(yaw=yaw))
            p.bounds_min=unreal.Vector(-ex,-ey,-100000);p.bounds_max=unreal.Vector(ex,ey,100000);p.steepness=1.;extra.append(p)
        padding=rules['debris_clearance_cm']
        for x,y,radius in inputs.discs: box(x,y,radius+padding,radius+padding)
        for line,half in inputs.corridors:
            for a,b in zip(line,line[1:]):
                length=math.dist(a[:2],b[:2]);box((a[0]+b[0])/2,(a[1]+b[1])/2,length/2+half+padding,half+padding,math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])))
        for n in keep:
            if str(n.get_editor_property('node_title'))=='Debris: Keep approaches clear':
                s=n.get_settings()
                original_node=next(v for v in source.get_editor_property('nodes') if str(v.get_editor_property('node_title'))=='Debris: Keep approaches clear')
                previous=list(original_node.get_settings().get_editor_property('points_to_create'))
                s.set_editor_property('points_to_create',previous+extra)
        groups=collections.defaultdict(list)
        for p in plans[label]: groups[(p['kind'],p['mesh'])].append(p)
        for row,((kind,index),points) in enumerate(sorted(groups.items())):
            n,s=g.add_node_of_type(unreal.PCGCreatePointsSettings); n.node_title=unreal.Name('P5: '+kind+' points'); n.set_node_position(0,9000+row*250)
            data=[]
            for p in points:
                point=unreal.PCGPoint();pitch,yaw,roll=p['rotation']
                point.transform=unreal.Transform(location=unreal.Vector(*p['xyz']),rotation=unreal.Rotator(pitch=pitch,yaw=yaw,roll=roll),scale=unreal.Vector(*p['scale']))
                point.seed=rules['seed']+len(data); data.append(point)
            s.points_to_create=data; s.coordinate_space=unreal.PCGCoordinateSpace.WORLD
            spawn,settings=g.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings);spawn.node_title=unreal.Name('P5: '+kind+' Nanite');spawn.set_node_position(450,9000+row*250)
            settings.synchronous_load=True; settings.set_mesh_selector_type(unreal.PCGMeshSelectorWeighted)
            descriptor=unreal.PCGSoftISMComponentDescriptor(); descriptor.set_editor_property('static_mesh',meshes[index])
            descriptor.set_editor_property('component_class',unreal.InstancedStaticMeshComponent)
            descriptor.set_editor_property('component_tags',[unreal.Name(TAG),unreal.Name('DF_P5_'+kind)])
            descriptor.set_editor_property('instance_end_cull_distance',rules[kind]['cull_cm'])
            descriptor.set_editor_property('instance_start_cull_distance',int(rules[kind]['cull_cm']*.72))
            body=descriptor.get_editor_property('body_instance')
            body.set_editor_property('collision_profile_name',unreal.Name('NoCollision' if kind in ('flats','edges','stakes') else 'BlockAll'))
            descriptor.set_editor_property('body_instance',body)
            entry=unreal.PCGMeshSelectorWeightedEntry();entry.set_editor_property('descriptor',descriptor);entry.set_editor_property('weight',1)
            selector=settings.get_editor_property('mesh_selector_parameters')
            selector.set_editor_property('mesh_entries',[entry])
            core['connect'](g,n,spawn)
        g.description=unreal.Text('Terrain v2 baked PCG points; seed/rules in Scripts/Data/world_dressing_phase5.json. Retained Phase3 dust/debris. Rebuild with build_phase5_dressing.py.')
        lib.save_loaded_asset(g);return g
    iterator=iter(pure['candidates'](inputs)); started=time.monotonic()
    state=dict(stage='sampling',handle=None,graphs={},labels=sorted(cells),index=0,generation_since=0,old_graphs={})
    # Failure restores streaming flags. Original graph assets remain saved;
    # regeneration can replace managed ISM resources before a later audit fails.
    spatial={label:a.get_editor_property('is_spatially_loaded') for label,a in cells.items()}
    def stop():
        unreal.unregister_slate_post_tick_callback(state['handle']);unreal._dustfall_phase5_dressing_handle=None
    def tick(delta):
        # Saving/compiling assets can pump Slate recursively on this build.
        if state.get('busy'): return
        state['busy']=True
        try:
            if time.monotonic()-started>rules['timeout_seconds']: raise RuntimeError('Dressing authoring timed out')
            if state['stage']=='sampling':
                for _ in range(rules['work_items_per_tick']):
                    candidate=next(iterator,None)
                    if candidate is None:
                        # Thin globally, never truncate the north/east when a
                        # category hits its budget in row-major traversal.
                        thinning=random.Random(rules['seed'])
                        for kind in list(counts):
                            cap=rules[kind].get('cap',counts[kind])
                            if counts[kind]<=cap:continue
                            candidates=[(label,p) for label in sorted(plans) for p in plans[label] if p['kind']==kind]
                            selected={id(p) for label,p in thinning.sample(candidates,cap)}
                            for label in plans:plans[label]=[p for p in plans[label] if p['kind']!=kind or id(p) in selected]
                            counts[kind]=cap
                        spires(); rock_count=sum(v for k,v in counts.items() if k!='stakes')
                        if rock_count>rules['max_rock_instances']: raise RuntimeError('Rock budget exceeded')
                        report.update(expected_counts=dict(counts),expected_rock_instances=rock_count)
                        state['stage']='graphs';break
                    process(candidate)
            elif state['stage']=='graphs':
                label=state['labels'][state['index']];state['graphs'][label]=graph(label);state['index']+=1
                if state['index']==len(cells):
                    report['path_material']=path_material(unreal,root,inputs)
                    for label,a in cells.items():
                        pcg=a.get_component_by_class(unreal.PCGComponent); state['old_graphs'][label]=pcg.get_graph()
                        # Authoring cells are pinned. Changing actor properties
                        # reconstructs Blueprint components and loses instance graphs.
                        a.modify();pcg.modify()
                        pcg.set_graph(state['graphs'][label]);pcg.generate(True)
                    state.update(stage='generating',generation_since=time.monotonic())
            else:
                if time.monotonic()-state['generation_since']<2:return
                live={a.get_actor_label():a for a in actors.get_all_level_actors() if a.get_actor_label() in cells}
                if len(live)!=64:raise RuntimeError('Lost PCG owners during generation')
                comps=[a.get_component_by_class(unreal.PCGComponent) for a in live.values()]
                if not all(c.get_editor_property('generated') and not c.get_editor_property('generation_in_progress') for c in comps):return
                for label,a in live.items():
                    actual=sum(c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent) if TAG in map(str,c.component_tags))
                    if actual!=len(plans[label]):
                        if time.monotonic()-state['generation_since']<15:return
                        raise RuntimeError('PCG output mismatch '+label+': '+str(actual)+' != '+str(len(plans[label])))
                    expected=sorted((meshes[p['mesh']].get_path_name(),p['kind'],*p['xyz'],*p['scale']) for p in plans[label])
                    actual_transforms=[]
                    for component in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
                        tags=list(map(str,component.component_tags))
                        if TAG not in tags:continue
                        kind=next(t.removeprefix('DF_P5_') for t in tags if t.startswith('DF_P5_'))
                        for index in range(component.get_instance_count()):
                            t=component.get_instance_transform(index,world_space=True);p=t.translation;s=t.scale3d
                            actual_transforms.append((component.static_mesh.get_path_name(),kind,p.x,p.y,p.z,s.x,s.y,s.z))
                    actual_transforms.sort()
                    if any(e[:2]!=v[:2] or any(abs(x-y)>.1 for x,y in zip(e[2:],v[2:])) for e,v in zip(expected,actual_transforms)):
                        if time.monotonic()-state['generation_since']<15:return
                        raise RuntimeError('Stale or transformed PCG point output '+label)
                    a.modify()
                    for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):c.modify()
                audit=runpy.run_path(str(root/'Scripts/verify_phase5_dressing_editor.py'))['audit'](root)
                report.update(audit)
                if audit['status']!='passed':raise RuntimeError('Actual output audit failed: '+str(audit['errors']))
                packages=[p for p in dirty() if p.get_path_name() not in before and ('L_Dustfall_Foundation' in p.get_path_name() or p.get_path_name().startswith(DEST))]
                if not unreal.EditorLoadingAndSavingUtils.save_packages(packages,True):raise RuntimeError('Could not save modified map/external actor/component packages')
                report.update(status='complete',elapsed_seconds=time.monotonic()-started,saved_packages=[p.get_path_name() for p in packages],
                              always_loaded_actors=[],rebuilt_cells=64,rebuild_reason='Global scatter rules replaced; all cells affected',seed=rules['seed'])
                write();stop();return
            report.update(status=state['stage'],planned_counts=dict(counts),graphs_authored=state['index']);write()
        except Exception:
            for label,a in cells.items():
                if unreal.SystemLibrary.is_valid(a) and a.get_editor_property('is_spatially_loaded')!=spatial[label]:
                    a.set_editor_property('is_spatially_loaded',spatial[label])
            report.update(status='failed',error=traceback.format_exc(),recovery='Original Phase3 graph is preserved. Inspect unsaved task output; rerun after correcting error. Do not save unrelated dirty packages.')
            write();unreal.log_error(report['error']);stop()
        finally:
            state['busy']=False
    write();state['handle']=unreal.register_slate_post_tick_callback(tick);unreal._dustfall_phase5_dressing_handle=state['handle']


if __name__=='__main__':
    try:main()
    except Exception:
        import unreal
        path=pathlib.Path(unreal.Paths.project_dir())/'Saved/Codex/phase5_dressing_build.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(dict(status='failed',error=traceback.format_exc()),indent=2),encoding='utf-8')
        raise
