"""Two lightweight editor scene captures of authored relief, no texture overrides.

Not a visibility matrix, runtime streaming test or user acceptance. Temporary
SceneCapture actor is destroyed and no map/asset is saved.
"""
import json
import math
import pathlib
import time
import unreal

ROOT=pathlib.Path(unreal.Paths.project_dir())
OUT=ROOT/'Saved/Codex/Phase3Terrain'
OUT.mkdir(parents=True,exist_ok=True)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop PIE before terrain capture')
shots=[('sinkhole',unreal.Vector(-5200,-3000,1800),unreal.Vector(-8500,-6500,-500)),
       ('relief_hill',unreal.Vector(3200,-4000,900),unreal.Vector(8000,-11000,2300))]
def look(p,q):
    d=q-p
    return unreal.Rotator(pitch=math.degrees(math.atan2(d.z,math.hypot(d.x,d.y))),
                          yaw=math.degrees(math.atan2(d.y,d.x)))
actor=actors.spawn_actor_from_class(unreal.SceneCapture2D,shots[0][1],look(shots[0][1],shots[0][2]))
component=actor.get_component_by_class(unreal.SceneCaptureComponent2D)
target=unreal.RenderingLibrary.create_render_target2d(world,1280,720,unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.set_editor_property('texture_target',target)
component.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
component.set_editor_property('capture_every_frame',False)
component.set_editor_property('always_persist_rendering_state',True)
component.set_editor_property('fov_angle',75.)
post=next((a for a in actors.get_all_level_actors() if isinstance(a,unreal.PostProcessVolume)),None)
if post:component.set_editor_property('post_process_settings',post.get_editor_property('settings'))
state={'index':0,'since':time.monotonic(),'handle':None}
report={'status':'running','scope':'Two editor SceneCapture views, normal texture residency; not player-camera acceptance','captures':[]}
def tick(delta):
    component.capture_scene()
    if time.monotonic()-state['since']<3:return
    name,p,q=shots[state['index']]
    unreal.RenderingLibrary.export_render_target(world,target,str(OUT),name+'.png')
    report['captures'].append({'file':name+'.png','camera_cm':[p.x,p.y,p.z],'target_cm':[q.x,q.y,q.z]})
    state['index']+=1
    if state['index']==len(shots):
        actors.destroy_actor(actor)
        unreal.unregister_slate_post_tick_callback(state['handle'])
        report['status']='complete; inspect images'
        (OUT/'report.json').write_text(json.dumps(report,indent=2))
        return
    _,p,q=shots[state['index']]
    actor.set_actor_location(p,False,True)
    actor.set_actor_rotation(look(p,q),False)
    state['since']=time.monotonic()
state['handle']=unreal.register_slate_post_tick_callback(tick)
