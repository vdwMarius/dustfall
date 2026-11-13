"""Capture measured editor visibility targets without saving test actors.

Three weather states, 40/60/100 m human-scale and boulder targets. Captures are
visual evidence, not automated acceptance. Run only with PIE stopped. Settles
each SceneCapture for five seconds to permit Lumen history. Restores lighting.
"""
import json
import math
import pathlib
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
OUT = ROOT/'Saved/Codex'/globals().get('OUTPUT_SUBDIR','Phase3Visibility')
OUT.mkdir(parents=True,exist_ok=True)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('Stop PIE before editor visibility captures')
world = editor.get_editor_world()
current = list(actors.get_all_level_actors())
fog_actor = next(a for a in current if isinstance(a,unreal.ExponentialHeightFog))
sun_actor = next(a for a in current if isinstance(a,unreal.DirectionalLight))
sky_actor = next(a for a in current if isinstance(a,unreal.SkyLight))
fog = fog_actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
sun = sun_actor.get_component_by_class(unreal.DirectionalLightComponent)
sky = sky_actor.get_component_by_class(unreal.SkyLightComponent)
saved = {'density':fog.get_editor_property('fog_density'),
         'color':fog.get_editor_property('fog_inscattering_luminance'),
         'rotation':sun_actor.get_actor_rotation(),'sun':sun.get_editor_property('intensity'),
         'sky':sky.get_editor_property('intensity')}
data = unreal.load_asset('/Game/Data/DA_Environment_Phase2')
temporary = []
report = {'status':'running','method':'Editor SceneCapture2D, measured horizontal distances; visual review required',
          'targets':[],'captures':[],'errors':[]}
state = {'index':0,'since':time.monotonic(),'handle':None}
breaker = unreal.get_default_object(unreal.GameplayStatics.static_class())
ignore = [a for a in current if not isinstance(a,unreal.LandscapeProxy)]


def ground(x,y):
    hit = unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),
                                                unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
    parts = breaker.call_method('BreakHitResult',(hit,))
    if not parts[0]: raise RuntimeError('Visibility target terrain not loaded: '+str((x,y)))
    return parts[5].z


def mesh_actor(mesh,location,scale,material=None):
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,location)
    temporary.append(actor)
    actor.set_actor_label('TEMP_VisibilityTarget')
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    if material: actor.static_mesh_component.set_material(0,material)
    actor.set_actor_scale3d(scale)
    return actor


