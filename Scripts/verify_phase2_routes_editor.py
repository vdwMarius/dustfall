"""Walk all landmark approaches and return home under day/night/storm in PIE.

Uses real CharacterMovement collision at 4x game time, not teleport traversal.
This is a navigation regression, not a frame-time benchmark. No assets are saved.
"""
import json
import math
import pathlib
import runpy
import time
import traceback
import unreal

ROOT=pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT=ROOT/'Saved/Codex/route_pie_report.json'
CASES=[('Day_Calm',0,.5),('Night_Haze',1,0.),('Day_Storm',2,.5)]
site=json.loads((ROOT/'Saved/Codex/landmark_build_report.json').read_text())['Cruiser']
lines=runpy.run_path(str(ROOT/'Scripts/phase2_layout.py'))['route_polylines']((site['relative_x_cm'],site['relative_y_cm']))
home_wreck, wreck_ruin, home_cruiser = [lines[k] for k in ['Home_Wreck','Wreck_Ruin','Home_Cruiser']]
POINTS=home_wreck[1:]+wreck_ruin[1:]+list(reversed(wreck_ruin[:-1]))+list(reversed(home_wreck[:-1]))+home_cruiser[1:]+list(reversed(home_cruiser[:-1]))
result={'status':'running','scope':'CharacterMovement route traversal at 4x game time; no performance claim', 'cases':[], 'errors':[]}
state={'stage':'start','since':time.monotonic(),'case':0,'handle':None,'owns_pie':False,'last_write':0}

def write():
    result['active_stage']=state['stage']
    result['active_case']=state['case']
    result['waypoint']=state.get('point')
    REPORT.write_text(json.dumps(result,indent=2),encoding='utf-8')

def finish(status):
    result['status']=status
    if 'old_throttle' in state:
        state['perf_settings'].set_editor_property('bThrottleCPUWhenNotForeground',state['old_throttle'])
    if state['owns_pie']:
        try:
            unreal.GameplayStatics.set_global_time_dilation(state['world'],1.)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        except Exception:
            result['errors'].append(traceback.format_exc())
    write()
    if state['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(state['handle'])
        state['handle']=None

def stage(name):
    state['stage'],state['since']=name,time.monotonic()

def tick(delta):
    try:
        now=time.monotonic()
        if now-state['last_write']>3:
            write();state['last_write']=now
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if state['stage']=='start':
            if editor.get_game_world():
                raise RuntimeError('End existing PIE before route verification')
            if '/Game/World/Maps/L_Dustfall_Foundation' not in editor.get_editor_world().get_path_name():
                raise RuntimeError('Open the foundation map first')
            perf=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
            state['perf_settings']=perf
            state['old_throttle']=perf.get_editor_property('bThrottleCPUWhenNotForeground')
            perf.set_editor_property('bThrottleCPUWhenNotForeground',False)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['owns_pie']=True
            stage('wait')
        elif state['stage']=='wait':
            world=editor.get_game_world()
            pawn=unreal.GameplayStatics.get_player_pawn(world,0) if world else None
            if not pawn:
                if now-state['since']>90: raise RuntimeError('PIE spawn timeout')
                return
            cls=unreal.load_class(None,'/Game/World/Blueprints/BP_DustfallEnvironmentDirector.BP_DustfallEnvironmentDirector_C')
            director=unreal.GameplayStatics.get_all_actors_of_class(world,cls)[0]
            movement=pawn.get_component_by_class(unreal.CharacterMovementComponent)
            movement.set_editor_property('max_walk_speed',750.)
            unreal.GameplayStatics.set_global_time_dilation(world,4.)
            state.update(world=world,pawn=pawn,director=director,movement=movement,
                         controller=unreal.GameplayStatics.get_player_controller(world,0))
            stage('case')
        elif state['stage']=='case':
            name,weather,clock=CASES[state['case']]
            state['pawn'].set_actor_location(unreal.Vector(550,0,150),False,False)
            state['director'].call_method('SetWeather',(weather,))
            state['director'].call_method('SetTimeOfDay',(clock,))
            state['point']=0
            state['case_start']=now
            state['previous_distance']=float('inf')
            state['progress_time']=now
            state['distance_cm']=0.
            state['previous_pos']=state['pawn'].get_actor_location()
            stage('settle')
        elif state['stage']=='settle':
            state['director'].call_method('SetTimeOfDay',(CASES[state['case']][2],))
            if now-state['since']>8:
                stage('walk')
        elif state['stage']=='walk':
            pawn=state['pawn'];p=pawn.get_actor_location()
            clock=CASES[state['case']][2]
            state['director'].call_method('SetWeather',(CASES[state['case']][1],))
            state['director'].call_method('SetTimeOfDay',(clock,))
            old=state['previous_pos']
            state['distance_cm']+=math.hypot(p.x-old.x,p.y-old.y)
            state['previous_pos']=p
            x,y=POINTS[state['point']]
            distance=math.hypot(x-p.x,y-p.y)
            if distance<160:
                state['point']+=1
                state['previous_distance']=float('inf')
                state['progress_time']=now
                if state['point']==len(POINTS):
                    result['cases'].append({'name':CASES[state['case']][0],'status':'pass',
                        'walked_cm':state['distance_cm'],'real_seconds':now-state['case_start'],
                        'waypoints_reached':len(POINTS),'weather':state['director'].get_editor_property('Weather'),
                        'storm_intensity':state['director'].get_editor_property('StormIntensity')})
                    state['case']+=1
                    if state['case']==len(CASES):
                        finish('passed');return
                    stage('case')
                return
            if distance<state['previous_distance']-30:
                state['previous_distance']=distance;state['progress_time']=now
            if now-state['progress_time']>8:
                raise RuntimeError('Blocked at %s waypoint %d: location=%s distance=%.1fcm' % (CASES[state['case']][0],state['point'],p,distance))
            if now-state['case_start']>250:
                raise RuntimeError('Route case timeout')
            state['controller'].set_control_rotation(unreal.Rotator(pitch=-5,yaw=math.degrees(math.atan2(y-p.y,x-p.x)),roll=0))
            step=max(.001,float(unreal.GameplayStatics.get_world_delta_seconds(state['world'])))
            strength=max(.02,min(1.,(distance-70.)/(750.*step)))
            pawn.add_movement_input(unreal.Vector((x-p.x)/distance,(y-p.y)/distance,0),strength,False)
    except Exception:
        result['errors'].append(traceback.format_exc());finish('failed')

write()
state['handle']=unreal.register_slate_post_tick_callback(tick)
