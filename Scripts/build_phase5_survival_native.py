"""M3b-3: migrate the existing survival Blueprint under the Lead's editor lock.

Run through editor_session.py with the foundation map open and PIE stopped,
after a full native build/restart. Run twice to check idempotence, then run
smoke_phase5_editor.py. Never launches an editor or replaces a level actor.

Manual rollback ONLY: close Unreal completely; use Backup_M3b3/manifest.json
to copy each backup to its original project-relative filename. The original
Blueprint and external actor/component packages are retained on first run.
Do not copy backups over loaded packages. No live restore entry point exists.
The new DA_Survival can remain unused after rollback; old tuning is untouched.
If migration fails after mutation, do not save dirty targets: close and restore.
"""
import json
import pathlib
import shutil
import traceback

import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
REPORT = ROOT / 'Saved/Codex/phase5_survival_native.json'
BACKUP = ROOT / 'Saved/Codex/Backup_M3b3'
MAP = '/Game/World/Maps/L_Dustfall_Foundation'
BP = '/Game/Systems/BP_SurvivalDirector'
OLD = '/Game/Data/DA_Survival_Phase3'
NEW = '/Game/Data/DA_Survival'
BEL = unreal.BlueprintEditorLibrary
LIB = unreal.EditorAssetLibrary
FUNCTIONS = ('RefreshRecoveryCache', 'SaveProgress', 'LoadProgress',
             'RecoverCrate', 'RespawnClone', 'GetSuitState')
VALUES = ('Oxygen', 'Power', 'Integrity', 'Stamina', 'CloneGeneration',
          'CarriedScrap', 'CrateScrap', 'CrateActive', 'CrateLocation',
          'SavedLocation', 'InHabitat', 'DeathInProgress', 'SprintExhausted',
          'SprintRequested', 'HabitatCenter', 'HabitatHalfExtent', 'CloneSpawn',
          'SaveElapsed', 'LastSaveSucceeded', 'WarningElapsed',
          'OxygenWarningCount', 'StaminaBeforeTick', 'SaveSlotName',
          'EnvironmentDirector', 'RecoveryActor', 'Tuning')
TUNING_FIELDS = ('MaxOxygen', 'MaxPower', 'MaxIntegrity', 'MaxStamina',
                 'OxygenDrainPerSecond', 'OxygenRefillPerSecond',
                 'PowerDrainPerSecond', 'PowerRefillPerSecond',
                 'StaminaDrainPerSecond', 'StaminaRefillPerSecond',
                 'StormIntegrityDrainPerSecond', 'WalkSpeed', 'SprintSpeed',
                 'ExhaustedSpeed', 'SaveIntervalSeconds', 'RecoveryDistance',
                 'OxygenWarningThreshold', 'OxygenWarningCooldown',
                 'StaminaRecoveryThreshold', 'SprintVelocityThreshold',
                 'OxygenWarningVolume', 'RecoveryOffset')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)
    return ok


def encode(value):
    if isinstance(value, unreal.Vector):
        return {'vector': [value.x, value.y, value.z]}
    if isinstance(value, unreal.Object):
        return {'object': value.get_path_name()}
    return value


def decode(value):
    if isinstance(value, dict):
        if 'vector' in value:
            return unreal.Vector(*value['vector'])
        return require(unreal.load_object(None, value['object']),
                       'Cannot resolve snapshot reference ' + value['object'])
    return value


def snapshot(obj):
    return {name: encode(obj.get_editor_property(name)) for name in VALUES}


def identity(actor):
    return dict(path=actor.get_path_name(), label=actor.get_actor_label(),
                folder=str(actor.get_folder_path()),
                tags=[str(t) for t in actor.get_editor_property('tags')],
                guid=actor.get_editor_property('actor_guid').to_string(),  # str() embeds a memory address
                spatial=actor.get_editor_property('is_spatially_loaded'))


def package(obj):
    return require(LIB.get_package_for_object(obj), 'Missing package: ' + obj.get_path_name())


def dirty_packages():
    return {p.get_path_name(): p for p in
            list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()) +
            list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())}


