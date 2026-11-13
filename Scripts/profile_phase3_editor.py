"""~105s PIE profiling of dense PCG, habitat and storms in an isolated save slot.

Does not assume the editor is visible. Records actual viewport resolution,
loaded native PCG instances and CSV frame times. Resource top-ups isolate the
rendering workload from death/respawn; normal survival still ticks. Restore
save-slot selection only after PIE has fully ended. Never save project assets.
"""
import json
import pathlib
import runpy
import time
import traceback
import unreal

ROOT=pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT=ROOT/'Saved/Codex/profile_phase3.json'
QA_SLOT='Dustfall_QA_Profile_Phase3'
CVARS={'t.MaxFPS':0,'r.VSync':0,'r.ScreenPercentage':100,'r.DynamicRes.OperationMode':0,
       'sg.ViewDistanceQuality':2,'sg.AntiAliasingQuality':2,'sg.ShadowQuality':2,
       'sg.GlobalIlluminationQuality':2,'sg.ReflectionQuality':2,'sg.PostProcessQuality':2,
       'sg.TextureQuality':2,'sg.EffectsQuality':2,'sg.FoliageQuality':2,'sg.ShadingQuality':2}
SETTLE_SECONDS=6.
CAPTURE_SECONDS=8.
result={'status':'running','scope':'PIE; editor visibility is not asserted. Actual viewport size recorded; High/100%render scale. Healthy-resource top-ups isolate rendering. Not packaged or target-hardware certification.',
        'cases':[],'errors':[],'isolated_save_slot':QA_SLOT}
state={'stage':'start','since':time.monotonic(),'started':time.monotonic(),'case':0,
       'handle':None,'owns':False,'old_cvars':{},'capturing':False,'final_status':None}


def write():
    result['active_stage']=state['stage']; result['active_case']=state['case']
    REPORT.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')


def command(value):
    unreal.SystemLibrary.execute_console_command(state['world'],value)


def stage(name):
    state['stage'],state['since']=name,time.monotonic(); write()


def finish(status):
    if state['capturing']:
        command('csvprofile stop'); state['capturing']=False
    for key,value in state['old_cvars'].items(): command(key+' '+str(value))
    if 'old_throttle' in state:
        state['perf_settings'].set_editor_property('bThrottleCPUWhenNotForeground',state['old_throttle'])
    state['final_status']=status
    if state['owns']:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        stage('wait_end')
    else:
        cleanup()


