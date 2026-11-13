"""PIE collision/impact/pit escape and recoverable-death-cache regression.

Teleports only arrange the start of each case; descent and escape use real
CharacterMovement. Saves are isolated; no asset writes or user save mutation.
"""
import json
import math
import pathlib
import time
import traceback
import unreal

ROOT=pathlib.Path(unreal.Paths.project_dir())
REPORT=ROOT/'Saved/Codex/phase3_hazard_verification.json'
SLOT='Dustfall_Phase3_HazardQA'
result={'status':'running','checks':{},'errors':[],
        'scope':'Real PIE falling collision/impact/escape; teleports arrange cases, callable cache recovery.'}
state={'stage':'start','since':time.monotonic(),'handle':None,'owns_pie':False}
editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def write():
    result['active_stage']=state['stage']
    REPORT.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')


def stage(name):
    state.update(stage=name,since=time.monotonic());write()


def check(name,ok,detail):
    result['checks'][name]={'status':'pass' if ok else 'fail','detail':detail}


def prop(name): return state['survival'].get_editor_property(name)
def setprop(name,value): state['survival'].set_editor_property(name,value)


def ground(x,y):
    world=state['world']
    ignore=[a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
            if not isinstance(a,unreal.LandscapeProxy)]
    hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,30000),unreal.Vector(x,y,-30000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
    parts=unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method('BreakHitResult',(hit,))
    if not parts[0]: raise RuntimeError('Terrain collision trace missed at %s,%s'%(x,y))
    return parts[5].z


def place(x,y,lift=0):
    state['movement'].stop_movement_immediately()
    state['pawn'].set_actor_location(unreal.Vector(x,y,ground(x,y)+state['halfheight']+8+lift),False,True)
    state['movement'].set_movement_mode(unreal.MovementMode.MOVE_FALLING)


def finish(status):
    if status=='completed':
        result['status']='failed' if any(c['status']!='pass' for c in result['checks'].values()) else 'passed'
    else: result['status']=status
    if state['owns_pie']:
        editor.editor_request_end_play();stage('cleanup')
    else: cleanup()


def cleanup():
    if 'editor_survival' in state:
        state['editor_survival'].set_editor_property('SaveSlotName',state['original_slot'])
    for suffix in ['', '_Exploration']:
        unreal.GameplayStatics.delete_game_in_slot(SLOT+suffix,0)
    write()
    if state['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(state['handle']);state['handle']=None


def tick(delta):
    try:
        age=time.monotonic()-state['since']; mode=state['stage']
        if mode=='cleanup':
            if not unreal.EditorLevelLibrary.get_pie_worlds(False):cleanup()
            return
        if mode=='start':
            if unreal.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('Stop PIE before hazard test')
            cls=unreal.load_class(None,'/Game/Systems/BP_SurvivalDirector.BP_SurvivalDirector_C')
            actor=next(a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_class()==cls)
            state.update(editor_survival=actor,original_slot=actor.get_editor_property('SaveSlotName'),survival_cls=cls)
            actor.set_editor_property('SaveSlotName',SLOT)
            unreal.GameplayStatics.delete_game_in_slot(SLOT,0)
            unreal.GameplayStatics.delete_game_in_slot(SLOT+'_Exploration',0)
            editor.editor_request_begin_play();state['owns_pie']=True;stage('wait')
        elif mode=='wait':
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            world=worlds[0] if worlds else None
            pawn=unreal.GameplayStatics.get_player_pawn(world,0) if world else None
            if not pawn:
                if age>60:raise RuntimeError('PIE spawn timeout')
                return
            survival=unreal.GameplayStatics.get_all_actors_of_class(world,state['survival_cls'])[0]
            cls=unreal.load_class(None,'/Script/dustfall.DustfallTerrainHazardDirector')
            hazards=unreal.GameplayStatics.get_all_actors_of_class(world,cls)
            if len(hazards)!=1:raise RuntimeError('Expected one always-loaded terrain hazard director')
            state.update(world=world,pawn=pawn,survival=survival,hazard=hazards[0],
                movement=pawn.get_component_by_class(unreal.CharacterMovementComponent),
                halfheight=pawn.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height())
            place(-8500,-3000)
            stage('rim')
        elif mode=='rim':
            if age<3:return
            state['rim']=state['pawn'].get_actor_location()
            state['generation']=int(prop('CloneGeneration'))
            setprop('Integrity',100.)
            place(-8500,-6500,1200)
            stage('impact')
        elif mode=='impact':
            if age<.4:return
            if state['movement'].is_falling():
                if age>12:raise RuntimeError('Pit fall collision timeout')
                return
            damage=float(state['hazard'].get_editor_property('LastImpactDamage'))
            check('physical pit landing applies suit damage',damage>0 and float(prop('Integrity'))<100,
                {'last_impact_damage':damage,'integrity':prop('Integrity'),'landing':state['pawn'].get_actor_location()})
            check('nonfatal impact preserves clone',int(prop('CloneGeneration'))==state['generation'],prop('CloneGeneration'))
            state.update(previous_distance=float('inf'),progress_time=time.monotonic())
            stage('escape')
        elif mode=='escape':
            for key in ['Oxygen','Power','Stamina']:setprop(key,100.)
            p=state['pawn'].get_actor_location();dx=-4100-p.x;dy=-6500-p.y;distance=math.hypot(dx,dy)
            if distance<180:
                check('pit east ramp escape by walking',True,{'position':p,'seconds':age})
                place(-8500,-3000);stage('fatal_rim');return
            if distance<state['previous_distance']-25:
                state.update(previous_distance=distance,progress_time=time.monotonic())
            if age>60 or time.monotonic()-state['progress_time']>10:
                check('pit east ramp escape by walking',False,{'position':p,'distance_cm':distance});finish('completed');return
            state['pawn'].add_movement_input(unreal.Vector(dx/distance,dy/distance,0),1.,False)
        elif mode=='fatal_rim':
            if age<3:return
            state['rim']=state['hazard'].get_editor_property('LastSafeLocation')
            state['generation']=int(prop('CloneGeneration'))
            setprop('Integrity',1.);setprop('CarriedScrap',9)
            place(-8500,-6500,1800);stage('fatal')
        elif mode=='fatal':
            if int(prop('CloneGeneration'))==state['generation']:
                if age>15:raise RuntimeError('Fatal impact did not create a new clone')
                return
            stage('cache_settle')
        elif mode=='cache_settle':
            if age<1:return
            crate=prop('CrateLocation');rim=state['rim']
            d=math.hypot(crate.x-rim.x,crate.y-rim.y)
            check('fatal impact clones once',int(prop('CloneGeneration'))==state['generation']+1,prop('CloneGeneration'))
            check('fatal cache relocated to safe rim',bool(prop('CrateActive')) and d<150,
                {'crate':crate,'safe_rim':rim,'horizontal_distance_cm':d})
            place(crate.x,crate.y);stage('recover')
        elif mode=='recover':
            if age<2:return
            state['survival'].call_method('RecoverCrate')
            check('rim cache payload recovered once',not bool(prop('CrateActive')) and int(prop('CarriedScrap'))>=9,
                {'crate_active':prop('CrateActive'),'carried_scrap':prop('CarriedScrap')})
            finish('completed')
    except Exception:
        result['errors'].append(traceback.format_exc());finish('failed')


write()
state['handle']=unreal.register_slate_post_tick_callback(tick)
