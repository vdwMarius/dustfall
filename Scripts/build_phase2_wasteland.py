"""Bake seeded Megascans rock cells and an automatic wasteland material.

Run after import_phase2_quixel.py and build_phase2_landmarks.py in the foundation
editor. Runtime content uses spatially streamed HISM cells, never Python.
"""
import json
import math
import pathlib
import random
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
DEST = '/Game/World/QuixelPhase2'
IDS = ['xgmdcay', 'xgncbgz', 'xgndbge', 'xgkmfcy', 'xgmncdu', 'xgoqfid', 'xgjnech', 'xgjodeb']
TAG = 'DF_Phase2_RockCell'


def terrain_material():
    path = '/Game/World/Materials/M_Wasteland_Phase2'
    existing = unreal.load_asset(path)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = existing or tools.create_asset('M_Wasteland_Phase2', '/Game/World/Materials', unreal.Material, unreal.MaterialFactoryNew())
    g = unreal.MaterialEditingLibrary
    g.delete_all_material_expressions(mat)
    def expr(cls, x=0, y=0):
        return g.create_material_expression(mat, cls, x, y)
    def link(a, out, b, pin):
        inputs = list(g.get_material_expression_input_names(b))
        outputs = list(g.get_material_expression_output_names(a))
        if pin == 'Input':
            pin = 'None'
        elif pin == 'Position':
            pin = 'World Position'
        if not out and outputs:
            out = outputs[0]
        if not g.connect_material_expressions(a, out, b, pin):
            raise RuntimeError('Material link failed: ' + pin)
    pos = expr(unreal.MaterialExpressionWorldPosition, -1400, 0)
    xy = expr(unreal.MaterialExpressionComponentMask, -1200, 0)
    for k, v in dict(r=True, g=True, b=False, a=False).items():
        xy.set_editor_property(k, v)
    link(pos, '', xy, 'Input')
    uv = expr(unreal.MaterialExpressionMultiply, -1000, 0)
    uv.set_editor_property('const_b', .0025)  # 4 m world texture repeat.
    link(xy, '', uv, 'A')
    macro = expr(unreal.MaterialExpressionMultiply, -1200, -500)
    macro.set_editor_property('const_b', .000025)
    link(pos, '', macro, 'A')
    noise = expr(unreal.MaterialExpressionNoise, -1000, -500)
    noise.set_editor_property('levels', 2)
    noise.set_editor_property('output_min', 0.)
    noise.set_editor_property('output_max', 1.)
    link(macro, '', noise, 'Position')
    normal_ws = expr(unreal.MaterialExpressionVertexNormalWS, -1000, -800)
    nz = expr(unreal.MaterialExpressionComponentMask, -800, -800)
    for k, v in dict(r=False, g=False, b=True, a=False).items():
        nz.set_editor_property(k, v)
    link(normal_ws, '', nz, 'Input')
    slope = expr(unreal.MaterialExpressionOneMinus, -600, -800)
    link(nz, '', slope, 'Input')
    slope_scale = expr(unreal.MaterialExpressionMultiply, -400, -800)
    slope_scale.set_editor_property('const_b', 4.)
    link(slope, '', slope_scale, 'A')
    steep = expr(unreal.MaterialExpressionClamp, -200, -800)
    link(slope_scale, '', steep, 'Input')
    samples = {}
    for j, ident in enumerate(['xgmpdek', 'xglmfbr', 'xgindb3']):
        samples[ident] = {}
        for i, kind in enumerate(['Albedo', 'Normal', 'Roughness']):
            s = expr(unreal.MaterialExpressionTextureSample, -700 + j * 240, i * 220)
            s.texture = unreal.load_asset(DEST + '/' + ident + '/T_' + ident + '_' + kind)
            if not s.texture:
                raise RuntimeError('Missing terrain texture ' + ident + kind)
            if kind == 'Normal':
                s.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
            elif kind == 'Roughness':
                s.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
            link(uv, '', s, 'UVs')
            samples[ident][kind] = s
    for i, (kind, prop) in enumerate([('Albedo', unreal.MaterialProperty.MP_BASE_COLOR), ('Normal', unreal.MaterialProperty.MP_NORMAL), ('Roughness', unreal.MaterialProperty.MP_ROUGHNESS)]):
        a = expr(unreal.MaterialExpressionLinearInterpolate, 200, i * 250)
        out = 'R' if kind == 'Roughness' else 'RGB'
        link(samples['xgmpdek'][kind], out, a, 'A')
        link(samples['xglmfbr'][kind], out, a, 'B')
        link(noise, '', a, 'Alpha')
        b = expr(unreal.MaterialExpressionLinearInterpolate, 450, i * 250)
        link(a, '', b, 'A')
        link(samples['xgindb3'][kind], out, b, 'B')
        link(steep, '', b, 'Alpha')
        if not g.connect_material_property(b, '', prop):
            raise RuntimeError('Cannot connect terrain material output')
    g.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def cell_blueprint():
    path = '/Game/World/Blueprints/BP_DustfallRockCell'
    bp = unreal.load_asset(path)
    if not bp:
        f = unreal.BlueprintFactory()
        f.set_editor_property('parent_class', unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_DustfallRockCell', '/Game/World/Blueprints', None, f)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for i, ident in enumerate(IDS):
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
        objects = [(h, lib.get_associated_object(lib.get_data(h)), str(lib.get_variable_name(lib.get_data(h)))) for h in handles]
        name = 'Rocks_' + ident
        entry = next((o for o in objects if o[2] == name), None)
        if not entry:
            handle, reason = sub.add_new_subobject(unreal.AddNewSubobjectParams(handles[0], unreal.HierarchicalInstancedStaticMeshComponent, bp))
            if not reason.is_empty():
                raise RuntimeError(str(reason))
            if not sub.rename_subobject(handle, unreal.Text(name)):
                raise RuntimeError('Cannot name instance component')
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            handles = sub.k2_gather_subobject_data_for_blueprint(bp)
            objects = [(h, lib.get_associated_object(lib.get_data(h)), str(lib.get_variable_name(lib.get_data(h)))) for h in handles]
            entry = next(o for o in objects if o[2] == name)
        c = entry[1]
        mesh = unreal.load_asset(DEST + '/' + ident + '/SM_' + ident)
        if not mesh:
            raise RuntimeError('Missing rock mesh ' + ident)
        c.set_static_mesh(mesh)
        c.set_collision_profile_name('NoCollision' if i < 3 else 'BlockAll')
        c.set_editor_property('mobility', unreal.ComponentMobility.STATIC)
        c.set_editor_property('instance_start_cull_distance', 15000 if i < 3 else 55000)
        c.set_editor_property('instance_end_cull_distance', 22000 if i < 3 else 75000)
    if not unreal.BlueprintEditorLibrary.compile_blueprint(bp):
        raise RuntimeError('Rock cell compile failed')
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    return bp


def segment_distance(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0., min(1., ((x-a[0])*dx + (y-a[1])*dy) / (dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx, y-a[1]-t*dy)


def build():
    world = unreal.EditorLevelLibrary.get_editor_world()
    if '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name():
        raise RuntimeError('Open the foundation map first')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    current = list(actors.get_all_level_actors())
    landscapes = [a for a in current if isinstance(a, unreal.LandscapeProxy)]
    ignored = [a for a in current if a not in landscapes]
    report_path = ROOT / 'Saved/Codex/landmark_build_report.json'
    landmarks = json.loads(report_path.read_text())
    cruiser = (landmarks['Cruiser']['relative_x_cm'], landmarks['Cruiser']['relative_y_cm'])
    lines = runpy.run_path(str(ROOT/'Scripts/phase2_layout.py'))['route_polylines'](cruiser)
    routes = [(a,b) for points in lines.values() for a,b in zip(points,points[1:])]
    rng = random.Random(2042)
    candidates = [(rng.uniform(-95000, 95000), rng.uniform(-95000, 95000)) for _ in range(1800)]
    for a, b in routes:
        length = math.hypot(b[0]-a[0], b[1]-a[1])
        for i in range(int(length/450)):
            t = i/max(1, int(length/450)-1)
            for side in [-1, 1]:
                offset = rng.uniform(650, 2500) * side
                candidates.append((a[0]+(b[0]-a[0])*t-(b[1]-a[1])/length*offset,
                                   a[1]+(b[1]-a[1])*t+(b[0]-a[0])/length*offset))
    placements = []
    breaker = unreal.get_default_object(unreal.GameplayStatics.static_class())
    widths = {}
    bounds_by_id = {}
    for ident in IDS:
        mesh = unreal.load_asset(DEST+'/'+ident+'/SM_'+ident)
        if not mesh:
            raise RuntimeError('Import rocks before building wasteland')
        bounds = mesh.get_bounds()
        bounds_by_id[ident] = bounds
        widths[ident] = max(bounds.box_extent.x, bounds.box_extent.y) * 2
    for x, y in candidates:
        if any(math.hypot(x-cx, y-cy) < radius for cx, cy, radius in
               [(0, 0, 1800), (15000, 10000, 1800), (35000, -25000, 1300), (*cruiser, 11500)]):
            continue
        if any(segment_distance(x, y, a, b) < 550 for a, b in routes):
            continue
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x,y,100000), unreal.Vector(x,y,-100000), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignored, unreal.DrawDebugTrace.NONE, True)
        parts = breaker.call_method('BreakHitResult', (hit,))
        if not parts[0] or parts[7].z < .65:
            continue
        index = rng.choices(range(8), weights=[22,22,22,14,9,6,4,1])[0]
        ident = IDS[index]
        desired = rng.uniform(30,120) if index < 3 else rng.uniform(250,800) if index < 6 else rng.uniform(1000,2400)
        # Keep the full mesh footprint outside routes, not only its pivot.
        if any(segment_distance(x, y, a, b) < 550 + desired*.5 for a, b in routes):
            continue
        if math.hypot(x,y) < 1800 + desired*.5:
            continue
        scale = desired / max(1., widths[ident])
        placements.append((x,y,parts[5].z,index,scale,rng.uniform(0,360)))
    if len(placements) < 500:
        raise RuntimeError('Insufficient loaded landscape or safe placements: ' + str(len(placements)))
    mat = terrain_material()
    bp = cell_blueprint()
    for a in current:
        if any(str(t) in [TAG, 'DF_Phase2_TerrainPrototype'] for t in a.tags):
            actors.destroy_actor(a)
    cells = {}
    counts = {ident:0 for ident in IDS}
    for x,y,z,index,scale,yaw in placements:
        key = (math.floor(x/25000), math.floor(y/25000))
        if key not in cells:
            origin = unreal.Vector(key[0]*25000+12500, key[1]*25000+12500, 0)
            actor = actors.spawn_actor_from_class(bp.generated_class(), origin)
            actor.set_actor_label('P2_RockCell_%d_%d' % key)
            actor.tags = [unreal.Name(TAG)]
            actor.set_folder_path('DUSTFALL/Phase2_Rocks')
            actor.set_editor_property('is_spatially_loaded', True)
            comps = actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent)
            cells[key] = (actor, {c.get_editor_property('static_mesh').get_name().removeprefix('SM_'): c for c in comps})
        actor, comps = cells[key]
        component = comps[IDS[index]]
        component.modify()
        bounds = bounds_by_id[IDS[index]]
        center = bounds.origin
        radians = math.radians(yaw)
        # Scan pivots can be offset substantially (especially ledges/cliffs).
        # Centre the actual footprint on the sampled site and seat its bottom.
        px = x-scale*(center.x*math.cos(radians)-center.y*math.sin(radians))
        py = y-scale*(center.x*math.sin(radians)+center.y*math.cos(radians))
        pz = z-scale*(center.z-bounds.box_extent.z)-5
        transform = unreal.Transform(location=unreal.Vector(px,py,pz), rotation=unreal.Rotator(yaw=yaw), scale=unreal.Vector(scale,scale,scale))
        component.add_instance(transform, True)
        actor.modify()
        counts[IDS[index]] += 1
    for landscape in landscapes:
        landscape.modify()
        landscape.set_editor_property('landscape_material', mat)
    result = {'seed':2042,'instances':len(placements),'streamed_cells':len(cells),'counts':counts,'routes_clear_radius_cm':550,'mesh_native_widths_cm':widths}
    (ROOT/'Saved/Codex/wasteland_build_report.json').write_text(json.dumps(result,indent=2))
    unreal.log('DUSTFALL wasteland: ' + str(result))


if __name__ == '__main__':
    build()
