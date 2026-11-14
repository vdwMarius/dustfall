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
    result=dict(status='starting',captures=[],scope='Unlit terrain/material diagnostic captures: PIE fog and dust hidden; authored atmosphere unchanged; not gameplay, lighting or performance acceptance')
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
    length=math.dist(p[:2],q[:2]);nx,ny=-(q[1]-p[1])/length,(q[0]-p[0])/length
    shot('canyon_rim_along',point(p[0]+nx*(rim+800),p[1]+ny*(rim+800),2000),point(q[0],q[1],100))
    shot('canyon_floor_up',point(p[0],p[1]),point(p[0],p[1]+rim,500))
    for line in paths:
        if line['type']!='descent': continue
        a=line['polyline_cm'][0];b=line['polyline_cm'][min(40,len(line['polyline_cm'])-1)]
        shot(line['id']+'_top',[a[0],a[1],a[2]+170],[b[0],b[1],b[2]+100])
        a=line['polyline_cm'][-1];b=line['polyline_cm'][max(0,len(line['polyline_cm'])-41)]
        shot(line['id']+'_foot',[a[0],a[1],a[2]+170],[b[0],b[1],b[2]+100])
    for f in data['features']:
        if f['type']!='escarpment': continue
        a,b=f['line_cm'][len(f['line_cm'])//2:len(f['line_cm'])//2+2]
        length=math.dist(a,b);n=[-(b[1]-a[1])/length*f['high_side'],(b[0]-a[0])/length*f['high_side']]
        top=[a[k]+n[k]*(f['face_width_cm']+3000) for k in range(2)]
        foot=[a[k]-n[k]*(f['talus_width_cm']+4500) for k in range(2)]
        shot(f['id']+'_top_down',point(*top,3000),point(a[0],a[1],500))
        shot(f['id']+'_foot_up',point(*foot,2500),point(*top,300))
    for path in paths:
        if path['id'] not in ('scar_trail','shelf_trail'): continue
        trail=path['polyline_cm'];a,b=trail[len(trail)//2],trail[min(len(trail)//2+20,len(trail)-1)]
        shot(path['id']+'_eye',point(a[0],a[1]),point(b[0],b[1]))
    shot('overview_south',[-70000,-85000,65000],[0,-30000,0])
    shot('overview_north',[75000,80000,85000],[0,15000,0])
    for field in data['features']:
        if field['type']!='spire_base': continue
        x,y,rx,ry,_,_=field['parameters']
        if field['id']=='needles_south': camera_position=point(x-rx*.6,y-ry*.6,2200)
        else: camera_position=point(x-rx,y-ry)
        shot(field['id']+'_silhouette',camera_position,point(x,y,field['dressing']['height_cm'][1]*.55))
    shot('flat_scatter_bare_patches',point(10000,18000),point(15000,22000,100))
    only=globals().get('ONLY_SHOTS')
    if only is not None: shots=[s for s in shots if s['name'] in only]
    if not shots: raise RuntimeError('No capture views selected')
    source=next(a for a in actors.get_all_level_actors() if a.get_class().get_name()=='BP_SurvivalDirector_C')
    original=source.get_editor_property('SaveSlotName');qa='Dustfall_Phase5_TerrainCapture_QA'
    def dirty():
        s=unreal.EditorLoadingAndSavingUtils
        return sorted(p.get_path_name() for p in list(s.get_dirty_map_packages())+list(s.get_dirty_content_packages()))
    result['initial_dirty_packages']=dirty()
    state=dict(stage='start',since=time.monotonic(),index=0,handle=None,camera=None,world=None,ending=False,frames=[])
    # Spawn in the editor world; PIE duplicates the temporary camera.
    camera=actors.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(*shots[0]['camera_cm']))
    if not camera: raise RuntimeError('Could not create temporary editor camera')
    camera.set_actor_label('DF_Phase5_TerrainCapture_Temporary')
    camera.tags=[unreal.Name('DF_Phase5_TerrainCapture_Temporary')]
    camera.set_editor_property('is_spatially_loaded',False)
    camera.get_component_by_class(unreal.CameraComponent).set_field_of_view(75)
    if not unreal.DustfallAtmosphereFX.set_capture_save_slot(source,qa):
        actors.destroy_actor(camera)
        raise RuntimeError('Could not isolate capture save slot')
    for slot in (qa,qa+'_Exploration'): unreal.GameplayStatics.delete_game_in_slot(slot,0)
    def end():
        if not state['ending']:
            if state.get('world'): unreal.SystemLibrary.execute_console_command(state['world'],'viewmode lit')
            state['ending']=True;state.update(stage='end',since=time.monotonic());editor.editor_request_end_play()
    def tick(delta):
        if state.get('busy'): return
        state['busy']=True
        try:
            if state['stage']=='end':
                if unreal.EditorLevelLibrary.get_pie_worlds(False):
                    if time.monotonic()-state['since']>15: editor.editor_request_end_play()
                    return
                if not unreal.DustfallAtmosphereFX.set_capture_save_slot(source,original):
                    raise RuntimeError('Could not restore capture save slot')
                if unreal.SystemLibrary.is_valid(camera): actors.destroy_actor(camera)
                for slot in (qa,qa+'_Exploration'): unreal.GameplayStatics.delete_game_in_slot(slot,0)
                result['final_dirty_packages']=dirty()
                result['cleanup']='PIE stopped; temporary camera destroyed; original slot restored; QA slots deleted; no packages saved'
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
                unreal.SystemLibrary.execute_console_command(w,'viewmode unlit')
                environment=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)
                                 if a.get_class().get_name()=='BP_DustfallEnvironmentDirector_C')
                state['environment']=environment
                pie_camera=next((a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.CameraActor)
                                 if 'DF_Phase5_TerrainCapture_Temporary' in map(str,a.tags)),None)
                if not pie_camera: raise RuntimeError('Temporary camera missing from PIE')
                controller=unreal.GameplayStatics.get_player_controller(w,0)
                controller.set_view_target_with_blend(pie_camera,0)
                survival=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)
                              if a.get_class().get_name()=='BP_SurvivalDirector_C')
                if str(survival.get_editor_property('SaveSlotName'))!=qa: raise RuntimeError('PIE save slot isolation failed')
                state.update(camera=pie_camera,controller=controller,survival=survival,stage='position')
            # Reset calm/day every tick, so the automatic weather cycle cannot obscure a capture.
            state['environment'].call_method('SetWeather',(0,))
            state['environment'].call_method('SetTimeOfDay',(.35,))
            for resource in ('Oxygen','Power','Integrity','Stamina'):
                state['survival'].set_editor_property(resource,100.)
            # Calm still has the game's intentional heavy haze. Disable PIE-only
            # fog components for terrain review; the editor world is untouched.
            loaded_actors=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)
            for fog_actor in loaded_actors:
                for fog in fog_actor.get_components_by_class(unreal.ExponentialHeightFogComponent): fog.set_visibility(False)
                if isinstance(fog_actor,unreal.DustfallAtmosphereFX): fog_actor.set_actor_hidden_in_game(True)
                if 'DF_Phase3_PCG' in map(str,fog_actor.tags):
                    for component in fog_actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
                        if component.static_mesh and component.static_mesh.get_path_name().startswith('/Engine/BasicShapes/Plane'):
                            component.set_hidden_in_game(True)
            if state['stage']=='position':
                s=shots[state['index']];p,q=s['camera_cm'],s['target_cm'];d=[q[k]-p[k] for k in range(3)]
                state['camera'].set_actor_location(unreal.Vector(*p),False,True)
                state['camera'].set_actor_rotation(unreal.Rotator(pitch=math.degrees(math.atan2(d[2],math.hypot(*d[:2]))),yaw=math.degrees(math.atan2(d[1],d[0]))),False)
                # The pawn supplies World Partition streaming sources; follow the camera.
                pawn=unreal.GameplayStatics.get_player_pawn(w,0)
                if pawn:
                    pawn.set_actor_location(unreal.Vector(*p),False,True)
                    movement=pawn.get_component_by_class(unreal.CharacterMovementComponent)
                    if movement: movement.set_movement_mode(unreal.MovementMode.MOVE_FLYING)
                    pawn.set_actor_hidden_in_game(True)
                state.update(stage='settle',since=time.monotonic(),frames=[],game_frames=[]);return
            if state['stage']=='settle':
                state['frames'].append(float(delta)*1000)
                state['game_frames'].append(float(unreal.GameplayStatics.get_world_delta_seconds(w))*1000)
                if time.monotonic()-state['since']<3:return
                name=shots[state['index']]['name'];file=out/(name+'.png')
                if file.exists():file.unlink()  # Only this task's named output, to detect fresh completion.
                unreal.SystemLibrary.execute_console_command(w,'HighResShot 1920x1080 filename="'+file.as_posix()+'"')
                state.update(stage='file',since=time.monotonic());return
            if state['stage']=='file':
                file=out/(shots[state['index']]['name']+'.png')
                if not file.exists() or not file.read_bytes().endswith(b'IEND\xaeB\x60\x82'):return
                loaded=unreal.GameplayStatics.get_all_actors_of_class(w,unreal.Actor)
                result['captures'].append(dict(**shots[state['index']],file=file.name,bytes=file.stat().st_size,
                    loaded_pcg_cells=sum('DF_Phase3_PCG' in map(str,a.tags) for a in loaded),
                    slate_frame_ms_mean=sum(state['frames'])/max(1,len(state['frames'])),
                    game_frame_ms_mean=sum(state['game_frames'])/max(1,len(state['game_frames'])),
                    frame_time_scope='PIE world/Slate deltas during three-second settle; not GPU or performance acceptance'))
                state['index']+=1;write()
                if state['index']==len(shots):result['status']='complete; inspect images';end();return
                state.update(stage='position',since=time.monotonic())
        except Exception:
            result.update(status='failed',error=traceback.format_exc());write();end()
        finally:
            state['busy']=False
    try:
        write();state['handle']=unreal.register_slate_post_tick_callback(tick);unreal._dustfall_phase5_capture_handle=state['handle']
    except Exception:
        unreal.DustfallAtmosphereFX.set_capture_save_slot(source,original)
        if unreal.SystemLibrary.is_valid(camera): actors.destroy_actor(camera)
        for slot in (qa,qa+'_Exploration'): unreal.GameplayStatics.delete_game_in_slot(slot,0)
        raise


if __name__=='__main__':main()
