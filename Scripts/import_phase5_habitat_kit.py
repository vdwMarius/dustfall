"""Editor authoring only: import M4 Blender kit without touching any level.

Run using the existing editor command queue, after the Lead grants the writer lock.
Requires the generator's manifest.json beside the FBXs. Fails on scale/socket/UCX
drift instead of silently generating replacement collision or adjusting import scale.
"""
import json
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
INBOX = ROOT / 'Saved/AssetInbox/HabitatKit'
DEST = '/Game/Habitat/Kit'
REPORT = ROOT / 'Saved/Codex/phase5_habitat_kit_import.json'
LIB = unreal.EditorAssetLibrary

# Existing materials contain the project's rust/dust world-position detail.
# Instances inherit those graphs; this importer never edits their parents.
PARENTS = {
    'M_Hab_PaintedMetal': 'M_P3_Hab_PaleMetal',
    'M_Hab_BareMetal': 'M_P3_Hab_RustedMetal',
    'M_Hab_DarkMetal': 'M_P3_Hab_Charcoal',
    'M_Hab_Rubber': 'M_P3_Hab_Charcoal',
    'M_Hab_Glass': 'M_P3_Hab_Solar',
    'M_Hab_Emissive_Warm': 'M_P3_Hab_Amber',
    'M_Hab_Emissive_Cool': 'M_P3_Hab_Cool',
    'M_Hab_InteriorPanel': 'M_P3_Hab_PaleMetal',
    'M_Hab_Fabric': 'M_P3_Hab_Bedding',
    'M_Hab_Hazard': None,
}
COLORS = {
    'PaintedMetal': (.46,.40,.30), 'BareMetal': (.29,.30,.28),
    'DarkMetal': (.055,.065,.065), 'Rubber': (.018,.023,.022),
    'Glass': (.035,.15,.18), 'Emissive_Warm': (1,.48,.12),
    'Emissive_Cool': (.15,.68,1), 'InteriorPanel': (.37,.35,.29),
    'Fabric': (.16,.12,.075), 'Hazard': (.85,.49,.035),
}


def require(value, message):
    if not value:
        raise RuntimeError(message)
    return value


def fallback_parent(slot):
    """Only create missing preview parents inside Kit; no changes to shared assets."""
    name = slot + '_PreviewParent'
    path = DEST + '/Materials/' + name
    m = LIB.load_asset(path)
    if m:
        return m
    m = require(unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, DEST+'/Materials', unreal.Material, unreal.MaterialFactoryNew()), path)
    g = unreal.MaterialEditingLibrary
    key = slot.removeprefix('M_Hab_')
    color = g.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    color.set_editor_property('constant', unreal.LinearColor(*COLORS[key], 1))
    g.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    rough = g.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 180)
    rough.set_editor_property('r', .65)
    g.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    if key.startswith('Emissive_'):
        g.connect_material_property(color, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    g.recompile_material(m)
    LIB.save_loaded_asset(m, False)
    return m


def material_instance(slot):
    name = 'MI_' + slot.removeprefix('M_')
    path = DEST+'/Materials/'+name
    parent_name = PARENTS[slot]
    parent = LIB.load_asset('/Game/Habitat/Materials/'+parent_name) if parent_name else None
    parent = parent or fallback_parent(slot)
    mi = LIB.load_asset(path)
    if not mi:
        mi = require(unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, DEST+'/Materials', unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew()), 'Cannot create '+path)
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
    LIB.save_loaded_asset(mi, False)
    return mi


def vector(v):
    return [v.x,v.y,v.z]


