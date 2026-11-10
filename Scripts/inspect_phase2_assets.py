"""Read-only saved content inventory; no asset acquisition or license inference."""
import json
import pathlib
import unreal

ROOT=pathlib.Path(unreal.Paths.project_dir()).resolve()
manifest=json.loads((ROOT/'Docs/Phase2_AssetManifest.json').read_text())
result={'assets':[],'errors':[]}
for entry in manifest['assets']:
    ident=entry['id'];record={'id':ident,'textures':{}}
    for kind in ['Albedo','Normal','Roughness']:
        texture=unreal.load_asset('/Game/World/QuixelPhase2/'+ident+'/T_'+ident+'_'+kind)
        if not texture:
            result['errors'].append('Missing texture '+ident+kind);continue
        record['textures'][kind]={'width':texture.blueprint_get_size_x(),'height':texture.blueprint_get_size_y()}
    if entry['mesh']:
        mesh=unreal.load_asset(entry['mesh'])
        if not mesh:
            result['errors'].append('Missing mesh '+ident)
        else:
            record['nanite']=mesh.get_editor_property('nanite_settings').enabled
            record['collision_primitives']=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_simple_collision_count(mesh)
            record['convex_collision_hulls']=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)
            if ident in ['xgkmfcy','xgmncdu','xgoqfid','xgjnech','xgjodeb'] and record['collision_primitives']+record['convex_collision_hulls']<=0:
                result['errors'].append('Missing or uninspectable blocking rock collision: '+ident)
    result['assets'].append(record)
result['status']='passed' if not result['errors'] else 'failed'
(ROOT/'Saved/Codex/asset_inspection.json').write_text(json.dumps(result,indent=2))
