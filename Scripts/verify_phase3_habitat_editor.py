"""PIE CharacterMovement traversal of both airlock cycles and door collision.

Owns its new PIE session; refuses to change an existing session. Writes JSON.
Uses a callable interaction event, not physical E; visual QA remains separate.
"""
import json
import pathlib
import time
import traceback
import unreal

REPORT=pathlib.Path(unreal.Paths.project_dir())/'Saved/Codex/phase3_habitat_pie.json'
QA_SLOT='Dustfall_QA_Habitat'
result={'status':'running','checks':{},'errors':[],'scope':'CharacterMovement collision and callable airlock event; physical E and visual quality require separate review.'}
state={'stage':'start','since':time.monotonic(),'handle':None,'owns_pie':False,'samples':0,'overlap':False}


def check(name,ok,detail): result['checks'][name]={'status':'pass' if ok else 'fail','detail':detail}
def stage(name): state.update(stage=name,since=time.monotonic())
def finish(status=None):
    result['status']=status or ('passed' if all(c['status']=='pass' for c in result['checks'].values()) else 'failed')
    if state['owns_pie']: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    if state['handle'] is not None: unreal.unregister_slate_post_tick_callback(state['handle']); state['handle']=None
    if not state['owns_pie'] and 'slot_actor' not in state:
        REPORT.write_text(json.dumps(result,indent=2,default=str)); return
    def cleanup(delta):
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(): return
        if 'slot_actor' in state: state['slot_actor'].set_editor_property('SaveSlotName',state['original_slot'])
        unreal.GameplayStatics.delete_game_in_slot(QA_SLOT,0)
        result['isolated_save_slot']=QA_SLOT
        REPORT.write_text(json.dumps(result,indent=2,default=str))
        unreal.unregister_slate_post_tick_callback(state['cleanup'])
    state['cleanup']=unreal.register_slate_post_tick_callback(cleanup)


def move_to(x):
    pawn=state['pawn']; dx=state['origin'].x+x-pawn.get_actor_location().x
    if abs(dx)>15: pawn.add_movement_input(unreal.Vector(1 if dx>0 else -1,0,0),1,False)
    else: pawn.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()


def tick(delta):
    try:
        age=time.monotonic()-state['since']
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if state['stage']=='start':
            if editor.get_game_world(): finish('blocked_existing_pie'); return
            slot_actor=next((a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_class().get_name()=='BP_SurvivalDirector_C'),None)
            if slot_actor:
                state.update(slot_actor=slot_actor,original_slot=slot_actor.get_editor_property('SaveSlotName'))
                slot_actor.set_editor_property('SaveSlotName',QA_SLOT)
            unreal.GameplayStatics.delete_game_in_slot(QA_SLOT,0)
            bp=unreal.load_asset('/Game/Habitat/BP_DustfallHabitatDirector')
            check('director compiles',unreal.BlueprintEditorLibrary.compile_blueprint(bp),bp.get_path_name())
            state['class']=bp.generated_class()
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play(); state['owns_pie']=True; stage('wait')
        elif state['stage']=='wait':
            world=editor.get_game_world(); pawn=unreal.GameplayStatics.get_player_pawn(world,0) if world else None
            if not pawn:
                if age>90: raise RuntimeError('PIE startup timeout')
                return
            ds=unreal.GameplayStatics.get_all_actors_of_class(world,state['class'])
            check('one habitat director',len(ds)==1,len(ds))
            if len(ds)!=1: finish(); return
            d=ds[0]; o=d.get_editor_property('HabitatOrigin')
            state.update(world=world,pawn=pawn,director=d,origin=o)
            check('spawn inside sanctuary',abs(pawn.get_actor_location().x-o.x)<475 and abs(pawn.get_actor_location().y-o.y)<325,str(pawn.get_actor_location()))
            pawn.set_actor_location(unreal.Vector(o.x+330,o.y,o.z+148),False,True); stage('closed')
        else:
            d=state['director']; o=state['origin']; pawn=state['pawn']
            inner=d.get_editor_property('InnerDoor').get_actor_location().z-o.z
            outer=d.get_editor_property('OuterDoor').get_actor_location().z-o.z
            state['samples']+=1
            if inner>300 and outer>300: state['overlap']=True
            if state['stage']=='closed':
                move_to(750)
                if age>1.5:
                    check('closed inner blocks capsule',pawn.get_actor_location().x-o.x<465,{'x_relative_cm':pawn.get_actor_location().x-o.x})
                    pawn.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
                    d.call_method('DF_RequestAirlock'); state['far_phase']=False; stage('out')
            elif state['stage']=='out':
                cycle=float(d.get_editor_property('CycleTime'))
                if cycle>=6: state['far_phase']=True
                move_to(1210 if state['far_phase'] else 750)
                if age>12.8:
                    check('exit through both doors',pawn.get_actor_location().x-o.x>1100,{'x_relative_cm':pawn.get_actor_location().x-o.x})
                    check('exit ends sealed',inner<250 and outer<250 and not d.get_editor_property('Cycling'),{'inner_z':inner,'outer_z':outer})
                    pawn.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
                    d.call_method('DF_RequestAirlock'); state['far_phase']=False; stage('in')
            elif state['stage']=='in':
                cycle=float(d.get_editor_property('CycleTime'))
                if cycle>=6: state['far_phase']=True
                move_to(300 if state['far_phase'] else 750)
                if age>12.8:
                    check('return through both doors',pawn.get_actor_location().x-o.x<400,{'x_relative_cm':pawn.get_actor_location().x-o.x})
                    check('entry ends sealed',inner<250 and outer<250 and not d.get_editor_property('Cycling'),{'inner_z':inner,'outer_z':outer})
                    check('interlock throughout traversal',not state['overlap'],{'samples':state['samples']})
                    stage('sanctuary')
                    for a in unreal.GameplayStatics.get_all_actors_of_class(state['world'],unreal.Actor):
                        if a.get_class().get_name()=='BP_SurvivalDirector_C':
                            state['survival']=a
                            state['oxygen_before']=float(a.get_editor_property('Oxygen'))
            elif state['stage']=='sanctuary' and age>2:
                if 'survival' in state:
                    s=state['survival']; now=float(s.get_editor_property('Oxygen'))
                    check('survival recognizes sanctuary',bool(s.get_editor_property('InHabitat')),str(s))
                    check('sanctuary oxygen not draining',now>=state['oxygen_before']-.01,{'before':state['oxygen_before'],'after':now})
                d.set_editor_property('Cycling',True); d.set_editor_property('TravelOut',True); d.set_editor_property('CycleTime',3.2)
                pawn.set_actor_location(unreal.Vector(o.x+500,o.y,o.z+148),False,True)
                pawn.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
                stage('obstruction')
            elif state['stage']=='obstruction' and age>1.5:
                check('doorway occupancy pauses interlocked cycle',float(d.get_editor_property('CycleTime'))<4 and inner>300 and outer<250,
                      {'time':float(d.get_editor_property('CycleTime')),'inner_z':inner,'outer_z':outer})
                finish()
    except Exception:
        result['errors'].append(traceback.format_exc()); finish('error')


REPORT.write_text(json.dumps(result,indent=2))
state['handle']=unreal.register_slate_post_tick_callback(tick)