def verify_mesh(mesh, expected, subsystem):
    bounds = mesh.get_bounds()
    origin, extent = vector(bounds.origin), vector(bounds.box_extent)
    actual = [[origin[i]-extent[i] for i in range(3)],
              [origin[i]+extent[i] for i in range(3)]]
    require(all(abs(actual[j][i]-expected['bounds_cm'][j][i])<.5
                for j in range(2) for i in range(3)),
            'FBX units/axes/bounds mismatch: '+mesh.get_name()+' '+str(actual))
    hulls = subsystem.get_convex_collision_count(mesh)
    require(hulls == expected['convex_hulls'],
            'UCX hull count mismatch: '+mesh.get_name()+' '+str(hulls))
    sockets = []
    for socket in expected['sockets']:
        # UE strips SOCKET_ when constructing a UStaticMeshSocket.
        name = socket['name'].removeprefix('SOCKET_')
        s = require(mesh.find_socket(name), 'Missing socket '+mesh.get_name()+':'+name)
        location = vector(s.get_editor_property('relative_location'))
        rotation = s.get_editor_property('relative_rotation')
        require(all(abs(location[i]-socket['position_cm'][i])<.1 for i in range(3)),
                'Socket translation mismatch '+name+':'+str(location))
        direction = unreal.MathLibrary.get_forward_vector(rotation)
        import math
        angle = math.radians(socket['yaw_degrees'])
        require(abs(direction.x-math.cos(angle))<.005 and
                abs(direction.y-math.sin(angle))<.005 and abs(direction.z)<.005,
                'Socket +X direction mismatch '+name)
        sockets.append({'name':name,'location_cm':location,'outward':vector(direction)})
    require(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'),
            'Nanite disabled '+mesh.get_name())
    return {'bounds_cm':actual,'convex_hulls':hulls,'sockets':sockets,'nanite':True}


def run(inbox=INBOX):
    inbox = Path(inbox)
    manifest = json.loads((inbox/'manifest.json').read_text())
    files = sorted(inbox.glob('SM_Hab_*.fbx'))
    require(files, 'No habitat FBXs in '+str(inbox))
    require({p.stem for p in files} == set(manifest['pieces']),
            'Manifest must match every FBX in inbox; regenerate the complete kit')
    require(manifest['validation']['sanctuary_contained'] and manifest['validation']['capsule_clear'],
            'Generator contract validation missing or failed')
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    materials = {slot:material_instance(slot) for slot in PARENTS}
    report = {'status':'running','inbox':str(inbox),'destination':DEST,'meshes':{},
              'level_modified':False,'validation':manifest['validation']}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    try:
        for path in files:
            options = unreal.FbxImportUI()
            for prop,value in [('import_mesh',True),('import_as_skeletal',False),
                               ('import_materials',False),('import_textures',False),
                               ('automated_import_should_detect_type',False),
                               ('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)]:
                options.set_editor_property(prop,value)
            data = options.static_mesh_import_data
            for prop,value in [('combine_meshes',False),('auto_generate_collision',False),
                               ('one_convex_hull_per_ucx',True),('build_nanite',True),
                               ('generate_lightmap_u_vs',False),('import_uniform_scale',1.0),
                               ('convert_scene',True),('convert_scene_unit',True),
                               ('force_front_x_axis',False),('transform_vertex_to_absolute',True),
                               ('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)]:
                data.set_editor_property(prop,value)
            task = unreal.AssetImportTask()
            task.set_editor_property('factory', unreal.FbxFactory())
            for prop,value in [('filename',str(path)),('destination_path',DEST),
                               ('destination_name',path.stem),('automated',True),
                               ('replace_existing',True),('save',False),('options',options)]:
                task.set_editor_property(prop,value)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            mesh = require(LIB.load_asset(DEST+'/'+path.stem), 'Import failed '+path.stem)
            require(isinstance(mesh,unreal.StaticMesh), 'Expected static mesh '+path.stem)
            for index,slot in enumerate(mesh.get_editor_property('static_materials')):
                slot_name = str(slot.get_editor_property('imported_material_slot_name'))
                require(slot_name in materials, 'Unknown material slot '+slot_name)
                mesh.set_material(index,materials[slot_name])
            report['meshes'][path.stem] = verify_mesh(mesh,manifest['pieces'][path.stem],subsystem)
            LIB.save_loaded_asset(mesh,False)
        report['status']='passed'
    except Exception as exc:
        report['status']='failed'; report['error']=str(exc)
        raise
    finally:
        REPORT.write_text(json.dumps(report,indent=2)+'\n')
    unreal.log('Habitat kit imported and verified; existing habitat/level untouched: '+str(REPORT))
    return report


if __name__=='__main__':
    run()
