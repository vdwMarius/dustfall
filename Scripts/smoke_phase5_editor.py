"""Brief M3b-3 callable PIE smoke; Lead runs after survival native authoring.

Requires sole editor lock, PIE stopped, foundation map open. Uses only dedicated
QA slots (including exploration companion); restores the authored slot and
never saves editor packages. Poll phase5_smoke.json until status is terminal:
queue completion only registers the callback. No other suites are launched.
Rates use elapsed game time over three seconds with 15% tolerance. Movement
is disabled in PIE to keep measurements out of falling/airlock interactions.
This does not establish physical-input, presentation or performance acceptance.
"""
import json
import pathlib
import time
import traceback

import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = ROOT / 'Saved/Codex/phase5_smoke.json'
QA = 'Dustfall_Phase5_BriefQA'
MAP = '/Game/World/Maps/L_Dustfall_Foundation'
SECONDS = 3.0
TOLERANCE = .15
SAVE_FIELDS = ('Oxygen', 'Power', 'Integrity', 'Stamina', 'CloneGeneration',
               'CarriedScrap', 'CrateScrap', 'CrateActive', 'CrateLocation', 'SavedLocation')


def main():
    result = dict(status='running', checks={}, measurements={}, errors=[],
                  scope='Brief native survival PIE only; no additional suites')
    state = dict(stage='start', handle=None, since=time.monotonic(), source=None,
                 original_slot=None, passed=False)
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    def write():
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')

    def check(name, ok):
        result['checks'][name] = bool(ok)
        if not ok:
            raise RuntimeError('Failed: ' + name)

    def delete_slots():
        for slot in (QA, QA + '_Exploration'):
            if unreal.GameplayStatics.does_save_game_exist(slot, 0):
                check('delete_qa_slot_' + slot, unreal.GameplayStatics.delete_game_in_slot(slot, 0))

    def restore_slot():
        if state['source'] is not None:
            state['source'].set_editor_property('SaveSlotName', state['original_slot'])
            check('authored_slot_restored', state['source'].get_editor_property('SaveSlotName') ==
                  state['original_slot'])

    def finish():
        result['status'] = 'cleaning_up'
        state.update(stage='end', since=time.monotonic())
        level.editor_request_end_play()
        # Editor actor and PIE actor are separate. Restore authoring immediately,
        # even if ending PIE is delayed, then verify again once PIE has ended.
        restore_slot()
        write()

    def game_time():
        return unreal.GameplayStatics.get_time_seconds(state['world'])

    def get(name):
        return state['s'].get_editor_property(name)

    def put(name, value):
        state['s'].set_editor_property(name, value)

    def move(position):
        state['p'].set_actor_location(position, False, True)
        check('teleport_succeeded', state['p'].get_actor_location().distance(position) < 1.)

    def measure(stage, inside, expected):
        move(get('HabitatCenter') if inside else state['outside'])
        put('Oxygen', state['max_oxygen'] * .5)
        put('Integrity', 100.)
        put('SaveElapsed', 0.)
        state.update(stage=stage, since=time.monotonic(), started=game_time(),
                     initial=get('Oxygen'), expected=expected, inside=inside)

    def measured(stage):
        elapsed = game_time() - state['started']
        if elapsed < SECONDS:
            return False
        actual = (get('Oxygen') - state['initial']) / elapsed
        expected = state['expected']
        result['measurements'][stage] = dict(elapsed_game_seconds=elapsed, actual_per_second=actual,
                                            expected_per_second=expected, tolerance=TOLERANCE)
        check(stage + '_habitat_state', bool(get('InHabitat')) == state['inside'])
        check(stage + '_rate', abs(actual - expected) <= abs(expected) * TOLERANCE)
        return True

    def tick(delta):
        try:
            stage = state['stage']
            age = time.monotonic() - state['since']
            if stage == 'end':
                if unreal.EditorLevelLibrary.get_pie_worlds(False):
                    if age > 30:
                        raise RuntimeError('PIE did not stop; QA files retained until editor stops')
                    return
                restore_slot()
                delete_slots()
                result['status'] = 'passed' if state['passed'] and not result['errors'] else 'failed'
                unreal.unregister_slate_post_tick_callback(state['handle'])
                write()
                return
            if age > 60:
                raise RuntimeError('Brief smoke stage timed out: ' + stage)
            if stage == 'start':
                level.editor_request_begin_play()
                state.update(stage='wait', since=time.monotonic())
                return
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:
                if stage != 'wait':
                    raise RuntimeError('PIE ended before smoke completed')
                return
            if stage == 'wait':
                if age < 2:
                    return
                world = worlds[0]
                bp_class = unreal.load_class(None, '/Game/Systems/BP_SurvivalDirector.BP_SurvivalDirector_C')
                s = unreal.GameplayStatics.get_actor_of_class(world, bp_class)
                check('director_is_native', isinstance(s, unreal.DustfallSurvivalDirector))
                p = unreal.GameplayStatics.get_player_character(world, 0)
                check('player_present', p is not None)
                state.update(world=world, s=s, p=p)
                check('isolated_pie_slot', get('SaveSlotName') == QA)
                tuning = get('Tuning') or get('LegacyTuning')
                check('tuning_present', tuning is not None)
                state['tuning'] = tuning
                for name, key in [('MaxOxygen', 'max_oxygen'), ('OxygenDrainPerSecond', 'drain'),
                                  ('OxygenRefillPerSecond', 'refill')]:
                    state[key] = float(tuning.get_editor_property(name))
                    check(key + '_positive', state[key] > 0)
                check('refill_window_not_clamped', state['max_oxygen'] * .5 > state['refill'] * SECONDS * 1.5)
                p.get_editor_property('character_movement').disable_movement()
                center = get('HabitatCenter')
                extent = get('HabitatHalfExtent')
                state['outside'] = center + unreal.Vector(extent.x + 1000., 0., 0.)
                measure('outside_baseline', False, -state['drain'])
                return
            s = state['s']
            if stage == 'outside_baseline' and measured(stage):
                s.set_suit_modifier('OxygenDrain', 'M3b3Smoke', 2.)
                measure('outside_double', False, -2. * state['drain'])
            elif stage == 'outside_double' and measured(stage):
                baseline = abs(result['measurements']['outside_baseline']['actual_per_second'])
                double = abs(result['measurements']['outside_double']['actual_per_second'])
                check('modifier_doubles_observed_drain', abs(double / baseline - 2.) <= 2. * TOLERANCE)
                s.clear_suit_modifier('OxygenDrain', 'M3b3Smoke')
                measure('outside_cleared', False, -state['drain'])
            elif stage == 'outside_cleared' and measured(stage):
                baseline = result['measurements']['outside_baseline']['actual_per_second']
                actual = result['measurements']['outside_cleared']['actual_per_second']
                check('clearing_restores_observed_drain', abs(actual / baseline - 1.) <= TOLERANCE)
                measure('inside_refill', True, state['refill'])
            elif stage == 'inside_refill' and measured(stage):
                s.set_capacity_bonus('Oxygen', 'M3b3Smoke', 25.)
                put('Oxygen', state['max_oxygen'] + 24.9)
                state.update(stage='capacity', started=game_time(), since=time.monotonic())
            elif stage == 'capacity':
                if game_time() - state['started'] < 1.:
                    return
                check('capacity_bonus_raises_maximum', abs(get('Oxygen') - (state['max_oxygen'] + 25.)) < .01)
                s.set_capacity_bonus('Oxygen', 'M3b3Smoke', 0.)
                state.update(stage='capacity_clear', started=game_time(), since=time.monotonic())
            elif stage == 'capacity_clear':
                if game_time() - state['started'] < .25:
                    return
                check('capacity_bonus_clear_restores_maximum', abs(get('Oxygen') - state['max_oxygen']) < .01)
                move(state['outside'])
                state['death_position'] = state['p'].get_actor_location()
                state['generation'] = get('CloneGeneration')
                put('Oxygen', 0.)
                state.update(stage='death', since=time.monotonic())
            elif stage == 'death':
                if get('CloneGeneration') == state['generation']:
                    return
                check('oxygen_zero_creates_one_clone', get('CloneGeneration') == state['generation'] + 1)
                check('clone_at_spawn', state['p'].get_actor_location().distance(get('CloneSpawn')) < 1.)
                check('death_crate_active', get('CrateActive'))
                tuning = state['tuning']
                try:
                    offset = tuning.get_editor_property('RecoveryOffset')
                except Exception:
                    offset = unreal.get_default_object(unreal.DustfallSurvivalTuning).get_editor_property('RecoveryOffset')
                expected = state['death_position'] + offset
                check('crate_at_death_position_with_tuning_offset', get('CrateLocation').distance(expected) < 1.)
                crate = get('RecoveryActor')
                check('recovery_actor_at_crate', crate is not None and crate.get_actor_location().distance(expected) < 1.)
                check('recovery_actor_visible', not crate.get_editor_property('hidden'))
                for name, value in [('Oxygen', 67.), ('Power', 71.), ('Integrity', 83.), ('Stamina', 49.),
                                    ('CarriedScrap', 4), ('CrateScrap', 7)]:
                    put(name, value)
                s.save_progress()
                check('save_progress_succeeds', get('LastSaveSucceeded'))
                saved = {name: get(name) for name in SAVE_FIELDS}
                saved_position = state['p'].get_actor_location()
                for name in SAVE_FIELDS:
                    value = saved[name]
                    put(name, value + unreal.Vector(100., 20., 30.) if isinstance(value, unreal.Vector)
                        else not value if isinstance(value, bool) else value + 1)
                move(state['outside'])
                s.load_progress()
                for name, value in saved.items():
                    observed = get(name)
                    ok = observed.distance(value) < .01 if isinstance(value, unreal.Vector) else observed == value
                    check('save_load_' + name, ok)
                check('save_load_player_location', state['p'].get_actor_location().distance(saved_position) < 1.)
                state['passed'] = True
                finish()
            write()
        except Exception:
            result['errors'].append(traceback.format_exc())
            state['passed'] = False
            if state['stage'] == 'end':
                result['status'] = 'failed'
                try:
                    restore_slot()
                finally:
                    unreal.unregister_slate_post_tick_callback(state['handle'])
                    write()
            else:
                try:
                    finish()
                except Exception:
                    result['errors'].append(traceback.format_exc())
                    # Keep callback alive in end stage so cleanup is retried.
                    write()

    try:
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if editor.get_game_world():
            raise RuntimeError('Stop PIE before smoke')
        world = editor.get_editor_world()
        if not world or world.get_path_name().split('.')[0] != MAP:
            raise RuntimeError('Foundation map required')
        if not hasattr(unreal, 'DustfallSurvivalDirector'):
            raise RuntimeError('Native build/editor restart required')
        sources = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                   if a.get_class().get_name() == 'BP_SurvivalDirector_C']
        check('one_authored_director', len(sources) == 1)
        source = sources[0]
        check('authored_director_native', isinstance(source, unreal.DustfallSurvivalDirector))
        original = source.get_editor_property('SaveSlotName')
        check('authored_slot_not_qa', original not in (QA, QA + '_Exploration'))
        state.update(source=source, original_slot=original)
        source.set_editor_property('SaveSlotName', QA)
        delete_slots()
        write()
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
    except Exception:
        result['errors'].append(traceback.format_exc())
        result['status'] = 'failed'
        try:
            restore_slot()
        finally:
            write()
        raise


if __name__ == '__main__':
    main()
