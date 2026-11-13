"""Author the walkable Phase 3 habitat and Blueprint-only interlocked airlock.

Run in the dedicated foundation editor. Replaces only tagged habitat geometry;
does not rebuild terrain, character graphs or the environment director.
All measurements are cm. E requests a 12-second entry/exit cycle near home.
"""
import json
import math
import pathlib
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
TAG = 'DF_Phase3_Habitat'
BP_PATH = '/Game/Habitat/BP_DustfallHabitatDirector'
BEL = unreal.BlueprintEditorLibrary
LIB = unreal.EditorAssetLibrary
IN = unreal.EdGraphPinDirection.EGPD_INPUT
OUT = unreal.EdGraphPinDirection.EGPD_OUTPUT


def require(v, message):
    if not v:
        raise RuntimeError(message)
    return v


def pin(n, name, direction):
    return require(next((p for p in n.list_all_pins() if str(p.get_pin_name()) == name and p.get_pin_direction() == direction), None),
                   'Missing pin %s on %s: %s' % (name, n.get_node_title(), [str(p.get_pin_name()) for p in n.list_all_pins()]))


def wire(a, ap, b, bp):
    require(pin(a, ap, OUT).try_create_connection(pin(b, bp, IN)), 'Cannot wire '+ap+' -> '+bp)


def val(n, p, v):
    require(pin(n, p, IN).set_pin_value(str(v)), 'Cannot set '+p)


def output(n):
    return str(next(p for p in n.list_all_pins() if p.get_pin_direction() == OUT and str(p.get_pin_type_display_string()) != 'Exec').get_pin_name())


