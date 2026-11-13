"""Author exploration Enhanced Input after a full native build/editor restart.

Lead must hold the exclusive editor lock and run this through editor_session.py
with PIE stopped and the foundation map open. Run twice to check idempotence.
Never launches an editor. Python is authoring only, never runtime.

build_player.py adds legacy F/V/LeftShift events; the template controller adds
/Game/Input/IMC_Default (move/look/jump) and IMC_MouseLook. Habitat and survival
builders use non-consuming legacy E events. All new actions explicitly disable
both Enhanced Input consumption and legacy key consumption, so E still reaches
the airlock/recovery Blueprint and existing template contexts remain untouched.
"""
import json
import pathlib
import traceback

import unreal


ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = ROOT / 'Saved/Codex/phase5_input_build.json'
MAP = '/Game/World/Maps/L_Dustfall_Foundation'
FOLDER = '/Game/Player/Input'
CONTEXT = FOLDER + '/IMC_DustfallExploration'
CONFIG = '/Game/Data/DA_Input_Dustfall'
BINDINGS = (
    ('Interact', 'interact', 'E'),
    ('Scanner', 'scanner', 'Q'),
    ('Inventory', 'inventory', 'Tab'),
    ('Journal', 'journal', 'J'),
    ('Beacon', 'beacon', 'B'),
    ('QuickSave', 'quick_save', 'F5'),
    ('QuickLoad', 'quick_load', 'F9'),
    ('ToggleSymptoms', 'toggle_symptoms', 'F8'),
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)
    return condition


def mappings(context):
    # UE 5.8 moved Mappings into DefaultKeyMappings; avoid the deprecated field.
    return list(context.get_editor_property('default_key_mappings').get_editor_property('mappings'))


def describe_mappings(context):
    return [dict(action=m.get_editor_property('action').get_path_name(),
                 key=str(m.get_editor_property('key').get_editor_property('key_name')))
            for m in mappings(context)]


def main(report):
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    require(not editor.get_game_world(), 'Stop PIE before authoring')
    world = require(editor.get_editor_world(), 'Editor world required')
    require(world.get_path_name().split('.')[0] == MAP, 'Foundation map required')
    require(hasattr(unreal, 'DustfallInputConfig'), 'Full native build and editor restart required')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    directors = [a for a in actors if isinstance(a, unreal.DustfallExplorationDirector)]
    require(len(directors) == 1, 'Exactly one loaded exploration director required')
    director = directors[0]
    library = unreal.EditorAssetLibrary
    actor_package = require(library.get_package_for_object(director), 'Director package missing')
    map_package = require(library.get_package_for_object(world), 'Map package missing')
    require('/__ExternalActors__/' in actor_package.get_path_name(), 'Expected World Partition external director package')

    # Refuse to overwrite unsaved edits to our targets. Leave all other dirty
    # scenes/packages alone, and never call save_dirty_packages/save_all_dirty_levels.
    targets = {CONTEXT, CONFIG, actor_package.get_path_name(), map_package.get_path_name()}
    targets.update(FOLDER + '/IA_Dustfall_' + name for name, _, _ in BINDINGS)
    dirty = (list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()) +
             list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
    require(not any(p.get_path_name() in targets for p in dirty),
            'Save or resolve existing unsaved edits to input targets/director/map first')

    # Read the actual template IMCs before editing; report them for Lead review.
    template_contexts = [require(unreal.load_asset(path), 'Missing template context ' + path)
                         for path in ('/Game/Input/IMC_Default', '/Game/Input/IMC_MouseLook')]
    template_before = {c.get_path_name(): describe_mappings(c) for c in template_contexts}
    report['template_mappings'] = template_before
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    created = []

    def asset(path, asset_class, factory):
        obj = unreal.load_asset(path) if library.does_asset_exist(path) else None
        if not obj:
            folder, name = path.rsplit('/', 1)
            obj = tools.create_asset(name, folder, asset_class, factory)
            created.append(path)
        require(isinstance(obj, asset_class), 'Missing or incorrect asset class: ' + path)
        obj.modify()
        return obj

    actions = []
    for name, field, key in BINDINGS:
        action = asset(FOLDER + '/IA_Dustfall_' + name, unreal.InputAction, unreal.InputAction_Factory())
        action.set_editor_property('value_type', unreal.InputActionValueType.BOOLEAN)
        action.set_editor_property('consume_input', False)
        action.set_editor_property('consumes_action_and_axis_mappings', False)
        action.set_editor_property('reserve_all_mappings', False)
        action.set_editor_property('trigger_when_paused', False)
        action.set_editor_property('triggers', [])
        action.set_editor_property('modifiers', [])
        actions.append((action, field, key))

    context = asset(CONTEXT, unreal.InputMappingContext, unreal.InputMappingContext_Factory())
    context.unmap_all()
    for action, _, key in actions:
        mapped_key = unreal.Key()  # unreal.Key takes no constructor arguments in this build (probed live)
        mapped_key.set_editor_property('key_name', key)
        context.map_key(action, mapped_key)
    factory = unreal.DataAssetFactory()
    factory.set_editor_property('data_asset_class', unreal.DustfallInputConfig)
    config = asset(CONFIG, unreal.DustfallInputConfig, factory)
    config.set_editor_property('mapping_context', context)
    config.set_editor_property('mapping_priority', 0)
    for action, field, _ in actions:
        config.set_editor_property(field, action)
    director.modify()
    director.set_editor_property('input_config', config)

    actual = describe_mappings(context)
    expected = [dict(action=a.get_path_name(), key=k) for a, _, k in actions]
    require(actual == expected, 'Expected exactly eight default mappings, without duplicates')
    require(all(not a.get_editor_property('consume_input') and
                not a.get_editor_property('consumes_action_and_axis_mappings') for a, _, _ in actions),
            'Exploration actions must not consume shared Enhanced/legacy keys')
    require(template_before == {c.get_path_name(): describe_mappings(c) for c in template_contexts},
            'Template contexts changed unexpectedly')
    for obj in [a for a, _, _ in actions] + [context, config]:
        require(library.save_loaded_asset(obj, False), 'Failed saving ' + obj.get_path_name())
    packages = [actor_package, map_package]
    require(unreal.EditorLoadingAndSavingUtils.save_packages(packages, False),
            'Failed saving director external package/map')
    report.update(
        status='built; runtime validation pending',
        created_assets=created,
        actions=actual,
        mapping_context=context.get_path_name(),
        input_config=config.get_path_name(),
        mapping_priority=0,
        native_director=director.get_path_name(),
        saved_packages=[p.get_path_name() for p in packages],
        template_contexts_unchanged=True,
        shared_e_non_consuming=True,
        trigger_event='Started',
        validation='Asset authoring checks only; physical keys and lifecycle require PIE',
    )


if __name__ == '__main__':
    result = {'status': 'failed'}
    try:
        main(result)
    except Exception:
        result['error'] = traceback.format_exc()
        raise
    finally:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2), encoding='utf-8')
        unreal.log('Phase5 input report: ' + str(REPORT))
