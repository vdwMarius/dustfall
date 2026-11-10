"""Capture steady-state PIE frame-time CSVs and streaming observations.

Editor measurements are not a mid-range or packaged performance guarantee.
Profiles use native viewport resolution, High scalability, 100% screen percentage,
no dynamic resolution or frame generation. All modified CVars are restored.
"""
import json
import pathlib
import time
import traceback
import unreal

ROOT=pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT=ROOT/'Saved/Codex/profile_phase2.json'
CASES=[('Home_Day',3000,0,180,1,.5),('Wreck_Day',11500,10000,0,1,.5),
       ('Ruin_Day',32000,-23000,-34,1,.5),('Cruiser_Day',-42500,5000,180,1,.5),
       ('Home_Night',3000,0,180,1,0.),('Cruiser_Storm',-42500,5000,180,2,.5),
       ('Far_Corner',85000,85000,225,0,.5)]
CVARS={'t.MaxFPS':0,'r.VSync':0,'r.ScreenPercentage':100,'r.DynamicRes.OperationMode':0,
       'sg.ViewDistanceQuality':2,'sg.AntiAliasingQuality':2,'sg.ShadowQuality':2,
       'sg.GlobalIlluminationQuality':2,'sg.ReflectionQuality':2,'sg.PostProcessQuality':2,
       'sg.TextureQuality':2,'sg.EffectsQuality':2,'sg.FoliageQuality':2,'sg.ShadingQuality':2}
result={'status':'running','scope':'Visible PIE with background throttling disabled, native viewport resolution, High, 100% render scale; steady states, not target-hardware certification','cases':[],'errors':[]}
state={'stage':'start','since':time.monotonic(),'case':0,'handle':None,'owns':False,'old_cvars':{}}

def write():
    result['active_stage']=state['stage'];result['active_case']=state['case']
    REPORT.write_text(json.dumps(result,indent=2),encoding='utf-8')

def command(text):
    unreal.SystemLibrary.execute_console_command(state['world'],text)

def stage(name):
    state['stage'],state['since']=name,time.monotonic();write()

def finish(status):
    if state.get('capturing'): command('csvprofile stop')
    for key,value in state['old_cvars'].items(): command(key+' '+str(value))
    if 'old_throttle' in state:
        state['perf_settings'].set_editor_property('bThrottleCPUWhenNotForeground',state['old_throttle'])
    result['status']=status;write()
    if state['owns']: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    if state['handle'] is not None: unreal.unregister_slate_post_tick_callback(state['handle'])

def tick(delta):
    try:
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        elapsed=time.monotonic()-state['since']
        if state['stage']=='start':
            if editor.get_game_world(): raise RuntimeError('End existing PIE before profiling')
            perf=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
            state['perf_settings']=perf
            state['old_throttle']=perf.get_editor_property('bThrottleCPUWhenNotForeground')
            perf.set_editor_property('bThrottleCPUWhenNotForeground',False)
            w=editor.get_editor_world();actors=unreal.EditorLevelLibrary.get_all_level_actors()
            ignored=[a for a in actors if not isinstance(a,unreal.LandscapeProxy)]
            zs=[]
            for _,x,y,*_ in CASES:
                h=unreal.SystemLibrary.line_trace_single(w,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,unreal.DrawDebugTrace.NONE,True)
                parts=unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method('BreakHitResult',(h,))
                if not parts[0]: raise RuntimeError('Load profile landscape cells first')
                zs.append(parts[5].z+150)
            state['zs']=zs
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play();state['owns']=True;stage('wait')
        elif state['stage']=='wait':
            w=editor.get_game_world();p=unreal.GameplayStatics.get_player_pawn(w,0) if w else None
            if not p:
                if elapsed>90: raise RuntimeError('PIE timeout')
                return
            state.update(world=w,pawn=p,controller=unreal.GameplayStatics.get_player_controller(w,0))
            cls=unreal.load_class(None,'/Game/World/Blueprints/BP_DustfallEnvironmentDirector.BP_DustfallEnvironmentDirector_C')
            state['director']=unreal.GameplayStatics.get_all_actors_of_class(w,cls)[0]
            for key,value in CVARS.items():
                state['old_cvars'][key]=unreal.SystemLibrary.get_console_variable_float_value(key)
                command(key+' '+str(value))
            result['settings']=CVARS
            result['viewport_size']=str(state['controller'].get_viewport_size())
            result['csv_directory']=str(ROOT/'Saved/Profiling/CSV')
            stage('case')
        elif state['stage']=='case':
            name,x,y,yaw,weather,clock=CASES[state['case']]
            d=state['director'];d.call_method('SetWeather',(weather,));d.call_method('SetTimeOfDay',(clock,))
            data=d.get_editor_property('EnvironmentData')
            d.set_editor_property('CurrentFogDensity',data.get_editor_property(['CalmFogDensity','HazeFogDensity','StormFogDensity'][weather]))
            d.set_editor_property('StormIntensity',1. if weather==2 else 0.)
            state['pawn'].set_actor_location(unreal.Vector(x,y,state['zs'][state['case']]),False,False)
            state['controller'].set_control_rotation(unreal.Rotator(pitch=-5,yaw=yaw,roll=0))
            stage('settle')
        elif state['stage']=='settle':
            state['director'].call_method('SetTimeOfDay',(CASES[state['case']][5],))
            if elapsed<7: return
            name=CASES[state['case']][0]
            command('csvprofile startfile=Phase2_'+name+'.csv');command('csvprofile start');state['capturing']=True
            state['samples']=[];stage('capture')
        elif state['stage']=='capture':
            state['director'].call_method('SetTimeOfDay',(CASES[state['case']][5],))
            state['samples'].append(float(unreal.GameplayStatics.get_world_delta_seconds(state['world']))*1000)
            if elapsed<10:return
            command('csvprofile stop');state['capturing']=False
            cls=unreal.load_class(None,'/Game/World/Blueprints/BP_DustfallRockCell.BP_DustfallRockCell_C')
            frames=sorted(state['samples']);n=len(frames)
            result['cases'].append({'name':CASES[state['case']][0],'samples':n,
                'game_delta_median_ms':frames[n//2], 'game_delta_p95_ms':frames[min(n-1,int(n*.95))],
                'game_delta_max_ms':frames[-1], 'loaded_rock_cells':len(unreal.GameplayStatics.get_all_actors_of_class(state['world'],cls)),
                'csv':'Phase2_'+CASES[state['case']][0]+'.csv'})
            state['case']+=1
            if state['case']==len(CASES):finish('completed');return
            stage('case')
    except Exception:
        result['errors'].append(traceback.format_exc());finish('failed')

write();state['handle']=unreal.register_slate_post_tick_callback(tick)