def material(name, color, roughness=.8, emission=None):
    path = '/Game/Habitat/Materials/'+name
    m = LIB.load_asset(path)
    if not m:
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, '/Game/Habitat/Materials', unreal.Material, unreal.MaterialFactoryNew())
    m.modify()
    g = unreal.MaterialEditingLibrary
    g.delete_all_material_expressions(m)
    c = g.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property('constant', unreal.LinearColor(*color, 1))
    g.connect_material_property(c, '', unreal.MaterialProperty.MP_BASE_COLOR)
    r = g.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 180)
    r.set_editor_property('r', roughness)
    g.connect_material_property(r, '', unreal.MaterialProperty.MP_ROUGHNESS)
    if not emission:
        def expr(cls,x,y): return g.create_material_expression(m,cls,x,y)
        def link(a,ap,b,bp):
            if bp=='Input': bp='None'
            elif bp=='Position': bp='World Position'
            outs=list(g.get_material_expression_output_names(a))
            if not ap and outs: ap=outs[0]
            require(g.connect_material_expressions(a,ap,b,bp),'Material connection '+bp)
        world=expr(unreal.MaterialExpressionWorldPosition,-1700,0)
        scale=expr(unreal.MaterialExpressionMultiply,-1500,0); scale.set_editor_property('const_b',.0075)
        link(world,'',scale,'A')
        normal=expr(unreal.MaterialExpressionVertexNormalWS,-1700,700)
        absolute=expr(unreal.MaterialExpressionAbs,-1500,700); link(normal,'',absolute,'Input')
        def mask(source,channels,x,y):
            n=expr(unreal.MaterialExpressionComponentMask,x,y)
            for channel in ['r','g','b','a']: n.set_editor_property(channel,channel in channels)
            link(source,'',n,'Input'); return n
        uvxy=mask(scale,'rg',-1300,0); uvxz=mask(scale,'rb',-1300,180); uvyz=mask(scale,'gb',-1300,360)
        nx=mask(absolute,'r',-1300,700); nz=mask(absolute,'b',-1300,850)
        def triplanar(kind,y):
            if 'Bedding' in name or 'Solar' in name: return None
            tex=LIB.load_asset('/Game/World/Megascans/Phase2/RustyMetal/T_RustyMetal_'+kind)
            if not tex: return None
            samples=[]
            for index,uv in enumerate([uvxz,uvyz,uvxy]):
                s=expr(unreal.MaterialExpressionTextureSample,-1000+index*220,y)
                s.texture=tex
                if kind=='Roughness': s.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
                link(uv,'',s,'UVs'); samples.append(s)
            blend=expr(unreal.MaterialExpressionLinearInterpolate,-300,y)
            out='R' if kind=='Roughness' else 'RGB'
            link(samples[0],out,blend,'A'); link(samples[1],out,blend,'B'); link(nx,'',blend,'Alpha')
            result=expr(unreal.MaterialExpressionLinearInterpolate,-60,y)
            link(blend,'',result,'A'); link(samples[2],out,result,'B'); link(nz,'',result,'Alpha')
            return result
        detail=triplanar('Albedo',-500)
        if detail:
            aged=expr(unreal.MaterialExpressionLinearInterpolate,220,-250)
            aged.set_editor_property('const_alpha',.63 if 'Charcoal' not in name else .22)
            link(c,'',aged,'A'); link(detail,'',aged,'B')
            noise=expr(unreal.MaterialExpressionNoise,-300,-950)
            noise.set_editor_property('levels',3); noise.set_editor_property('output_min',.62); noise.set_editor_property('output_max',1.04)
            link(scale,'',noise,'Position')
            varied=expr(unreal.MaterialExpressionMultiply,450,-250)
            link(aged,'',varied,'A'); link(noise,'',varied,'B')
            g.connect_material_property(varied,'',unreal.MaterialProperty.MP_BASE_COLOR)
        else:
            noise=expr(unreal.MaterialExpressionNoise,-300,-950)
            noise.set_editor_property('levels',2); noise.set_editor_property('output_min',.92); noise.set_editor_property('output_max',1.04)
            link(scale,'',noise,'Position')
            varied=expr(unreal.MaterialExpressionMultiply,450,-250)
            link(c,'',varied,'A'); link(noise,'',varied,'B')
            g.connect_material_property(varied,'',unreal.MaterialProperty.MP_BASE_COLOR)
        surface_roughness=triplanar('Roughness',1100)
        if surface_roughness:
            blend=expr(unreal.MaterialExpressionLinearInterpolate,250,1100)
            blend.set_editor_property('const_alpha',.55)
            link(r,'',blend,'A'); link(surface_roughness,'',blend,'B')
            g.connect_material_property(blend,'',unreal.MaterialProperty.MP_ROUGHNESS)
        if 'Metal' in name or 'Charcoal' in name:
            metallic=expr(unreal.MaterialExpressionConstant,450,1300); metallic.set_editor_property('r',.18 if 'Charcoal' in name else .35)
            g.connect_material_property(metallic,'',unreal.MaterialProperty.MP_METALLIC)
            texture=LIB.load_asset('/Game/World/Megascans/Phase2/RustyMetal/T_RustyMetal_Normal')
            if texture:
                detail_normal=expr(unreal.MaterialExpressionTextureSample,220,1450)
                detail_normal.texture=texture
                detail_normal.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
                g.connect_material_property(detail_normal,'RGB',unreal.MaterialProperty.MP_NORMAL)
    if emission:
        e = g.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 350)
        e.set_editor_property('constant', unreal.LinearColor(*emission, 1))
        g.connect_material_property(e, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    g.recompile_material(m)
    LIB.save_loaded_asset(m)
    return m


def import_pod_meshes():
    paths=runpy.run_path(str(ROOT/'Scripts/habitat_pod_meshes.py'))['generate'](ROOT)
    output={}
    for key,path in paths.items():
        options=unreal.FbxImportUI()
        options.set_editor_property('import_mesh',True)
        options.set_editor_property('import_as_skeletal',False)
        options.set_editor_property('import_materials',False)
        options.set_editor_property('import_textures',False)
        options.set_editor_property('automated_import_should_detect_type',False)
        options.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
        data=options.static_mesh_import_data
        data.set_editor_property('combine_meshes',True)
        data.set_editor_property('auto_generate_collision',False)
        data.set_editor_property('build_nanite',True)
        data.set_editor_property('convert_scene',False)
        data.set_editor_property('force_front_x_axis',False)
        task=unreal.AssetImportTask()
        task.set_editor_property('filename',str(path)); task.set_editor_property('destination_path','/Game/Habitat/Meshes')
        task.set_editor_property('destination_name',path.stem); task.set_editor_property('automated',True)
        task.set_editor_property('replace_existing',True); task.set_editor_property('save',True); task.set_editor_property('options',options)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=require(LIB.load_asset('/Game/Habitat/Meshes/'+path.stem),'Pod import failed '+key)
        output[key]=mesh
    return output


def director_blueprint():
    bp = LIB.load_asset(BP_PATH)
    if not bp:
        f = unreal.BlueprintFactory(); f.set_editor_property('parent_class', unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_DustfallHabitatDirector', '/Game/Habitat', None, f)
    ed = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(bp))
    tick = require(ed.find_event_node('ReceiveTick'), 'No Tick')
    begin = require(ed.find_event_node('ReceiveBeginPlay'), 'No BeginPlay')
    ed.remove_nodes([n for n in ed.list_all_nodes() if n not in [tick, begin]])
    types = {'InnerDoor': BEL.get_object_reference_type(unreal.StaticMeshActor),
             'OuterDoor': BEL.get_object_reference_type(unreal.StaticMeshActor),
             'HabitatOrigin': BEL.get_struct_type(unreal.Vector.static_struct()),
             'InteriorSpawn': BEL.get_struct_type(unreal.Vector.static_struct()),
             'CycleTime': BEL.get_basic_type_by_name('real'),
             'Cycling': BEL.get_basic_type_by_name('bool'),
             'TravelOut': BEL.get_basic_type_by_name('bool')}
    existing = [str(n) for n in BEL.list_member_variable_names(bp, False)]
    for name, typ in types.items():
        if name not in existing:
            require(BEL.add_member_variable(bp, name, typ), 'Cannot add '+name)
        elif name in ['HabitatOrigin', 'InteriorSpawn']:
            BEL.change_member_variable_type(bp, unreal.Name(name), typ)
        BEL.set_blueprint_variable_instance_editable(bp, name, True)
    require(BEL.compile_blueprint(bp), 'Habitat variables failed compilation')
    ed = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(bp))
    tick = require(ed.find_event_node('ReceiveTick'), 'No Tick')
    begin = require(ed.find_event_node('ReceiveBeginPlay'), 'No BeginPlay')
    counter = [0]
    def place(n):
        counter[0] += 1
        n.set_node_pos(unreal.IntPoint((counter[0] % 8)*260, (counter[0]//8)*240))
        return n
    def call(name): return place(require(ed.add_call_function_node('/Script/Engine.'+name), 'Cannot call '+name))
    def get(name): return place(require(ed.add_get_member_variable_node(unreal.Name(name)), 'Cannot get '+name))
    def setter(name): return place(require(ed.add_set_member_variable_node(unreal.Name(name)), 'Cannot set '+name))
    def binary(name, a, b=None, literal=None):
        n = call('KismetMathLibrary:'+name)
        wire(a, output(a), n, 'A')
        if b is not None: wire(b, output(b), n, 'B')
        else: val(n, 'B', literal)
        return n
    def branch(condition, before, exec_pin='then'):
        n = place(require(ed.add_branch_node(), 'Cannot branch'))
        wire(condition, output(condition), n, 'Condition'); wire(before, exec_pin, n, 'execute')
        return n
    pawn = call('GameplayStatics:GetPlayerPawn'); val(pawn, 'PlayerIndex', 0)
    loc = call('Actor:K2_GetActorLocation'); wire(pawn, 'ReturnValue', loc, 'self')
    origin = get('HabitatOrigin')
    relative = binary('Subtract_VectorVector', loc, origin)
    split = call('KismetMathLibrary:BreakVector'); wire(relative, 'ReturnValue', split, 'InVec')
    controller = call('GameplayStatics:GetPlayerController'); val(controller, 'PlayerIndex', 0)
    enable = call('Actor:EnableInput'); wire(begin, 'then', enable, 'execute'); wire(controller, 'ReturnValue', enable, 'PlayerController')
    key = place(require(ed.create_node_from_name('Input|KeyboardEvents|E', unreal.Vector2D(0, 0), []), 'Cannot bind E'))
    # Both airlock and crate use E; neither should swallow the other interaction.
    try: key.set_editor_property('consume_input', False)
    except Exception: pass
    request = place(require(ed.add_custom_event_node('DF_RequestAirlock'), 'Cannot add request event'))
    not_busy = call('KismetMathLibrary:Not_PreBool'); wire(get('Cycling'), 'Cycling', not_busy, 'A')
    distance = call('KismetMathLibrary:VSize'); wire(relative, 'ReturnValue', distance, 'A')
    near = binary('Less_DoubleDouble', distance, literal=1500)
    can = binary('BooleanAND', near, not_busy)
    gate = branch(can, key, 'Pressed')
    # A second branch allows the named automation/gameplay event to share logic.
    gate2 = branch(can, request)
    outgoing = call('KismetMathLibrary:Less_DoubleDouble'); wire(split, 'X', outgoing, 'A'); val(outgoing, 'B', 750)
    set_out = setter('TravelOut'); wire(outgoing, 'ReturnValue', set_out, 'TravelOut')
    wire(gate, 'then', set_out, 'execute'); wire(gate2, 'then', set_out, 'execute')
    reset = setter('CycleTime'); val(reset, 'CycleTime', 0); wire(set_out, 'then', reset, 'execute')
    start = setter('Cycling'); val(start, 'Cycling', 'true'); wire(reset, 'then', start, 'execute')
    age = get('CycleTime'); cycling = get('Cycling')
    delta = call('KismetMathLibrary:Add_DoubleDouble'); wire(age, 'CycleTime', delta, 'A'); wire(tick, 'DeltaSeconds', delta, 'B')
    # Pause before a closing boundary while the capsule occupies that doorway.
    # Keeping the cycle clock paused also prevents the opposite door opening.
    yabs=call('KismetMathLibrary:Abs'); wire(split,'Y',yabs,'A')
    in_width=binary('Less_DoubleDouble',yabs,literal=145)
    blockers=[]
    for low,high,a,b in [(3,4,500,1000),(9,10,1000,500)]:
        portal=call('KismetMathLibrary:SelectFloat'); wire(get('TravelOut'),'TravelOut',portal,'bPickA'); val(portal,'A',a); val(portal,'B',b)
        dx=call('KismetMathLibrary:Subtract_DoubleDouble'); wire(split,'X',dx,'A'); wire(portal,'ReturnValue',dx,'B')
        absdx=call('KismetMathLibrary:Abs'); wire(dx,'ReturnValue',absdx,'A')
        at_door=binary('Less_DoubleDouble',absdx,literal=95)
        window=binary('BooleanAND',binary('GreaterEqual_DoubleDouble',age,literal=low),binary('Less_DoubleDouble',age,literal=high))
        blockers.append(binary('BooleanAND',window,binary('BooleanAND',at_door,in_width)))
    paused=binary('BooleanOR',blockers[0],blockers[1])
    safe_age=call('KismetMathLibrary:SelectFloat'); wire(paused,'ReturnValue',safe_age,'bPickA'); wire(age,'CycleTime',safe_age,'A'); wire(delta,'ReturnValue',safe_age,'B')
    select_age = call('KismetMathLibrary:SelectFloat'); wire(cycling, 'Cycling', select_age, 'bPickA'); wire(safe_age, 'ReturnValue', select_age, 'A'); val(select_age, 'B', 0)
    set_age = setter('CycleTime'); wire(tick, 'then', set_age, 'execute'); wire(select_age, 'ReturnValue', set_age, 'CycleTime')
    due = binary('GreaterEqual_DoubleDouble', age, literal=12)
    active = call('KismetMathLibrary:Not_PreBool'); wire(due, 'ReturnValue', active, 'A')
    still = binary('BooleanAND', cycling, active)
    set_active = setter('Cycling'); wire(set_age, 'then', set_active, 'execute'); wire(still, 'ReturnValue', set_active, 'Cycling')
    early = binary('Less_DoubleDouble', age, literal=4)
    late_start = binary('Greater_DoubleDouble', age, literal=6)
    late_end = binary('Less_DoubleDouble', age, literal=10)
    late = binary('BooleanAND', late_start, late_end)
    outgoing_get = get('TravelOut')
    previous = set_active
    for name, first, second, x in [('InnerDoor', early, late, 500), ('OuterDoor', late, early, 1000)]:
        sel = call('KismetMathLibrary:SelectFloat'); wire(outgoing_get, 'TravelOut', sel, 'bPickA')
        for condition, channel in [(first, 'A'), (second, 'B')]:
            height = call('KismetMathLibrary:SelectFloat'); wire(condition, 'ReturnValue', height, 'bPickA'); val(height, 'A', 350); val(height, 'B', 0)
            wire(height, 'ReturnValue', sel, channel)
        enabled_height = call('KismetMathLibrary:SelectFloat'); wire(cycling, 'Cycling', enabled_height, 'bPickA'); wire(sel, 'ReturnValue', enabled_height, 'A'); val(enabled_height, 'B', 0)
        z = call('KismetMathLibrary:Add_DoubleDouble'); wire(enabled_height, 'ReturnValue', z, 'A'); val(z, 'B', 190)
        vector = call('KismetMathLibrary:MakeVector'); val(vector, 'X', x); val(vector, 'Y', 0); wire(z, 'ReturnValue', vector, 'Z')
        world = binary('Add_VectorVector', vector, origin)
        move = call('Actor:K2_SetActorLocation'); wire(get(name), name, move, 'self'); wire(world, 'ReturnValue', move, 'NewLocation'); wire(previous, 'then', move, 'execute')
        val(move, 'bSweep', 'false'); val(move, 'bTeleport', 'true'); previous = move
    require(BEL.compile_blueprint(bp), 'Habitat graph compile failed: '+str(list(ed.list_nodes_with_errors())))
    LIB.save_loaded_asset(bp, False)
    return bp


def build():
    world = unreal.EditorLevelLibrary.get_editor_world()
    require('/Game/World/Maps/L_Dustfall_Foundation' in world.get_path_name(), 'Open foundation map')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    current = list(actors.get_all_level_actors())
    old_base = next((a for a in current if a.get_actor_label() == 'Hab_Base_Temporary'), None)
    old_director = next((a for a in current if a.get_actor_label() == 'Dustfall Habitat Director'), None)
    if old_director and hasattr(old_director.get_editor_property('HabitatOrigin'), 'x'):
        o = old_director.get_editor_property('HabitatOrigin'); origin = (o.x,o.y,o.z)
    elif old_base:
        require(old_base, 'No original habitat origin')
        o = old_base.get_actor_location(); origin = (o.x,o.y,o.z-10)
    else:
        floor = next((a for a in current if a.get_actor_label() == 'P3_Hab_Floor'), None)
        if floor:
            o = floor.get_actor_location(); origin = (o.x,o.y,o.z-25)
        else:
            # Recover an interrupted authoring pass using its explicit saved
            # anchor; never silently relocate the habitat to the world origin.
            report = ROOT/'Saved/Codex/phase3_habitat_build.json'
            require(report.exists(), 'No habitat origin, floor or recovery report')
            origin = tuple(json.loads(report.read_text())['origin_cm'])
            require(len(origin)==3, 'Invalid habitat recovery anchor')
    bp = director_blueprint()  # Compile before replacing geometry.
    cube = require(unreal.load_asset('/Engine/BasicShapes/Cube.Cube'), 'No cube')
    metal = material('M_P3_Hab_PaleMetal', (.28,.245,.19), .78)
    dark = material('M_P3_Hab_Charcoal', (.045,.04,.032), .88)
    bedding = material('M_P3_Hab_Bedding', (.13,.105,.072), .96)
    amber = material('M_P3_Hab_Amber', (.4,.15,.025), .5, (1.8,.5,.055))
    cool = material('M_P3_Hab_Cool', (.08,.2,.3), .5, (.25,1.5,2.5))
    blue = material('M_P3_Hab_Solar', (.004,.009,.025), .34)
    rust = material('M_P3_Hab_RustedMetal',(.105,.047,.018),.96)
    grime = material('M_P3_Hab_DustGrime',(.055,.035,.019),.99)
    pod_meshes=import_pod_meshes()
    # Finish all material graph authoring before replacing the playable shell.
    for a in current:
        tags = [str(t) for t in a.tags]
        if TAG in tags or 'DF_Phase1_Habitat_Blockout' in tags or 'DF_Phase2_HomeApproach' in tags:
            actors.destroy_actor(a)
        elif a.get_actor_label()=='Foundation Landing Pad' and 'DF_Phase1_World' in tags:
            # Retire the oversized temporary slab; the pod and its boarding ramp
            # supply the actual floor/collision. Keep the rest of world intact.
            actors.destroy_actor(a)
    def pos(p): return unreal.Vector(*(origin[i]+p[i] for i in range(3)))
    def box(label, center, size, mat=metal, rotation=None, collision=True, movable=False):
        a = require(actors.spawn_actor_from_class(unreal.StaticMeshActor, pos(center)), 'Cannot spawn '+label)
        a.set_actor_label('P3_Hab_'+label); a.tags=[unreal.Name(TAG)]
        a.set_folder_path('DUSTFALL/Phase3_Habitat'); a.set_editor_property('is_spatially_loaded', False)
        c=a.static_mesh_component; c.set_static_mesh(cube); c.set_material(0,mat)
        c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
        c.set_mobility(unreal.ComponentMobility.MOVABLE if movable else unreal.ComponentMobility.STATIC)
        a.set_actor_scale3d(unreal.Vector(*(v/100 for v in size)))
        if rotation: a.set_actor_rotation(unreal.Rotator(pitch=rotation[0],yaw=rotation[1],roll=rotation[2]), False)
        return a
    def pod(label,mat):
        a=actors.spawn_actor_from_class(unreal.StaticMeshActor,pos((0,0,0)))
        a.set_actor_label('P3_Hab_Curved_'+label); a.tags=[unreal.Name(TAG)]
        a.set_folder_path('DUSTFALL/Phase3_Habitat/CustomHull'); a.set_editor_property('is_spatially_loaded',False)
        c=a.static_mesh_component; c.set_static_mesh(pod_meshes[label]); c.set_material(0,mat)
        c.set_collision_profile_name('NoCollision')
        return a
    for label,mat in [('HullPanels',metal),('PressureLiner',dark),('HullRibs',dark),('EndCaps',metal),
                      ('WindowGlass',amber),('AirlockBarrel',metal),('DoorFrame',dark),('DamagePetals',metal),
                      ('RustScars',rust),('LowerGrime',grime),('RepairPlates',dark)]: pod(label,mat)
    # Invisible, deliberately conservative pressure-volume collision retains the
    # tested centre aisle. The exterior silhouette comes from authored curves.
    def proxy(label,center,size):
        a=box(label,center,size,dark); a.static_mesh_component.set_visibility(False)
        return a
    box('Floor', (0,0,25), (1040,800,50), dark)
    proxy('BackPressureCollision',(-510,0,240),(20,780,430))
    for side in [-1,1]:
        proxy('SidePressureCollision_'+str(side),(0,side*400,210),(1040,20,340))
        proxy('EntranceSide_'+str(side),(510,side*275,240),(20,270,430))
        proxy('AirlockWall_'+str(side),(750,side*200,220),(500,20,340))
    proxy('RoofPressureCollision',(0,0,470),(1040,540,24))
    proxy('EntranceLintel',(510,0,400),(20,360,80))
    box('AirlockFloor', (750,0,25), (500,400,50), dark)
    proxy('AirlockRoof',(750,0,409),(540,320,24))
    for side in [-1,1]: proxy('OuterJamb_'+str(side),(1000,side*165,200),(30,70,300))
    proxy('OuterLintel',(1000,0,369),(30,360,70))
    inner=box('InnerDoor', (500,0,190), (18,180,280), dark, movable=True)
    outer=box('OuterDoor', (1000,0,190), (18,220,280), metal, movable=True)
    # These details are attached to the moving door so they travel with its
    # existing interlocked motion rather than leaving floating hardware behind.
    for label,offset,size,mat in [('Viewport',(12,0,65),(4,90,32),dark),('Handle',(15,70,0),(8,10,48),dark),
                                  ('Vent',(12,0,-60),(4,85,70),dark)]:
        detail=box('Door'+label,(1000+offset[0],offset[1],190+offset[2]),size,mat,collision=False,movable=True)
        detail.attach_to_actor(outer,'',unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,False)
    # Gentle 50cm ramp approaches the outer door at the same floor height.
    box('ApproachRamp', (1250,0,15), (520,350,20), dark, rotation=(-5.5,0,0))
    for x in [-400,-200,0,200,400]:
        box('FloorSeam_'+str(x), (x,0,50.5), (3,680,1), metal, collision=False)
        for side in [-1,1]:
            box('WallRib_%s_%s'%(x,side), (x,side*345,200), (14,18,280), dark, collision=False)
    # Bed remains outside the clear central path from spawn to airlock.
    box('BedFrame', (-130,-240,82), (240,135,64), dark)
    box('Mattress', (-130,-240,123), (230,125,22), bedding)
    box('Pillow', (-210,-240,143), (55,112,18), bedding, collision=False)
    box('Blanket', (-90,-240,139), (140,128,10), bedding, collision=False)
    box('Workbench', (-90,250,130), (330,130,20), metal)
    for x in [-220,40]: box('BenchLeg_'+str(x),(x,250,85),(16,100,70),dark)
    box('BrokenFabricator', (0,250,190), (120,90,100), dark)
    box('FabricatorFace', (0,199,195), (90,4,55), blue, collision=False)
    box('FabricatorStatus', (42,194,165), (8,3,8), amber, collision=False)
    for z in [170,245,320]:
        box('Shelf_'+str(z), (-440,80,z), (90,280,10), dark)
        for j in range(4): box('StoredCanister_%s_%s'%(z,j),(-440,-20+j*62,z+27),(40,40,45),metal,collision=False)
    for y in [-325,325]:
        box('UtilityConduit_'+str(y), (0,y,300), (950,10,10), dark, collision=False)
    for side in [-1,1]:
        for x in [-210,0,210]:
            box('SolarPanel_%s_%s'%(side,x),(x,side*103,535),(200,195,9),blue,rotation=(0,0,side*12),collision=False)
            box('SolarMount_%s_%s'%(side,x),(x,side*100,502),(8,8,65),dark,collision=False)
            for step in range(-4,5):
                box('SolarCell_%s_%s_%s'%(side,x,step),(x+step*21,side*103,541),(1,194,1),metal,rotation=(0,0,side*12),collision=False)
    box('Antenna',(-380,200,590),(5,5,330),dark,collision=False)
    box('AntennaCrossbar',(-380,200,690),(100,5,5),metal,collision=False)
    for x in [-300,250,900]:
        exterior = x==900
        p=(x,0,350 if exterior else 390)
        box('Lamp_'+str(x),p,(50,35,8),amber,collision=False)
        a=actors.spawn_actor_from_class(unreal.PointLight,pos((p[0],p[1],p[2]-25)))
        a.set_actor_label('P3_Hab_Practical_'+str(x)); a.tags=[unreal.Name(TAG)]; a.set_folder_path('DUSTFALL/Phase3_Habitat')
        a.set_editor_property('is_spatially_loaded',False)
        c=a.point_light_component; c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('intensity_units',unreal.LightUnits.LUMENS); c.set_intensity(1000 if exterior else 650)
        c.set_light_color(unreal.LinearColor(1,.57,.26,1)); c.set_attenuation_radius(1200 if exterior else 650)
        c.set_editor_property('volumetric_scattering_intensity',.1 if exterior else 0)
    box('CoolTaskLamp',(-80,330,300),(100,8,10),cool,collision=False)
    task=actors.spawn_actor_from_class(unreal.PointLight,pos((-80,235,285)))
    task.set_actor_label('P3_Hab_CoolTaskLight'); task.tags=[unreal.Name(TAG)]
    task.set_folder_path('DUSTFALL/Phase3_Habitat'); task.set_editor_property('is_spatially_loaded',False)
    task_light=task.point_light_component; task_light.set_mobility(unreal.ComponentMobility.MOVABLE)
    task_light.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
    task_light.set_intensity(220); task_light.set_attenuation_radius(500)
    task_light.set_light_color(unreal.LinearColor(.35,.65,1.,1.))
    task_light.set_editor_property('cast_shadows',False)
    task_light.set_editor_property('volumetric_scattering_intensity',0.)
    # Licensed scanned equipment gives the functional primitive shell real
    # manufactured surface detail. Bounds-centred transforms handle scan pivots.
    def scanned(label,ident,center,longest,yaw=0):
        mesh=LIB.load_asset('/Game/World/QuixelPhase2/'+ident+'/SM_'+ident)
        if not mesh: return
        bounds=mesh.get_bounds(); s=longest/max(1,2*max(bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z))
        angle=math.radians(yaw); c=bounds.origin
        correction=(s*(c.x*math.cos(angle)-c.y*math.sin(angle)),s*(c.x*math.sin(angle)+c.y*math.cos(angle)),s*c.z)
        a=actors.spawn_actor_from_class(unreal.StaticMeshActor,pos(tuple(center[i]-correction[i] for i in range(3))))
        a.set_actor_label('P3_Hab_Scan_'+label); a.tags=[unreal.Name(TAG)]
        a.set_folder_path('DUSTFALL/Phase3_Habitat/Dressing'); a.set_editor_property('is_spatially_loaded',False)
        a.static_mesh_component.set_static_mesh(mesh); a.static_mesh_component.set_collision_profile_name('NoCollision')
        a.set_actor_scale3d(unreal.Vector(s,s,s)); a.set_actor_rotation(unreal.Rotator(yaw=yaw),False)
    scanned('InteriorPowerCabinet','ullibjd',(-460,290,235),105,180)
    scanned('WorkbenchCable','vkzidgds',(-100,240,150),110)
    scanned('ExteriorRecyclerTank','wdklears',(-200,490,160),220)
    scanned('ExteriorServiceCabinet','ullibjd',(300,405,200),120,90)
    scanned('LooseMaintenanceCover','wcljbdb',(-400,255,65),90,15)
    # Layered internal services, equipment, identification and repairs.
    for side in [-1,1]:
        for x in [-400,-200,0,200,400]:
            for z in [90,310]:
                box('PanelBolt_%s_%s_%s'%(side,x,z),(x+18,side*421,z),(5,4,5),dark,collision=False)
        box('RepairPatch_'+str(side),(-200,side*422,185),(115,5,105),dark,rotation=(0,0,side*5),collision=False)
        box('InteriorLowerService_'+str(side),(0,side*336,80),(950,12,12),dark,collision=False)
        box('ExteriorLowerStrap_'+str(side),(0,side*409,124),(1010,7,12),dark,collision=False)
        for x in [-440,-110,380]:
            box('StrapMount_%s_%s'%(side,x),(x,side*413,124),(30,10,28),metal,collision=False)
    for x in [-150,-70,10]:
        box('BedFabricSeam_'+str(x),(x,-240,145),(3,124,2),dark,collision=False)
    for y in [-76,76]:
        box('InnerDoorRail_'+str(y),(486,y,190),(5,8,270),metal,collision=False)
    # Storage labels, drawer fronts and service vent louvers add human scale.
    for j in range(7):
        box('FabricatorVent_'+str(j),(20,201,170+j*8),(45,5,2),metal,collision=False)
        box('RecyclerVent_'+str(j),(-485,180,160+j*15),(3,100,4),metal,collision=False)
    for x in [-185,-75,35]:
        box('BenchDrawer_'+str(x),(x,187,104),(100,7,35),dark,collision=False)
        box('DrawerHandle_'+str(x),(x,181,109),(35,5,5),metal,collision=False)
    for y in [-285,-220,-155]: box('MattressCrease_'+str(y),(-120,y,147),(190,2,2),dark,collision=False)
    for x,yaw in [(1025,0),(475,180)]:
        a=actors.spawn_actor_from_class(unreal.TextRenderActor,pos((x,0,345)))
        a.set_actor_label('P3_Hab_AirlockInstructions_'+str(x)); a.tags=[unreal.Name(TAG)]
        a.set_folder_path('DUSTFALL/Phase3_Habitat'); a.set_editor_property('is_spatially_loaded',False)
        a.set_actor_rotation(unreal.Rotator(yaw=yaw),False)
        text=a.get_component_by_class(unreal.TextRenderComponent)
        text.set_text('E  CYCLE AIRLOCK'); text.set_world_size(15)
        text.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    director=actors.spawn_actor_from_class(bp.generated_class(),pos((0,0,0)))
    director.set_actor_label('Dustfall Habitat Director'); director.tags=[unreal.Name(TAG)]
    director.set_editor_property('is_spatially_loaded',False)
    director.set_editor_property('InnerDoor',inner); director.set_editor_property('OuterDoor',outer)
    director.set_editor_property('HabitatOrigin',pos((0,0,0))); director.set_editor_property('InteriorSpawn',pos((-120,0,148)))
    for a in current:
        if isinstance(a,unreal.PlayerStart):
            a.modify(); a.set_actor_location(pos((-120,0,148)),False,True); a.set_actor_rotation(unreal.Rotator(yaw=0),False)
    report={'art_revision':'rounded_custom_pod_v1','custom_meshes':{k:v.get_path_name() for k,v in pod_meshes.items()},
            'origin_cm':origin,'HabitatCenter':[origin[0],origin[1],origin[2]+235],
            'HabitatHalfExtent':[475,325,185],'CloneSpawn':[origin[0]-120,origin[1],origin[2]+148],
            'inner_door_x_cm':origin[0]+500,'outer_door_x_cm':origin[0]+1000,
            'controls':'E near home: near door open 0-4s, both closed 4-6s, far door open 6-10s, both closed by 12s'}
    (ROOT/'Saved/Codex/phase3_habitat_build.json').write_text(json.dumps(report,indent=2))
    for a in actors.get_all_level_actors():
        if a.get_class().get_name() == 'BP_SurvivalDirector_C':
            a.modify()
            for name in ['HabitatCenter','HabitatHalfExtent','CloneSpawn']:
                a.set_editor_property(name,unreal.Vector(*report[name]))
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_all_dirty_levels()
    unreal.log('DUSTFALL Phase 3 habitat built: '+str(report))


if __name__=='__main__':
    build()