def actor_packages(actor):
    objects = [actor] + list(actor.get_components_by_class(unreal.ActorComponent))
    return {package(o).get_path_name(): package(o) for o in objects}


def backup(packages, report):
    manifest_path = BACKUP / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    for name in packages:
        require(name.startswith('/Game/'), 'Only project packages may be backed up: ' + name)
        relative = 'Content/' + name[len('/Game/'):] + '.uasset'
        source = ROOT / relative
        require(source.is_file(), 'Save target before migration; missing file: ' + str(source))
        destination = BACKUP / relative
        if relative not in manifest:
            require(not destination.exists(), 'Orphaned backup; resolve manually: ' + str(destination))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            manifest[relative] = str(destination.relative_to(ROOT))
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        require((ROOT / manifest[relative]).is_file(), 'Recorded backup missing: ' + relative)
    report['backups'] = manifest
    first_snapshot = BACKUP / 'snapshot.json'
    if not first_snapshot.exists():
        first_snapshot.write_text(json.dumps(report['snapshot'], indent=2), encoding='utf-8')


def compile_checked(asset, report):
    entry = dict(asset=asset.get_path_name(), messages=[])
    report['compile_messages'].append(entry)
    try:
        ok = BEL.compile_blueprint(asset)
        entry['status'] = str(asset.get_editor_property('status'))
        for graph in BEL.list_graphs(asset):
            ed = unreal.BlueprintGraphEditor.get_graph_editor(graph)
            for severity, nodes in [('error', ed.list_nodes_with_errors()),
                                    ('warning', ed.list_nodes_with_warnings()),
                                    ('note', ed.list_nodes_with_notes())]:
                for node in nodes:
                    entry['messages'].append(dict(severity=severity, graph=graph.get_name(),
                        node=node.get_path_name(), text=str(node.get_editor_property('error_msg'))))
        # CompileBlueprint's bool excludes errors only; Status also catches
        # non-node warnings. A status without graph messages remains explicit.
        entry['passed'] = bool(ok and asset.get_editor_property('status') ==
                               unreal.BlueprintStatus.BS_UP_TO_DATE and not any(
                                   m['severity'] in ('error', 'warning') for m in entry['messages']))
        return entry['passed']
    except Exception:
        entry.update(passed=False, error=traceback.format_exc())
        return False


