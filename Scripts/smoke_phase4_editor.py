"""Brief isolated PIE functional smoke, not regression/performance acceptance.

Use after Phase4 authoring. Callable methods, no physical keyboard validation.
Only the QA slots below are deleted; user's Phase3/4 saves are untouched.
"""
import json
import pathlib
import time
import traceback
import unreal
ROOT=pathlib.Path(unreal.Paths.project_dir())
REPORT=ROOT/'Saved/Codex/phase4_smoke.json'
QA='Dustfall_Phase4_BriefQA'
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
source=next(a for a in actors.get_all_level_actors() if a.get_class().get_name()=='BP_SurvivalDirector_C')
original=source.get_editor_property('SaveSlotName')
source.set_editor_property('SaveSlotName',QA)
for slot in [QA,QA+'_Exploration']:unreal.GameplayStatics.delete_game_in_slot(slot,0)
result={'status':'running','scope':'Brief callable PIE smoke only; full regression, keyboard, reload, visual and performance validation deferred','checks':{},'errors':[]}
state={'stage':'start','handle':None,'since':time.monotonic()}
def write():REPORT.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
def check(name,ok):
    result['checks'][name]=bool(ok)
    if not ok:raise RuntimeError('Failed: '+name)
def finish():
    editor.editor_request_end_play();state.update(stage='end',since=time.monotonic());write()
def tick(delta):
    try:
        stage=state['stage']
        if stage=='end':
            if unreal.EditorLevelLibrary.get_pie_worlds(False):return
            source.set_editor_property('SaveSlotName',original)
            for slot in [QA,QA+'_Exploration']:unreal.GameplayStatics.delete_game_in_slot(slot,0)
            unreal.unregister_slate_post_tick_callback(state['handle']);write();return
        if time.monotonic()-state['since']>45:raise RuntimeError('Brief smoke timeout')
        if stage=='start':
            editor.editor_request_begin_play();state.update(stage='wait',since=time.monotonic());return
        worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:return
        world=worlds[0]
        if stage=='capture':
            if time.monotonic()-state['since']>1.0:finish()
            return
        if stage=='wait':
            if time.monotonic()-state['since']<2:return
            d=unreal.GameplayStatics.get_actor_of_class(world,unreal.DustfallExplorationDirector)
            check('native_exploration_present',d is not None)
            s=unreal.GameplayStatics.get_actor_of_class(world,unreal.load_class(None,'/Game/Systems/BP_SurvivalDirector.BP_SurvivalDirector_C'))
            state.update(d=d,s=s,p=unreal.GameplayStatics.get_player_pawn(world,0))
            s.set_editor_property('Oxygen',67.0)
            s.call_method('SaveProgress')
            check('legacy_save_success',s.get_editor_property('LastSaveSucceeded'))
            s.set_editor_property('Oxygen',21.0)
            s.call_method('LoadProgress')
            check('legacy_load_restores_value',abs(s.get_editor_property('Oxygen')-67.0)<.01)
            s.set_editor_property('CarriedScrap',2)
            s.set_editor_property('CrateScrap',3)
            migrated=d.load_exploration()
            result['migration_observed']={'loaded':migrated,'carried':d.inventory_count(),'recovery':{str(k):v for k,v in dict(d.get_editor_property('recovery_inventory')).items()}}
            check('schema1_scalar_migration',migrated and d.inventory_count()==2 and result['migration_observed']['recovery'].get('Scrap',0)==3)
            d.set_editor_property('inventory',{})
            d.set_editor_property('recovery_inventory',{})
            nodes=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.DustfallSalvageNode)
            salvage=next(a for a in nodes if not a.get_editor_property('lore_text'))
            state['p'].set_actor_location(salvage.get_actor_location()+unreal.Vector(160,0,100),False,True)
            check('world_salvage_interaction',d.interact() and salvage.get_editor_property('claimed'))
            record=next(a for a in nodes if a.get_editor_property('lore_text'))
            state['p'].set_actor_location(record.get_actor_location()+unreal.Vector(160,0,100),False,True)
            check('world_record_archived',d.interact() and len(d.get_editor_property('journal'))==1)
            d.set_editor_property('inventory',{})
            check('typed_inventory_add',d.add_item('Wiring',5) and d.add_item('PowerCell',2) and d.inventory_count()==7)
            check('capacity_rejects_without_loss',not d.add_item('Scrap',1000000) and d.inventory_count()==7)
            power=s.get_editor_property('Power')
            check('scanner_spends_power',d.pulse_scanner() and s.get_editor_property('Power')<power)
            check('beacon_place',d.place_beacon() and len(d.get_editor_property('beacons'))==1)
            check('beacon_refund',d.place_beacon() and len(d.get_editor_property('beacons'))==0 and d.inventory_count()==7)
            s.call_method('RespawnClone');state.update(stage='death',since=time.monotonic());return
        d,s,p=state['d'],state['s'],state['p']
        if stage=='death':
            if time.monotonic()-state['since']<.4:return
            crate=s.get_editor_property('RecoveryActor')
            check('recovery_cache_visible',crate is not None and not crate.get_editor_property('hidden'))
            light=crate.get_component_by_class(unreal.PointLightComponent)
            check('recovery_light_enabled',light is not None and light.get_editor_property('intensity')>0)
            check('death_moves_typed_payload',d.inventory_count()==0 and len(d.get_editor_property('recovery_inventory'))==2)
            p.set_actor_location(s.get_editor_property('CrateLocation')+unreal.Vector(0,0,65),False,True)
            check('typed_crate_recovery',d.recover_inventory() and d.inventory_count()==7)
            check('no_duplicate_recovery',not d.recover_inventory() and d.inventory_count()==7)
            check('save_snapshot',d.save_exploration())
            d.add_item('Glass',1)
            check('load_snapshot',d.load_exploration() and d.inventory_count()==7)
            d.set_symptom_intensity(0)
            check('symptoms_accessibility_off',d.get_symptom_intensity()==0 and not d.is_symptom_active())
            result['status']='passed'
            d.set_editor_property('inventory_open',True)
            d.set_editor_property('journal_open',False)
            unreal.SystemLibrary.execute_console_command(world,'Shot')
            result['viewport_capture']='Requested normal-residency game viewport Shot; inspect Saved/Screenshots/WindowsEditor'
            state.update(stage='capture',since=time.monotonic());write()
    except Exception:
        result['status']='failed';result['errors'].append(traceback.format_exc());finish()
write();state['handle']=unreal.register_slate_post_tick_callback(tick)
