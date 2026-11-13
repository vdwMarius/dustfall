"""Asynchronous PIE survival regression; uses an isolated QA save slot.

Run in sole editor with foundation map loaded, no PIE. Does not touch the user's
Dustfall_Phase3 slot. Callable recovery validates logic, not physical E input.
"""
import json
import pathlib
import time
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = ROOT / 'Saved/Codex/phase3_survival_verification.json'
QA_SLOT = 'Dustfall_Phase3_AutomatedQA'
result = {'status': 'running', 'checks': {}, 'errors': [], 'scope': 'Real PIE resource ticks; callable interaction functions, not physical keyboard.'}
state = {'stage': 'start', 'since': time.monotonic(), 'handle': None, 'owns_pie': False}
editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cls = unreal.load_class(None, '/Game/Systems/BP_SurvivalDirector.BP_SurvivalDirector_C')
editor_actor = next((a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_class() == cls), None)
if not editor_actor:
    raise RuntimeError('Build Phase 3 survival before running verification')
original_slot = editor_actor.get_editor_property('SaveSlotName')
editor_actor.set_editor_property('SaveSlotName', QA_SLOT)
unreal.GameplayStatics.delete_game_in_slot(QA_SLOT, 0)


def write():
    REPORT.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')


def stage(name):
    state.update(stage=name, since=time.monotonic())
    write()


def check(name, ok, detail):
    result['checks'][name] = {'status': 'pass' if ok else 'fail', 'detail': detail}


def prop(name):
    return state['director'].get_editor_property(name)


def setprop(name, value):
    state['director'].set_editor_property(name, value)


def invoke(name):
    return state['director'].call_method(name)


def finish(status='completed'):
    result['status'] = ('failed' if any(c['status'] == 'fail' for c in result['checks'].values()) else 'passed') if status == 'completed' else status
    if state['owns_pie']:
        editor.editor_request_end_play()
        stage('wait_end')
        return
    cleanup()


def cleanup():
    editor_actor.set_editor_property('SaveSlotName', original_slot)
    unreal.GameplayStatics.delete_game_in_slot(QA_SLOT, 0)
    write()
    if state['handle']:
        unreal.unregister_slate_post_tick_callback(state['handle'])
        state['handle'] = None


def move(location):
    state['pawn'].set_actor_location(location, False, True)