def main(report):
    require(not globals().get('RESTORE_BACKUP', False), 'Live restore forbidden; see module docstring')
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    require(not editor.get_game_world(), 'Stop PIE before authoring')
    world = require(editor.get_editor_world(), 'Editor world required')
    require(world.get_path_name().split('.')[0] == MAP, 'Foundation map required')
    require(hasattr(unreal, 'DustfallSurvivalDirector') and hasattr(unreal, 'DustfallSurvivalTuning'),
            'Full native build and editor restart required')
    # Checked against installed 5.8 headers. Fail before mutation if Python
    # bindings differ; Lead may probe them without risking a half migration.
    for owner, names in [(BEL, ('get_blueprint_parent_class', 'list_graphs', 'remove_function_graph',
                               'reparent_blueprint', 'list_member_variable_names')),
                         (unreal.BlueprintGraphEditor, ('remove_member_variable', 'remove_nodes',
                               'list_nodes_with_warnings', 'list_nodes_with_errors', 'list_nodes_with_notes'))]:
        for name in names:
            require(hasattr(owner, name), 'Missing API ' + name + '; stop. Proposed fallback: '
                    'Lead authors a thin native child and replaces the asset at the same path '
                    'in a separate reviewed migration preserving actor references.')
    bp = require(unreal.load_asset(BP), 'Missing survival Blueprint')
    # Validate reflection-only access before any graph/member removal.
    # 'ubergraph_pages' is not exposed to Python in this build (probed live);
    # the legacy Blueprint has exactly one event graph.
    event_graphs = [require(BEL.find_event_graph(bp), 'Expected legacy EventGraph')]
    bp.get_editor_property('status')
    require(hasattr(unreal.BlueprintStatus, 'BS_UP_TO_DATE'), 'Missing BlueprintStatus.BS_UP_TO_DATE')
    old = require(unreal.load_asset(OLD), 'Missing legacy tuning')
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = [a for a in subsystem.get_all_level_actors() if a.get_class() == bp.generated_class()]
    require(len(matches) == 1, 'Exactly one loaded survival actor required; load authoring cells first')
    actor = matches[0]
    actor_path = actor.get_path_name()
    saved_identity = identity(actor)
    require(not saved_identity['spatial'], 'Survival actor must already be always loaded')
    ap = actor_packages(actor)
    require('/__ExternalActors__/' in package(actor).get_path_name(), 'External actor package required')
    targets = {package(bp).get_path_name(), NEW, package(world).get_path_name(), *ap}
    before_dirty = dirty_packages()
    require(not (targets & before_dirty.keys()), 'Resolve existing unsaved target edits first')
    # Capture registry referencers BEFORE the new parent removes old dependencies.
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    refs = sorted(str(n) for n in registry.get_referencers(BP, unreal.AssetRegistryDependencyOptions(
        include_soft_package_references=True, include_hard_package_references=True,
        include_searchable_names=True, include_soft_management_references=True,
        include_hard_management_references=True)))
    require(not (set(refs) & before_dirty.keys()), 'Resolve unsaved referencer edits before compiling')
    report['snapshot'] = dict(cdo=snapshot(unreal.get_default_object(bp.generated_class())),
                              actor=snapshot(actor), identity=saved_identity)
    backup({package(bp).get_path_name(): package(bp), **ap}, report)
    REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
    native_tuning = unreal.load_asset(NEW)
    if native_tuning:
        require(isinstance(native_tuning, unreal.DustfallSurvivalTuning), 'DA_Survival has incorrect class')
    else:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.DustfallSurvivalTuning)
        try:
            native_tuning = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                'DA_Survival', '/Game/Data', unreal.DustfallSurvivalTuning, factory)
        except Exception:
            native_tuning = None
            report['tuning_creation_error'] = traceback.format_exc()
        if native_tuning:
            native_tuning.modify()
            copied = []
            for name in TUNING_FIELDS:
                try:
                    value = old.get_editor_property(name)
                except Exception:
                    continue  # Fields absent on legacy asset keep native defaults.
                native_tuning.set_editor_property(name, value)
                copied.append(name)
            report['copied_tuning_fields'] = copied
        else:
            report['tuning_fallback'] = 'Native asset creation returned None; using LegacyTuning'
    bp.modify()
    native_class = unreal.DustfallSurvivalDirector.static_class()
    if BEL.get_blueprint_parent_class(bp) != native_class:
        event = require(BEL.find_event_graph(bp), 'Expected legacy EventGraph')
        ed = unreal.BlueprintGraphEditor.get_graph_editor(event)
        for name in list(BEL.list_graph_names(bp)):
            if any(str(name) == f or str(name).startswith(f + '_') for f in FUNCTIONS):
                BEL.remove_function_graph(bp, name)
        for event_graph in event_graphs:
            event_editor = unreal.BlueprintGraphEditor.get_graph_editor(event_graph)
            event_editor.remove_nodes(list(event_editor.list_all_nodes()))
            require(not list(event_editor.list_all_nodes()), 'Event-graph nodes remain')
        local = {str(n) for n in BEL.list_member_variable_names(bp, False)}
        for name in VALUES:
            if name in local:
                require(ed.remove_member_variable(name), 'Cannot remove member ' + name)
        require(not ({str(n) for n in BEL.list_member_variable_names(bp, False)} & set(VALUES)),
                'Legacy members remain')
        BEL.reparent_blueprint(bp, native_class)
    require(compile_checked(bp, report), 'Survival Blueprint compile has errors/warnings; see report')
    # Compilation reinstantiates actors. Resolve by original object path, never
    # spawn/delete, and compare the stable actor GUID as well as path/metadata.
    actor = require(unreal.load_object(None, actor_path), 'Actor identity lost during reinstance')
    cdo = unreal.get_default_object(bp.generated_class())
    for label, obj in [('cdo', cdo), ('actor', actor)]:
        obj.modify()
        expected = dict(report['snapshot'][label])
        expected.update(Tuning=encode(native_tuning), LegacyTuning=encode(None if native_tuning else old))
        for name, value in expected.items():
            obj.set_editor_property(name, decode(value))
        report['restored'][label] = expected
    actor.set_editor_property('is_spatially_loaded', False)
    require(identity(actor) == saved_identity, 'Actor identity/label/folder/tags changed')
    for ref in refs:
        entry = dict(package=ref, assets=[])
        report['referencers'].append(entry)
        try:
            for data in registry.get_assets_by_package_name(ref):
                obj = data.get_asset()
                if isinstance(obj, unreal.Blueprint) and obj != bp:
                    entry['assets'].append(dict(asset=obj.get_path_name(), passed=compile_checked(obj, report)))
            entry['status'] = 'failed' if any(not a['passed'] for a in entry['assets']) else 'checked'
        except Exception:
            entry.update(status='failed', error=traceback.format_exc())
    # Recompiling dependents can reinstance the director again. Re-resolve and
    # verify before saving anything, then re-read after explicit targeted saves.
    def verify():
        current = require(unreal.load_object(None, actor_path), 'Missing original actor')
        observed = dict(cdo=snapshot(unreal.get_default_object(bp.generated_class())), actor=snapshot(current))
        checks = {'parent': BEL.get_blueprint_parent_class(bp) == native_class,
                  'identity': identity(current) == saved_identity}
        for label in ('cdo', 'actor'):
            obj = unreal.get_default_object(bp.generated_class()) if label == 'cdo' else current
            for name, value in report['restored'][label].items():
                checks[label + '.' + name] = encode(obj.get_editor_property(name)) == value
        return dict(checks=checks, values=observed, passed=all(checks.values()))
    report['verification'] = verify()
    require(report['verification']['passed'], 'Restored values or references differ before save')
    require(LIB.save_loaded_asset(bp, False), 'Blueprint save failed')
    report['saved_packages'].append(package(bp).get_path_name())
    if native_tuning:
        require(LIB.save_loaded_asset(native_tuning, False), 'Native tuning save failed')
        report['saved_packages'].append(package(native_tuning).get_path_name())
    packages = actor_packages(unreal.load_object(None, actor_path))
    # Reinstancing may fix incoming actor/component references in other external
    # packages. Save those new dirty packages too, never pre-existing user edits.
    for name, obj in dirty_packages().items():
        if name not in before_dirty and ('/__ExternalActors__/' in name or '/__ExternalObjects__/' in name):
            require(name.startswith('/Game/') and '/L_Dustfall_Foundation/' in name,
                    'Unexpected external package modified: ' + name)
            packages[name] = obj
    packages[package(world).get_path_name()] = package(world)
    require(unreal.EditorLoadingAndSavingUtils.save_packages(list(packages.values()), False),
            'External actor/component/map save failed')
    report['saved_packages'].extend(packages)
    require(not (set(report['saved_packages']) & dirty_packages().keys()), 'Saved targets remain dirty')
    report['verification'] = verify()
    report['verification']['scope'] = 'Re-read saved loaded objects; no editor restart/disk reload performed'
    require(report['verification']['passed'], 'Saved value verification failed')
    report['status'] = ('failed: referencer compile errors/warnings' if any(
        r['status'] == 'failed' for r in report['referencers']) else 'built; PIE smoke pending')
    require(not report['status'].startswith('failed'), 'Referencer compilation failed; see report')


if __name__ == '__main__':
    result = dict(status='failed', snapshot={}, restored={}, referencers=[],
                  compile_messages=[], saved_packages=[], verification={})
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        main(result)
    except Exception:
        result.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        REPORT.write_text(json.dumps(result, indent=2), encoding='utf-8')
        unreal.log('M3b-3 report: ' + str(REPORT))
