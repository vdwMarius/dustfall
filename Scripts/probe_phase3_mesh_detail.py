"""Read-only source/assembly UV and geometry comparison."""
import json
import pathlib
import unreal

if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End PIE before mesh-detail probe: editor mesh utilities return zero while PIE runs')
result={}
sub=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
for ident in ['xgmdcay','xgkmfcy','xgjodeb','xgjnech']:
    for kind,path in [('source','/Game/World/QuixelPhase2/'+ident+'/SM_'+ident),
                      ('merged','/Game/World/Phase3/Meshes/SM_PCG_'+ident)]:
        mesh=unreal.load_asset(path)
        if not mesh and kind=='merged': mesh=unreal.load_asset('/Game/World/Phase3/Meshes/SM_SM_PCG_'+ident)
        if not mesh: continue
        entry={'mesh':mesh.get_path_name(),'uv_channels':sub.get_num_uv_channels(mesh,0),
               'materials':[[str(v.material_slot_name),v.material_interface.get_path_name() if v.material_interface else None] for v in mesh.get_editor_property('static_materials')],
               'errors':[]}
        try:
            desc=mesh.get_static_mesh_description(0)
            entry['description_vertices']=desc.get_vertex_count()
            entry['description_triangles']=desc.get_triangle_count()
            entry['vertex_instances']=desc.get_vertex_instance_count()
            samples=[]
            for i in range(0,min(entry['vertex_instances'],4096),max(1,min(entry['vertex_instances'],4096)//128)):
                vid=unreal.VertexInstanceID()
                vid.set_editor_property('id_value',i)
                if not desc.is_vertex_instance_valid(vid): continue
                uv=desc.get_vertex_instance_uv(vid,0)
                samples.append([float(uv.x),float(uv.y)])
            entry['uv0_samples']=samples[:24]
            if samples:
                entry['uv0_min']=[min(p[j] for p in samples) for j in range(2)]
                entry['uv0_max']=[max(p[j] for p in samples) for j in range(2)]
                entry['uv0_unique_samples']=len(set(tuple(p) for p in samples))
        except Exception as exc:
            entry['errors'].append(str(exc))
            entry['description_methods']={n:str(getattr(unreal.StaticMeshDescription,n).__doc__)[:500] for n in dir(unreal.StaticMeshDescription) if any(t in n for t in ['count','uv','vertex_instance'])}
            entry['vertex_id_doc']=str(unreal.VertexInstanceID.__doc__)
        result[ident+'_'+kind]=entry
path=pathlib.Path(unreal.Paths.project_dir())/'Saved/Codex/phase3_mesh_detail_probe.json'
path.write_text(json.dumps(result,indent=2))
unreal.log('Mesh detail comparison: '+str(path))
