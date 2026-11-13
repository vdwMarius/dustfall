"""Read-only PCG geometry/rendering audit; queue with all authoring cells loaded.

Checks actual components/instances, not only builder inputs. It does not test
visual acceptance, GPU cost, or physical movement through generated collision.
"""
import hashlib
import json
import math
import pathlib
import runpy
import struct
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world(): raise RuntimeError('End PIE before full-world PCG authoring audit')
if '/Game/World/Maps/L_Dustfall_Foundation' not in editor.get_editor_world().get_path_name():
    raise RuntimeError('Open the foundation map before PCG audit')
runpy.run_path(str(ROOT/'Scripts/load_phase3_authoring_cells.py'),run_name='__main__')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = list(actors.get_all_level_actors())
cells = [a for a in all_actors if 'DF_Phase3_PCG' in [str(t) for t in a.tags]]
report = {'status':'running','loaded_cells':len(cells),'cells':{},'meshes':{},
          'counts':{'rocks':0,'dust_sheets':0,'debris':0},'errors':[],
          'limits':'Read-only component audit; does not establish visual or performance acceptance.'}
digest = hashlib.sha256()
layout_records = []
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
landmarks = json.loads((ROOT/'Saved/Codex/landmark_build_report.json').read_text())
cruiser = (landmarks['Cruiser']['relative_x_cm'],landmarks['Cruiser']['relative_y_cm'])
lines = runpy.run_path(str(ROOT/'Scripts/phase2_layout.py'))['route_polylines'](cruiser)
segments = [(a,b) for points in lines.values() for a,b in zip(points,points[1:])]


def segment_distance(x,y,a,b):
    dx,dy = b[0]-a[0],b[1]-a[1]
    t = max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)


minimum = {'route_center_clearance_cm':float('inf'),'home_center_clearance_cm':float('inf')}
variations = {}
for actor in sorted(cells,key=lambda a:a.get_actor_label()):
    pcg = actor.get_component_by_class(unreal.PCGComponent)
    item = {'counts':{},'generated':pcg.get_editor_property('generated'),
            'graph_assigned':pcg.get_graph() is not None,
            'spatially_loaded':actor.get_editor_property('is_spatially_loaded'),
            'generation_trigger':str(pcg.get_editor_property('generation_trigger')),
            'seed':pcg.get_editor_property('seed')}
    for component in sorted(actor.get_components_by_class(unreal.InstancedStaticMeshComponent),key=lambda c:c.get_path_name()):
        mesh = component.static_mesh
        if not mesh: continue
        path = mesh.get_path_name()
        count = component.get_instance_count()
        tags = [str(t) for t in component.component_tags]
        kind = 'debris' if 'DF_Phase3_PCGDebris' in tags else 'dust_sheets' if path.startswith('/Engine/BasicShapes/Plane') else 'rocks'
        report['counts'][kind] += count
        item['counts'][path] = item['counts'].get(path,0)+count
        if path not in report['meshes']:
            report['meshes'][path] = {'kind':kind,'nanite':mesh.get_editor_property('nanite_settings').enabled,
                                     'convex_hulls':subsystem.get_convex_collision_count(mesh),
                                     'collision_profile':str(component.get_collision_profile_name()),
                                     'cull_start':component.get_editor_property('instance_start_cull_distance'),
                                     'cull_end':component.get_editor_property('instance_end_cull_distance')}
        record = variations.setdefault(path,{'scale_min':[float('inf')]*3,'scale_max':[0.]*3,
                                            'height_min_cm':float('inf'),'height_max_cm':float('-inf')})
        for index in range(count):
            transform = component.get_instance_transform(index,world_space=True)
            location = transform.translation
            scale = transform.scale3d
            for j,v in enumerate([scale.x,scale.y,scale.z]):
                record['scale_min'][j]=min(record['scale_min'][j],v)
                record['scale_max'][j]=max(record['scale_max'][j],v)
            record['height_min_cm']=min(record['height_min_cm'],location.z)
            record['height_max_cm']=max(record['height_max_cm'],location.z)
            rotation = transform.rotation
            layout_records.append((path,location.x,location.y,location.z,rotation.x,rotation.y,rotation.z,rotation.w,scale.x,scale.y,scale.z))
            if kind=='rocks':
                distances=[segment_distance(location.x,location.y,a,b) for a,b in segments]
                nearest=min(distances)
                if nearest<minimum['route_center_clearance_cm']:
                    minimum['route_center_clearance_cm']=nearest
                    report['closest_route_rock']={'mesh':path,'location_cm':[location.x,location.y,location.z],
                                                   'scale':[scale.x,scale.y,scale.z],
                                                   'segment':segments[distances.index(nearest)],
                                                   'cell':actor.get_actor_label()}
                minimum['home_center_clearance_cm']=min(minimum['home_center_clearance_cm'],math.hypot(location.x,location.y))
    report['cells'][actor.get_actor_label()]=item
report['variations']=variations
report['minimum_clearances']=minimum
for record in sorted(layout_records):
    digest.update(record[0].encode())
    digest.update(struct.pack('<10d',*record[1:]))
report['layout_sha256']=digest.hexdigest()
report['render_cvars']={name:unreal.SystemLibrary.get_console_variable_int_value(name)
                        for name in ['r.Nanite','r.DynamicGlobalIlluminationMethod','r.ReflectionMethod','r.Shadow.Virtual.Enable']}
report['legacy_rock_cells_loaded']=sum('DF_Phase2_RockCell' in [str(t) for t in a.tags] for a in all_actors)
report['legacy_debris_actors_loaded']=sum('DF_Phase2_Debris' in [str(t) for t in a.tags] for a in all_actors)
if len(cells)!=64: report['errors'].append('Full audit needs all64PCGcells loaded')
if any(not v['graph_assigned'] or not v['generated'] for v in report['cells'].values()): report['errors'].append('Missing assigned/generated graph')
if any(v['kind']=='rocks' and not v['nanite'] for v in report['meshes'].values()): report['errors'].append('Opaque rock output lacks Nanite')
if minimum['route_center_clearance_cm']<550: report['errors'].append('Rock center intrudes into route clearance')
if minimum['home_center_clearance_cm']<2100: report['errors'].append('Rock center intrudes into home clearance')
report['status']='passed' if not report['errors'] else 'failed'
(ROOT/'Saved/Codex/phase3_environment_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('Phase3environment inspection: '+report['status']+' '+str(report['counts']))
