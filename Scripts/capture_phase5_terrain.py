"""Background-safe PIE HighResShot terrain review, with isolated QA save slots.

Requires completed Phase5 terrain authoring. Run under sole editor lock.
No editor actors/assets/weather are saved. Output: Saved/Codex/Phase5Terrain.
"""
import json
import math
import pathlib
import time
import traceback
import unreal


def main():
    root=pathlib.Path(unreal.Paths.project_dir());out=root/'Saved/Codex/Phase5Terrain';out.mkdir(parents=True,exist_ok=True)
    result=dict(status='starting',captures=[],scope='Clear-weather review captures; not gameplay/visibility acceptance')
    def write(): (out/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if unreal.EditorLevelLibrary.get_game_world(): raise RuntimeError('Stop PIE before capture')
    terrain=json.loads((root/'Docs/Phase5_TerrainResults.json').read_text())
    if terrain['status']!='complete': raise RuntimeError('Terrain authoring/collision verification must finish first')
    paths=json.loads((root/'Saved/Codex/TerrainMasks/polylines.json').read_text())['paths']
    data=json.loads((root/'Saved/Codex/terrain_features_v2_resolved.json').read_text())
    world=unreal.EditorLevelLibrary.get_editor_world()
    ignore=[a for a in actors.get_all_level_actors() if not isinstance(a,unreal.LandscapeProxy)]
    breaker=unreal.get_default_object(unreal.GameplayStatics.static_class())
    def ground(x,y):
        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
        parts=breaker.call_method('BreakHitResult',(hit,))
        if not parts[0]: raise RuntimeError('Capture ground trace missed '+str((x,y)))
        return parts[5].z
    def point(x,y,lift=170): return [x,y,ground(x,y)+lift]
    shots=[]
    def shot(name,p,q): shots.append(dict(name=name,camera_cm=p,target_cm=q))
    canyon=next(f for f in data['features'] if f['type']=='canyon')
    p=canyon['line_cm'][len(canyon['line_cm'])//2];q=canyon['line_cm'][min(len(canyon['line_cm'])//2+2,len(canyon['line_cm'])-1)]
    rim=max(canyon['rim_width_cm'])/2
    shot('canyon_rim_along',point(p[0],p[1]+rim+400),point(q[0],q[1],100))
    shot('canyon_floor_up',point(p[0],p[1]),point(p[0],p[1]+rim,500))
    for line in paths:
        if line['type']!='descent': continue
        a=line['polyline_cm'][0];b=line['polyline_cm'][min(40,len(line['polyline_cm'])-1)]
        shot(line['id']+'_top',[a[0],a[1],a[2]+170],[b[0],b[1],b[2]+100])
    for f in data['features']:
        if f['type']!='escarpment': continue
        a,b=f['line_cm'][len(f['line_cm'])//2:len(f['line_cm'])//2+2]
        length=math.dist(a,b);n=[-(b[1]-a[1])/length*f['high_side'],(b[0]-a[0])/length*f['high_side']]
        top=[a[k]+n[k]*(f['face_width_cm']+600) for k in range(2)]
        foot=[a[k]-n[k]*(f['talus_width_cm']+600) for k in range(2)]
        shot(f['id']+'_top_down',point(*top),point(*foot,100))
        shot(f['id']+'_foot_up',point(*foot),point(*top,300))
    trail=next(p for p in paths if p['id']=='scar_trail')['polyline_cm'];a,b=trail[len(trail)//2],trail[min(len(trail)//2+20,len(trail)-1)]
    shot('worn_path_eye',[a[0],a[1],a[2]+170],[b[0],b[1],b[2]+170])
    shot('overview_south',[-70000,-85000,65000],[0,-30000,0])
    shot('overview_north',[75000,80000,85000],[0,15000,0])
    source=next(a for a in actors.get_all_level_actors() if a.get_class().get_name()=='BP_SurvivalDirector_C')
    original=source.get_editor_property('SaveSlotName');qa='Dustfall_Phase5_TerrainCapture_QA'
    state=dict(stage='start',since=time.monotonic(),index=0,handle=None,camera=None,world=None,ending=False)
    source.set_editor_property('SaveSlotName',qa)
    for slot in (qa,qa+'_Exploration'): unreal.GameplayStatics.delete_game_in_slot(slot,0)
    def end():
        if not state['ending']:
            state['ending']=True;state.update(stage='end',since=time.monotonic());editor.editor_request_end_play()
    def tick(delta):
        try:
            if state['stage']=='end':
                if unreal.EditorLevelLibrary.get_pie_worlds(False):
                    if time.monotonic()-state['since']>15: editor.editor_request_end_play()
                    return
                source.set_editor_property('SaveSlotName',original)
                for slot in (qa,qa+'_Exploration'): unreal.GameplayStatics.delete_game_in_slot(slot,0)
                unreal.unregister_slate_post_tick_callback(state['handle']);unreal._dustfall_phase5_capture_handle=None;write();return
            if time.monotonic()-state['since']>45: raise RuntimeError('Capture stage timeout: '+state['stage'])
            if state['stage']=='start':
                editor.editor_request_begin_play();state.update(stage='wait',since=time.monotonic());return
            worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:return
            w=worlds[0]
            if state['stage']=='wait':
                if time.monotonic()-state['since']<3:return
                state['world']=w
                environment=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)
                                 if a.get_class().get_name()=='BP_DustfallEnvironmentDirector_C')
                state['environment']=environment
                transform=unreal.Transform()
                camera=unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(w,unreal.CameraActor,transform,
                      unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None)
                if not camera: raise RuntimeError('Could not spawn PIE camera')
                unreal.GameplayStatics.finish_spawning_actor(camera,transform)
                camera.get_component_by_class(unreal.CameraComponent).set_field_of_view(75)
                controller=unreal.GameplayStatics.get_player_controller(w,0)
                controller.set_view_target_with_blend(camera,0)
                state.update(camera=camera,stage='position')
            # Reset calm/day every tick, so the automatic weather cycle cannot obscure a capture.
            state['environment'].call_method('SetWeather',(0,))
            state['environment'].call_method('SetTimeOfDay',(.35,))
            # Calm still has the game's intentional heavy haze. Disable PIE-only
            # fog components for terrain review; the editor world is untouched.
            for fog_actor in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.ExponentialHeightFog):
                fog_actor.get_component_by_class(unreal.ExponentialHeightFogComponent).set_visibility(False)
            if state['stage']=='position':
                s=shots[state['index']];p,q=s['camera_cm'],s['target_cm'];d=[q[k]-p[k] for k in range(3)]
                state['camera'].set_actor_location(unreal.Vector(*p),False,True)
                state['camera'].set_actor_rotation(unreal.Rotator(pitch=math.degrees(math.atan2(d[2],math.hypot(*d[:2]))),yaw=math.degrees(math.atan2(d[1],d[0]))),False)
                state.update(stage='settle',since=time.monotonic());return
            if state['stage']=='settle':
                if time.monotonic()-state['since']<3:return
                name=shots[state['index']]['name'];file=out/(name+'.png')
                if file.exists():file.unlink()  # Only this task's named output, to detect fresh completion.
                unreal.SystemLibrary.execute_console_command(w,'HighResShot 1920x1080 filename="'+file.as_posix()+'"')
                state.update(stage='file',since=time.monotonic());return
            if state['stage']=='file':
                file=out/(shots[state['index']]['name']+'.png')
                if not file.exists() or not file.read_bytes().endswith(b'IEND\xaeB\x60\x82'):return
                result['captures'].append(dict(**shots[state['index']],file=file.name,bytes=file.stat().st_size))
                state['index']+=1;write()
                if state['index']==len(shots):result['status']='complete; inspect images';end();return
                state.update(stage='position',since=time.monotonic())
        except Exception:
            result.update(status='failed',error=traceback.format_exc());write();end()
    try:
        write();state['handle']=unreal.register_slate_post_tick_callback(tick);unreal._dustfall_phase5_capture_handle=state['handle']
    except Exception:
        source.set_editor_property('SaveSlotName',original)
        for slot in (qa,qa+'_Exploration'): unreal.GameplayStatics.delete_game_in_slot(slot,0)
        raise


if __name__=='__main__':main()
