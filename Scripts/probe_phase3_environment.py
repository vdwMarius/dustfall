"""Read-only environment API inventory for the lead's single editor."""
import unreal
import json
import pathlib

names = ['PCGGraph','PCGGraphFactory','PCGVolume','PCGComponent','PCGPoint',
         'PCGSurfaceSamplerSettings','PCGSpatialNoiseSettings','PCGDensityFilterSettings',
         'PCGCreatePointsSettings','PCGDifferenceSettings','PCGStaticMeshSpawnerSettings',
         'PCGMeshSelectorWeighted','PCGMeshSelectorWeightedEntry','PCGSoftISMComponentDescriptor',
         'PCGTransformPointsSettings','StaticMeshEditorSubsystem','MergeStaticMeshActorsOptions',
         'MeshMergingSettings','LocalFogVolume','LocalFogVolumeComponent','PCGToolset']
result = {}
for name in names:
    cls = getattr(unreal,name,None)
    entry = {'exists':cls is not None}
    if cls:
        entry['doc'] = str(cls.__doc__)[:20000]
        entry['methods'] = {n:str(getattr(cls,n).__doc__)[:1500] for n in dir(cls)
                            if any(k in n for k in ['add_node','get_input','merge_static','set_graph','generate','create_graph','create_volume','get_graph','remove_node'])}
    result[name] = entry
path = pathlib.Path(unreal.Paths.project_dir())/'Saved/Codex/phase3_environment_probe.json'
path.write_text(json.dumps(result,indent=2),encoding='utf-8')
unreal.log('Environment API probe: '+str(path))
