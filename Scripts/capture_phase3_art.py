"""Warm-Lumen editor captures of habitat and actual PCG rock formations.

No saved assets/settings changed. Inspect report and PNGs under
Saved/Codex/Phase3Art. These are scene review images, not performance evidence.
"""
import json
import math
import pathlib
import runpy
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
OUT = ROOT/'Saved/Codex/Phase3Art'
OUT.mkdir(parents=True,exist_ok=True)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world(): raise RuntimeError('Stop PIE before editor art captures')
world = editor.get_editor_world()
if '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name(): raise RuntimeError('Open foundation map before art capture')
runpy.run_path(str(ROOT/'Scripts/load_phase3_authoring_cells.py'),run_name='__main__')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = list(actors.get_all_level_actors())
origin = runpy.run_path(str(ROOT/'Scripts/habitat_layout.py'))['habitat_origin'](all_actors)
report = {'status':'running','captures':[],'errors':[],
          'scope':'Editor scene review; persisted exposure and atmosphere; 6sLumen history; no FPS claim.'}
state = {'capture':None,'handle':None,'index':0,'since':time.monotonic(),
         'old_full_mips':unreal.SystemLibrary.get_console_variable_int_value('r.Streaming.FullyLoadUsedTextures'),
         'prestream_components':[]}


def point(x,y,z): return unreal.Vector(origin[0]+x,origin[1]+y,origin[2]+z)


def look(location,target):
    d = target-location
    return unreal.Rotator(pitch=math.degrees(math.atan2(d.z,math.hypot(d.x,d.y))),
                          yaw=math.degrees(math.atan2(d.y,d.x)))


shots = [('habitat_exterior',point(1900,-1800,850),point(150,0,230),65.),
         ('habitat_interior',point(350,-255,230),point(-160,50,200),85.),
         ('habitat_workbench',point(-240,-90,230),point(-70,240,190),72.)]
if globals().get('EXTERIOR_ONLY',False): shots=shots[:1]
formation = None
candidates = []
for a in ([] if globals().get('HABITAT_ONLY',False) else all_actors):
    if 'DF_Phase3_PCG' not in [str(t) for t in a.tags]: continue
    for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
        if not c.static_mesh: continue
        path = c.static_mesh.get_path_name()
        if not any(ident in path for ident in ['xgjnech','xgjodeb']): continue
        for i in range(c.get_instance_count()):
            t = c.get_instance_transform(i,world_space=True)
            p = t.translation
            dist = math.hypot(p.x-origin[0],p.y-origin[1])
            if dist>3500:
                # View real instanced geometry, never a separately posed sample.
                height = c.static_mesh.get_bounds().box_extent.z*2*t.scale3d.z
                candidates.append((dist,p,height,path,c))
if candidates:
    _,p,height,path,formation_component = min(candidates,key=lambda v:v[0])
    target = unreal.Vector(p.x,p.y,p.z+height*.45)
    report['rock_formation']={'mesh':path,'location_cm':[p.x,p.y,p.z],'height_cm':height}
    # SceneCapture secondary cameras do not necessarily drive texture streaming
    # like the real editor/player camera. Request this distant formation's full
    # mips before judging whether its UV/material data is actually broken.
    formation_component.prestream_textures(90.,False,0)
    state['prestream_components'].append(formation_component)
    for angle in [0,90,180,270]:
        r = math.radians(angle)
        distance = max(2200.,height*1.2)
        x,y=p.x+math.cos(r)*distance,p.y+math.sin(r)*distance
        ignore=[a for a in all_actors if not isinstance(a,unreal.LandscapeProxy)]
        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),
                                                  unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
        parts=unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method('BreakHitResult',(hit,))
        if not parts[0]:
            report['errors'].append('Rock camera terrain missing atangle'+str(angle)); continue
        camera = unreal.Vector(x,y,max(parts[5].z+250.,p.z+max(350.,height*.35)))
        shots.append(('rock_formation_'+str(angle),camera,target,70.))
elif not globals().get('HABITAT_ONLY',False):
    report['errors'].append('No large PCG formation found in loaded world; rock captures omitted.')


def finish(status):
    report['status']=status
    if state['capture'] and unreal.SystemLibrary.is_valid(state['capture']): actors.destroy_actor(state['capture'])
    if state['handle'] is not None: unreal.unregister_slate_post_tick_callback(state['handle'])
    unreal.SystemLibrary.execute_console_command(world,'r.Streaming.FullyLoadUsedTextures '+str(state['old_full_mips']))
    for component in state['prestream_components']:
        if unreal.SystemLibrary.is_valid(component): component.prestream_textures(0.,False,0)
    (OUT/'report.json').write_text(json.dumps(report,indent=2,default=str))


try:
    unreal.SystemLibrary.execute_console_command(world,'r.Streaming.FullyLoadUsedTextures 1')
    report['temporary_full_texture_mips']=True
    report['limits']='Full texture residency is temporary capture QA only; this is not a streaming/performance benchmark.'
    name,location,target,fov = shots[0]
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D,location,look(location,target))
    state['capture']=capture
    capture.set_actor_label('TEMP_Phase3ArtCapture')
    c = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    t = unreal.RenderingLibrary.create_render_target2d(world,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    c.set_editor_property('texture_target',t)
    c.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    c.set_editor_property('capture_every_frame',False)
    c.set_editor_property('always_persist_rendering_state',True)
    c.set_editor_property('fov_angle',fov)
    c.set_editor_property('post_process_blend_weight',1.)
    try:
        exposure = next((a for a in all_actors if isinstance(a,unreal.PostProcessVolume) and 'DF_Phase1_Exposure' in [str(t) for t in a.tags]),None)
        post = exposure.get_editor_property('settings') if exposure else c.get_editor_property('post_process_settings')
        post.set_editor_property('override_dynamic_global_illumination_method',True)
        post.set_editor_property('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN)
        post.set_editor_property('override_reflection_method',True)
        post.set_editor_property('reflection_method',unreal.ReflectionMethod.LUMEN)
        c.set_editor_property('post_process_settings',post)
    except Exception as exc: report['errors'].append('Capture Lumen override: '+str(exc))
    def tick(delta):
        try:
            # Hidden/minimized authoring sessions may not tick CaptureEveryFrame.
            # Explicit captures also make a headless art-review pass meaningful.
            c.capture_scene()
            if time.monotonic()-state['since']<6: return
            name,location,target,fov = shots[state['index']]
            # CaptureEveryFrame already populated the warmed target.
            unreal.RenderingLibrary.export_render_target(world,t,str(OUT),name+'.png')
            report['captures'].append({'file':name+'.png','location_cm':[location.x,location.y,location.z],
                                       'look_at_cm':[target.x,target.y,target.z],'fov':fov})
            state['index']+=1
            if state['index']==len(shots): finish('complete; inspect visually')
            else:
                _,location,target,fov = shots[state['index']]
                capture.set_actor_location(location,False,True)
                capture.set_actor_rotation(look(location,target),False)
                c.set_editor_property('fov_angle',fov)
                state['since']=time.monotonic()
        except Exception:
            report['errors'].append(traceback.format_exc()); finish('failed')
    state['handle']=unreal.register_slate_post_tick_callback(tick)
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
except Exception:
    report['errors'].append(traceback.format_exc()); finish('failed')
    raise
