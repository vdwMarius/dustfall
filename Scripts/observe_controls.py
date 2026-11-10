"""Read-only PIE telemetry while checking physical keyboard controls."""
import json
import pathlib
import time
import unreal

report = pathlib.Path(unreal.Paths.project_saved_dir()) / 'Codex/keyboard_report.json'
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_game_world()
if not world:
    raise RuntimeError('Start the dedicated editor PIE session before observing controls')
pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
pc = unreal.GameplayStatics.get_player_controller(world, 0)
start = pawn.get_actor_location()
begin = time.monotonic()
evidence = {'scope': 'Read-only observations during physical UI input; no action injection.',
            'max_horizontal_cm': 0.0, 'max_rise_cm': 0.0, 'max_speed_setting': 0.0,
            'minimum_camera_arm_cm': 400.0, 'flashlight_seen_on': False,
            'initial_yaw': pc.get_control_rotation().yaw, 'max_look_change_deg': 0.0}

def observe(delta):
    if not editor.get_game_world() or time.monotonic() - begin > 90:
        unreal.unregister_slate_post_tick_callback(handle)
        return
    pos = pawn.get_actor_location()
    evidence['max_horizontal_cm'] = max(evidence['max_horizontal_cm'], ((pos.x-start.x)**2+(pos.y-start.y)**2)**0.5)
    evidence['max_rise_cm'] = max(evidence['max_rise_cm'], pos.z-start.z)
    movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
    arm = pawn.get_component_by_class(unreal.SpringArmComponent)
    light = pawn.get_component_by_class(unreal.SpotLightComponent)
    evidence['max_speed_setting'] = max(evidence['max_speed_setting'], movement.max_walk_speed)
    evidence['minimum_camera_arm_cm'] = min(evidence['minimum_camera_arm_cm'], arm.target_arm_length)
    evidence['flashlight_seen_on'] |= light.is_visible()
    evidence['max_look_change_deg'] = max(evidence['max_look_change_deg'], abs(pc.get_control_rotation().yaw - evidence['initial_yaw']))
    evidence['current_arm_cm'] = arm.target_arm_length
    evidence['flashlight_on'] = light.is_visible()
    report.write_text(json.dumps(evidence, indent=2), encoding='utf-8')

handle = unreal.register_slate_post_tick_callback(observe)