def cleanup():
    # This deliberately waits until the PIE world is gone, so an EndPlay save
    # cannot accidentally write profiled state into the user's normal slot.
    if 'slot_actor' in state:
        state['slot_actor'].set_editor_property('SaveSlotName',state['original_slot'])
    unreal.GameplayStatics.delete_game_in_slot(QA_SLOT,0)
    result['status']=state['final_status']
    result['elapsed_seconds']=time.monotonic()-state['started']
    write()
    if state['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(state['handle']); state['handle']=None


def topup():
    for name in ['Oxygen','Power','Integrity','Stamina']:
        state['survival'].set_editor_property(name,100.)


def native_pcg_snapshot():
    cells=unreal.GameplayStatics.get_all_actors_of_class(state['world'],state['cell_class'])
    counts={'loaded_cells':len(cells),'ism_components':0,'rock_instances':0,'dust_sheet_instances':0,'debris_instances':0,
            'active_generation_components':0}
    for a in cells:
        pcg=a.get_component_by_class(unreal.PCGComponent)
        if pcg and pcg.get_editor_property('generation_in_progress'): counts['active_generation_components']+=1
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if not c.static_mesh: continue
            counts['ism_components']+=1
            tags=[str(t) for t in c.component_tags]
            kind='debris_instances' if 'DF_Phase3_PCGDebris' in tags else 'dust_sheet_instances' if c.static_mesh.get_path_name().startswith('/Engine/BasicShapes/Plane') else 'rock_instances'
            counts[kind]+=c.get_instance_count()
    return counts


def tick(delta):
    try:
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        elapsed=time.monotonic()-state['since']
        mode=state['stage']
        if mode=='wait_end':
            if not editor.get_game_world(): cleanup()
            elif elapsed>30: raise RuntimeError('PIE did not end; isolated slot deliberately remains selected')
            return
        if time.monotonic()-state['started']>180: raise RuntimeError('Profile exceeded180second safety limit')
        if mode=='start':
            if editor.get_game_world(): raise RuntimeError('End existing PIE before profiling')
            world=editor.get_editor_world()
            if '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name(): raise RuntimeError('Open foundation map before profiling')
            runpy.run_path(str(ROOT/'Scripts/load_phase3_authoring_cells.py'),run_name='__main__')
            actors=list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
            layout=runpy.run_path(str(ROOT/'Scripts/habitat_layout.py'))
            origin=layout['habitat_origin'](actors)
            ox,oy,oz=origin
            # Seven steady-state cases; teleports are excluded from capture.
            state['cases']=[('Habitat_Interior',ox-120,oy,oz+148,155,1,.5,True),
                            ('Home_Day',ox+3000,oy,0,180,1,.5,False),
                            ('Wreck_Day',ox+11500,oy+10000,0,0,1,.5,False),
                            ('Cruiser_Day',ox-42500,oy+5000,0,180,1,.5,False),
                            ('Home_Night',ox+3000,oy,0,180,1,0.,False),
                            ('Cruiser_Storm',ox-42500,oy+5000,0,180,2,.5,False),
                            ('Dense_Field_Far',ox+85000,oy+85000,0,225,0,.5,False)]
            ignore=[a for a in actors if not isinstance(a,unreal.LandscapeProxy)]
            zs=[]
            breaker=unreal.get_default_object(unreal.GameplayStatics.static_class())
            for _,x,y,z,*rest in state['cases']:
                if rest[-1]: zs.append(z); continue
                hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
                parts=breaker.call_method('BreakHitResult',(hit,))
                if not parts[0]: raise RuntimeError('Load all profile landscape cells first')
                zs.append(parts[5].z+150)
            state['zs']=zs
            survival_class=unreal.load_class(None,'/Game/Systems/BP_SurvivalDirector.BP_SurvivalDirector_C')
            slot_actor=next(a for a in actors if a.get_class()==survival_class)
            state.update(slot_actor=slot_actor,original_slot=slot_actor.get_editor_property('SaveSlotName'),survival_class=survival_class)
            slot_actor.set_editor_property('SaveSlotName',QA_SLOT)
            unreal.GameplayStatics.delete_game_in_slot(QA_SLOT,0)
            perf=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
            state['perf_settings']=perf; state['old_throttle']=perf.get_editor_property('bThrottleCPUWhenNotForeground')
            perf.set_editor_property('bThrottleCPUWhenNotForeground',False)
            state['cell_class']=unreal.load_class(None,'/Game/World/Phase3/Blueprints/BP_DustfallPCGCell.BP_DustfallPCGCell_C')
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play(); state['owns']=True; stage('wait')
        elif mode=='wait':
            world=editor.get_game_world(); pawn=unreal.GameplayStatics.get_player_pawn(world,0) if world else None
            if not pawn:
                if elapsed>45: raise RuntimeError('PIE startup timeout')
                return
            if elapsed<2: return
            survival=unreal.GameplayStatics.get_all_actors_of_class(world,state['survival_class'])[0]
            if survival.get_editor_property('SaveSlotName')!=QA_SLOT: raise RuntimeError('Profile did not inherit isolated save slot')
            env_class=unreal.load_class(None,'/Game/World/Blueprints/BP_DustfallEnvironmentDirector.BP_DustfallEnvironmentDirector_C')
            state.update(world=world,pawn=pawn,controller=unreal.GameplayStatics.get_player_controller(world,0),survival=survival,
                         director=unreal.GameplayStatics.get_all_actors_of_class(world,env_class)[0])
            for key,value in CVARS.items():
                state['old_cvars'][key]=unreal.SystemLibrary.get_console_variable_float_value(key); command(key+' '+str(value))
            result['settings']=CVARS
            result['viewport_size']=list(state['controller'].get_viewport_size())
            result['csv_directory']=str(ROOT/'Saved/Profiling/CSV')
            result['runtime_render_cvars']={name:unreal.SystemLibrary.get_console_variable_int_value(name) for name in ['r.Nanite','r.DynamicGlobalIlluminationMethod','r.ReflectionMethod','r.Shadow.Virtual.Enable']}
            stage('case')
        elif mode=='case':
            name,x,y,z,yaw,weather,clock,interior=state['cases'][state['case']]
            topup()
            d=state['director']; d.call_method('SetWeather',(weather,)); d.call_method('SetTimeOfDay',(clock,))
            data=d.get_editor_property('EnvironmentData')
            d.set_editor_property('CurrentFogDensity',data.get_editor_property(['CalmFogDensity','HazeFogDensity','StormFogDensity'][weather]))
            d.set_editor_property('StormIntensity',1. if weather==2 else 0.)
            state['pawn'].set_actor_location(unreal.Vector(x,y,state['zs'][state['case']]),False,True)
            boom=state['pawn'].get_component_by_class(unreal.SpringArmComponent)
            if boom: boom.set_editor_property('target_arm_length',0. if interior else 400.)
            state['pawn'].get_component_by_class(unreal.SkeletalMeshComponent).set_owner_no_see(interior)
            state['controller'].set_control_rotation(unreal.Rotator(pitch=-5,yaw=yaw))
            stage('settle')
        elif mode=='settle':
            state['director'].call_method('SetTimeOfDay',(state['cases'][state['case']][6],))
            if elapsed<SETTLE_SECONDS: return
            topup()
            name=state['cases'][state['case']][0]
            command('csvprofile startfile=Phase3_'+name+'.csv'); command('csvprofile start'); state['capturing']=True
            state['samples']=[]; stage('capture')
        elif mode=='capture':
            state['director'].call_method('SetTimeOfDay',(state['cases'][state['case']][6],))
            state['samples'].append(float(unreal.GameplayStatics.get_world_delta_seconds(state['world']))*1000)
            if elapsed<CAPTURE_SECONDS: return
            command('csvprofile stop'); state['capturing']=False
            frames=sorted(state['samples']); n=len(frames)
            result['cases'].append({'name':state['cases'][state['case']][0],'samples':n,
                                    'game_delta_median_ms':frames[n//2],'game_delta_p95_ms':frames[min(n-1,int(n*.95))],
                                    'game_delta_p99_ms':frames[min(n-1,int(n*.99))],'game_delta_max_ms':frames[-1],
                                    'viewport_size':list(state['controller'].get_viewport_size()),
                                    'loaded_pcg':native_pcg_snapshot(),'csv':'Phase3_'+state['cases'][state['case']][0]+'.csv'})
            state['case']+=1
            if state['case']==len(state['cases']): finish('completed'); return
            stage('case')
    except Exception:
        result['errors'].append(traceback.format_exc())
        if state['stage']=='wait_end':
            # Keep waiting for the real end; never restore the user slot while
            # a PIE world could still save into it.
            state['final_status']='failed'; write(); return
        finish('failed')


write(); state['handle']=unreal.register_slate_post_tick_callback(tick)