def finish(status):
    fog.set_fog_density(saved['density']); fog.set_fog_inscattering_color(saved['color'])
    sun_actor.set_actor_rotation(saved['rotation'],False); sun.set_intensity(saved['sun']); sky.set_intensity(saved['sky'])
    for actor in temporary:
        if unreal.SystemLibrary.is_valid(actor): actors.destroy_actor(actor)
    report['status']=status
    (OUT/'report.json').write_text(json.dumps(report,indent=2,default=str))
    if state['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(state['handle'])
    callback = globals().get('ON_COMPLETE')
    if callback:
        callback(status,report)


try:
    cx,cy = 2500.,-4000.
    cz = ground(cx,cy)+180.
    camera = unreal.Vector(cx,cy,cz)
    cube = unreal.load_asset('/Engine/BasicShapes/Cube')
    sphere = unreal.load_asset('/Engine/BasicShapes/Sphere')
    dark = unreal.load_asset('/Game/Habitat/Materials/M_P3_Hab_Charcoal')
    rock = unreal.load_asset('/Game/World/Phase3/Meshes/SM_PCG_xgkmfcy')
    if not rock: raise RuntimeError('Build native PCG rock assets first')
    for index,distance in enumerate([4000.,6000.,10000.]):
        for kind,angle in [('human',-21+index*14),('boulder',-15+index*14)]:
            r = math.radians(angle)
            x,y = cx+distance*math.cos(r),cy+distance*math.sin(r)
            z = ground(x,y)
            if kind=='human':
                # 1.8m total human-scale silhouette with shoulders/head/legs.
                mesh_actor(cube,unreal.Vector(x,y,z+112),unreal.Vector(.35,.6,.85),dark)
                mesh_actor(sphere,unreal.Vector(x,y,z+165),unreal.Vector(.3,.3,.3),dark)
                for off in [-15,15]:
                    mesh_actor(cube,unreal.Vector(x,y+off,z+35),unreal.Vector(.27,.22,.7),dark)
            else:
                width = max(rock.get_bounds().box_extent.x,rock.get_bounds().box_extent.y)*2
                s = 400./width
                mesh_actor(rock,unreal.Vector(x,y,z-15),unreal.Vector(s,s,s))
            report['targets'].append({'kind':kind,'horizontal_distance_m':distance/100.,'location_cm':[x,y,z],'angle_degrees':angle})
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D,camera,unreal.Rotator(pitch=0,yaw=0))
    temporary.append(capture)
    component = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    target = unreal.RenderingLibrary.create_render_target2d(world,1920,1080,unreal.TextureRenderTargetFormat.RTF_RGBA8)
    component.set_editor_property('texture_target',target)
    component.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    component.set_editor_property('capture_every_frame',True)
    component.set_editor_property('always_persist_rendering_state',True)
    component.set_editor_property('fov_angle',65.)
    component.set_editor_property('post_process_blend_weight',1.)
    try:
        exposure = next((a for a in current if isinstance(a,unreal.PostProcessVolume) and 'DF_Phase1_Exposure' in [str(t) for t in a.tags]),None)
        post = exposure.get_editor_property('settings') if exposure else component.get_editor_property('post_process_settings')
        post.set_editor_property('override_dynamic_global_illumination_method',True)
        post.set_editor_property('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN)
        post.set_editor_property('override_reflection_method',True)
        post.set_editor_property('reflection_method',unreal.ReflectionMethod.LUMEN)
        component.set_editor_property('post_process_settings',post)
        report['capture_exposure_ev100'] = [post.get_editor_property('auto_exposure_min_brightness'),post.get_editor_property('auto_exposure_max_brightness')]
    except Exception as exc:
        report['errors'].append('Scene capture Lumen overrides: '+str(exc))
    sun_actor.set_actor_rotation(unreal.Rotator(pitch=-65,yaw=-35),False)
    fog.set_fog_inscattering_color(unreal.LinearColor(data.get_editor_property('FogRed'),data.get_editor_property('FogGreen'),data.get_editor_property('FogBlue'),1.))
    presets = globals().get('CAPTURE_WEATHERS',[('baseline',0),('haze',1),('storm',2)])
    def apply(index):
        name,weather = presets[index]
        fog.set_fog_density(data.get_editor_property(['CalmFogDensity','HazeFogDensity','StormFogDensity'][weather]))
        light_multiplier = data.get_editor_property('StormLightMultiplier') if weather==2 else 1.
        candidate = globals().get('LIGHTING_CANDIDATE',{})
        sun.set_intensity(candidate.get('sun',data.get_editor_property('SunIntensity'))*light_multiplier)
        sky.set_intensity(candidate.get('sky',data.get_editor_property('DaySkyIntensity'))*light_multiplier)
    apply(0)
    def tick(delta):
        try:
            if time.monotonic()-state['since']<5: return
            name,weather = presets[state['index']]
            # CaptureEveryFrame already populated the warmed target.
            unreal.RenderingLibrary.export_render_target(world,target,str(OUT),name+'.png')
            report['captures'].append({'file':name+'.png','weather':weather,'fog_density':fog.get_editor_property('fog_density')})
            state['index']+=1
            if state['index']==len(presets):
                finish('complete; inspect silhouettes visually')
            else:
                apply(state['index']); state['since']=time.monotonic()
        except Exception:
            report['errors'].append(traceback.format_exc()); finish('failed')
    state['handle'] = unreal.register_slate_post_tick_callback(tick)
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
except Exception:
    report['errors'].append(traceback.format_exc()); finish('failed')
    raise