def poll(delta):
    try:
        age = time.monotonic() - state['since']
        mode = state['stage']
        if mode == 'wait_end':
            if not unreal.EditorLevelLibrary.get_pie_worlds(False):
                cleanup()
            return
        if mode == 'start':
            if unreal.EditorLevelLibrary.get_pie_worlds(False):
                raise RuntimeError('End existing PIE before survival verification')
            editor.editor_request_begin_play()
            state['owns_pie'] = True
            stage('wait_pie')
        elif mode == 'wait_pie':
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:
                if age > 45:
                    raise RuntimeError('PIE world timeout')
                return
            world = worlds[0]
            actors = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            if not actors or not pawn:
                return
            state.update(world=world, director=actors[0], pawn=pawn)
            if age < 2:
                return
            check('isolated save slot', prop('SaveSlotName') == QA_SLOT, prop('SaveSlotName'))
            spawn = prop('CloneSpawn')
            state['outside'] = spawn + unreal.Vector(1800, 0, 0)
            move(state['outside'])
            setprop('Oxygen', 80.); setprop('Power', 80.)
            stage('outside_drain')
        elif mode == 'outside_drain' and age > 2:
            check('outside oxygen and power drain', prop('Oxygen') < 79.9 and prop('Power') < 79.99 and not prop('InHabitat'),
                  {'oxygen': prop('Oxygen'), 'power': prop('Power'), 'inside': prop('InHabitat')})
            move(prop('CloneSpawn')); setprop('Oxygen', 50.); setprop('Power', 50.)
            stage('inside_refill')
        elif mode == 'inside_refill' and age > 1:
            check('sanctuary refill', prop('InHabitat') and prop('Oxygen') > 52 and prop('Power') > 51,
                  {'oxygen': prop('Oxygen'), 'power': prop('Power'), 'inside': prop('InHabitat')})
            move(state['outside']); setprop('Oxygen', 10.); setprop('Power', 0.)
            setprop('WarningElapsed', 99.); setprop('OxygenWarningCount', 0)
            light = state['pawn'].get_component_by_class(unreal.SpotLightComponent)
            light.set_visibility(True, False)
            stage('warning')
        elif mode == 'warning' and age > .6:
            light = state['pawn'].get_component_by_class(unreal.SpotLightComponent)
            check('power depletion disables flashlight', not light.is_visible(), {'power': prop('Power'), 'visible': light.is_visible()})
            check('low oxygen sound cooldown', prop('OxygenWarningCount') == 1 and prop('WarningElapsed') < 2.,
                  {'playback_requests': prop('OxygenWarningCount'), 'elapsed': prop('WarningElapsed'), 'scope': 'Playback node execution telemetry; subjective listening still required'})
            setprop('Oxygen', 80.); setprop('Power', 80.)
            move(state['outside']); setprop('Stamina', 5.); setprop('SprintRequested', True)
            state['max_sprint_velocity'] = 0.
            state['observed_natural_exhaustion'] = None
            state['minimum_sprint_stamina'] = 5.
            stage('sprint_depletion')
        elif mode == 'sprint_depletion':
            state['pawn'].add_movement_input(unreal.Vector(1, 0, 0), 1., True)
            velocity = state['pawn'].get_velocity()
            state['max_sprint_velocity'] = max(state['max_sprint_velocity'], (velocity.x ** 2 + velocity.y ** 2) ** .5)
            state['minimum_sprint_stamina'] = min(state['minimum_sprint_stamina'], prop('Stamina'))
            speed = state['pawn'].get_component_by_class(unreal.CharacterMovementComponent).max_walk_speed
            if state['max_sprint_velocity'] > 550 and prop('SprintExhausted') and speed <= 500:
                state['observed_natural_exhaustion'] = {'elapsed': age, 'stamina': prop('Stamina'), 'max_walk_speed': speed}
            # Observe the transition, rather than sampling a single wall-clock
            # instant: terrain settling can delay acceleration, and a long run
            # may already have recovered enough stamina to resume sprinting.
            if state['observed_natural_exhaustion'] or age > 6.:
                check('real sprint depletion limits speed', bool(state['observed_natural_exhaustion']),
                      {'maximum_velocity': state['max_sprint_velocity'], 'minimum_stamina': state['minimum_sprint_stamina'],
                       'observed_exhaustion': state['observed_natural_exhaustion'], 'final_stamina': prop('Stamina'),
                       'final_exhausted': prop('SprintExhausted'), 'final_max_walk_speed': speed})
                setprop('SprintRequested', False)
                move(prop('CloneSpawn')); setprop('Stamina', 0.)
                stage('exhaustion')
        elif mode == 'exhaustion' and age > .15:
            speed = state['pawn'].get_component_by_class(unreal.CharacterMovementComponent).max_walk_speed
            check('exhaustion limits speed', prop('SprintExhausted') and speed <= 500,
                  {'exhausted': prop('SprintExhausted'), 'max_walk_speed': speed})
            setprop('Stamina', 90.)
            move(state['outside']); setprop('CarriedScrap', 7)
            state['clone_before'] = prop('CloneGeneration')
            setprop('Oxygen', 0.); stage('oxygen_death')
        elif mode == 'oxygen_death' and age > .8:
            distance = (state['pawn'].get_actor_location() - prop('CloneSpawn')).length()
            check('oxygen death creates one clone', prop('CloneGeneration') == state['clone_before'] + 1 and prop('Oxygen') > 90 and distance < 180,
                  {'clone': prop('CloneGeneration'), 'spawn_error_cm': distance, 'oxygen': prop('Oxygen')})
            check('death leaves recoverable payload', prop('CrateActive') and prop('CrateScrap') == 7 and prop('CarriedScrap') == 0,
                  {'active': prop('CrateActive'), 'cache': prop('CrateScrap'), 'carried': prop('CarriedScrap')})
            move(state['outside']); setprop('CarriedScrap', 3); setprop('Integrity', 0.)
            stage('integrity_death')
        elif mode == 'integrity_death' and age > .8:
            check('integrity death preserves pending cache', prop('CloneGeneration') == state['clone_before'] + 2 and prop('CrateScrap') == 10 and prop('Integrity') > 90,
                  {'clone': prop('CloneGeneration'), 'cache': prop('CrateScrap'), 'integrity': prop('Integrity')})
            setprop('Oxygen', 73.); invoke('SaveProgress')
            check('save succeeded', prop('LastSaveSucceeded'), 'QA slot only')
            setprop('Oxygen', 12.); setprop('CrateScrap', 0); setprop('CrateActive', False); setprop('CloneGeneration', 99)
            invoke('LoadProgress')
            check('load restores stats clone and pending cache', abs(prop('Oxygen') - 73) < .1 and prop('CrateScrap') == 10 and prop('CrateActive') and prop('CloneGeneration') == state['clone_before'] + 2,
                  {'oxygen': prop('Oxygen'), 'cache': prop('CrateScrap'), 'active': prop('CrateActive'), 'clone': prop('CloneGeneration')})
            invoke('RecoverCrate')
            check('recovery requires proximity', prop('CrateActive') and prop('CarriedScrap') == 0, 'Called from habitat before approaching cache')
            move(prop('CrateLocation') + unreal.Vector(0, 0, 65)); invoke('RecoverCrate')
            check('recovery transfers payload once', prop('CarriedScrap') == 10 and prop('CrateScrap') == 0 and not prop('CrateActive'),
                  {'carried': prop('CarriedScrap'), 'cache': prop('CrateScrap'), 'active': prop('CrateActive')})
            invoke('RecoverCrate')
            check('recovery cannot duplicate', prop('CarriedScrap') == 10, prop('CarriedScrap'))
            invoke('LoadProgress')
            check('recovered state persisted', not prop('CrateActive') and prop('CarriedScrap') == 10, 'Immediate reload after recovery save')
            finish()
    except Exception:
        result['errors'].append(traceback.format_exc())
        finish('error')


write()
state['handle'] = unreal.register_slate_post_tick_callback(poll)
