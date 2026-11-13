"""Fast read-only actual PCG audit. Load all 64 authoring cells beforehand.

Does not generate, load cells, save assets, change streaming, or run navigation.
The builder calls audit() before saving; standalone writes only its JSON report.
"""
import collections
import hashlib
import json
import math
import pathlib
import runpy
import struct


def audit(root):
    import unreal
    builder=runpy.run_path(str(root/'Scripts/build_phase5_dressing.py'))
    pure,inputs=builder['load_inputs'](root)
    tag=builder['TAG']; rules=inputs.rules
    if unreal.EditorLevelLibrary.get_game_world(): raise RuntimeError('Stop PIE for read-only dressing audit')
    world=unreal.EditorLevelLibrary.get_editor_world()
    if '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name(): raise RuntimeError('Open foundation map')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    meshsub=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    cells=[a for a in actors.get_all_level_actors() if 'DF_Phase3_PCG' in map(str,a.tags)]
    report=dict(status='running',cells={},counts={},collision_checks={},errors=[],corridor_violation_count=0,
                mask_checks={'size':inputs.size,'path_nonzero_texels':sum(v>0 for v in inputs.path_mask),
                             'cliff_texels':inputs.cliff_mask.count(255),'talus_texels':inputs.cliff_mask.count(85)},
                limits='Component/bounds/mask audit only; no gameplay, visual, persistence, HLOD or performance acceptance')
    counts=collections.Counter(); violations=[]; records=[]
    landscapes=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.LandscapeProxy)]
    report['landscape_materials']=[]
    for landscape in landscapes:
        material=landscape.get_editor_property('landscape_material')
        path=material.get_path_name() if material else ''
        report['landscape_materials'].append(path)
        if not path.startswith(builder['DEST']+'/Materials/M_Wasteland_Tracks_'):
            report['errors'].append('Landscape missing world-position track material')
    if not landscapes:report['errors'].append('Landscape proxies are not loaded')
    texture=unreal.load_asset(builder['DEST']+'/Materials/T_TerrainPaths')
    if not texture or texture.get_editor_property('srgb'):report['errors'].append('Track mask texture missing or sRGB')
    for actor in cells:
        label=actor.get_actor_label(); pcg=actor.get_component_by_class(unreal.PCGComponent)
        item=dict(counts={},spatially_loaded=actor.get_editor_property('is_spatially_loaded'))
        if not pcg or not pcg.generated or pcg.generation_in_progress or not pcg.get_graph() or not pcg.get_graph().get_path_name().startswith(builder['DEST']+'/PCG/'):
            report['errors'].append('Missing completed Phase5 graph: '+label)
        if not item['spatially_loaded']: report['errors'].append('Cell not spatially streamed: '+label)
        local=collections.Counter()
        for component in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            tags=list(map(str,component.component_tags));mesh=component.static_mesh
            if not mesh: continue
            if tag in tags:
                kind=next((t.removeprefix('DF_P5_') for t in tags if t.startswith('DF_P5_')),None)
                if kind not in rules: report['errors'].append('Unknown category on '+component.get_path_name());continue
            elif 'DF_Phase3_PCGDebris' in tags: kind='debris'
            elif mesh.get_path_name().startswith('/Engine/BasicShapes/Plane'): kind='dust'
            else:
                if component.get_instance_count(): report['errors'].append('Unreplaced legacy rock output '+component.get_path_name())
                continue
            path=mesh.get_path_name(); number=component.get_instance_count();counts[kind]+=number;local[kind]+=number
            blocking=str(component.get_collision_profile_name()) not in ('NoCollision','None')
            b=mesh.get_bounds(); bounds=([b.origin.x,b.origin.y,b.origin.z],[b.box_extent.x,b.box_extent.y,b.box_extent.z])
            convex=meshsub.get_convex_collision_count(mesh); simple=meshsub.get_simple_collision_count(mesh)
            report['collision_checks'][path]=dict(nanite=mesh.get_editor_property('nanite_settings').enabled,
                convex_hulls=convex,simple_shapes=simple,blocking=blocking)
            if kind!='dust' and not mesh.get_editor_property('nanite_settings').enabled: report['errors'].append('Nanite disabled '+path)
            if kind in ('cliffs','spires','rims','slopes','talus') and (not blocking or convex+simple==0):
                report['errors'].append('Missing matching blocking simple/convex collision '+path)
            for index in range(number):
                transform=component.get_instance_transform(index,world_space=True);p=transform.translation;s=transform.scale3d
                q=transform.rotation; rotation=q.rotator()
                records.append((path,kind,p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z))
                if kind=='dust': continue # Airborne sheets are nonblocking, not geology.
                radius,_=pure['footprint'](bounds,[s.x,s.y,s.z],rotation.pitch,rotation.roll)
                if not inputs.clear(p.x,p.y,radius):
                    report['corridor_violation_count']+=1
                    if len(violations)<32:violations.append(dict(cell=label,kind=kind,mesh=path,index=index,xy_cm=[p.x,p.y],radius_cm=radius))
                if kind in ('cliffs','talus'):
                    expected=255 if kind=='cliffs' else 85
                    if inputs.mask(inputs.cliff_mask,p.x,p.y)!=expected:
                        report['errors'].append('Output outside '+kind+' mask: '+label)
        item['counts']=dict(local);report['cells'][label]=item
    rock_count=sum(v for k,v in counts.items() if k not in ('dust','debris','stakes'))
    if len(cells)!=64: report['errors'].append('Expected 64 loaded cells, got '+str(len(cells)))
    if report['corridor_violation_count']: report['errors'].append('Actual instance footprints intersect corridors/protected areas/world edge')
    if rock_count>rules['max_rock_instances']: report['errors'].append('Rock instance budget exceeded')
    for kind in ('flats','slopes','talus','cliffs','rims','edges','spires','stakes'):
        if counts[kind]==0:report['errors'].append('No actual output for '+kind)
    expected_spires=sum(f['dressing']['count']*rules['spires']['tiers'] for f in inputs.features['features'] if f['type']=='spire_base')
    if counts['spires']!=expected_spires:report['errors'].append('Spire assembly count does not match all 51 designed spires')
    if not all(report['mask_checks'][k]>0 for k in ('path_nonzero_texels','cliff_texels','talus_texels')):report['errors'].append('Terrain masks empty')
    digest=hashlib.sha256()
    for record in sorted(records):
        digest.update((record[0]+'|'+record[1]).encode());digest.update(struct.pack('<10d',*record[2:]))
    report.update(status='passed' if not report['errors'] else 'failed',counts=dict(counts),rock_instances=rock_count,
                  instances_per_cell={k:sum(v['counts'].values()) for k,v in report['cells'].items()},
                  corridor_violations_sample=violations,layout_sha256=digest.hexdigest())
    report['errors']=sorted(set(report['errors']))
    return report


if __name__=='__main__':
    import unreal
    root=pathlib.Path(unreal.Paths.project_dir());report=audit(root)
    (root/'Saved/Codex/phase5_dressing_verify.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('Phase5 dressing '+report['status']+': '+str(report['counts']))
