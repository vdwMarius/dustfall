"""Author native Phase4 exploration after Phase3 acceptance gates; single writer only.

Requires compiled/restarted native classes. Idempotently updates stable nodes;
keeps Phase3 suit and airlock assets. No Python dependency in packaged gameplay.
"""
import json
import pathlib
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
TAG = 'DF_Phase4_Exploration'

def main():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('Stop PIE before authoring')
    if '/Game/World/Maps/L_Dustfall_Foundation' not in editor.get_editor_world().get_path_name():
        raise RuntimeError('Foundation map required')
    if not hasattr(unreal, 'DustfallExplorationDirector'):
        raise RuntimeError('Compile and restart native editor first')
    runpy.run_path(str(ROOT/'Scripts/load_phase3_authoring_cells.py'), run_name='__main__')
    subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    current=list(subsystem.get_all_level_actors())
    ox,oy,oz=runpy.run_path(str(ROOT/'Scripts/habitat_layout.py'))['habitat_origin'](current)
    survival=next(a for a in current if a.get_class().get_name()=='BP_SurvivalDirector_C')
    folder='/Game/Data'
    tuning=unreal.load_asset(folder+'/DA_Exploration_Phase4')
    if not tuning:
        factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.DustfallExplorationTuning)
        tuning=unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_Exploration_Phase4',folder,unreal.DustfallExplorationTuning,factory)
    if not tuning:raise RuntimeError('Exploration tuning creation failed')
    unreal.EditorAssetLibrary.save_loaded_asset(tuning,False)
    director=next((a for a in current if isinstance(a,unreal.DustfallExplorationDirector)),None)
    if not director:director=subsystem.spawn_actor_from_class(unreal.DustfallExplorationDirector,unreal.Vector(ox,oy,oz))
    director.modify();director.set_actor_label('Dustfall Exploration Director')
    director.set_editor_property('is_spatially_loaded',False)
    director.set_editor_property('survival_director',survival);director.set_editor_property('tuning',tuning)
    director.tags=[unreal.Name(TAG)];director.set_folder_path('DUSTFALL/Phase4')
    # Protected approaches keep these small interactive nodes out of dense PCG.
    specs=[
        ('route_power_01',2300,1300,'PowerCell',3,'EMERGENCY CELL CANISTER','',0),
        ('route_scrap_01',4200,3400,'Scrap',8,'TORN SERVICE CASING','',0),
        ('route_wiring_01',8000,5200,'Wiring',5,'SEVERED CONDUIT','',0),
        ('wreck_glass_01',12900,8600,'Glass',4,'TRANSPORT OPTICS','',0),
        ('wreck_polymer_01',13700,9200,'Polymer',6,'SEALED CARGO LINER','',0),
        ('ruin_fragment_01',33900,-24100,'AlienFragment',1,'UNIDENTIFIED FRAGMENT','',0),
        ('route_log_01',5700,3900,'',0,'RECORD 01 / THE WAY HOME',
         'The amber lamps are yours. Keep them behind your left shoulder.\nThe transport has spare cells. Do not spend your last breath searching it.',1),
        ('wreck_log_01',13200,10200,'',0,'RECORD 02 / FLIGHT CREW',
         'We landed three times. The recorder insists this is the first.\nI marked the damaged hatch with two strips of amber tape.',4),
        ('ruin_log_01',34500,-23600,'',0,'RECORD 03 / MATCHING SERIAL',
         'The suit outside carries my serial. Its log ends tomorrow.\nI have left the route open. Whoever reads this: return before dusk.',7),
    ]
    ignored=[a for a in current if not isinstance(a,unreal.LandscapeProxy)]
    world=editor.get_editor_world()
    breaker=unreal.get_default_object(unreal.GameplayStatics.static_class())
    def ground(x,y):
        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,50000),unreal.Vector(x,y,-50000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,unreal.DrawDebugTrace.NONE,True)
        data=breaker.call_method('BreakHitResult',(hit,))
        if not data[0]:raise RuntimeError('Missing loaded landscape below salvage %s,%s'%(x,y))
        return float(data[5].z)
    rusty=unreal.load_asset('/Game/World/QuixelPhase2/wcljbdb/M_wcljbdb')
    records=[]
    wreck_report=ROOT/'Saved/Codex/phase4_wreck_build.json'
    wreck_positions={}
    if wreck_report.exists():
        wreck=json.loads(wreck_report.read_text(encoding='utf-8'))
        for index,position in enumerate(wreck.get('salvage_cm',[])):
            identity='wreck_interior_%02d'%index
            specs.append((identity,0,0,'PowerCell' if index==0 else 'Wiring',2 if index==0 else 7,'CARGO CELL RESERVE' if index==0 else 'FLIGHT BUS COUPLER','',0))
            wreck_positions[identity]=unreal.Vector(*position)
        if wreck.get('lore_cm'):
            identity='wreck_bridge_record'
            specs.append((identity,0,0,'',0,'RECORD 04 / CREW MANIFEST','The cargo manifest lists one passenger. The airlock counted two.\nOne suit is still answering the roll call.',5))
            wreck_positions[identity]=unreal.Vector(*wreck['lore_cm'])
    for identity,x,y,item,quantity,label,lore,strain in specs:
        node=next((a for a in current if isinstance(a,unreal.DustfallSalvageNode) and str(a.get_editor_property('stable_id'))==identity),None)
        position=wreck_positions.get(identity)
        if position is None:position=unreal.Vector(ox+x,oy+y,ground(ox+x,oy+y)+25)
        if not node:node=subsystem.spawn_actor_from_class(unreal.DustfallSalvageNode,position)
        node.modify();node.set_actor_location(position,False,True)
        node.set_actor_label('P4_'+identity);node.tags=[unreal.Name(TAG)]
        node.set_folder_path('DUSTFALL/Phase4/Records' if lore else 'DUSTFALL/Phase4/Salvage')
        for name,value in [('stable_id',unreal.Name(identity)),('item_id',unreal.Name(item)),('quantity',quantity),('display_name',label),('lore_text',lore),('lore_strain',strain)]:node.set_editor_property(name,value)
        # Small nodes remain loaded so scanner targets/claims survive streaming boundaries.
        node.set_editor_property('is_spatially_loaded',False)
        mesh=node.get_editor_property('mesh')
        if rusty:mesh.set_material(0,rusty)
        label_component=node.get_editor_property('label')
        label_component.set_editor_property('ld_max_draw_distance',1400)
        records.append(dict(id=identity,item=item,quantity=quantity,location=[position.x,position.y,position.z],lore=bool(lore)))
    mode=unreal.load_asset('/Game/Core/BP_DustfallGameMode')
    mode.modify();unreal.get_default_object(mode.generated_class()).set_editor_property('hud_class',unreal.DustfallExplorationHUD)
    unreal.EditorAssetLibrary.save_loaded_asset(mode,False)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_all_dirty_levels()
    report={'status':'built; runtime validation pending','native_director':director.get_path_name(),'tuning':tuning.get_path_name(),'nodes':records,'save_policy':'Schema2 full exploration snapshot in Phase3-slot companion; schema1 scalar migration'}
    (ROOT/'Saved/Codex/phase4_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('Phase4 native exploration authored. Run verify_phase4_editor.py.')

if __name__=='__main__':main()
