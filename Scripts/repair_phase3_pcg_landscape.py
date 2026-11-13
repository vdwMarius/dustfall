"""One-time migrate Phase 3 graph from obsolete Landscape input to typed getter."""
import unreal
g = unreal.load_asset('/Game/World/Phase3/PCG/PCG_DustfallEnvironment')
source = next((n for n in g.get_editor_property('nodes') if isinstance(n.get_settings(),unreal.PCGGetLandscapeSettings)),None)
if not source:
    source,settings = g.add_node_of_type(unreal.PCGGetLandscapeSettings)
    source.set_editor_property('node_title',unreal.Name('Landscape source'))
    settings.set_editor_property('unbounded',False)
    source.set_node_position(-300,0)
for node in g.get_editor_property('nodes'):
    if isinstance(node.get_settings(),unreal.PCGSurfaceSamplerSettings):
        g.add_edge(source,'Out',node,'Surface')
unreal.EditorAssetLibrary.save_loaded_asset(g)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if 'DF_Phase3_PCG' in [str(t) for t in a.tags]:
        a.get_component_by_class(unreal.PCGComponent).generate(True)
unreal.log('PCG native landscape source connected and cells regenerated')
