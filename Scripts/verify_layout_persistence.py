"""Read-only full-world persistence audit; compare across real editor restarts.

Run once with SNAPSHOT_NAME='before_restart', then 'after_restart'. The audit
loads editor cells only, does not save content or generate any PCG output.
"""
import hashlib
import json
import pathlib
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
OUT = ROOT / 'Saved/Codex'
name = globals().get('SNAPSHOT_NAME', 'before_restart')
if name not in ('before_restart', 'after_restart'):
    raise ValueError('Unsupported snapshot name')
if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop PIE first')
runpy.run_path(str(ROOT/'Scripts/load_phase3_authoring_cells.py'), run_name='__main__')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
rows = []
counts = {'pcg_cells': 0, 'instances': 0, 'static_mesh_actors': 0}
for actor in actors:
    label = actor.get_actor_label()
    if actor.get_class().get_name() == 'BP_DustfallPCGCell_C':
        counts['pcg_cells'] += 1
    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = component.static_mesh
        if not mesh:
            continue
        mesh_path = mesh.get_path_name()
        if isinstance(component, unreal.InstancedStaticMeshComponent):
            count = component.get_instance_count()
            counts['instances'] += count
            for i in range(count):
                t = component.get_instance_transform(i, world_space=True)
                rows.append((mesh_path, str(t)))
        else:
            counts['static_mesh_actors'] += 1
            rows.append((label, mesh_path, str(component.get_world_transform())))
rows.sort()
digest = hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()
snapshot = {'name': name, 'counts': counts, 'layout_sha256': digest,
            'scope': 'Saved mesh transforms/instances after loading all editor cells; no regeneration. Cooked validation is separate.'}
(OUT / ('layout_' + name + '.json')).write_text(json.dumps(snapshot, indent=2))
if name == 'after_restart':
    before = json.loads((OUT/'layout_before_restart.json').read_text())
    snapshot['status'] = 'passed' if all(before[k] == snapshot[k] for k in ('counts', 'layout_sha256')) else 'failed'
    snapshot['before'] = before
    (OUT/'layout_persistence.json').write_text(json.dumps(snapshot, indent=2))
unreal.log(json.dumps(snapshot))
